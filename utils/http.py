"""HTTP 請求工具：處理舊式站台的 SSL SECLEVEL 與憑證相容性。"""
import logging
from typing import Optional

import requests
import urllib3
from urllib3.util.ssl_ import create_urllib3_context

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)


class CustomHttpAdapter(requests.adapters.HTTPAdapter):
    """降 SSL security level 到 1，支援舊站台的相容性。"""

    def init_poolmanager(self, *args, **kwargs):
        context = create_urllib3_context()
        try:
            context.set_ciphers("DEFAULT@SECLEVEL=1")
        except Exception:
            logger.warning("Could not set SECLEVEL=1, falling back to default.")
        kwargs["ssl_context"] = context
        return super().init_poolmanager(*args, **kwargs)


def get_session() -> requests.Session:
    """回傳掛好 CustomHttpAdapter 的 session。"""
    session = requests.Session()
    session.mount("https://", CustomHttpAdapter())
    return session


def get_request(
    url: str,
    params: Optional[dict] = None,
    headers: Optional[dict] = None,
    timeout: int = 15,
    verify: bool = True,
) -> requests.Response:
    """集中式 HTTP GET；SSL 失敗時對已知舊站台自動 fallback verify=False。"""
    legacy_domains = ["twse.com.tw", "tpex.org.tw", "isin.twse.com.tw"]
    session = get_session()
    try:
        return session.get(url, params=params, headers=headers, timeout=timeout, verify=verify)
    except requests.exceptions.SSLError as e:
        is_legacy = any(d in url for d in legacy_domains)
        is_cert_err = any(err in str(e) for err in ["Missing Subject Key Identifier", "certificate verify failed"])
        if is_legacy or is_cert_err:
            logger.warning(f"SSL issue detected for {url}. Retrying with verify=False...")
            return requests.get(url, params=params, headers=headers, timeout=timeout, verify=False)
        raise
