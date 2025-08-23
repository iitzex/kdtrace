import sys
import platform
from datetime import datetime, timedelta
from multiprocessing import Pool

import pandas as pd

import fetch
from fetch import get_revenue, get_profitability, get_eps, get_investors
from indicator import kd, ma
from gen_html import html_generator
from util import get_list


def set_font():
    from pandas.plotting import register_matplotlib_converters
    register_matplotlib_converters()

    import matplotlib.font_manager as fm
    if platform.system() == "Darwin":
        font = fm.FontProperties(
            fname="/System/Library/Fonts/STHeiti Medium.ttc", size=14
        )
    else:
        font = fm.FontProperties(
            fname="/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc", size=14
        )

    return font


def drawing(
    sid,
    title,
    num,
    df_f,
    df_daily,
    df_weekly,
    df_monthly,
    df_ma,
    df_revenue,
    df_eps,
    df_profitability,
    df_investors,
):
    import matplotlib as mpt
    import matplotlib.pyplot as plt
    font = set_font()

    mpt.rc("xtick", labelsize=10)
    mpt.rc("ytick", labelsize=10)

    plt.subplots_adjust(
        top=0.92, bottom=0.08, left=0.10, right=0.95, hspace=0.15, wspace=0.25
    )

    fig = plt.figure(figsize=(26, 13))
    x0 = plt.subplot2grid((6, 2), (0, 0), rowspan=2)
    x1 = plt.subplot2grid((6, 2), (2, 0))
    x2 = plt.subplot2grid((6, 2), (3, 0))
    x3 = plt.subplot2grid((6, 2), (4, 0), rowspan=2)
    # x4 = plt.subplot2grid((6, 2), (5, 0))
    y0 = plt.subplot2grid((6, 2), (0, 1), rowspan=2)
    y1 = plt.subplot2grid((6, 2), (2, 1), rowspan=2)
    y2 = plt.subplot2grid((6, 2), (4, 1), rowspan=2)

    begin = df_f.index[-1].to_pydatetime() - timedelta(num)
    begin = datetime(begin.year, begin.month, 1) - timedelta(1)

    df = df_f.loc[df_f.index >= begin]
    ma = df_ma.loc[df_ma.index >= begin]

    x0.plot(df.index, df.close, "r", alpha=0.5, linewidth=2.5, zorder=1)
    x0.plot(ma.index, ma.w_5, "#10008C", alpha=0.8, linewidth=1.5, zorder=2)
    x0.plot(ma.index, ma.w_20, "#3A2AC8", alpha=0.8, linewidth=1.5, zorder=2)
    x0.plot(ma.index, ma.w_60, "#46B030", alpha=0.8, linewidth=1.5, zorder=2)
    x0.plot(ma.index, ma.w_120, "#962DE1", alpha=0.8, linewidth=1.5, zorder=2)
    x0.plot(ma.index, ma.w_250, "#FF8E43", alpha=0.8, linewidth=1.5, zorder=2)
    x0.set_title("價格/均線", loc="right", fontproperties=font)
    x0.get_yaxis().tick_right()
    x0.yaxis.grid(True)
    # x0.get_xaxis().set_visible(False)

    x1.bar(df.index, df.amount, 0.7, color="#E11E17", edgecolor="none")
    x1.set_title("成交量", loc="right", fontproperties=font)
    x1.get_yaxis().tick_right()
    x1.get_xaxis().set_visible(False)

    # df_bias = pd.concat([df_f.close, df_ma.w_20], axis=1)
    # df_bias['bias'] = (df_bias.close - df_bias.w_20) / df_bias.w_20 * 100
    # # print(df_bias)
    # for i, row in df_bias.iterrows():
    #     print(i, "%.2f %.2f %+3.2f" % (row['close'], row['w_20'], row['bias']))

    df_daily = df_daily.loc[df_daily.index >= begin]
    highK = df_daily[df_daily.k >= 80]
    lowK = df_daily[df_daily.k <= 20]
    # x2.plot(df_daily.index, df_daily.k, "r", df_daily.index,
    #         df_daily.d, "c", alpha=0.5, linewidth=1)
    # x2.plot(highK.index, highK.k, "ro", mec="r", markersize=3)
    # x2.plot(lowK.index, lowK.k, "go", mec="g", markersize=3)
    # x2.set_title("日KD", loc="right", fontproperties=font)

    df_weekly = df_weekly.loc[df_weekly.index >= begin]
    WhighK = df_weekly[df_weekly.wk >= 80]
    WlowK = df_weekly[df_weekly.wk <= 20]
    # x3.plot(df_weekly.index, df_weekly.wk, "r", df_weekly.index,
    #         df_weekly.wd, "c", alpha=0.5, linewidth=1)
    # x3.plot(WhighK.index, WhighK.wk, "ro", mec="r", markersize=3)
    # x3.plot(WlowK.index, WlowK.wk, "go", mec="g", markersize=3)
    # x3.set_title("週KD", loc="right", fontproperties=font)

    df_monthly = df_monthly.loc[df_monthly.index >= begin]
    MhighK = df_monthly[df_monthly.mk >= 80]
    MlowK = df_monthly[df_monthly.mk <= 20]
    x2.plot(df_daily.index, df_daily.k, "r", df_daily.index,
            df_daily.d, "c", alpha=0.5, linewidth=1)
    x2.scatter(highK.index, highK.k, c="#E87373", s=6)
    x2.scatter(lowK.index, lowK.k, c="#94e9a2", s=6)
    x2.plot(df_weekly.index, df_weekly.wk, "r", df_weekly.index,
            df_weekly.wd, "c", alpha=0.5, linewidth=1)
    # x2.plot(WhighK.index, WhighK.wk, "ro", mec="r", markersize=3)
    # x2.plot(WlowK.index, WlowK.wk, "go", mec="g", markersize=3)
    x2.scatter(WhighK.index, WhighK.wk, c="#A50707", s=6)
    x2.scatter(WlowK.index, WlowK.wk, c="#06941e", s=6)
    x2.plot(df_monthly.index, df_monthly.mk, "r", df_monthly.index,
            df_monthly.md, "c", alpha=0.5, linewidth=1)
    # x2.plot(MhighK.index, MhighK.mk, "ro", mec="r", markersize=3)
    # x2.plot(MlowK.index, MlowK.mk, "go", mec="g", markersize=3)
    x2.scatter(MhighK.index, MhighK.mk, c="#530303", s=6)
    x2.scatter(MlowK.index, MlowK.mk, c="#02360A", s=6)
    x2.set_title("KD", loc="right", fontproperties=font)
    x2.set_ylim(0, 100)
    x2.get_xaxis().set_ticklabels([])
    x2.get_yaxis().set_visible(False)
    x2.tick_params(colors="w")

    x3.bar(df_investors.index, df_investors.total, width=0.4, color="#068ee9")
    x3.bar(df_investors.index, df_investors.foreign,
           width=0.25, color="#0cf5f1")
    x3.get_yaxis().tick_right()
    x3.set_title(f"法人", loc="right", fontproperties=font)

    y0.set_title(f"{sid}, {title}    月營收/年增率",
                 loc="right", fontproperties=font)
    y0.plot(df_f.index, df_f.close, "r", alpha=0.7, linewidth=2, zorder=1)
    y0.yaxis.grid(True)
    p = y0.twinx()
    p.bar(df_revenue.index, df_revenue.revenue, width=15,
          color="#ecf3f6", edgecolor="#FFA000", alpha=0.7, zorder=3)
    q = y0.twinx()
    q.plot(df_revenue.index, df_revenue.revenueYOY,
           "#085dcb", alpha=0.9, zorder=2)
    # q.scatter(df_revenue.index, df_revenue.revenueYOY, color="#c38d9e", s=4)
    q.spines["right"].set_position(("axes", 1.1))
    q.spines["right"].set_visible(True)
    q.set_ylim(-40, 60)

    y1.set_title("EPS", loc="right", fontproperties=font)
    y1.plot(df_f.index, df_f.close, "r", alpha=0.7, linewidth=1, zorder=1)
    y1.get_yaxis().set_visible(False)
    p = y1.twinx()
    p.bar(df_eps.index, df_eps.eps, width=40, color="#b8d8d8",
          edgecolor="#00838f", alpha=0.7, zorder=2)
    q = y1.twinx()
    # q.scatter(df_eps.index, df_eps.epsYOY, color="#c38d9e", s=4)
    q.plot(df_eps.index, df_eps.epsYOY, "#a614d6", alpha=0.9, zorder=1)
    q.spines["right"].set_position(("axes", 1.1))
    q.spines["right"].set_visible(True)
    q.set_ylim(-40, 70)

    y2.set_title("毛利率/營益率/稅後營益率", loc="right", fontproperties=font)
    y2.plot(df_f.index, df_f.close, "r", alpha=0.2, linewidth=1, zorder=1)
    y2.get_yaxis().set_visible(False)
    p = y2.twinx()
    p.plot(df_profitability.index, df_profitability.grossMargin, c="g")
    p.plot(df_profitability.index, df_profitability.operatingMargin, c="b")
    p.plot(df_profitability.index, df_profitability.profitMargin, c="c")
    y2.get_xaxis().set_visible(False)

    # div = dividend * 100 / df.close[-1]
    # chip = concentrate(sid)

    # subtitle = f"{sid}, {title}, {price}, ({div:.1f}%), {str(chip)}, {{{val}}}"
    # subtitle = f"{sid}, {title}"
    # fig.suptitle(subtitle, fontproperties=font)

    fig.subplots_adjust(bottom=0.1, hspace=0.5)
    fig.set_facecolor("white")
    try:
        plt.savefig("pic/" + sid + ".png", bbox_inches="tight")
    except ValueError as e:
        print(sid, e)
    plt.close()


