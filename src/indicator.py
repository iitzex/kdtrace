from typing import Tuple

import numpy as np
import pandas as pd


def calc_kd(df: pd.DataFrame, window: int = 9, k_col: str = 'k', d_col: str = 'd') -> pd.DataFrame:
    """計算 KD 隨機指標。"""
    if df.empty:
        return pd.DataFrame(columns=[k_col, d_col])

    low_min = df['low'].rolling(window=window).min()
    low_min = low_min.fillna(df['low'].expanding().min())
    
    high_max = df['high'].rolling(window=window).max()
    high_max = high_max.fillna(df['high'].expanding().max())
    
    # RSV calculation
    denom = high_max - low_min
    rsv = (df['close'] - low_min) / denom * 100
    rsv = rsv.fillna(50) # Neutral value for flat lines
    
    # EWM with com=2 corresponds to 1/3 smoothing used in common KD
    slowk = rsv.ewm(com=2).mean()
    slowd = slowk.ewm(com=2).mean()
    
    return pd.concat([slowk, slowd], axis=1, keys=[k_col, d_col])

def ma(df: pd.DataFrame, windows: Tuple[int, ...] = (5, 20, 60, 120, 250)) -> pd.DataFrame:
    """計算多個週期的移動平均線。"""
    if 'close' not in df.columns or df.empty:
        return pd.DataFrame()
        
    s = df.close.dropna()
    ma_dict = {f'w_{w}': s.rolling(window=w).mean() for w in windows}
    return pd.DataFrame(ma_dict, index=s.index)

def kd(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """回傳日 / 週 / 月 KD 三個頻率的指標。"""
    # Daily KD
    df_daily = calc_kd(df, window=9, k_col='k', d_col='d')
    
    # Resampling helpers
    ohlc_dict = {'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'}
    
    # Weekly KD
    df_w = df.resample('W-MON', label='left', closed='left').apply(ohlc_dict).dropna()
    df_weekly = calc_kd(df_w, window=6, k_col='wk', d_col='wd')
    
    # Monthly KD
    df_m = df.resample('ME', label='left', closed='left').apply(ohlc_dict).dropna()
    df_monthly = calc_kd(df_m, window=6, k_col='mk', d_col='md')
    
    return df_daily, df_weekly, df_monthly


def log_slope_r2(series: pd.Series, window: int) -> Tuple[float, float]:
    """對 series 最近 window 個點取自然對數後做一次線性迴歸，回 (slope, R²)。

    slope 是 log 空間的斜率，可視為每期的複合成長率近似。
    資料不足、含非正值、或 flat 時回 (nan, nan)。
    """
    s = series.dropna().iloc[-window:]
    if len(s) < max(4, window // 2):
        return (float("nan"), float("nan"))
    if (s <= 0).any():
        return (float("nan"), float("nan"))

    y = np.log(s.to_numpy(dtype=float))
    x = np.arange(len(y), dtype=float)
    slope, intercept = np.polyfit(x, y, 1)
    y_pred = slope * x + intercept
    ss_res = float(np.sum((y - y_pred) ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    if ss_tot <= 0:
        return (float("nan"), float("nan"))
    r2 = 1.0 - ss_res / ss_tot
    return (float(slope), float(r2))


def normalized_position(series: pd.Series, window: int) -> float:
    """最近 window 個點中，當下值在 min~max 區間的相對位置 (0~1)，KD 風格。

    資料 < 2 筆回 nan；區間退化為常數時回 0.5（中性）。
    """
    s = series.dropna().iloc[-window:]
    if len(s) < 2:
        return float("nan")
    lo = float(s.min())
    hi = float(s.max())
    if hi - lo <= 0:
        return 0.5
    return float((s.iloc[-1] - lo) / (hi - lo))
