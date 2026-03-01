import logging
import pandas as pd
from util import get_list, get_request

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class YieldRateFetcher:
    """Fetches stock yield rate information."""
    
    URL = "https://stock.wespai.com/rate114"
    
    def fetch_data(self) -> pd.DataFrame:
        """Fetches and parses the yield rate table."""
        logging.info(f"Fetching yield rate data from {self.URL}...")
        try:
            # Using centralized request handler to handle potential SSL/connection issues
            response = get_request(self.URL)
            response.raise_for_status()
            
            # read_html returns a list of dataframes
            frames = pd.read_html(response.text, index_col="代號")
            if not frames:
                logging.error("No tables found in the response.")
                return pd.DataFrame()
                
            full_df = frames[0]
            # Select and rename columns for clarity
            cols = ["公司", "現金殖利率", "股價", "配息", "除息日", "發息日"]
            df = full_df[[c for c in cols if c in full_df.columns]].copy()
            
            # Data cleaning: Convert generic "dividend" to per-thousand shares if needed
            # In original: df.loc[:, "配息"] *= 1000
            if "配息" in df.columns:
                df["配息"] = pd.to_numeric(df["配息"], errors='coerce') * 1000
                
            return df
        except Exception as e:
            logging.error(f"Failed to fetch yield rate data: {e}")
            return pd.DataFrame()

def main():
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
