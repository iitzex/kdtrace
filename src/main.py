import os
import time
import platform
import logging
import argparse
import statistics
from datetime import datetime, timedelta
from multiprocessing import Pool
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

import pandas as pd
import matplotlib.pyplot as plt
from pandas.plotting import register_matplotlib_converters

plt.style.use('seaborn-v0_8-whitegrid')
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['xtick.labelsize'] = 15
plt.rcParams['ytick.labelsize'] = 15
register_matplotlib_converters()

from fetch import CNYESFetcher, FetchConfig
from indicator import kd, ma
from gen_html import html_generator
from utils import get_list, setup_logger

logger = logging.getLogger(__name__)

class StockVisualizer:
    """Handles all plotting logic for stock analysis."""

    def __init__(self):
        self.font = self._set_font()

    def _set_font(self):
        import matplotlib.font_manager as fm
        if platform.system() == "Darwin":
            font_path = "/System/Library/Fonts/STHeiti Medium.ttc"
        else:
            font_path = "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"
        
        if os.path.exists(font_path):
            return fm.FontProperties(fname=font_path, size=14)
        return fm.FontProperties(size=14)

    def draw_report(self, sid: str, title: str, data: Dict[str, Any], output_path: str) -> Tuple[float, float]:
        """繪圖與存檔；回傳 (plot_time, save_time) 以供 profiling。"""
        t_plot_start = time.perf_counter()
        fig = plt.figure(figsize=(26, 13))
        plt.subplots_adjust(top=0.92, bottom=0.08, left=0.10, right=0.95, hspace=0.15, wspace=0.25)

        # Layout grids
        x0 = plt.subplot2grid((6, 2), (0, 0), rowspan=2) # Price & MA
        x1 = plt.subplot2grid((6, 2), (2, 0))            # Volume
        x2 = plt.subplot2grid((6, 2), (3, 0))            # KD
        x3 = plt.subplot2grid((6, 2), (4, 0), rowspan=2) # Investors
        
        y0 = plt.subplot2grid((6, 2), (0, 1), rowspan=2) # Price & Revenue
        y1 = plt.subplot2grid((6, 2), (2, 1), rowspan=2) # Price & EPS
        y2 = plt.subplot2grid((6, 2), (4, 1), rowspan=2) # Profitability

        # Extract data
        df = data['df_f']
        df_ma = data['df_ma']
        begin_date = data['begin_date']
        
        # Filter by display range
        df_disp = df.loc[df.index >= begin_date]
        ma_disp = df_ma.loc[df_ma.index >= begin_date]
        
        df_inv = data['df_investors']
        if not df_inv.empty:
            df_inv = df_inv.loc[df_inv.index >= pd.Timestamp(begin_date)]
            df_inv = df_inv.sort_index()

        # 1. Price & MA (X0)
        self._plot_price_ma(x0, df_disp, ma_disp)
        
        # 2. Volume (X1)
        self._plot_volume(x1, df_disp)

        # 3. KD (X2)
        self._plot_kd(x2, data['df_daily'], data['df_weekly'], data['df_monthly'], begin_date)

        # 4. Investors (X3)
        self._plot_investors(x3, df_inv)

        # 5. Revenue (Y0)
        self._plot_revenue(y0, df, data['df_revenue'], sid, title, data['price'], data['eps4q_sum'])

        # 6. EPS (Y1)
        self._plot_eps(y1, df, data['df_eps'], data['eps4q_sum'], data['price'])

        # 7. Profitability (Y2)
        self._plot_profitability(y2, df, data['df_profitability'])

        fig.subplots_adjust(bottom=0.1, hspace=0.5)
        fig.set_facecolor("white")

        plot_time = time.perf_counter() - t_plot_start
        t_save_start = time.perf_counter()
        try:
            plt.savefig(output_path)
        except Exception as e:
            logging.error(f"Error saving plot for {sid}: {e}")
        finally:
            plt.close()
        save_time = time.perf_counter() - t_save_start
        return plot_time, save_time

    def _plot_price_ma(self, ax, df, ma):
        # Professional Red for Price
        ax.plot(df.index, df.close, color="#ef4444", alpha=0.6, linewidth=2.5, zorder=1)
        
        # Harmonized Ocean Blue tones for Moving Averages
        colors = {
            "w_5": "#0ea5e9",   # Sky 500
            "w_20": "#0284c7",  # Sky 700
            "w_60": "#0c4a6e",  # Sky 900
            "w_120": "#6366f1", # Indigo 500
            "w_250": "#94a3b8"  # Slate 400
        }
        for col, color in colors.items():
            if col in ma.columns:
                ax.plot(ma.index, ma[col], color=color, alpha=0.9, linewidth=1.5, zorder=2)
        
        ax.set_title("Price & MA", loc="right", fontproperties=self.font, fontsize=18, color="#64748b")
        ax.get_yaxis().tick_right()
        ax.yaxis.grid(True, linestyle='--', alpha=0.3)

    def _plot_volume(self, ax, df):
        # Case specific: Red for Rise, Green for Fall
        colors = ["#ef4444" if c >= 0 else "#22c55e" for c in df.close.diff().fillna(0)]
        ax.bar(df.index, df.amount, 0.7, color=colors, alpha=0.6, edgecolor="none")
        ax.set_title("Volume", loc="right", fontproperties=self.font, fontsize=18, color="#64748b")
        ax.get_yaxis().tick_right()
        ax.get_xaxis().set_visible(False)
        ax.yaxis.grid(True, linestyle='--', alpha=0.3)

    def _plot_kd(self, ax, daily, weekly, monthly, begin):
        def _get_k_points(df, k_col, thresh_high=80, thresh_low=20):
            d = df.loc[df.index >= begin]
            return d, d[d[k_col] >= thresh_high], d[d[k_col] <= thresh_low]

        # Use Red/Ocean Blue for KD
        d_daily, h_daily, l_daily = _get_k_points(daily, 'k')
        ax.plot(d_daily.index, d_daily.k, color="#ef4444", alpha=0.7, linewidth=1.2)
        ax.plot(d_daily.index, d_daily.d, color="#0ea5e9", alpha=0.7, linewidth=1.2)
        ax.scatter(h_daily.index, h_daily.k, c="#e11d48", s=8, zorder=3)
        ax.scatter(l_daily.index, l_daily.k, c="#22c55e", s=8, zorder=3)

        d_week, h_week, l_week = _get_k_points(weekly, 'wk')
        ax.plot(d_week.index, d_week.wk, color="#ef4444", linestyle="--", alpha=0.4, linewidth=1)
        ax.plot(d_week.index, d_week.wd, color="#0ea5e9", linestyle="--", alpha=0.4, linewidth=1)

        ax.set_title("KD (Daily/Weekly)", loc="right", fontproperties=self.font, fontsize=18, color="#64748b")
        ax.set_ylim(0, 100)
        ax.axhline(80, color="#e2e8f0", linestyle=":", linewidth=0.8)
        ax.axhline(20, color="#e2e8f0", linestyle=":", linewidth=0.8)
        ax.get_xaxis().set_ticklabels([])
        ax.get_yaxis().set_visible(False)

    def _plot_investors(self, ax, df):
        if not df.empty:
            # Different shades of Ocean Blue
            ax.bar(df.index, df.get('totalVolume', 0), width=0.5, color="#0ea5e9", alpha=0.4, label="Total")
            ax.bar(df.index, df.get('foreignVolume', 0), width=0.3, color="#0284c7", alpha=0.8, label="Foreign")
        ax.get_yaxis().tick_right()
        ax.set_title("Institutional Investors", loc="right", fontproperties=self.font, fontsize=18, color="#64748b")
        ax.yaxis.grid(True, linestyle='--', alpha=0.3)

    def _plot_revenue(self, ax, df_f, df_rev, sid, title, price, eps_sum):
        yield_rate = (eps_sum * 100 / price) if price > 0 else 0
        header = f"{sid}, {title} {price} [{yield_rate:.1f}%]    Revenue Growth"
        ax.set_title(header, loc="right", fontproperties=self.font, fontsize=18, color="#1e293b", fontweight="bold")
        ax.plot(df_f.index, df_f.close, color="#ef4444", alpha=0.7, linewidth=2, zorder=1)
        ax.yaxis.grid(True, linestyle='--', alpha=0.3)
        
        if not df_rev.empty:
            p = ax.twinx()
            # Professional Amber Yellow for Revenue
            p.bar(df_rev.index, df_rev.revenue, width=15, color="#fef3c7", edgecolor="#fbbf24", alpha=0.8, zorder=3)
            q = ax.twinx()
            q.plot(df_rev.index, df_rev.revenueYOY, color="#0ea5e9", linewidth=2, alpha=0.9, zorder=4)
            q.spines["right"].set_position(("axes", 1.08))
            q.set_ylim(-40, 100)

    def _plot_eps(self, ax, df_f, df_eps, eps_sum, price):
        yield_rate = (eps_sum * 100 / price) if price > 0 else 0
        ax.set_title(f"EPS: {eps_sum:.2f} [{yield_rate:.1f}%]", loc="right", fontproperties=self.font, fontsize=18, color="#64748b")
        ax.plot(df_f.index, df_f.close, color="#ef4444", alpha=0.7, linewidth=1, zorder=1)
        ax.get_yaxis().set_visible(False)
        
        if not df_eps.empty:
            p = ax.twinx()
            # Amber Yellow palette for EPS
            p.bar(df_eps.index, df_eps.eps, width=40, color="#fbbf24", edgecolor="#d97706", alpha=0.8, zorder=2)
            q = ax.twinx()
            q.plot(df_eps.index, df_eps.epsYOY, color="#6366f1", linewidth=1.5, alpha=0.9, zorder=1)
            q.spines["right"].set_position(("axes", 1.08))
            q.set_ylim(-40, 150)

    def _plot_profitability(self, ax, df_f, df_prof):
        ax.set_title("Margins (%)", loc="right", fontproperties=self.font, fontsize=18, color="#64748b")
        ax.plot(df_f.index, df_f.close, color="#ef4444", alpha=0.7, linewidth=1, zorder=1)
        ax.get_yaxis().set_visible(False)
        
        if not df_prof.empty:
            p = ax.twinx()
            # Amber tones for Margins
            p.plot(df_prof.index, df_prof.get('grossMargin', []), color="#f59e0b", linewidth=2, label="Gross")
            p.plot(df_prof.index, df_prof.get('operatingMargin', []), color="#fbbf24", linewidth=1.5, label="Op")
            p.plot(df_prof.index, df_prof.get('profitMargin', []), color="#6366f1", linewidth=1, label="Net")
        ax.get_xaxis().set_visible(False)

