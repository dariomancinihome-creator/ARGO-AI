from __future__ import annotations
import math
import numpy as np
import pandas as pd
import yfinance as yf

UNIVERSE = {
    "EUR/USD":"EURUSD=X","GBP/USD":"GBPUSD=X","USD/JPY":"JPY=X",
    "Gold":"GC=F","Silver":"SI=F","Nasdaq 100":"NQ=F","S&P 500":"ES=F",
    "DAX":"FDAX.DE","Bitcoin":"BTC-USD","Ethereum":"ETH-USD",
    "NVIDIA":"NVDA","Tesla":"TSLA","Amazon":"AMZN","Meta":"META",
    "AMD":"AMD","Apple":"AAPL",
}
STOCH_CONFIGS=[(5,3,3),(8,3,3),(10,5,5)]

def download_15m(ticker):
    df=yf.download(ticker,period="1mo",interval="15m",auto_adjust=True,
                   progress=False,threads=False,multi_level_index=False,prepost=False)
    if df is None or df.empty: return pd.DataFrame()
    if isinstance(df.columns,pd.MultiIndex):
        df.columns=[c[0] if isinstance(c,tuple) else c for c in df.columns]
    for c in ["Open","High","Low","Close","Volume"]:
        if c not in df: df[c]=np.nan
        df[c]=pd.to_numeric(df[c],errors="coerce")
    return df[["Open","High","Low","Close","Volume"]].dropna(subset=["High","Low","Close"])

def ema(s,n): return s.ewm(span=n,adjust=False).mean()

def atr(df,n=14):
    p=df["Close"].shift(1)
    tr=pd.concat([df["High"]-df["Low"],(df["High"]-p).abs(),(df["Low"]-p).abs()],axis=1).max(axis=1)
    return tr.rolling(n).mean()

def adx(df,n=14):
    up=df["High"].diff(); down=-df["Low"].diff()
    pdm=pd.Series(np.where((up>down)&(up>0),up,0.),index=df.index)
    mdm=pd.Series(np.where((down>up)&(down>0),down,0.),index=df.index)
    a=atr(df,n)
    pdi=100*pdm.ewm(alpha=1/n,adjust=False).mean()/a
    mdi=100*mdm.ewm(alpha=1/n,adjust=False).mean()/a
    dx=100*(pdi-mdi).abs()/(pdi+mdi).replace(0,np.nan)
    return dx.ewm(alpha=1/n,adjust=False).mean()

def stochastic(df,kp,ks,dp):
    lo=df["Low"].rolling(kp).min(); hi=df["High"].rolling(kp).max()
    raw=100*(df["Close"]-lo)/(hi-lo).replace(0,np.nan)
    k=raw.rolling(ks).mean(); d=k.rolling(dp).mean()
    return k,d

def prepare(df,cfg):
    x=df.copy()
    x["EMA9"]=ema(x.Close,9); x["EMA21"]=ema(x.Close,21)
    x["EMA9_SLOPE"]=x.EMA9.pct_change()
    x["ATR"]=atr(x); x["ATR_PCT"]=x.ATR/x.Close*100
    x["ADX"]=adx(x); x["ADX_DELTA"]=x.ADX.diff()
    x["K"],x["D"]=stochastic(x,*cfg)
    x["BULL"]=(x.K>x.D)&(x.K.shift(1)<=x.D.shift(1))
    x["BEAR"]=(x.K<x.D)&(x.K.shift(1)>=x.D.shift(1))
    x["RET15"]=x.Close.shift(-1)/x.Close-1
    x["RET30"]=x.Close.shift(-2)/x.Close-1
    return x

