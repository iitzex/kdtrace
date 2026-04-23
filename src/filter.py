import argparse
import logging
import os
from multiprocessing import Pool
from typing import Optional, Tuple

from fetch import CNYESFetcher, FetchConfig
from gen_html import HtmlGenerator
from utils import get_list, setup_logger

logger = logging.getLogger(__name__)


def _pool_worker_init():
    """spawn 模式下 worker 不會執行 main()，需在每個 worker 手動呼叫 setup_logger()。"""
    setup_logger()


class StockFilter:
    """依基本面條件篩選股票，支援多行程平行。"""

    def __init__(self, fetcher: CNYESFetcher, eps_threshold: float = 0.0,
                 rev_yoy_threshold: float = 0.0, window: int = 3):
        """條件：最近 `window` 季 EPS > eps_threshold 且最近 `window` 月 revenueYOY > rev_yoy_threshold。"""
        self.fetcher = fetcher
        self.eps_threshold = eps_threshold
        self.rev_yoy_threshold = rev_yoy_threshold
        self.window = window

    def check_criteria(self, item: Tuple[str, str]) -> Optional[Tuple[str, str]]:
        """檢查單一股票是否符合基本面條件；不符合或無資料回 None。"""
        sid, title = item
        try:
            df_rev = self.fetcher.get_revenue(sid)
            df_eps = self.fetcher.get_eps(sid)

            if df_rev.empty or df_eps.empty:
                return None

            eps_ok = (df_eps['eps'].iloc[:self.window] > self.eps_threshold).all()
            rev_ok = (df_rev['revenueYOY'].iloc[:self.window] > self.rev_yoy_threshold).all()

            if eps_ok and rev_ok:
                logging.info(f"MATCH: {sid} {title}")
                return (sid, title)

        except Exception as e:
            logging.debug(f"Skipping {sid} due to processing error: {e}")

        return None

    def run_screening(self, source_list: str = "tse", output_file: str = "filter.csv", cores: int = 1):
        """跑篩選並把結果寫成 CSV；cores>1 時用 Pool 平行。"""
        stocks = get_list(source_list)
        logging.info(f"Screening {len(stocks)} stocks from {source_list} using {cores} cores...")
        
        filtered_results = []
        
        if cores > 1:
            with Pool(cores, initializer=_pool_worker_init) as p:
                results = p.map(self.check_criteria, stocks)
                filtered_results = [r for r in results if r is not None]
        else:
            for item in stocks:
                result = self.check_criteria(item)
                if result:
                    filtered_results.append(result)

        # Save to CSV
        try:
            with open(output_file, "w", encoding="utf-8") as f:
                for sid, title in filtered_results:
                    f.write(f"{sid},{title}\n")
            logging.info(f"Saved {len(filtered_results)} filtered results to {output_file}")
        except Exception as e:
            logging.error(f"Error saving filter list: {e}")

def main():
    setup_logger()
    parser = argparse.ArgumentParser(description="KDTrace Fundamental Stock Screener")
    parser.add_argument("--cores", type=int, default=os.cpu_count() or 1,
                        help="Number of CPU cores to use (default: all)")
    parser.add_argument("--source", default="tse", help="Source stock list CSV name (without .csv)")
    parser.add_argument("--output", default="filter.csv", help="Output filtered CSV filename")
    parser.add_argument("--reload", action="store_true", help="Force reload data from CNYES")
    parser.add_argument("--eps-threshold", type=float, default=0.0,
                        help="Min EPS for the recent window (default: 0 = positive)")
    parser.add_argument("--rev-yoy-threshold", type=float, default=0.0,
                        help="Min revenue YOY %% for the recent window (default: 0 = positive)")
    parser.add_argument("--window", type=int, default=3,
                        help="Quarters/months to check (default: 3)")
    args = parser.parse_args()

    config = FetchConfig(reload=args.reload)
    fetcher = CNYESFetcher(config)
    screen = StockFilter(fetcher, eps_threshold=args.eps_threshold,
                         rev_yoy_threshold=args.rev_yoy_threshold, window=args.window)
    
    # Run filter with specified parameters
    screen.run_screening(args.source, args.output, args.cores)
    
    # Generate HTML for the filtered list
    logging.info(f"Generating HTML report for {args.output}...")
    generator = HtmlGenerator()
    # The HtmlGenerator.generate method expects the base name of the csv
    report_name = args.output.replace(".csv", "")
    generator.generate(report_name)

if __name__ == "__main__":
    main()