FETCH_CATEGORIES = ("revenue", "eps", "profitability", "investors", "info")


class StockAnalyzer:
    """Orchestrates the analysis of multiple stocks."""

    def __init__(self, fetcher: CNYESFetcher, visualizer: StockVisualizer, force: bool = False):
        self.fetcher = fetcher
        self.visualizer = visualizer
        self.force = force
        os.makedirs("pic", exist_ok=True)

    def _is_up_to_date(self, sid: str) -> bool:
        """若 pic/{sid}.png 的 mtime 晚於所有輸入（CSV + JSON cache）→ 可跳過重畫。"""
        png = Path(f"pic/{sid}.png")
        if not png.exists():
            return False
        png_mtime = png.stat().st_mtime

        data = Path(f"data/{sid}.csv")
        if not data.exists() or data.stat().st_mtime > png_mtime:
            return False

        for cat in FETCH_CATEGORIES:
            j = Path(f"json/{sid}_{cat}.json")
            if not j.exists() or j.stat().st_mtime > png_mtime:
                return False
        return True

    def analyze_stock(self, items: Tuple[str, str]) -> Optional[Dict[str, float]]:
        """單支股票的完整流程；回傳每階段耗時（秒），用於 profiling。跳過時回傳 {'_skipped': 0.0}。"""
        sid, title = items
        timings: Dict[str, float] = {}

        if not self.force and self._is_up_to_date(sid):
            logging.debug(f"Skip {sid} (up-to-date)")
            return {'_skipped': 0.0}

        logging.info(f"Analyzing {sid} {title}...")

        try:
            data_path = f"data/{sid}.csv"
            if not os.path.exists(data_path):
                logging.warning(f"Data file for {sid} missing.")
                return None

            t = time.perf_counter()
            df_f = pd.read_csv(data_path, index_col=0, parse_dates=True, date_format='%Y-%m-%d')
            if df_f.empty:
                return None
            df_f = df_f.iloc[-255 * 5:]
            df_f = df_f.apply(pd.to_numeric, errors="coerce")
            timings['read_csv'] = time.perf_counter() - t

            # 5 個 CNYES endpoint 併發；每支股票打 5 條獨立檔案／endpoint，無共享寫入
            t = time.perf_counter()
            with ThreadPoolExecutor(max_workers=5) as ex:
                f_rev = ex.submit(self.fetcher.get_revenue, sid)
                f_eps = ex.submit(self.fetcher.get_eps, sid)
                f_prof = ex.submit(self.fetcher.get_profitability, sid)
                f_inv = ex.submit(self.fetcher.get_investors, sid)
                f_price = ex.submit(self.fetcher.get_price, sid)
                df_rev = f_rev.result()
                df_eps = f_eps.result()
                df_prof = f_prof.result()
                df_investors = f_inv.result()
                price = f_price.result()
            timings['fetch_phase'] = time.perf_counter() - t

            t = time.perf_counter()
            df_daily, df_weekly, df_monthly = kd(df_f)
            df_ma = ma(df_f)
            timings['indicators'] = time.perf_counter() - t

            eps4q_sum = df_eps.eps.head(4).sum() if not df_eps.empty else 0
            num_days = min(300, len(df_f.index))
            begin_date = df_f.index[-1].to_pydatetime() - timedelta(num_days)
            begin_date = datetime(begin_date.year, begin_date.month, 1) - timedelta(1)

            plot_data = {
                'df_f': df_f,
                'df_ma': df_ma,
                'df_daily': df_daily,
                'df_weekly': df_weekly,
                'df_monthly': df_monthly,
                'df_revenue': df_rev,
                'df_eps': df_eps,
                'df_profitability': df_prof,
                'df_investors': df_investors,
                'price': price,
                'eps4q_sum': eps4q_sum,
                'begin_date': begin_date
            }

            output_file = f"pic/{sid}.png"
            plot_time, save_time = self.visualizer.draw_report(sid, title, plot_data, output_file)
            timings['plot'] = plot_time
            timings['savefig'] = save_time

            return timings

        except Exception as e:
            logging.error(f"Unexpected error analyzing {sid}: {e}")
            return None

