"""utils 套件的最小 smoke tests。"""
import logging

from utils.logger import setup_logger
from utils.stocks import get_list


def test_setup_logger_is_idempotent():
    """setup_logger 多次呼叫只應生效一次（避免重複 handler）。"""
    root = logging.getLogger()
    before = len(root.handlers)
    setup_logger()
    setup_logger()
    setup_logger()
    after = len(root.handlers)
    # 呼叫後 handler 數量不應該線性增加
    assert after - before <= 1


def test_get_list_missing_file_returns_empty(tmp_path, monkeypatch):
    """檔案不存在時回空 list，不丟例外。"""
    monkeypatch.chdir(tmp_path)
    assert get_list("nonexistent") == []


def test_get_list_parses_and_validates(tmp_path, monkeypatch):
    """只回傳 sid 是數字且 >= bound 的 rows。"""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "sample.csv").write_text(
        "1101,台泥\n"
        "2330,台積電\n"
        "abc,非數字應被濾掉\n"
        ",空 sid 應被濾掉\n",
        encoding="utf-8",
    )
    result = get_list("sample")
    assert result == [("1101", "台泥"), ("2330", "台積電")]


def test_get_list_bound_filter(tmp_path, monkeypatch):
    """bound 參數篩掉 sid < bound 的項目。"""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "sample.csv").write_text("1000,A\n2000,B\n3000,C\n", encoding="utf-8")
    result = get_list("sample", bound=2000)
    assert [sid for sid, _ in result] == ["2000", "3000"]


def test_get_session_reuses_adapter():
    """get_session 回傳掛 CustomHttpAdapter 的 session；連續呼叫產生獨立 session。"""
    from utils.http import CustomHttpAdapter, get_session
    s1 = get_session()
    s2 = get_session()
    assert s1 is not s2  # 每次呼叫都是新 session
    adapter = s1.get_adapter("https://example.com")
    assert isinstance(adapter, CustomHttpAdapter)
