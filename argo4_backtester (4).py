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

STOCH_CONFIGS = [(5,3,3), (8,3,3), (10,5,5)]


def download_15m(ticker: str) -> pd.DataFrame:
    df = yf.download(
        ticker,
        period="1mo",
        interval="15m",
        auto_adjust=True,
        progress=False,
        threads=False,
        multi_level_index=False,
        prepost=False,
    )
    if df is None or df.empty:
        return pd.DataFrame()

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]

    for col in ["Open", "High", "Low", "Close", "Volume"]:
        if col not in df.columns:
            df[col] = np.nan
        df[col] = pd.to_numeric(df[col], errors="coerce")

    return df[["Open","High","Low","Close","Volume"]].dropna(
        subset=["High","Low","Close"]
    ).copy()


def ema(series: pd.Series, n: int) -> pd.Series:
    return series.ewm(span=n, adjust=False).mean()


def atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    prev_close = df["Close"].shift(1)
    tr = pd.concat([
        df["High"] - df["Low"],
        (df["High"] - prev_close).abs(),
        (df["Low"] - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.rolling(n).mean()


def adx(df: pd.DataFrame, n: int = 14) -> pd.Series:
    up = df["High"].diff()
    down = -df["Low"].diff()

    plus_dm = pd.Series(
        np.where((up > down) & (up > 0), up, 0.0),
        index=df.index
    )
    minus_dm = pd.Series(
        np.where((down > up) & (down > 0), down, 0.0),
        index=df.index
    )

    a = atr(df, n)
    plus_di = 100 * plus_dm.ewm(alpha=1/n, adjust=False).mean() / a
    minus_di = 100 * minus_dm.ewm(alpha=1/n, adjust=False).mean() / a

    denom = (plus_di + minus_di).replace(0, np.nan)
    dx = 100 * (plus_di - minus_di).abs() / denom
    return dx.ewm(alpha=1/n, adjust=False).mean()


def stochastic(df: pd.DataFrame, k_period: int, k_smooth: int, d_period: int):
    low_n = df["Low"].rolling(k_period).min()
    high_n = df["High"].rolling(k_period).max()

    raw = 100 * (df["Close"] - low_n) / (high_n - low_n).replace(0, np.nan)
    k = raw.rolling(k_smooth).mean()
    d = k.rolling(d_period).mean()
    return k, d


def stoch_zone(value) -> str:
    if pd.isna(value):
        return "N/D"
    lo = int(np.clip(np.floor(float(value) / 10) * 10, 0, 90))
    return f"{lo:02d}-{lo+10:02d}"


def prepare(df: pd.DataFrame, cfg: tuple[int,int,int]) -> pd.DataFrame:
    x = df.copy()

    x["EMA9"] = ema(x["Close"], 9)
    x["EMA21"] = ema(x["Close"], 21)
    x["EMA9_SLOPE"] = x["EMA9"].pct_change() * 100
    x["EMA_GAP_PCT"] = (x["EMA9"] - x["EMA21"]) / x["Close"] * 100

    x["ATR"] = atr(x, 14)
    x["ATR_PCT"] = x["ATR"] / x["Close"] * 100

    x["ADX"] = adx(x, 14)
    x["ADX_DELTA"] = x["ADX"].diff()

    x["K"], x["D"] = stochastic(x, *cfg)
    x["KD_GAP"] = x["K"] - x["D"]
    x["K_DELTA"] = x["K"].diff()

    x["BULL_CROSS"] = (
        (x["K"] > x["D"]) &
        (x["K"].shift(1) <= x["D"].shift(1))
    )
    x["BEAR_CROSS"] = (
        (x["K"] < x["D"]) &
        (x["K"].shift(1) >= x["D"].shift(1))
    )

    x["RET15"] = x["Close"].shift(-1) / x["Close"] - 1
    x["RET30"] = x["Close"].shift(-2) / x["Close"] - 1

    return x


def build_events(df: pd.DataFrame, cfg, asset: str, ticker: str) -> list[dict]:
    x = prepare(df, cfg)
    rows = []

    for direction, cross_col in [("BUY","BULL_CROSS"),("SELL","BEAR_CROSS")]:
        sig = x[x[cross_col]].copy()
        sign = 1 if direction == "BUY" else -1

        for ts, row in sig.iterrows():
            if pd.isna(row["RET15"]) or pd.isna(row["RET30"]):
                continue

            ema_aligned = (
                (row["EMA9"] > row["EMA21"] and row["EMA9_SLOPE"] > 0)
                if direction == "BUY"
                else
                (row["EMA9"] < row["EMA21"] and row["EMA9_SLOPE"] < 0)
            )

            rows.append({
                "Timestamp": ts,
                "Asset": asset,
                "Ticker": ticker,
                "Stoch": f"{cfg[0]}-{cfg[1]}-{cfg[2]}",
                "Direction": direction,
                "K": row["K"],
                "D": row["D"],
                "K zone": stoch_zone(row["K"]),
                "KD gap": row["KD_GAP"],
                "K delta": row["K_DELTA"],
                "EMA aligned": bool(ema_aligned),
                "EMA gap %": row["EMA_GAP_PCT"],
                "EMA9 slope %": row["EMA9_SLOPE"],
                "ADX": row["ADX"],
                "ADX delta": row["ADX_DELTA"],
                "ATR %": row["ATR_PCT"],
                "Hour UTC": ts.hour,
                "Move15 %": sign * row["RET15"] * 100,
                "Move30 %": sign * row["RET30"] * 100,
                "Win15": bool(sign * row["RET15"] > 0),
                "Win30": bool(sign * row["RET30"] > 0),
            })

    return rows


def _rule_candidates(train: pd.DataFrame, min_train_signals: int = 15) -> pd.DataFrame:
    """
    Discover candidate DNA rules ONLY on the training sample.
    Rules intentionally remain simple to reduce overfitting:
    Asset + Stoch + Direction + K zone, optionally EMA aligned state.
    """
    candidates = []

    # Base DNA: zone only
    g1 = train.groupby(["Asset","Stoch","Direction","K zone"], dropna=False)
    for keys, q in g1:
        if len(q) < min_train_signals:
            continue
        candidates.append({
            "Asset": keys[0],
            "Stoch": keys[1],
            "Direction": keys[2],
            "K zone": keys[3],
            "EMA state": "ANY",
            "Train signals": len(q),
            "Train Win15 %": q["Win15"].mean() * 100,
            "Train Win30 %": q["Win30"].mean() * 100,
            "Train Move15 %": q["Move15 %"].mean(),
        })

    # Refined DNA: zone + EMA alignment
    g2 = train.groupby(
        ["Asset","Stoch","Direction","K zone","EMA aligned"],
        dropna=False
    )
    for keys, q in g2:
        if len(q) < min_train_signals:
            continue
        candidates.append({
            "Asset": keys[0],
            "Stoch": keys[1],
            "Direction": keys[2],
            "K zone": keys[3],
            "EMA state": "ALIGNED" if bool(keys[4]) else "NOT_ALIGNED",
            "Train signals": len(q),
            "Train Win15 %": q["Win15"].mean() * 100,
            "Train Win30 %": q["Win30"].mean() * 100,
            "Train Move15 %": q["Move15 %"].mean(),
        })

    result = pd.DataFrame(candidates)

    if result.empty:
        return result

    # Ranking uses accuracy + sample size; not pure win-rate.
    sample_bonus = np.minimum(result["Train signals"], 50) / 50 * 10
    result["Discovery score"] = (
        result["Train Win15 %"] * 0.70
        + result["Train Win30 %"] * 0.20
        + sample_bonus
    )

    return result.sort_values(
        ["Discovery score","Train signals"],
        ascending=False
    ).reset_index(drop=True)


def _apply_rule(test: pd.DataFrame, rule: pd.Series) -> pd.DataFrame:
    mask = (
        (test["Asset"] == rule["Asset"]) &
        (test["Stoch"] == rule["Stoch"]) &
        (test["Direction"] == rule["Direction"]) &
        (test["K zone"] == rule["K zone"])
    )

    if rule["EMA state"] == "ALIGNED":
        mask &= test["EMA aligned"] == True
    elif rule["EMA state"] == "NOT_ALIGNED":
        mask &= test["EMA aligned"] == False

    return test[mask].copy()


def validate_rules(events: pd.DataFrame,
                   train_fraction: float = 0.70,
                   min_train_signals: int = 15,
                   min_test_signals: int = 5):
    if events.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    events = events.sort_values("Timestamp").reset_index(drop=True)

    split_index = int(len(events) * train_fraction)
    split_index = max(1, min(split_index, len(events)-1))

    train = events.iloc[:split_index].copy()
    test = events.iloc[split_index:].copy()

    candidates = _rule_candidates(
        train,
        min_train_signals=min_train_signals
    )

    results = []

    for _, rule in candidates.iterrows():
        q = _apply_rule(test, rule)

        test_signals = len(q)

        if test_signals:
            test_win15 = q["Win15"].mean() * 100
            test_win30 = q["Win30"].mean() * 100
            test_move15 = q["Move15 %"].mean()
        else:
            test_win15 = np.nan
            test_win30 = np.nan
            test_move15 = np.nan

        results.append({
            **rule.to_dict(),
            "Test signals": test_signals,
            "Test Win15 %": test_win15,
            "Test Win30 %": test_win30,
            "Test Move15 %": test_move15,
            "Win15 degradation pp": (
                rule["Train Win15 %"] - test_win15
                if test_signals else np.nan
            ),
            "Pass sample": test_signals >= min_test_signals,
        })

    validated = pd.DataFrame(results)

    if not validated.empty:
        validated["Stable"] = (
            (validated["Pass sample"]) &
            (validated["Test Win15 %"] >= 55) &
            (validated["Win15 degradation pp"] <= 12)
        )

        validated["Validation score"] = np.where(
            validated["Pass sample"],
            validated["Test Win15 %"] * 0.55
            + validated["Train Win15 %"] * 0.20
            + validated["Test Win30 %"].fillna(0) * 0.10
            + np.minimum(validated["Test signals"], 25) / 25 * 10
            - validated["Win15 degradation pp"].clip(lower=0) * 0.25,
            0
        )

        validated = validated.sort_values(
            ["Stable","Validation score","Test signals"],
            ascending=[False,False,False]
        ).reset_index(drop=True)

    return train, test, validated


def run_validation(selected_assets: list[str]):
    events_rows = []
    errors = []

    for asset in selected_assets:
        ticker = UNIVERSE[asset]
        try:
            df = download_15m(ticker)
            if df.empty:
                errors.append(f"{asset}: nessun dato")
                continue

            for cfg in STOCH_CONFIGS:
                events_rows += build_events(df, cfg, asset, ticker)

        except Exception as exc:
            errors.append(f"{asset}: {exc}")

    events = pd.DataFrame(events_rows)

    if events.empty:
        return events, pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), errors

    train, test, validated = validate_rules(events)

    return events, train, test, validated, errors
