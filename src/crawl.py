import csv
import logging
import os
import random
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional

from utils import get_request, setup_logger


@dataclass
class CrawlConfig:
    """爬蟲設定。"""
    prefix: str = "data"
    max_retries: int = 5
    min_sleep: int = 1
    max_sleep: int = 5
    tse_url_template: str = "https://www.twse.com.tw/exchangeReport/MI_INDEX?response=json&date={date}&type=ALLBUT0999"
    otc_url_template: str = "http://www.tpex.org.tw/web/stock/aftertrading/otc_quotes_no1430/stk_wn1430_result.php?l=zh-tw&d={date_tw}&sect=EW&_={ts}"


class DataRecorder:
    """把爬到的資料寫入各股票的 CSV 檔。"""

    def __init__(self, prefix: str):
        self.prefix = prefix
        if not os.path.isdir(prefix):
            os.makedirs(prefix)

    def record(self, stock_id: str, row: List[str]):
        """將一列資料 append 到對應股票的 CSV。"""
        file_path = os.path.join(self.prefix, f"{stock_id}.csv")
        file_exists = os.path.isfile(file_path)
        
        with open(file_path, "a", encoding="utf-8", newline="") as f:
            cw = csv.writer(f)
            if not file_exists or os.path.getsize(file_path) == 0:
                cw.writerow(["date", "amount", "volume", "open", "high", "low", "close", "diff", "number"])
            cw.writerow(row)


class Crawler:
    """爬取股價資料的主類別。"""

    def __init__(self, config: Optional[CrawlConfig] = None):
        self.config = config or CrawlConfig()
        self.recorder = DataRecorder(self.config.prefix)

    def _clean_row(self, row: List[str]) -> List[str]:
        """清除欄位中的逗號與空白。"""
        return [content.replace(",", "").strip() for content in row]

    def fetch_tse_data(self, date_str: str):
        """抓指定日期的上市股票資料並寫入 CSV。"""
        dstr = date_str.replace("-", "")
        url = self.config.tse_url_template.format(date=dstr)

        try:
            response = get_request(url)
            if response.status_code != 200:
                logging.error(f"Failed to fetch TSE data for {date_str}: HTTP {response.status_code}")
                return

            data = response.json()
            if data.get("stat") != "OK":
                logging.info(f"TSE status not OK for {date_str}: {data.get('stat')}")
                return

            # Indices for TSE data in j['tables'][8]['data' or similar]
            # Based on original code: j['tables'][8]['data']
            # Note: The table index might vary, but we keep the logic from the original version.
            tables = data.get('tables', [])
            if len(tables) <= 8:
                logging.warning(f"Unexpected TSE data structure for {date_str}")
                return

            for item in tables[8].get('data', []):
                # item[0]: stock_id, item[1]: name, 
                # item[2]: 成交股數, item[4]: 成交金額
                # item[5]: 開盤價, item[6]: 最高價, item[7]: 最低價, item[8]: 收盤價
                # item[9]: 漲跌符號, item[10]: 漲跌價差, item[3]: 成交筆數
                sign = "-" if "-" in item[9] else ""
                row = self._clean_row([
                    date_str,            # 日期
                    item[2][:-4] if len(item[2]) > 4 else "0",  # 成交股數 (去除後四位，假設為仟股)
                    item[4],             # 成交金額
                    item[5],             # 開盤價
                    item[6],             # 最高價
                    item[7],             # 最低價
                    item[8],             # 收盤價
                    sign + item[10],     # 漲跌價差
                    item[3],             # 成交筆數
                ])
                self.recorder.record(item[0], row)
        except Exception as e:
            logging.error(f"Error processing TSE data for {date_str}: {e}")

    def fetch_otc_data(self, date_str: str, date_str_tw: str):
        """上櫃資料抓取（尚未實作，保留 hook）。"""
        pass

    def crawl_date(self, dt: datetime):
        """抓指定日期的全部資料。"""
        date_str = dt.strftime("%Y-%m-%d")
        logging.info(f"Crawling {date_str}")
        self.fetch_tse_data(date_str)


def get_latest_crawled_date(csv_path: str) -> Optional[datetime]:
    """從參考 CSV 找出目前已爬到的最新日期。"""
    if not os.path.exists(csv_path):
        return None
    
    try:
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            dates = []
            for row in reader:
                d_str = row.get("date")
                if d_str and len(d_str) == 10:
                    try:
                        dates.append(datetime.strptime(d_str, "%Y-%m-%d"))
                    except ValueError:
                        continue
            return max(dates) if dates else None
    except Exception as e:
        logging.error(f"Error reading {csv_path}: {e}")
        return None


def run():
    """爬蟲 CLI 進入點。"""
    parser = argparse.ArgumentParser(description="KDTrace Stock Data Crawler")
    parser.add_argument("--begin", help="Begin date (YYYY-MM-DD)")
    parser.add_argument("--end", help="End date (YYYY-MM-DD)")
    parser.add_argument("--date", help="Single date to crawl (YYYY-MM-DD)")
    args = parser.parse_args()

    setup_logger()

    if args.date:
        begin = datetime.strptime(args.date, "%Y-%m-%d")
        end = begin
    elif args.begin:
        begin = datetime.strptime(args.begin, "%Y-%m-%d")
        end = datetime.strptime(args.end, "%Y-%m-%d") if args.end else datetime.today()
    else:
        # Default auto-catchup logic
        reference_csv = os.path.join("data", "0050.csv")
        latest_date = get_latest_crawled_date(reference_csv)
        if latest_date:
            begin = latest_date + timedelta(days=1)
        else:
            begin = datetime.today() - timedelta(days=30)
        end = datetime.today()

    # Normalize to midnight
    begin = begin.replace(hour=0, minute=0, second=0, microsecond=0)
    end = end.replace(hour=0, minute=0, second=0, microsecond=0)

    logging.info(f"Crawl Range: {begin.date()} to {end.date()}")

    crawler = Crawler()
    current = begin
    error_count = 0
    max_errors = 5

    while current <= end and error_count < max_errors:
        try:
            crawler.crawl_date(current)
            # Random sleep to avoid being blocked
            time.sleep(random.randint(crawler.config.min_sleep, crawler.config.max_sleep))
            error_count = 0 
        except Exception as e:
            logging.error(f"Failed to crawl {current.date()}: {e}")
            error_count += 1
        finally:
            current += timedelta(days=1)

    if error_count >= max_errors:
        logging.critical("Too many consecutive errors. Exiting.")


if __name__ == "__main__":
    import argparse
    run()
