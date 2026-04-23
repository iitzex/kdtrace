import logging
import argparse
from multiprocessing import Pool
from typing import Tuple, Optional
from fetch import CNYESFetcher, FetchConfig
from utils import get_list, setup_logger
from gen_html import HtmlGenerator

logger = logging.getLogger(__name__)


def _pool_worker_init():
    """spawn 模式下 worker 不會執行 main()，需在每個 worker 手動呼叫 setup_logger()。"""
    setup_logger()


class StockFilter:
    """Filters stocks based on fundamental criteria with multiprocessing support."""

    def __init__(self, fetcher: CNYESFetcher):
        self.fetcher = fetcher

    def check_criteria(self, item: Tuple[str, str]) -> Optional[Tuple[str, str]]:
        """Checks if a single stock meets the fundamental criteria."""
        sid, title = item
        try:
            # Fetch required indicators
            df_rev = self.fetcher.get_revenue(sid)
            df_eps = self.fetcher.get_eps(sid)
            
            if df_rev.empty or df_eps.empty:
                return None
            
            # Criteria: Positive EPS for last 3 quarters AND Positive Revenue YOY for last 3 months
            eps_ok = (df_eps['eps'].iloc[:3] > 0).all()
            rev_ok = (df_rev['revenueYOY'].iloc[:3] > 0).all()
            
            if eps_ok and rev_ok:
                logging.info(f"MATCH: {sid} {title}")
                return (sid, title)
                
        except Exception as e:
            logging.debug(f"Skipping {sid} due to processing error: {e}")
        
        return None

    def run_screening(self, source_list: str = "tse", output_file: str = "filter.csv", cores: int = 1):
        """Screens stocks and saves results to a CSV using multiple processes."""
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
    parser.add_argument("--cores", type=int, default=8, help="Number of CPU cores to use")
    parser.add_argument("--source", default="tse", help="Source stock list CSV name (without .csv)")
    parser.add_argument("--output", default="filter.csv", help="Output filtered CSV filename")
    parser.add_argument("--reload", action="store_true", help="Force reload data from CNYES")
    args = parser.parse_args()

    # Use existing infrastructure
    config = FetchConfig(reload=args.reload)
    fetcher = CNYESFetcher(config)
    screen = StockFilter(fetcher)
    
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
