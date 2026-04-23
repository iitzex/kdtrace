# TODO

## 優先 (待使用者執行)

```
task                                              | why
uv run python src/main.py --cores 10 --force     | revenue/margins 修正後重畫所有 PNG
停用 2pm 排程 (trig_01Fgmk7AZ3dNegqbfUyRzoqo)    | 事項本地已完成，已停用但建議從 claude.ai 確認
```

## 已完成 ✓

### Tier 1 — 真會咬人的
```
item                            | fix                                        | commit
multiprocessing spawn logger    | Pool initializer 呼叫 setup_logger()      | 19746f7
JSON cache 原子寫入             | tmp + os.replace                          | 3475e82
revenue/profitability base_ts   | pytest mock session，4 tests pass         | 69c4515
--force 連動 --reload           | fetch_config.reload = reload or force     | 70ebe6d
```

### Tier 2 — 品質提升
commit `7b0c8dd`：--cores 預設 `os.cpu_count()` / `FetchConfig.cache_ttl_seconds` / gen_list `--dry-run` / filter 條件可設定 / del_wrong `--mode check` exit 1 / ruff E/F/I（main.py E402 per-file ignore）。

### Tier 3 — 基礎設施（OTC 跳過）
commit `502f9c9`：
- utils smoke tests (setup_logger idempotent / get_list / get_session / CustomHttpAdapter)
- rate.py 按 column name 找 table（不再依賴 frames[0] 位置）

### 效能（歷史）
A1 savefig -tight（-40%）、A3 增量跳過、A4 ThreadPoolExecutor 併發（-54% cold）、CNYESFetcher requests.Session 重用（cold fetch_phase -33%）。

### P3 — 文字整理
commit `cc0e035`：docstring 中英統一（9 檔），行為未變。

## 延後 / 不做

```
item                                       | reason
A2 plot 層 subplot 結構重整                | 潛在 -15% × 1067 支 / 10 cores ≈ -1.5s；不值 visual regression 風險
OTC (tpex.org.tw) 支援                     | 使用者明示跳過
fetch.py 5 個 get_* 改資料驅動             | 每 method 3-4 行；抽象成本 > 收益
抽 parallel_map() 共用 Pool 樣板           | 只 2 個 caller；DRY 未痛
```

## 已知問題 (外部 / 上游)

```
issue                                                | impact           | action
src/fetch.get_price 讀 column "21"                   | 取值依賴假設     | 查 CNYES 文件 / 實測欄位意義
stock 3454 的 investors CNYES 偶發 500               | 單支股票遺失圖   | 上游問題，容錯已處理
README Python 3.12+ vs pyproject 3.14+ 不一致        | 文件不一致       | 需使用者決策
```

## Ops

```
task                            | cadence
crawl.py 每日更新                | 交易日每天跑一次（支援自動追趕缺漏日期）
gen_list.py --dry-run 審視      | 每季跑一次，確認不會誤刪
main.py                        | crawl 後跑；增量跳過會幫忙省時
pytest                         | commit 前；目前 9 tests，< 1s
ruff check src/ tests/         | commit 前
```
