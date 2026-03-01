import json
import csv
import logging
from pathlib import Path
from typing import List, Tuple, Optional

import requests
import urllib3
from urllib3.util.ssl_ import create_urllib3_context

# Suppress insecure request warnings when we explicitly use verify=False
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class CustomHttpAdapter(requests.adapters.HTTPAdapter):
    """
    A custom HTTP adapter that lowers the SSL security level to 1 for legacy sites.
    """
    def init_poolmanager(self, *args, **kwargs):
        context = create_urllib3_context()
        try:
            context.set_ciphers('DEFAULT@SECLEVEL=1')
        except Exception:
            logging.warning("Could not set SECLEVEL=1, falling back to default.")
        kwargs['ssl_context'] = context
        return super().init_poolmanager(*args, **kwargs)

def get_session() -> requests.Session:
    """Returns a session with the custom SSL adapter."""
    session = requests.Session()
    adapter = CustomHttpAdapter()
    session.mount('https://', adapter)
    return session

def get_request(url: str, params: Optional[dict] = None, headers: Optional[dict] = None, 
                timeout: int = 15, verify: bool = True) -> requests.Response:
    """
    A centralized request wrapper that handles SSL SECLEVEL=1 and retries with verify=False
    for known legacy domain issues.
    """
    legacy_domains = ["twse.com.tw", "tpex.org.tw", "isin.twse.com.tw"]
    
    session = get_session()
    try:
        return session.get(url, params=params, headers=headers, timeout=timeout, verify=verify)
    except requests.exceptions.SSLError as e:
        is_legacy = any(domain in url for domain in legacy_domains)
        is_cert_err = any(err in str(e) for err in ["Missing Subject Key Identifier", "certificate verify failed"])
        
        if is_legacy or is_cert_err:
            logging.warning(f"SSL issue detected for {url}. Retrying with verify=False...")
            return requests.get(url, params=params, headers=headers, timeout=timeout, verify=False)
        raise e

def get_list(name: str, bound: int = 0) -> List[Tuple[str, str]]:
    """
    Reads a stock list CSV and returns a list of (sid, title) tuples.
    """
    file_path = Path(f"{name}.csv")
    if not file_path.exists():
        logging.error(f"Stock list file {file_path} not found.")
        return []

    stocks = []
    try:
        with file_path.open("r", encoding="utf-8") as f:
            for row in csv.reader(f):
                if not row or len(row) < 2:
                    continue
                sid = row[0].strip()
                title = row[1].strip()
                
                # Basic validation: ensure sid is numeric and meets bound
                if sid.isdigit() and int(sid) >= bound:
                    stocks.append((sid, title))
    except Exception as e:
        logging.error(f"Error reading stock list {name}: {e}")
        
    return stocks

if __name__ == "__main__":
    # Test reading the list
    tse_list = get_list("tse")
    logging.info(f"Loaded {len(tse_list)} stocks from tse.csv")
    if tse_list:
        logging.info(f"Sample: {tse_list[0]}")
