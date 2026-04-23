"""Regression tests：CNYES financialIndicator endpoint 的 `to` 參數必須傳 base_ts（起算點）。

若改回 to_ts（現在），API 會回 200 OK 但陣列全空（silent failure）。
"""
from unittest.mock import MagicMock

import pytest
import requests

from fetch import CNYESFetcher, FetchConfig


def _make_mock_fetcher() -> CNYESFetcher:
    """建立 fetcher 並把 session 替換為 mock，讓 fetch_json 走 HTTP 分支但不真的發請求。"""
    fetcher = CNYESFetcher(FetchConfig(reload=True, cache_dir="/tmp/kdtrace_test_cache"))
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "statusCode": 200,
        "message": "OK",
        "data": [{"time": [1, 2], "revenue": [1, 2], "revenueYOY": [1, 2],
                  "eps": [1, 2], "epsYOY": [1, 2],
                  "grossMargin": [1, 2], "operatingMargin": [1, 2], "profitMargin": [1, 2]}],
    }
    mock_resp.raise_for_status.return_value = None
    fetcher._session = MagicMock()
    fetcher._session.get.return_value = mock_resp
    return fetcher


@pytest.mark.parametrize("method_name", ["get_revenue", "get_profitability", "get_eps"])
def test_financial_indicator_uses_base_ts(method_name: str):
    """revenue / profitability / eps 都必須用 base_ts（5 年前），否則 CNYES 回空陣列。"""
    fetcher = _make_mock_fetcher()
    getattr(fetcher, method_name)("1101")
    call = fetcher._session.get.call_args
    params = call.kwargs["params"]
    assert params["to"] == str(fetcher.base_ts), (
        f"{method_name} 傳 to={params['to']}，應為 base_ts={fetcher.base_ts}；"
        "若傳 to_ts（現在）CNYES 會回 200 OK 但陣列全空，是 silent failure"
    )


def test_investors_uses_to_ts():
    """investors 是不同 endpoint，要傳 to_ts（現在）才不會截斷近期資料（commit 8ec7a84）。"""
    fetcher = _make_mock_fetcher()
    fetcher._session.get.return_value.json.return_value = {
        "data": [{"time": [1, 2], "volumeCharting": [{"foreignVolume": 0}]}]
    }
    fetcher.get_investors("1101")
    params = fetcher._session.get.call_args.kwargs["params"]
    assert params["to"] == str(fetcher.to_ts), "investors 必須用 to_ts"


def test_fetch_json_retries_on_retryable_http_error():
    fetcher = CNYESFetcher(
        FetchConfig(reload=True, cache_dir="/tmp/kdtrace_test_cache", max_retries=3, retry_backoff_seconds=0)
    )
    ok_resp = MagicMock()
    ok_resp.raise_for_status.return_value = None
    ok_resp.json.return_value = {"data": [{"time": [1], "eps": [1], "epsYOY": [2]}]}

    retry_resp = MagicMock()
    retry_resp.raise_for_status.side_effect = requests.HTTPError(
        "502 Server Error",
        response=MagicMock(status_code=502),
    )

    fetcher._session = MagicMock()
    fetcher._session.get.side_effect = [retry_resp, ok_resp]

    data = fetcher.fetch_json("1101", "https://example.com", {}, "eps")

    assert data == {"data": [{"time": [1], "eps": [1], "epsYOY": [2]}]}
    assert fetcher._session.get.call_count == 2
