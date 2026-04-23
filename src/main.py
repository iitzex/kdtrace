import argparse
import logging
import os
import platform
import statistics
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timedelta
from multiprocessing import Pool
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import matplotlib.pyplot as plt
import pandas as pd
from pandas.plotting import register_matplotlib_converters

plt.style.use('seaborn-v0_8-whitegrid')
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['xtick.labelsize'] = 15
plt.rcParams['ytick.labelsize'] = 15
register_matplotlib_converters()

from fetch import CNYESFetcher, FetchConfig
from gen_html import html_generator
from indicator import kd, ma
from utils import get_list, setup_logger

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AppPaths:
    data_dir: Path = Path("data")
    json_dir: Path = Path("json")
    pic_dir: Path = Path("pic")
    stock_list_name: str = "tse"


@dataclass
class AnalysisResult:
    sid: str
    title: str
    df_f: pd.DataFrame
    df_ma: pd.DataFrame
    df_daily: pd.DataFrame
    df_weekly: pd.DataFrame
    df_monthly: pd.DataFrame
    df_revenue: pd.DataFrame
    df_eps: pd.DataFrame
    df_profitability: pd.DataFrame
    df_investors: pd.DataFrame
    price: float
    eps4q_sum: float
    begin_date: datetime

    def to_plot_data(self) -> Dict[str, Any]:
        return {
            "df_f": self.df_f,
            "df_ma": self.df_ma,
            "df_daily": self.df_daily,
            "df_weekly": self.df_weekly,
            "df_monthly": self.df_monthly,
            "df_revenue": self.df_revenue,
            "df_eps": self.df_eps,
            "df_profitability": self.df_profitability,
            "df_investors": self.df_investors,
            "price": self.price,
            "eps4q_sum": self.eps4q_sum,
            "begin_date": self.begin_date,
        }


class StockVisualizer:
    """股票分析圖表繪製的所有邏輯。"""

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

    def draw_report(self, result: AnalysisResult, output_path: str) -> Tuple[float, float]:
        """繪圖與存檔；回傳 (plot_time, save_time) 以供 profiling。"""
        sid = result.sid
        title = result.title
        data = result.to_plot_data()
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
    """編排多支股票的分析流程。"""

    def __init__(
        self,
        fetcher: CNYESFetcher,
        visualizer: StockVisualizer,
        force: bool = False,
        paths: AppPaths = AppPaths(),
    ):
        self.fetcher = fetcher
        self.visualizer = visualizer
        self.force = force
        self.paths = paths
        self.paths.pic_dir.mkdir(exist_ok=True)

    def _data_path(self, sid: str) -> Path:
        return self.paths.data_dir / f"{sid}.csv"

    def _json_cache_path(self, sid: str, category: str) -> Path:
        return self.paths.json_dir / f"{sid}_{category}.json"

    def _output_path(self, sid: str) -> Path:
        return self.paths.pic_dir / f"{sid}.png"

    def _is_up_to_date(self, sid: str) -> bool:
        """若 pic/{sid}.png 的 mtime 晚於所有輸入（CSV + JSON cache）→ 可跳過重畫。"""
        png = self._output_path(sid)
        if not png.exists():
            return False
        png_mtime = png.stat().st_mtime

        data = self._data_path(sid)
        if not data.exists() or data.stat().st_mtime > png_mtime:
            return False

        for cat in FETCH_CATEGORIES:
            j = self._json_cache_path(sid, cat)
            if not j.exists() or j.stat().st_mtime > png_mtime:
                return False
        return True

    def _read_price_data(self, sid: str) -> pd.DataFrame:
        data_path = self._data_path(sid)
        if not data_path.exists():
            raise FileNotFoundError(f"Data file for {sid} missing.")

        df_f = pd.read_csv(data_path, index_col=0, parse_dates=True, date_format="%Y-%m-%d")
        if df_f.empty:
            raise ValueError(f"Data file for {sid} is empty.")
        df_f = df_f.iloc[-255 * 5:]
        df_f = df_f.apply(pd.to_numeric, errors="coerce")
        return df_f

    def _fetch_remote_data(self, sid: str) -> Dict[str, Any]:
        with ThreadPoolExecutor(max_workers=5) as ex:
            future_map = {
                "df_revenue": ex.submit(self.fetcher.get_revenue, sid),
                "df_eps": ex.submit(self.fetcher.get_eps, sid),
                "df_profitability": ex.submit(self.fetcher.get_profitability, sid),
                "df_investors": ex.submit(self.fetcher.get_investors, sid),
                "price": ex.submit(self.fetcher.get_price, sid),
            }
            return {name: future.result() for name, future in future_map.items()}

    def _build_analysis_result(self, sid: str, title: str, df_f: pd.DataFrame, remote_data: Dict[str, Any]) -> AnalysisResult:
        df_daily, df_weekly, df_monthly = kd(df_f)
        df_ma = ma(df_f)

        df_eps = remote_data["df_eps"]
        eps4q_sum = df_eps.eps.head(4).sum() if not df_eps.empty else 0
        num_days = min(300, len(df_f.index))
        begin_date = df_f.index[-1].to_pydatetime() - timedelta(num_days)
        begin_date = datetime(begin_date.year, begin_date.month, 1) - timedelta(1)

        return AnalysisResult(
            sid=sid,
            title=title,
            df_f=df_f,
            df_ma=df_ma,
            df_daily=df_daily,
            df_weekly=df_weekly,
            df_monthly=df_monthly,
            df_revenue=remote_data["df_revenue"],
            df_eps=df_eps,
            df_profitability=remote_data["df_profitability"],
            df_investors=remote_data["df_investors"],
            price=remote_data["price"],
            eps4q_sum=eps4q_sum,
            begin_date=begin_date,
        )

    def analyze_stock(self, items: Tuple[str, str]) -> Optional[Dict[str, float]]:
        """單支股票的完整流程；回傳每階段耗時（秒），用於 profiling。跳過時回傳 {'_skipped': 0.0}。"""
        sid, title = items
        timings: Dict[str, float] = {}

        if not self.force and self._is_up_to_date(sid):
            logging.debug(f"Skip {sid} (up-to-date)")
            return {'_skipped': 0.0}

        logging.info(f"Analyzing {sid} {title}...")

        try:
            t = time.perf_counter()
            df_f = self._read_price_data(sid)
            timings['read_csv'] = time.perf_counter() - t

            t = time.perf_counter()
            remote_data = self._fetch_remote_data(sid)
            timings['fetch_phase'] = time.perf_counter() - t

            t = time.perf_counter()
            result = self._build_analysis_result(sid, title, df_f, remote_data)
            timings['indicators'] = time.perf_counter() - t

            output_file = str(self._output_path(sid))
            plot_time, save_time = self.visualizer.draw_report(result, output_file)
            timings['plot'] = plot_time
            timings['savefig'] = save_time

            return timings

        except (FileNotFoundError, ValueError) as e:
            logging.warning(str(e))
            return None
        except Exception as e:
            logging.error(f"Unexpected error analyzing {sid}: {e}")
            return None


