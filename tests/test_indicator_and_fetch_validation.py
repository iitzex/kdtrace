import math

import numpy as np
import pandas as pd

from fetch import CNYESFetcher, FetchConfig
from indicator import kd, log_slope_r2, ma, normalized_position


def test_kd_and_ma_smoke():
    dates = pd.date_range("2024-01-01", periods=10, freq="D")
    df = pd.DataFrame(
        {
            "open": range(10, 20),
            "high": range(11, 21),
            "low": range(9, 19),
            "close": range(10, 20),
        },
        index=dates,
    )

    daily, weekly, monthly = kd(df)
    ma_df = ma(df)

    assert list(daily.columns) == ["k", "d"]
    assert list(weekly.columns) == ["wk", "wd"]
    assert list(monthly.columns) == ["mk", "md"]
    assert "w_5" in ma_df.columns
    assert daily.index.equals(df.index)


def test_fetch_validation_rejects_length_mismatch(tmp_path):
    fetcher = CNYESFetcher(FetchConfig(reload=False, cache_dir=str(tmp_path / "json")))
    bad_payload = {
        "data": [
            {
                "time": [1, 2],
                "revenue": [10],
                "revenueYOY": [5, 6],
            }
        ]
    }

    df = fetcher._to_dataframe("1101", "revenue", bad_payload, {"revenue": "revenue", "revenueYOY": "revenueYOY"})

    assert df.empty


def test_fetch_finalize_sorts_dedups_and_numeric_coerces(tmp_path):
    fetcher = CNYESFetcher(FetchConfig(reload=False, cache_dir=str(tmp_path / "json")))
    raw = pd.DataFrame(
        {"eps": ["1.5", "bad", "2.5"], "epsYOY": ["10", "20", "30"]},
        index=pd.to_datetime(["2024-03-31", "2024-03-31", "2023-12-31"]),
    )

    df = fetcher._finalize_dataframe("2330", "eps", raw)

    assert df.index.is_monotonic_increasing
    assert len(df) == 2
    assert pd.isna(df.loc[pd.Timestamp("2024-03-31"), "eps"])


def test_log_slope_r2_rising_series():
    # 指數成長 ~ log 後線性，slope>0 且 R² 接近 1
    s = pd.Series(np.exp(np.linspace(0, 2, 24)))
    slope, r2 = log_slope_r2(s, window=24)
    assert slope > 0
    assert r2 > 0.99


def test_log_slope_r2_flat_returns_nan():
    # 完全 flat → ss_tot=0 → nan（避免除零錯得出假 R²）
    s = pd.Series([100.0] * 24)
    slope, r2 = log_slope_r2(s, window=24)
    assert math.isnan(slope) and math.isnan(r2)


def test_log_slope_r2_rejects_non_positive():
    # log 不吃 0 / 負值，直接回 nan
    s = pd.Series([1.0, 2.0, 0.0, 3.0, 4.0, 5.0])
    slope, r2 = log_slope_r2(s, window=6)
    assert math.isnan(slope) and math.isnan(r2)


def test_log_slope_r2_insufficient_data():
    s = pd.Series([1.0, 2.0])
    slope, r2 = log_slope_r2(s, window=24)
    assert math.isnan(slope) and math.isnan(r2)


def test_normalized_position_rising_near_top():
    s = pd.Series(range(1, 13))
    pos = normalized_position(s, window=12)
    assert pos == 1.0


def test_normalized_position_flat_is_neutral():
    s = pd.Series([5.0] * 8)
    pos = normalized_position(s, window=8)
    assert pos == 0.5


def test_normalized_position_middle():
    s = pd.Series([0.0, 10.0, 5.0])
    pos = normalized_position(s, window=3)
    assert pos == 0.5
