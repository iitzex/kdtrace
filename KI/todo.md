# TODO

## 待決策（需使用者）

```
item                                              | note
push 到 GitHub                                    | 本地有 11 個未 push commits
README 標 Python 3.12+，pyproject 要 3.14+        | 擇一修正；CLAUDE.md 預設 3.12
從 claude.ai 確認 routine 已停                    | trig_01Fgmk7AZ3dNegqbfUyRzoqo（已 disable）
```

## 已知問題（上游 / 外部，無需動作）

```
issue                                                | impact           | note
src/fetch.get_price 讀 column "21"                   | 取值依賴假設     | CNYES 沒文件，實測可動但低價值
stock 3454 的 investors CNYES 偶發 500               | 單支股票遺失圖   | 上游問題，容錯已處理
```

## Ops 流程

```
task                              | cadence
uv run python src/crawl.py        | 交易日每天；支援自動追趕缺漏日期
uv run python src/gen_list.py --dry-run | 每季；先 dry-run 審視再真跑
uv run python src/main.py --cores 10    | crawl 後；增量跳過 → 大多數時候近 0s
uv run pytest                     | commit 前；9 tests < 1s
uv run ruff check src/ tests/     | commit 前；E/F/I 規則
```

## 後續建議（架構 / 品質）

```
item                                              | note
明文化資料模型（PriceBar / RevenueSeries / EPS 等） | 降低隱含欄位約定；API 欄位漂移時較早失敗
集中管理 settings / paths                         | data/json/pic/tse.csv/cache TTL/years_back 不再散落
PNG 快取判斷從 mtime 升級到 metadata / hash       | 降低誤判，保留分析版本與輸入依賴
HTML 卡片增加摘要資訊                             | 現價、近四季 EPS、最近營收 YOY、更新時間
補批次可觀測性                                    | cache hit/miss、失敗分類、endpoint 耗時、成功率
```

## 已完成（參考用）

### 本 session 架構與效能

```
commit    | summary
088fd8d   | refactor: utils/ 套件集中 logging（setup_logger 冪等）
0645ccb   | chore: Python 程式搬到 src/
b9c9d9a   | docs: README 路徑更新到 src/
9ab86d9   | docs: KI/arch.md + KI/todo.md
```

### 效能優化（warm 14s → 0.x 秒增量；cold 40s → 18s）

```
commit    | summary                                                   | gain
f197ec3   | perf: savefig -tight + ThreadPoolExecutor + 增量跳過       | -40% savefig / -54% cold fetch
c3f0108   | perf: CNYESFetcher 重用 requests.Session                  | -33% cold fetch_phase
```

### 修正

```
commit    | summary
996e3e1   | fix: revenue/profitability 用 base_ts（CNYES silent bug）
19746f7   | fix: spawn worker 跑 setup_logger()（Pool initializer）
3475e82   | fix: JSON cache 原子寫入 (tmp + os.replace)
70ebe6d   | feat: --force 連動 --reload
```

### 品質 / 測試 / 文件

```
commit    | summary
69c4515   | test: revenue/profitability base_ts smoke tests (4 pass)
7b0c8dd   | chore: Tier 2（--cores 預設、cache TTL、gen_list dry-run、filter 條件、del_wrong exit code、ruff）
502f9c9   | test: utils smoke tests；rate.py 按 column name 選 table
cc0e035   | docs: docstring 中英統一（9 檔）
worktree  | P0: fetch/crawl 資料驗證 + indicator/crawl/html/main smoke tests（15 pass）
worktree  | P1: main.py 抽出 AnalysisResult / AppPaths；分析與繪圖解耦（15 pass）
worktree  | P2: AnalysisService / ReportService + CLI 模式分流（16 pass）
```

## 已延後 / 不做

```
item                                | reason
A2 plot 層 subplot 結構重整         | 潛在 -1.5s × 全量；不值 visual regression 風險
OTC (tpex.org.tw) 支援              | 使用者明示跳過
fetch.py 5 個 get_* 改資料驅動      | 每 method 3-4 行；抽象成本 > 收益
抽 parallel_map() 共用 Pool 樣板    | 只 2 個 caller；DRY 未痛
```
