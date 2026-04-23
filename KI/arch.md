# KDTrace 架構

台灣股市資料抓取 → 技術指標計算 → 圖表生成 → HTML 儀表板的 batch pipeline。

目前主線已從單一腳本式 orchestrator 演進為：

`CLI main.py → AnalysisService / ReportService → StockAnalyzer / StockVisualizer → fetch / indicator / gen_html / utils`

## 目錄結構

```
kdtrace/
├── src/                  # 所有 Python 程式碼
│   ├── main.py           # CLI 入口 + service orchestration + analyzer / visualizer
│   ├── crawl.py          # TWSE 每日 OHLC 爬蟲 → data/{sid}.csv
│   ├── fetch.py          # CNYES 財報抓取器 → json/{sid}_*.json
│   ├── filter.py         # 基本面篩選 → filter.csv + filter.html
│   ├── gen_list.py       # TWSE ISIN 股票清單 → tse.csv
│   ├── gen_html.py       # 股票 HTML 報表 (CSS + img 卡片)
│   ├── del_wrong.py      # CSV 修補工具 (trim/dedup/sort/check)
│   ├── rate.py           # 殖利率 → rate.xlsx
│   ├── indicator.py      # KD / MA 計算
│   └── utils/            # 共用模組
│       ├── logger.py     # setup_logger() 冪等；CLI entry 統一呼叫
│       ├── http.py       # get_request (SSL SECLEVEL=1 + legacy fallback)
│       └── stocks.py     # get_list (CSV → [(sid, title), ...])
├── data/                 # OHLC 時間序列 ({sid}.csv)
├── json/                 # CNYES JSON 快取 ({sid}_{category}.json，24h TTL)
├── pic/                  # matplotlib PNG 圖表 ({sid}.png)
├── tse.csv               # 主股票清單
├── tse.html              # 主 HTML 儀表板 (由 main.py 生成)
├── filter.csv / .html    # 篩選結果
├── rate.xlsx             # 殖利率報表
├── pyproject.toml        # uv 管理
├── uv.lock               # 鎖檔
└── .python-version       # 3.14
```

## 模組職責

```
module      | role                                  | entry    | depends on
main.py     | CLI / service / analyzer / visualizer | CLI      | fetch, indicator, gen_html, utils
crawl.py    | TWSE 股價爬蟲 + row validation        | CLI      | utils.http
fetch.py    | CNYES 財報 (5 endpoints) + retry/cache| import   | utils.http
filter.py   | 基本面篩選                    | CLI      | fetch, gen_html, utils
gen_html.py | HTML 報表生成                 | import   | utils.stocks
gen_list.py | TWSE ISIN → tse.csv           | CLI      | utils.http, bs4
del_wrong.py| CSV 修補                      | CLI      | -
rate.py     | 殖利率爬蟲 → xlsx             | CLI      | utils.http, utils.stocks
indicator.py| KD (daily/weekly/monthly), MA | import   | pandas, numpy
```

## main.py 內部角色

```
type / function      | responsibility
AppPaths             | 集中管理 data/json/pic 與主股票清單名稱
AnalysisResult       | 單支股票分析完成後的中介資料物件；供 visualizer 消費
StockAnalyzer        | 讀價格資料、抓遠端資料、算指標、組裝 AnalysisResult
StockVisualizer      | matplotlib 畫 7 格圖表，輸出 pic/{sid}.png
AnalysisService      | 管理股票清單、profile / batch / single-stock 執行模式
ReportService        | 管理主 HTML 報表輸出
```

## 資料流

```
gen_list.py    → tse.csv
crawl.py       → data/{sid}.csv          (每日 append 一列 OHLC)
main.py CLI    → AnalysisService
               → StockAnalyzer.read_csv(data/{sid}.csv)
               → fetch.py → json/{sid}_*.json (5 endpoints, 24h TTL)
               → indicator.kd/ma
               → AnalysisResult
               → StockVisualizer → pic/{sid}.png
               → ReportService / gen_html.generate() → tse.html
```

## 外部依賴 (API / site)

```
source                                 | used by       | note
www.twse.com.tw/exchangeReport/MI_INDEX| crawl.py      | legacy SSL，需 SECLEVEL=1 + verify=False fallback
isin.twse.com.tw                       | gen_list.py   | 同上；Big5-HKSCS 編碼
marketinfo.api.cnyes.com/…/revenue     | fetch.py      | `to` 是起算點，傳 base_ts (5y ago)
marketinfo.api.cnyes.com/…/eps         | fetch.py      | 同上，resolution=Q
marketinfo.api.cnyes.com/…/profitability| fetch.py     | 同上
marketinfo.api.cnyes.com/…/3majorInvestors| fetch.py   | `to` 是截止日，傳 to_ts (now) [commit 8ec7a84]
ws.api.cnyes.com/…/quote               | fetch.py      | 現價 (column 21)；502/503/504 會短退避重試
stock.wespai.com/rate114               | rate.py       | 殖利率表 (pd.read_html)
```

## Runtime 約定

```
item                  | rule
Python 呼叫           | uv run python src/<module>.py （禁止直接 python）
CWD                   | 一律在專案根目錄執行；所有路徑都是 CWD-relative
依賴管理              | uv add / uv sync；禁止 pip install
logging               | CLI entry 呼叫 setup_logger()；module 內用 logging.getLogger(__name__)
main.py 模式          | `--profile N` / `--sid <id>` / batch all-stocks 三種路徑已分流
```

## 效能設計

```
optimization              | impact                           | flag/機制
matplotlib Agg (implicit) | 預設；不打開 interactive backend | -
savefig 不用 tight_bbox   | savefig -40%                     | -
5 CNYES endpoint 併發     | cold fetch -76%                  | ThreadPoolExecutor
增量跳過 (mtime 比較)     | 無變動重跑近零成本               | main.py --force 可繞過
Pool 多核                 | 預設 10 cores                    | main.py --cores N
profile harness           | per-stage timing 表              | main.py --profile N
CNYES quote retry         | 降低單次 502/503/504 失敗率      | fetch.py retry/backoff
```

## Cache 語意

```
layer          | path               | TTL/invalidation
CNYES JSON     | json/{sid}_*.json | 24h (fetch.py 檢查 mtime)
              |                    | reload / stale 時會重抓；暫時性 HTTP 錯誤會 retry
PNG           | pic/{sid}.png      | main.py _is_up_to_date: mtime vs data+json
              |                    | --force 強制重畫
```

## 資料正確性保護

```
area          | guard
fetch.py      | 驗證 time / required field 存在、list 長度一致、數值 coercion、去重排序
crawl.py      | TWSE row validation；非數字欄位、缺欄、非法 sid 直接略過
tests         | 主流程 smoke tests + fetch params regression + crawl/html smoke
```

## 已知限制

- OTC (tpex.org.tw) 在 `crawl.fetch_otc_data` 是 placeholder（`pass`），尚未實作
- `fetch.py` 的 `get_price` 讀 column "21"，欄位意義沒有文件佐證，僅依現況假設
- 1 支股票（3454）的 CNYES `investors` endpoint 偶發 500，上游問題
- 右下三率圖的異常大多來自上游 `profitMargin` 真實負值，不是本地計算錯誤；目前已加 legend 與 0 baseline 提升可讀性
