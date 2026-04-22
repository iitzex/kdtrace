"""集中管理 logging 設定；所有 CLI entry 在 main 內呼叫一次 setup_logger()。"""
import logging

_CONFIGURED = False


def setup_logger(level: int = logging.INFO) -> None:
    """設定 root logger；冪等，多次呼叫只會生效第一次。"""
    global _CONFIGURED
    if _CONFIGURED:
        return
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )
    _CONFIGURED = True