STAGE_ORDER = [
    'read_csv', 'fetch_phase', 'indicators', 'plot', 'savefig',
]


def _pool_worker_init():
    """spawn 模式下 worker 不會執行 main()，需在每個 worker 手動呼叫 setup_logger()。"""
    setup_logger()


def _print_profile_report(samples: List[Dict[str, float]]):
    """印 TOON 格式的 per-stage 統計表；分離 processed vs skipped。"""
    skipped = sum(1 for s in samples if '_skipped' in s)
    processed = [s for s in samples if '_skipped' not in s]

    logging.info(f"processed={len(processed)} | skipped={skipped}")
    if not processed:
        logging.warning("No stocks processed (all skipped or failed).")
        return

    samples = processed
    n = len(samples)
    header = "stage               | n  | mean_ms | median_ms | p95_ms  | total_s | share"
    lines = [header]
    totals: Dict[str, float] = {}
    for stage in STAGE_ORDER:
        vals = [s[stage] for s in samples if stage in s]
        if not vals:
            continue
        totals[stage] = sum(vals)

    grand_total = sum(totals.values())

    for stage in STAGE_ORDER:
        vals = sorted(s[stage] for s in samples if stage in s)
        if not vals:
            continue
        mean_ms = statistics.mean(vals) * 1000
        median_ms = statistics.median(vals) * 1000
        p95_ms = vals[min(len(vals) - 1, int(len(vals) * 0.95))] * 1000
        total_s = sum(vals)
        share = (total_s / grand_total * 100) if grand_total > 0 else 0
        lines.append(
            f"{stage:<19} | {len(vals):<2} | {mean_ms:>7.1f} | {median_ms:>9.1f} | "
            f"{p95_ms:>7.1f} | {total_s:>7.2f} | {share:>4.1f}%"
        )

    per_stock_total = grand_total / n
    lines.append(f"{'TOTAL':<19} | {n:<2} | {per_stock_total*1000:>7.1f} | {'-':>9} | "
                 f"{'-':>7} | {grand_total:>7.2f} | 100.0%")

    print("\n" + "\n".join(lines) + "\n")


