"""股票清單讀取工具。"""
import csv
import logging
from pathlib import Path
from typing import List, Tuple

logger = logging.getLogger(__name__)


def get_list(name: str, bound: int = 0) -> List[Tuple[str, str]]:
    """讀取 {name}.csv；回傳 [(sid, title), ...]。sid 須為數字且 >= bound。"""
    file_path = Path(f"{name}.csv")
    if not file_path.exists():
        logger.error(f"Stock list file {file_path} not found.")
        return []

    stocks: List[Tuple[str, str]] = []
    try:
        with file_path.open("r", encoding="utf-8") as f:
            for row in csv.reader(f):
                if not row or len(row) < 2:
                    continue
                sid = row[0].strip()
                title = row[1].strip()
                if sid.isdigit() and int(sid) >= bound:
                    stocks.append((sid, title))
    except Exception as e:
        logger.error(f"Error reading stock list {name}: {e}")

    return stocks
