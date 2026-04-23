from typing import Tuple

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
    df_w = df.resample('W-Mon', label='left', closed='left').apply(ohlc_dict).dropna()
    df_weekly = calc_kd(df_w, window=6, k_col='wk', d_col='wd')
    
    # Monthly KD
    df_m = df.resample('ME', label='left', closed='left').apply(ohlc_dict).dropna()
    df_monthly = calc_kd(df_m, window=6, k_col='mk', d_col='md')
    
    return df_daily, df_weekly, df_monthly
