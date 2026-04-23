import argparse
import logging
import os
import re
from dataclasses import dataclass
from typing import List, Set

from bs4 import BeautifulSoup, Tag

from utils import get_request, setup_logger

logger = logging.getLogger(__name__)


@dataclass
class StockInfo:
    """Represents a single stock's basic information."""
    sid: str
    name: str

    def to_csv_row(self) -> str:
        return f"{self.sid},{self.name}\n"


class StockListGenerator:
    """Generates and maintains a list of active stocks from TWSE."""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.tse_url = "https://isin.twse.com.tw/isin/C_public.jsp?strMode=2"
        # self.otc_url = "https://isin.twse.com.tw/isin/C_public.jsp?strMode=4"

    def _parse_html(self, content: bytes) -> List[StockInfo]:
        """Parses the ISIN HTML content to extract stock information."""
        # Using lxml as the primary parser, falling back to html.parser if needed
        try:
            soup = BeautifulSoup(content.decode('Big5-HKSCS', errors='backslashreplace'), "lxml")
        except Exception:
            logging.warning("lxml not found, falling back to html.parser")
            soup = BeautifulSoup(content.decode('Big5-HKSCS', errors='backslashreplace'), "html.parser")

        stocks: List[StockInfo] = []
        for row in soup.find_all('tr'):
            if not isinstance(row, Tag):
                continue
            
            columns = row.find_all('td')
            if len(columns) < 6:
                continue
            
            # Filter for specific product type if necessary (e.g., 'ESVUFR' for common stocks)
            if columns[5].text.strip() == 'ESVUFR':
                text_content = columns[0].text.strip()
                # Matches "StockID Name" pattern (e.g., "1101　台泥")
                match = re.search(r"(\d{4,6})\s+(.*)", text_content)
                if match:
                    sid = match.group(1)
                    name = match.group(2).strip()
                    stocks.append(StockInfo(sid=sid, name=name))
        
        return stocks

    def fetch_stock_list(self) -> List[StockInfo]:
        """Fetches the latest stock list from the TSE website."""
        logging.info(f"Fetching stock list from {self.tse_url}...")
        try:
            response = get_request(self.tse_url)
            if response.status_code == 200:
                logging.info("Successfully fetched content (HTTP 200)")
                return self._parse_html(response.content)
            else:
                logging.error(f"Failed to fetch content: HTTP {response.status_code}")
        except Exception as e:
            logging.error(f"Error during fetch/parse: {e}")
        
        return []

    def save_list(self, stocks: List[StockInfo], filename: str = "tse.csv") -> None:
        """Saves the extracted stock list to a CSV file."""
        logging.info(f"Writing {len(stocks)} entries to {filename}...")
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                for stock in stocks:
                    f.write(stock.to_csv_row())
        except Exception as e:
            logging.error(f"Failed to write to {filename}: {e}")

    def cleanup_obsolete_data(self, current_stocks: List[StockInfo], dry_run: bool = False) -> None:
        """Deletes CSV files in data_dir for stocks no longer in the current list.

        dry_run=True 只列出會被刪除的檔案，不實際刪除。
        """
        if not os.path.isdir(self.data_dir):
            logging.warning(f"Data directory '{self.data_dir}' does not exist. Skipping cleanup.")
            return

        prefix = "[DRY-RUN] Would clean" if dry_run else "Starting cleanup of"
        logging.info(f"{prefix} obsolete data in '{self.data_dir}'...")
        current_ids: Set[str] = {stock.sid for stock in current_stocks}

        # Reference files that should never be deleted
        protected_files = {"0050"}

        existing_files = [f for f in os.listdir(self.data_dir) if f.endswith(".csv")]
        target_files = [
            f for f in existing_files
            if f.replace(".csv", "") not in current_ids
            and f.replace(".csv", "") not in protected_files
        ]

        if not target_files:
            logging.info("No obsolete files found.")
            return

        if dry_run:
            logging.info(f"[DRY-RUN] {len(target_files)} files would be deleted:")
            for f in target_files[:20]:
                logging.info(f"  - {f}")
            if len(target_files) > 20:
                logging.info(f"  ... and {len(target_files) - 20} more")
            return

        deleted_count = 0
        for file_name in target_files:
            file_path = os.path.join(self.data_dir, file_name)
            try:
                os.remove(file_path)
                deleted_count += 1
                logging.debug(f"Deleted obsolete data: {file_name}")
            except Exception as e:
                logging.error(f"Error deleting {file_name}: {e}")

        logging.info(f"Cleanup complete. Deleted {deleted_count} obsolete files.")


def main():
    setup_logger()
    parser = argparse.ArgumentParser(description="KDTrace Stock List Generator")
    parser.add_argument("--dry-run", action="store_true",
                        help="List obsolete files without deleting them")
    args = parser.parse_args()

    generator = StockListGenerator()
    stocks = generator.fetch_stock_list()

    if stocks:
        generator.save_list(stocks, "tse.csv")
        generator.cleanup_obsolete_data(stocks, dry_run=args.dry_run)
    else:
        logging.error("Failed to generate stock list. Aborting cleanup to prevent accidental data loss.")


if __name__ == '__main__':
    main()
