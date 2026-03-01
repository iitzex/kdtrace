import re
import os
import logging
from dataclasses import dataclass
from typing import List, Set, Tuple, Optional
from bs4 import BeautifulSoup, Tag
from util import get_request

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


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
                logging.info(f"Successfully fetched content (HTTP 200)")
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

    def cleanup_obsolete_data(self, current_stocks: List[StockInfo]) -> None:
        """Deletes CSV files in data_dir for stocks no longer in the current list."""
        if not os.path.isdir(self.data_dir):
            logging.warning(f"Data directory '{self.data_dir}' does not exist. Skipping cleanup.")
            return

        logging.info(f"Starting cleanup of obsolete data in '{self.data_dir}'...")
        current_ids: Set[str] = {stock.sid for stock in current_stocks}
        
        # Reference files that should never be deleted
        protected_files = {"0050"}
        
        existing_files = [f for f in os.listdir(self.data_dir) if f.endswith(".csv")]
        deleted_count = 0
        
        for file_name in existing_files:
            sid = file_name.replace(".csv", "")
            if sid not in current_ids and sid not in protected_files:
                file_path = os.path.join(self.data_dir, file_name)
                try:
                    os.remove(file_path)
                    deleted_count += 1
                    logging.debug(f"Deleted obsolete data: {file_name}")
                except Exception as e:
                    logging.error(f"Error deleting {file_name}: {e}")
        
        if deleted_count > 0:
            logging.info(f"Cleanup complete. Deleted {deleted_count} obsolete files.")
        else:
            logging.info("No obsolete files found.")


def main():
    generator = StockListGenerator()
    stocks = generator.fetch_stock_list()
    
    if stocks:
        generator.save_list(stocks, "tse.csv")
        generator.cleanup_obsolete_data(stocks)
    else:
        logging.error("Failed to generate stock list. Aborting cleanup to prevent accidental data loss.")


if __name__ == '__main__':
    main()
