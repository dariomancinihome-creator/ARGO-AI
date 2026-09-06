from __future__ import annotations
import pandas as pd

def stochastic(df: pd.DataFrame, k_period: int, k_smooth: int, d_period: int):
    low_n = df["Low"].rolling(k_period).min()
    high_n = df["High"].rolling(k_period).max()
    raw_k = 100 * (df["Close"] - low_n) / (high_n - low_n).replace(0, pd.NA)
    k = raw_k.rolling(k_smooth).mean()
    d = k.rolling(d_period).mean()
    return k.astype(float), d.astype(float)
