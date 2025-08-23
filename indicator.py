import pandas as pd
import numpy as np


def calc_kd(df: pd.DataFrame, window: int, k_col: str, d_col: str) -> pd.DataFrame:
    low_list = df['low'].rolling(window=window, center=False).min()
    low_list.fillna(df['low'].expanding(min_periods=1).min(), inplace=True)
    high_list = df['high'].rolling(window=window, center=False).max()
    high_list.fillna(df['high'].expanding(min_periods=1).max(), inplace=True)
    rsv = (df['close'] - low_list) / (high_list - low_list) * 100
    slowk = rsv.ewm(com=2).mean()
    slowd = slowk.ewm(com=2).mean()
    return pd.concat([slowk, slowd], axis=1, keys=[k_col, d_col])


def D_KD(df: pd.DataFrame) -> pd.DataFrame:
    return calc_kd(df, window=9, k_col='k', d_col='d')


def W_KD(df: pd.DataFrame) -> pd.DataFrame:
    ohlc_dict = {'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'}
    df_w = df.resample('W-Mon', label='left',
                       closed='left').apply(ohlc_dict).dropna()
    return calc_kd(df_w, window=6, k_col='wk', d_col='wd')


def M_KD(df: pd.DataFrame) -> pd.DataFrame:
    ohlc_dict = {'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'}
    df_m = df.resample('ME', label='left', closed='left').apply(
        ohlc_dict).dropna()
    return calc_kd(df_m, window=6, k_col='mk', d_col='md')


def month_mean(df: pd.DataFrame) -> pd.DataFrame:
    ohlc_dict = {col: np.mean for col in ['open', 'high', 'low', 'close']}
    df_m = df.resample('M', label='left', closed='left').apply(
        ohlc_dict).dropna()
    return df_m


def ma(df: pd.DataFrame) -> pd.DataFrame:
    s = df.close.dropna()
    ma_dict = {
        'w_5': s.rolling(window=5).mean(),
        'w_20': s.rolling(window=20).mean(),
        'w_60': s.rolling(window=60).mean(),
        'w_120': s.rolling(window=120).mean(),
        'w_250': s.rolling(window=250).mean()
    }
    return pd.DataFrame(ma_dict)


def kd(df: pd.DataFrame):
    pd.options.display.float_format = '{:,.2f}'.format

    return D_KD(df), W_KD(df), M_KD(df)
