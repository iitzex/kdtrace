import time
import json
import os
import logging
import pandas as pd
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass, field
from util import get_list, get_request

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

@dataclass
class FetchConfig:
    """Configuration for the CNYES data fetcher."""
    headers: Dict[str, str] = field(default_factory=lambda: {
        'accept': 'application/json, text/plain, */*',
        'accept-language': 'zh-TW,zh;q=0.7',
        'dnt': '1',
        'origin': 'https://www.cnyes.com',
        'referer': 'https://www.cnyes.com/',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    })
    cache_dir: str = "json"
    reload: bool = True
    years_back: int = 5

class CNYESFetcher:
    """Fetcher for financial data from CNYES (marketinfo.api.cnyes.com)."""

    def __init__(self, config: FetchConfig = FetchConfig()):
        self.config = config
        os.makedirs(self.config.cache_dir, exist_ok=True)
        
        # Calculate standard timestamps
        self.to_ts = int(time.time())
        # The original code had a curious logic: int(time.time()) - 31536000 * 5
        # That's actually 5 years AGO. Usually 'to' implies 'until now'.
        # However, looking at the original params, it set 'to' to 5 years ago.
        # I'll preserve the original logic but make it configurable if needed.
        self.base_ts = self.to_ts - 31536000 * self.config.years_back

    def _get_cache_path(self, sid: str, category: str) -> str:
        return os.path.join(self.config.cache_dir, f"{sid}_{category}.json")

    def fetch_json(self, sid: str, url: str, params: Dict[str, Any], category: str) -> Optional[Dict[str, Any]]:
        """Fetches JSON data with local file caching support and 24h expiration."""
        cache_path = self._get_cache_path(sid, category)
        
        cache_exists = os.path.exists(cache_path)
        is_stale = False
        if cache_exists:
            # Invalidate cache if older than 24 hours
            if time.time() - os.path.getmtime(cache_path) > 86400:
                is_stale = True
        
        if self.config.reload or not cache_exists or is_stale:
            try:
                # Using util.get_request which already handles some session-like behavior and SSL issues
                response = get_request(url, params=params, headers=self.config.headers)
                response.raise_for_status()
                data = response.json()
                
                with open(cache_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=4)
                return data
            except Exception as e:
                logging.error(f"Failed to fetch {category} for {sid}: {e}")
                return None
        else:
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logging.error(f"Failed to read cache for {sid} {category}: {e}")
                return None

    def _to_dataframe(self, data: Optional[Dict[str, Any]], columns_map: Dict[str, str]) -> pd.DataFrame:
        """Helper to convert CNYES JSON response to a clean pandas DataFrame."""
        if not data or "data" not in data or not data["data"]:
            return pd.DataFrame()
        
        stock_data = data["data"][0]
        try:
            df_data = {new_name: stock_data[old_name] for old_name, new_name in columns_map.items()}
            df = pd.DataFrame(df_data, index=pd.to_datetime(stock_data["time"], unit="s"))
            df.index.name = "date"
            return df
        except KeyError as e:
            logging.warning(f"Map error in data: {e}")
            return pd.DataFrame()

    def get_revenue(self, sid: str) -> pd.DataFrame:
        url = f'https://marketinfo.api.cnyes.com/mi/api/v1/financialIndicator/revenue/TWS:{sid}:STOCK'
        params = {'year': str(self.config.years_back), 'to': f'{self.to_ts}'}
        data = self.fetch_json(sid, url, params, "revenue")
        return self._to_dataframe(data, {"revenue": "revenue", "revenueYOY": "revenueYOY"})

    def get_profitability(self, sid: str) -> pd.DataFrame:
        url = f'https://marketinfo.api.cnyes.com/mi/api/v1/financialIndicator/profitability/TWS:{sid}:STOCK'
        params = {'year': str(self.config.years_back), 'to': f'{self.to_ts}'}
        data = self.fetch_json(sid, url, params, "profitability")
        return self._to_dataframe(data, {
            "grossMargin": "grossMargin",
            "operatingMargin": "operatingMargin",
            "profitMargin": "profitMargin"
        })

    def get_eps(self, sid: str) -> pd.DataFrame:
        url = f'https://marketinfo.api.cnyes.com/mi/api/v1/financialIndicator/eps/TWS:{sid}:STOCK'
        params = {'resolution': 'Q', 'year': str(self.config.years_back), 'to': f'{self.base_ts}'}
        data = self.fetch_json(sid, url, params, "eps")
        return self._to_dataframe(data, {"eps": "eps", "epsYOY": "epsYOY"})

    def get_price(self, sid: str) -> float:
        """Fetch current price. Returns -1.0 if failed."""
        url = f'https://ws.api.cnyes.com/ws/api/v1/quote/quotes/TWS:{sid}:STOCK?column=K,E,KEY,M,AI'
        data = self.fetch_json(sid, url, {}, "info")
        if data and "data" in data and data["data"]:
            return float(data["data"][0].get('21', -1))
        return -1.0

    def get_investors(self, sid: str) -> pd.DataFrame:
        url = f'https://marketinfo.api.cnyes.com/mi/api/v1/chipsObserve/3majorInvestors/TWS:{sid}:STOCK'
        params = {'year': str(self.config.years_back), 'to': f'{self.to_ts}'}
        data = self.fetch_json(sid, url, params, "investors")
        
        if not data or "data" not in data or not data["data"]:
            return pd.DataFrame()
            
        stock_data = data["data"][0]
        try:
            chart_data = stock_data["volumeCharting"]
            df = pd.DataFrame(chart_data)
            df.index = pd.to_datetime(stock_data["time"], unit="s")
            df.index.name = "date"
            # Keep only relevant columns
            valid_cols = ["foreignVolume", "domesticVolume", "dealerVolume", "totalVolume"]
            return df[[c for c in valid_cols if c in df.columns]]
        except Exception as e:
            logging.error(f"Error parsing investor data for {sid}: {e}")
            return pd.DataFrame()

def main():
    config = FetchConfig(reload=True)
    fetcher = CNYESFetcher(config)
    
    # Process TSE list
    stocks = get_list("tse")
    logging.info(f"Starting batch fetch for {len(stocks)} stocks...")
    
    for sid, name in stocks:
        logging.info(f"Processing {sid} {name}...")
        price = fetcher.get_price(sid)
        df_eps = fetcher.get_eps(sid)
        df_rev = fetcher.get_revenue(sid)
        df_prof = fetcher.get_profitability(sid)
        df_inv = fetcher.get_investors(sid)
        
        logging.info(f"  Done: Price={price}, EPS rows={len(df_eps)}")
        # Example break or limit for testing if needed
        # break 

if __name__ == "__main__":
    main()