def evaluate(df,cfg,asset,ticker):
    x=prepare(df,cfg)
    atr_cut=x.ATR_PCT.quantile(.40)
    rows=[]
    for direction,cross in [("BUY","BULL"),("SELL","BEAR")]:
        s=x[x[cross]].copy()
        if s.empty: continue
        if direction=="BUY":
            s["EMA_OK"]=(s.EMA9>s.EMA21)&(s.EMA9_SLOPE>0)
        else:
            s["EMA_OK"]=(s.EMA9<s.EMA21)&(s.EMA9_SLOPE<0)
        s["ADX_OK"]=(s.ADX>=18)&(s.ADX_DELTA>0)
        s["ATR_OK"]=s.ATR_PCT>=atr_cut
        sign=1 if direction=="BUY" else -1
        s["WIN15"]=sign*s.RET15>0; s["WIN30"]=sign*s.RET30>0
        s["MOVE15"]=sign*s.RET15*100; s["MOVE30"]=sign*s.RET30*100

        levels=[
            ("1 Stoch puro", pd.Series(True,index=s.index)),
            ("2 + EMA", s.EMA_OK),
            ("3 + EMA + ADX", s.EMA_OK&s.ADX_OK),
            ("4 + EMA + ADX + ATR", s.EMA_OK&s.ADX_OK&s.ATR_OK),
        ]
        base_n=len(s)
        for mode,mask in levels:
            q=s[mask].dropna(subset=["RET15","RET30"])
            if q.empty: continue
            # denominator is trading days represented by the downloaded sample,
            # so filters are comparable on the same time base.
            all_days=max(1,pd.Index(x.index.date).nunique())
            err15=100*(1-q.WIN15.mean())
            err30=100*(1-q.WIN30.mean())
            rows.append({
                "Asset":asset,"Ticker":ticker,"Stoch":f"{cfg[0]}-{cfg[1]}-{cfg[2]}",
                "Direction":direction,"Filter level":mode,"Signals":len(q),
                "Signals/day":len(q)/all_days,
                "Win15 %":q.WIN15.mean()*100,"Error15 %":err15,
                "Win30 %":q.WIN30.mean()*100,"Error30 %":err30,
                "Move15 %":q.MOVE15.mean(),"Move30 %":q.MOVE30.mean(),
                "Signals retained %":100*len(q)/base_n,
                "Signals removed %":100*(1-len(q)/base_n),
                "Median ADX":q.ADX.median(),"Median ATR %":q.ATR_PCT.median(),
            })
    return rows

def run_lab(selected=None):
    rows=[]; errors=[]
    for asset in (selected or list(UNIVERSE)):
        ticker=UNIVERSE[asset]
        try:
            df=download_15m(ticker)
            if df.empty:
                errors.append(f"{asset}: nessun dato"); continue
            for cfg in STOCH_CONFIGS: rows += evaluate(df,cfg,asset,ticker)
        except Exception as e: errors.append(f"{asset}: {e}")
    r=pd.DataFrame(rows)
    if not r.empty:
        # Efficiency: reward low error and useful frequency; do not over-reward tiny samples.
        sample_factor=np.minimum(1,r["Signals"]/20)
        r["Efficiency score"]=(
            (100-r["Error15 %"])*.55+(100-r["Error30 %"])*.15+
            np.minimum(r["Signals/day"],8)/8*20+
            r["Signals retained %"]*.10
        )*sample_factor
        r=r.sort_values(["Efficiency score","Signals"],ascending=False).reset_index(drop=True)
    return r,errors

def filter_impact(result):
    if result.empty: return result
    keys=["Asset","Stoch","Direction"]
    base=result[result["Filter level"]=="1 Stoch puro"][keys+["Signals","Error15 %"]].rename(
        columns={"Signals":"Base signals","Error15 %":"Base error %"})
    out=result.merge(base,on=keys,how="left")
    out["Errors reduced pp"]=out["Base error %"]-out["Error15 %"]
    out["Signals sacrificed"]=out["Base signals"]-out["Signals"]
    out["pp error reduction / 10% signals lost"]=np.where(
        out["Signals removed %"]>0,
        out["Errors reduced pp"]/(out["Signals removed %"]/10),np.nan)
    return out
