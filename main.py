import os
import sys
import platform
import logging
import argparse
from datetime import datetime, timedelta
from multiprocessing import Pool
from typing import Dict, Any, List, Tuple, Optional

import pandas as pd
import matplotlib.pyplot as plt
from pandas.plotting import register_matplotlib_converters

# Use professional styling
plt.style.use('seaborn-v0_8-whitegrid')
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS'] # For Mac CJK support
plt.rcParams['axes.unicode_minus'] = False
register_matplotlib_converters()

# Internal imports
from fetch import CNYESFetcher, FetchConfig
from indicator import kd, ma
from gen_html import html_generator
from util import get_list

# Register converters for matplotlib and pandas
register_matplotlib_converters()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class StockVisualizer:
    """Handles all plotting logic for stock analysis."""

    def __init__(self):
        self.font = self._set_font()
        plt.rc("xtick", labelsize=10)
        plt.rc("ytick", labelsize=10)

    def _set_font(self):
        import matplotlib.font_manager as fm
        if platform.system() == "Darwin":
            font_path = "/System/Library/Fonts/STHeiti Medium.ttc"
        else:
            font_path = "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"
        
        if os.path.exists(font_path):
            return fm.FontProperties(fname=font_path, size=14)
        return fm.FontProperties(size=14)

    def draw_report(self, sid: str, title: str, data: Dict[str, Any], output_path: str):
        """Main method to draw the comprehensive stock report."""
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
        
        try:
            plt.savefig(output_path, bbox_inches="tight")
        except Exception as e:
            logging.error(f"Error saving plot for {sid}: {e}")
        finally:
            plt.close()

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

class StockAnalyzer:
    """Orchestrates the analysis of multiple stocks."""

    def __init__(self, fetcher: CNYESFetcher, visualizer: StockVisualizer):
        self.fetcher = fetcher
        self.visualizer = visualizer
        os.makedirs("pic", exist_ok=True)

    def analyze_stock(self, items: Tuple[str, str]):
        """Complete analysis workflow for a single stock."""
        sid, title = items
        logging.info(f"Analyzing {sid} {title}...")

        try:
            # 1. Load historical data
            data_path = f"data/{sid}.csv"
            if not os.path.exists(data_path):
                logging.warning(f"Data file for {sid} missing.")
                return

            df_f = pd.read_csv(data_path, index_col=0, parse_dates=True, date_format='%Y-%m-%d')
            if df_f.empty:
                return

            # Keep 5 years of daily data
            df_f = df_f.iloc[-255 * 5:]
            df_f = df_f.apply(pd.to_numeric, errors="coerce")

            # 2. Fetch external data
            df_rev = self.fetcher.get_revenue(sid)
            df_eps = self.fetcher.get_eps(sid)
            df_prof = self.fetcher.get_profitability(sid)
            df_investors = self.fetcher.get_investors(sid)
            price = self.fetcher.get_price(sid)

            # 3. Calculate indicators
            df_daily, df_weekly, df_monthly = kd(df_f)
            df_ma = ma(df_f)

            # 4. Prepare data for plotting
            eps4q_sum = df_eps.eps.head(4).sum() if not df_eps.empty else 0
            
            # Display range (approx 300 days)
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

            # 5. Generate visual report
            output_file = f"pic/{sid}.png"
            self.visualizer.draw_report(sid, title, plot_data, output_file)

        except Exception as e:
            logging.error(f"Unexpected error analyzing {sid}: {e}")

def main():
    parser = argparse.ArgumentParser(description="KDTrace Stock Analysis Engine")
    parser.add_argument("--cores", type=int, default=10, help="Number of CPU cores to use")
    parser.add_argument("--reload", action="store_true", help="Force reload data from CNYES")
    parser.add_argument("--sid", help="Specific stock ID to analyze")
    args = parser.parse_args()

    # Initialize components
    fetch_config = FetchConfig(reload=args.reload)
    fetcher = CNYESFetcher(fetch_config)
    visualizer = StockVisualizer()
    analyzer = StockAnalyzer(fetcher, visualizer)

    try:
        if args.sid:
            # Analyze single stock
            stocks = [(args.sid, "Manual")]
        else:
            # Batch analyze TSE list
            stocks = get_list("tse")
            logging.info(f"Starting batch analysis for {len(stocks)} stocks using {args.cores} cores...")

        if args.cores > 1:
            with Pool(args.cores) as p:
                p.map(analyzer.analyze_stock, stocks)
        else:
            for item in stocks:
                analyzer.analyze_stock(item)

        # Generate final HTML dashboard
        html_generator()
        
    except Exception as e:
        logging.error(f"Main loop error: {e}")

if __name__ == "__main__":
    main()