def gen_pic(items):
    sid, title = items
    print(f"{sid}, {title}")

    df_f = pd.read_csv("data/" + str(sid) + ".csv",
                       index_col=0, parse_dates=True, date_format='%Y-%m-%d')
    df_f = df_f.iloc[-255 * 5:]
    df_f = df_f.apply(pd.to_numeric, errors="coerce")

    df_revenue = get_revenue(sid)
    df_eps = get_eps(sid)
    df_profitability = get_profitability(sid)
    df_investors = get_investors(sid)

    df_daily, df_weekly, df_monthly = kd(df_f)
    df_ma = ma(df_f)

    index_num = min(300, len(df_f.index))

    close_min = df_f["close"].min()
    close_max = df_f["close"].max()
    df_f["close_p"] = 100 * (df_f["close"] - close_min) / \
        (close_max - close_min)

    # df_n = df_f.reindex(df_gain.index, method="nearest")
    # df_n["eps_p"] = df_gain["eps_p"]
    # df_n = df_n[-2:]
    # df_p = df_n["eps_p"] - df_n["close_p"] > 10
    # pval = round((df_n["eps_p"] - df_n["close_p"]).sum() / 2, 1)
    # df_g = df_gain[-4:]["eps"] > 0

    # df_a = df_f.reindex(df_revenue.index, method="nearest")
    # df_a["pro_p"] = df_revenue["pro_p"]
    # df_a = df_a[-4:]
    # aval = round((df_a["pro_p"] - df_a["close_p"]).sum() / 4, 1)

    # val = round(pval + aval, 1)

    # if df_p.all() and df_g.all():
    #     msg = f"{sid}, {title}, {val}"
    #     print("\t\t+" + msg)
    #     with open("filter.csv", "a") as f:
    #         f.write(msg + "\n")

    try:
        drawing(
            sid,
            title,
            index_num,
            df_f,
            df_daily,
            df_weekly,
            df_monthly,
            df_ma,
            df_revenue,
            df_eps,
            df_profitability,
            df_investors,
        )
    except Exception as e:
        print(f"Error processing {sid}: {e}")


def sort_filter():
    fil = pd.read_csv("filter.csv", header=None)
    fil = fil.sort_values(by=[2], ascending=False)
    fil.to_csv("filter.csv", index=False, header=False)

    d_str = datetime.now().strftime("%Y-%m-%d")
    fil.to_csv(f"filter/{d_str}.csv", index=False, header=False)


if __name__ == "__main__":
    fetch.RELOAD = False

    args = sys.argv
    cores = 1
    if len(args) > 1:
        cores = int(args[1])

    # gen_pic(("6288", "聯嘉"))

    try:
        with open("filter.csv", "w") as f:
            f.write("")
        f.close()

        tse = get_list("tse")
        print(len(tse))
        Pool(cores).map(gen_pic, tse)

        # sort_filter()
        html_generator()
    except OSError as e:
        print(e)
