# KDTrace 股市分析系統

KDTrace 是一個現代化的台灣股市資料爬取、技術指標分析及報表生成系統。本專案經過全面重構，採用物件導向設計 (OOP)、嚴格的類型標註 (Type Hinting) 以及 `uv` 依賴管理，具備高度的穩定性與擴充性。

## 🌟 核心特色

- **現代化架構**：全面物件導向化，職責分離 (SRP)，代碼易於維護與擴充。
- **高效能爬取**：
  - `Crawler` 模組支援自動重試與隨機延遲。
  - `CNYESFetcher` 透過 `requests.Session` 提升財報資料抓取效能。
- **精品化設計**：
  - **進階視覺化**：自訂 `StockVisualizer` 產生包含 KDJ、均線、法人買賣超、營收及 EPS 的高品質分析圖表。
  - **專業報表**：生成響應式、淺色模式設計的 HTML 分析儀表板。
- **魯棒性 (Robustness)**：
  - 集中化 SSL 安全管理，解決 TWSE 等網站的舊型證書相容性問題。
  - 智慧緩存機制，減少重複請求，保護 API 資源。

## 🛠️ 技術棧

- **語言**: Python 3.12+
- **依賴管理**: [uv](https://github.com/astral-sh/uv)
- **資料處理**: `pandas`, `numpy`
- **圖表繪製**: `matplotlib`
- **網路請求**: `requests`, `urllib3`
- **介面解析**: `beautifulsoup4`, `lxml`

## 🚀 快速開始

### 1. 安裝與設定

本專案建議使用 `uv` 進行快速安裝：

```bash
# 安裝依賴
uv sync
```

### 2. 獲取股票清單

更新最新的上市 (TSE) 股票名單：

```bash
uv run python src/gen_list.py
```

### 3. 爬取歷史股價

```bash
uv run python src/crawl.py
```

### 4. 執行綜合分析與圖表生成

分析全部股票（支援多核心平行處理）：

```bash
uv run python src/main.py --cores 8
```

或是分析特定股票：

```bash
uv run python src/main.py --sid 2330 --reload
```

## 📂 專案結構

- `src/main.py`: 系統入口，調度分析 (`StockAnalyzer`) 與視覺化 (`StockVisualizer`)。
- `src/crawl.py`: 股價爬取核心。
- `src/fetch.py`: 鉅亨網 (CNYES) 財報模型與資料抓取 (`CNYESFetcher`)。
- `src/indicator.py`: 技術指標 (KD, MA) 計算邏輯。
- `src/gen_html.py`: 現代化 HTML 報表生成器 (`HtmlGenerator`)。
- `src/utils/`: 工具包（`logger.py` 集中式 logging、`http.py` SSL/Session、`stocks.py` CSV 讀取）。
- `src/del_wrong.py`: 靈活的資料裁切/回滾工具（支援前/後裁切）。
- `src/filter.py`: 基於基本面的股票篩選器。
- `src/rate.py`: 殖利率資料採集與 Excel 報表生成。

## ⚙️ 進階操作

### 資料裁切 (Data Trimming)
當資料發生錯誤需要回滾時，可使用 `src/del_wrong.py`：

```bash
# 刪除所有資料檔案的前 50 筆紀錄
uv run python src/del_wrong.py --count 50 --pos first
```

### 篩選潛力股
執行 `src/filter.py` 根據預設條件（EPS 與營收成長）篩選股票：

```bash
uv run python src/filter.py
```

## 📝 授權
[MIT License](LICENSE)
