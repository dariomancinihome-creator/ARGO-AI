from __future__ import annotations
import numpy as np
import pandas as pd
import yfinance as yf

UNIVERSE = {"Bitcoin":"BTC-USD","GBP/USD":"GBPUSD=X"}
STOCH_CONFIG = (8,3,3)

# Test assumptions. GBPUSD uses the published XTB Italy instrument spread as a conservative
# fixed round-trip hurdle. BTC is tested as scenarios because XTB crypto spreads are variable.
XTB = {
    "GBP/USD": {"spread_mode":"absolute", "spread":0.00017, "slippage_bps_each_side":0.5},
    "Bitcoin": {"spread_mode":"percent", "spread_pct":0.22, "slippage_bps_each_side":2.0},
}

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

def stochastic(df,kp=8,ks=3,dp=3):
    lo=df.Low.rolling(kp).min(); hi=df.High.rolling(kp).max()
    raw=100*(df.Close-lo)/(hi-lo).replace(0,np.nan)
    k=raw.rolling(ks).mean()
    return k,k.rolling(dp).mean()

def zone(v):
    if pd.isna(v): return "N/D"
    lo=int(np.clip(np.floor(v/10)*10,0,90))
    return f"{lo:02d}-{lo+10:02d}"

def build_events(asset,ticker):
    df=download_15m(ticker)
    if df.empty: return pd.DataFrame()
    x=df.copy()
    x["K"],x["D"]=stochastic(x)
    x["BULL"]=(x.K>x.D)&(x.K.shift(1)<=x.D.shift(1))
    x["BEAR"]=(x.K<x.D)&(x.K.shift(1)>=x.D.shift(1))
    for n,label in [(1,"15"),(2,"30"),(3,"45"),(4,"60")]:
        x[f"RET{label}"]=x.Close.shift(-n)/x.Close-1

    rows=[]
    for direction,cross in [("BUY","BULL"),("SELL","BEAR")]:
        s=x[x[cross]].copy()
        sign=1 if direction=="BUY" else -1
        for ts,r in s.iterrows():
            if any(pd.isna(r[f"RET{h}"]) for h in ["15","30","45","60"]): continue
            row={"Timestamp":ts,"Asset":asset,"Direction":direction,"K":r.K,"D":r.D,
                 "K zone":zone(r.K),"Entry mid":r.Close}
            for h in ["15","30","45","60"]:
                row[f"Gross move {h}m %"]=sign*r[f"RET{h}"]*100
            rows.append(row)
    return pd.DataFrame(rows)

def cost_pct(asset,entry_mid):
    p=XTB[asset]
    if p["spread_mode"]=="absolute":
        spread_pct=p["spread"]/entry_mid*100
    else:
        spread_pct=p["spread_pct"]
    # slippage is modeled on entry + exit.
    slip_pct=(p["slippage_bps_each_side"]*2)/100
    return spread_pct+slip_pct,spread_pct,slip_pct

def apply_xtb_costs(events):
    out=events.copy()
    costs=out.apply(lambda r:cost_pct(r.Asset,r["Entry mid"]),axis=1)
    out["Spread cost %"]=[x[1] for x in costs]
    out["Slippage allowance %"]=[x[2] for x in costs]
    out["Total hurdle %"]=[x[0] for x in costs]
    for h in ["15","30","45","60"]:
        out[f"Net move {h}m %"]=out[f"Gross move {h}m %"]-out["Total hurdle %"]
        out[f"Net WIN {h}m"]=out[f"Net move {h}m %"]>0
    return out

def dna_filter(df):
    # Only the two structures that survived prior validation.
    return df[
        ((df.Asset=="Bitcoin")&(df.Direction=="BUY")&(df["K zone"]=="10-20")) |
        ((df.Asset=="GBP/USD")&(df.Direction=="SELL")&(df["K zone"]=="70-80"))
    ].copy()

def summarize(df):
    if df.empty: return pd.DataFrame()
    rows=[]
    for (asset,direction,kzone),q in df.groupby(["Asset","Direction","K zone"]):
        days=max(1,pd.Index(q.Timestamp.dt.date).nunique())
        r={"Asset":asset,"Direction":direction,"K zone":kzone,"Signals":len(q),
           "Signals/day":len(q)/days,"Avg hurdle %":q["Total hurdle %"].mean()}
        for h in ["15","30","45","60"]:
            r[f"Gross Win {h}m %"]=(q[f"Gross move {h}m %"]>0).mean()*100
            r[f"Net Win {h}m %"]=q[f"Net WIN {h}m"].mean()*100
            r[f"Avg net {h}m %"]=q[f"Net move {h}m %"].mean()
        rows.append(r)
    return pd.DataFrame(rows)

def run_test5():
    all_events=[]; errors=[]
    for asset,ticker in UNIVERSE.items():
        try:
            e=build_events(asset,ticker)
            if e.empty: errors.append(f"{asset}: nessun dato")
            else: all_events.append(e)
        except Exception as exc: errors.append(f"{asset}: {exc}")
    if not all_events: return pd.DataFrame(),pd.DataFrame(),errors
    events=pd.concat(all_events,ignore_index=True)
    events["Timestamp"]=pd.to_datetime(events["Timestamp"],utc=True)
    events=apply_xtb_costs(events)
    dna=dna_filter(events)
    return dna,summarize(dna),errors
