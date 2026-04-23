import pandas as pd

from fetch import CNYESFetcher, FetchConfig
from indicator import kd, ma


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