class AnalysisService:
    """管理分析模式、股票清單與執行策略。"""

    def __init__(self, analyzer: StockAnalyzer, paths: AppPaths = AppPaths()):
        self.analyzer = analyzer
        self.paths = paths

    def get_stocks(self, sid: Optional[str] = None, limit: Optional[int] = None) -> List[Tuple[str, str]]:
        if sid:
            stocks = [(sid, "Manual")]
        else:
            stocks = get_list(self.paths.stock_list_name)
        if limit is not None:
            return stocks[:limit]
        return stocks

    def run_profile(self, limit: int, reload_enabled: bool = False) -> None:
        stocks = self.get_stocks(limit=limit)
        cache_mode = "cold (reload=True)" if reload_enabled else "warm"
        logging.info(f"Profiling {len(stocks)} stocks sequentially | cache={cache_mode}")
        t0 = time.perf_counter()
        samples = [t for t in (self.analyzer.analyze_stock(item) for item in stocks) if t]
        wall = time.perf_counter() - t0
        logging.info(f"Wall time: {wall:.2f}s | successful samples: {len(samples)}/{len(stocks)}")
        _print_profile_report(samples)

    def run_batch(self, stocks: List[Tuple[str, str]], cores: int) -> None:
        if cores > 1:
            with Pool(cores, initializer=_pool_worker_init) as p:
                p.map(self.analyzer.analyze_stock, stocks)
            return

        for item in stocks:
            self.analyzer.analyze_stock(item)


class ReportService:
    """管理靜態 HTML 報表輸出。"""

    def __init__(self, stock_list_name: str = AppPaths().stock_list_name):
        self.stock_list_name = stock_list_name

    def generate_main_report(self) -> None:
        if self.stock_list_name == "tse":
            html_generator()
            return

        from gen_html import HtmlGenerator

        HtmlGenerator().generate(self.stock_list_name)

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


def _build_services(args: argparse.Namespace) -> Tuple[AppPaths, AnalysisService, ReportService]:
    paths = AppPaths()
    fetch_config = FetchConfig(reload=args.reload or args.force)
    fetcher = CNYESFetcher(fetch_config)
    visualizer = StockVisualizer()
    analyzer = StockAnalyzer(fetcher, visualizer, force=args.force, paths=paths)
    return paths, AnalysisService(analyzer, paths=paths), ReportService(stock_list_name=paths.stock_list_name)


def _run_profile_mode(service: AnalysisService, args: argparse.Namespace) -> None:
    service.run_profile(limit=args.profile, reload_enabled=args.reload or args.force)


def _run_analysis_mode(service: AnalysisService, report_service: ReportService, args: argparse.Namespace) -> None:
    stocks = service.get_stocks(sid=args.sid)
    if not args.sid:
        logging.info(f"Starting batch analysis for {len(stocks)} stocks using {args.cores} cores...")
    service.run_batch(stocks, args.cores)
    report_service.generate_main_report()


def main():
    setup_logger()
    parser = argparse.ArgumentParser(description="KDTrace Stock Analysis Engine")
    parser.add_argument("--cores", type=int, default=os.cpu_count() or 1,
                        help="Number of CPU cores to use (default: all)")
    parser.add_argument("--reload", action="store_true", help="Force reload data from CNYES")
    parser.add_argument("--sid", help="Specific stock ID to analyze")
    parser.add_argument("--profile", type=int, metavar="N",
                        help="Profile first N stocks sequentially and print per-stage timing")
    parser.add_argument("--force", action="store_true",
                        help="Force re-render (implies --reload to also refresh data cache)")
    args = parser.parse_args()

    _, analysis_service, report_service = _build_services(args)

    try:
        if args.profile:
            _run_profile_mode(analysis_service, args)
            return

        _run_analysis_mode(analysis_service, report_service, args)

    except Exception as e:
        logging.error(f"Main loop error: {e}")

if __name__ == "__main__":
    main()