def main():
    setup_logger()
    parser = argparse.ArgumentParser(description="KDTrace Stock Analysis Engine")
    parser.add_argument("--cores", type=int, default=10, help="Number of CPU cores to use")
    parser.add_argument("--reload", action="store_true", help="Force reload data from CNYES")
    parser.add_argument("--sid", help="Specific stock ID to analyze")
    parser.add_argument("--profile", type=int, metavar="N",
                        help="Profile first N stocks sequentially and print per-stage timing")
    parser.add_argument("--force", action="store_true",
                        help="Force re-render even if pic/{sid}.png is up-to-date")
    args = parser.parse_args()

    fetch_config = FetchConfig(reload=args.reload)
    fetcher = CNYESFetcher(fetch_config)
    visualizer = StockVisualizer()
    analyzer = StockAnalyzer(fetcher, visualizer, force=args.force)

    try:
        if args.profile:
            stocks = get_list("tse")[:args.profile]
            cache_mode = "cold (reload=True)" if args.reload else "warm"
            logging.info(f"Profiling {len(stocks)} stocks sequentially | cache={cache_mode}")
            t0 = time.perf_counter()
            samples = [t for t in (analyzer.analyze_stock(item) for item in stocks) if t]
            wall = time.perf_counter() - t0
            logging.info(f"Wall time: {wall:.2f}s | successful samples: {len(samples)}/{len(stocks)}")
            _print_profile_report(samples)
            return

        if args.sid:
            stocks = [(args.sid, "Manual")]
        else:
            stocks = get_list("tse")
            logging.info(f"Starting batch analysis for {len(stocks)} stocks using {args.cores} cores...")

        if args.cores > 1:
            with Pool(args.cores, initializer=_pool_worker_init) as p:
                p.map(analyzer.analyze_stock, stocks)
        else:
            for item in stocks:
                analyzer.analyze_stock(item)

        html_generator()

    except Exception as e:
        logging.error(f"Main loop error: {e}")

if __name__ == "__main__":
    main()
