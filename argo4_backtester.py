from __future__ import annotations
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
    p=df.Close.shift(1)
    tr=pd.concat([df.High-df.Low,(df.High-p).abs(),(df.Low-p).abs()],axis=1).max(axis=1)
    return tr.rolling(n).mean()

def adx(df,n=14):
    up=df.High.diff(); down=-df.Low.diff()
    pdm=pd.Series(np.where((up>down)&(up>0),up,0.),index=df.index)
    mdm=pd.Series(np.where((down>up)&(down>0),down,0.),index=df.index)
    a=atr(df,n)
    pdi=100*pdm.ewm(alpha=1/n,adjust=False).mean()/a
    mdi=100*mdm.ewm(alpha=1/n,adjust=False).mean()/a
    dx=100*(pdi-mdi).abs()/(pdi+mdi).replace(0,np.nan)
    return dx.ewm(alpha=1/n,adjust=False).mean()

def stochastic(df,kp,ks,dp):
    lo=df.Low.rolling(kp).min(); hi=df.High.rolling(kp).max()
    raw=100*(df.Close-lo)/(hi-lo).replace(0,np.nan)
    k=raw.rolling(ks).mean()
    return k,k.rolling(dp).mean()

def zone(v):
    if pd.isna(v): return "N/D"
    lo=int(np.clip(np.floor(v/10)*10,0,90))
    return f"{lo:02d}-{lo+10:02d}"

def prepare(df,cfg):
    x=df.copy()
    x["EMA9"]=ema(x.Close,9); x["EMA21"]=ema(x.Close,21)
    x["EMA9_SLOPE"]=x.EMA9.pct_change()*100
    x["EMA_GAP_PCT"]=(x.EMA9-x.EMA21)/x.Close*100
    x["ATR"]=atr(x); x["ATR_PCT"]=x.ATR/x.Close*100
    x["ADX"]=adx(x); x["ADX_DELTA"]=x.ADX.diff()
    x["K"],x["D"]=stochastic(x,*cfg)
    x["KD_GAP"]=x.K-x.D
    x["K_DELTA"]=x.K.diff()
    x["D_DELTA"]=x.D.diff()
    x["BULL"]=(x.K>x.D)&(x.K.shift(1)<=x.D.shift(1))
    x["BEAR"]=(x.K<x.D)&(x.K.shift(1)>=x.D.shift(1))
    x["RET15"]=x.Close.shift(-1)/x.Close-1
    x["RET30"]=x.Close.shift(-2)/x.Close-1
    return x

def event_rows(df,cfg,asset,ticker):
    x=prepare(df,cfg); rows=[]
    for direction,cross in [("BUY","BULL"),("SELL","BEAR")]:
        s=x[x[cross]].copy()
        sign=1 if direction=="BUY" else -1
        for ts,r in s.iterrows():
            if pd.isna(r.RET15) or pd.isna(r.RET30): continue
            rows.append({
                "Timestamp":ts,"Asset":asset,"Ticker":ticker,
                "Stoch":f"{cfg[0]}-{cfg[1]}-{cfg[2]}","Direction":direction,
                "K":r.K,"D":r.D,"K zone":zone(r.K),"KD gap":r.KD_GAP,
                "K delta":r.K_DELTA,"D delta":r.D_DELTA,
                "EMA9":r.EMA9,"EMA21":r.EMA21,"EMA gap %":r.EMA_GAP_PCT,
                "EMA9 slope %":r.EMA9_SLOPE,
                "EMA aligned": bool((r.EMA9>r.EMA21 and r.EMA9_SLOPE>0) if direction=="BUY"
                                    else (r.EMA9<r.EMA21 and r.EMA9_SLOPE<0)),
                "ADX":r.ADX,"ADX delta":r.ADX_DELTA,"ATR %":r.ATR_PCT,
                "Hour UTC":ts.hour,
                "Move15 %":sign*r.RET15*100,"Move30 %":sign*r.RET30*100,
                "Win15":bool(sign*r.RET15>0),"Win30":bool(sign*r.RET30>0),
            })
    return rows

def run_dna(selected):
    rows=[]; errors=[]; trading_days={}
    for asset in selected:
        ticker=UNIVERSE[asset]
        try:
            df=download_15m(ticker)
            if df.empty:
                errors.append(f"{asset}: nessun dato"); continue
            trading_days[asset]=max(1,pd.Index(df.index.date).nunique())
            for cfg in STOCH_CONFIGS:
                rows += event_rows(df,cfg,asset,ticker)
        except Exception as e:
            errors.append(f"{asset}: {e}")
    events=pd.DataFrame(rows)
    if events.empty: return events,pd.DataFrame(),pd.DataFrame(),errors

    g=events.groupby(["Asset","Stoch","Direction","K zone"],dropna=False)
    zones=g.agg(Signals=("Win15","size"),Win15_pct=("Win15","mean"),
                Win30_pct=("Win30","mean"),Move15_pct=("Move15 %","mean"),
                Median_ADX=("ADX","median"),Median_ATR_pct=("ATR %","median")).reset_index()
    zones["Win15 %"]=zones.Win15_pct*100; zones["Error15 %"]=100-zones["Win15 %"]
    zones["Win30 %"]=zones.Win30_pct*100; zones["Error30 %"]=100-zones["Win30 %"]
    zones["Signals/day"]=zones.apply(lambda r:r.Signals/trading_days.get(r.Asset,1),axis=1)
    zones=zones.drop(columns=["Win15_pct","Win30_pct"])

    h=events.groupby(["Asset","Stoch","Direction","Hour UTC"]).agg(
        Signals=("Win15","size"),Win15=("Win15","mean"),Win30=("Win30","mean")).reset_index()
    h["Win15 %"]=h.Win15*100; h["Error15 %"]=100-h["Win15 %"]; h["Win30 %"]=h.Win30*100
    h=h.drop(columns=["Win15","Win30"])
    return events,zones,h,errors
