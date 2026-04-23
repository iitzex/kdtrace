import logging

import pandas as pd

from utils import get_list, get_request, setup_logger

logger = logging.getLogger(__name__)

class YieldRateFetcher:
    """抓殖利率資訊。"""
    
    URL = "https://stock.wespai.com/rate114"
    
    REQUIRED_COLS = {"代號", "公司", "現金殖利率"}
    OUTPUT_COLS = ["公司", "現金殖利率", "股價", "配息", "除息日", "發息日"]

    def fetch_data(self) -> pd.DataFrame:
        """抓取殖利率表；以 column name 找目標 table，table 結構變動時會失敗得很明確。"""
        logging.info(f"Fetching yield rate data from {self.URL}...")
        try:
            response = get_request(self.URL)
            response.raise_for_status()

            frames = pd.read_html(response.text)
            if not frames:
                logging.error("No tables found in the response.")
                return pd.DataFrame()

            # 按 column name 找含必要欄位的 table，不再依賴 frames[0] 位置
            target = next(
                (f for f in frames if self.REQUIRED_COLS.issubset(set(f.columns))),
                None,
            )
            if target is None:
                logging.error(
                    f"No table contains required columns {self.REQUIRED_COLS}; "
                    f"available columns in first frame: {list(frames[0].columns)}"
                )
                return pd.DataFrame()

            full_df = target.set_index("代號")
            df = full_df[[c for c in self.OUTPUT_COLS if c in full_df.columns]].copy()

            if "配息" in df.columns:
                df["配息"] = pd.to_numeric(df["配息"], errors='coerce') * 1000

            return df
        except Exception as e:
            logging.error(f"Failed to fetch yield rate data: {e}")
            return pd.DataFrame()

def main():
    setup_logger()
    fetcher = YieldRateFetcher()
    df = fetcher.fetch_data()
    
    if df.empty:
        logging.error("Empty data, exiting.")
        return

    # Check for specific "my" list if it exists
    my_stocks = [sid for sid, _ in get_list("my")]
    
    output_file = "rate.xlsx"
    try:
        with pd.ExcelWriter(output_file) as writer:
            if my_stocks:
                # Filter only stocks in our interest list
                valid_my = [s for s in my_stocks if s in df.index]
                if valid_my:
                    df.loc[valid_my].to_excel(writer, sheet_name="My Interests")
            
            df.to_excel(writer, sheet_name="All Stocks")
        logging.info(f"Report saved to {output_file}")
    except Exception as e:
        logging.error(f"Error saving Excel report: {e}")

if __name__ == "__main__":
    main()
