import argparse
import logging
import os
from multiprocessing import Pool
from typing import Optional, Tuple

from fetch import CNYESFetcher, FetchConfig
from gen_html import HtmlGenerator
from indicator import log_slope_r2, normalized_position
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

            eps_ok = (df_eps['eps'].iloc[-self.window:] > self.eps_threshold).all()
            rev_ok = (df_rev['revenueYOY'].iloc[-self.window:] > self.rev_yoy_threshold).all()

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

class TrendFilter:
    """趨勢濾網：revenue 在 log 空間的斜率 (+R²) 夠強、EPS 落在歷史區間相對高位。

    判斷優於 StockFilter「最近 N 期 > 門檻」的原因：
    - revenue 成長本質接近指數，取 log 後的斜率才是真正的成長速率；
      搭配 R² 可濾掉「剛好最近幾期高、但整體震盪無方向」的假訊號。
    - EPS 用 (now - min) / (max - min) 判斷位置，比對「門檻」更能反映
      當下相對歷史的位階（類似 KD，0~1 之間）。
    """

    def __init__(self, fetcher: CNYESFetcher,
                 rev_months: int = 24, rev_slope_min: float = 0.0, rev_r2_min: float = 0.3,
                 eps_quarters: int = 12, eps_position_min: float = 0.7):
        self.fetcher = fetcher
        self.rev_months = rev_months
        self.rev_slope_min = rev_slope_min
        self.rev_r2_min = rev_r2_min
        self.eps_quarters = eps_quarters
        self.eps_position_min = eps_position_min

    def check_criteria(self, item: Tuple[str, str]) -> Optional[Tuple[str, str]]:
        """檢查單支股票是否同時符合 revenue 趨勢 + EPS 位置條件；不符合或無資料回 None。"""
        sid, title = item
        try:
            df_rev = self.fetcher.get_revenue(sid)
            df_eps = self.fetcher.get_eps(sid)

            if df_rev.empty or df_eps.empty:
                return None

            slope, r2 = log_slope_r2(df_rev["revenue"], self.rev_months)
            pos = normalized_position(df_eps["eps"], self.eps_quarters)

            if (slope == slope and r2 == r2 and pos == pos  # nan check
                    and slope > self.rev_slope_min
                    and r2 >= self.rev_r2_min
                    and pos >= self.eps_position_min):
                logging.info(f"MATCH: {sid} {title} slope={slope:.4f} r2={r2:.2f} pos={pos:.2f}")
                return (sid, title)

        except Exception as e:
            logging.debug(f"Skipping {sid} due to processing error: {e}")

        return None

    def run_screening(self, source_list: str = "tse", output_file: str = "trend.csv", cores: int = 1):
        """跑篩選並把結果寫成 CSV；cores>1 時用 Pool 平行。"""
        stocks = get_list(source_list)
        logging.info(f"Trend-screening {len(stocks)} stocks from {source_list} using {cores} cores...")

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

        try:
            with open(output_file, "w", encoding="utf-8") as f:
                for sid, title in filtered_results:
                    f.write(f"{sid},{title}\n")
            logging.info(f"Saved {len(filtered_results)} trend-matched results to {output_file}")
        except Exception as e:
            logging.error(f"Error saving trend list: {e}")


def main():
    setup_logger()
    parser = argparse.ArgumentParser(description="KDTrace Fundamental Stock Screener")
    parser.add_argument("--mode", choices=["basic", "trend"], default="basic",
                        help="basic: 最近 N 期 EPS/revenueYOY > 門檻；trend: revenue log 斜率 + EPS 位置")
    parser.add_argument("--cores", type=int, default=os.cpu_count() or 1,
                        help="Number of CPU cores to use (default: all)")
    parser.add_argument("--source", default="tse", help="Source stock list CSV name (without .csv)")
    parser.add_argument("--output", default=None,
                        help="Output CSV filename (default: filter.csv for basic, trend.csv for trend)")
    parser.add_argument("--reload", action="store_true", help="Force reload data from CNYES")
    # basic-mode thresholds
    parser.add_argument("--eps-threshold", type=float, default=0.0,
                        help="[basic] Min EPS for the recent window (default: 0 = positive)")
    parser.add_argument("--rev-yoy-threshold", type=float, default=0.0,
                        help="[basic] Min revenue YOY %% for the recent window (default: 0 = positive)")
    parser.add_argument("--window", type=int, default=3,
                        help="[basic] Quarters/months to check (default: 3)")
    # trend-mode thresholds
    parser.add_argument("--rev-months", type=int, default=24,
                        help="[trend] Months of revenue used for log-slope fit (default: 24)")
    parser.add_argument("--rev-slope-min", type=float, default=0.0,
                        help="[trend] Min log-slope of revenue (default: 0 = any uptrend)")
    parser.add_argument("--rev-r2-min", type=float, default=0.3,
                        help="[trend] Min R² of log-slope fit (default: 0.3)")
    parser.add_argument("--eps-quarters", type=int, default=12,
                        help="[trend] Quarters of EPS history for position calc (default: 12)")
    parser.add_argument("--eps-position-min", type=float, default=0.7,
                        help="[trend] Min EPS position in [0,1] (default: 0.7 = top 30%%)")
    args = parser.parse_args()

    config = FetchConfig(reload=args.reload)
    fetcher = CNYESFetcher(config)

    if args.mode == "basic":
        screen = StockFilter(fetcher, eps_threshold=args.eps_threshold,
                             rev_yoy_threshold=args.rev_yoy_threshold, window=args.window)
        output = args.output or "filter.csv"
    else:
        screen = TrendFilter(fetcher,
                             rev_months=args.rev_months,
                             rev_slope_min=args.rev_slope_min,
                             rev_r2_min=args.rev_r2_min,
                             eps_quarters=args.eps_quarters,
                             eps_position_min=args.eps_position_min)
        output = args.output or "trend.csv"

    screen.run_screening(args.source, output, args.cores)

    logging.info(f"Generating HTML report for {output}...")
    generator = HtmlGenerator()
    report_name = output.replace(".csv", "")
    generator.generate(report_name)

if __name__ == "__main__":
    main()
