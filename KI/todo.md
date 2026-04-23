# TODO

## 優先 (待使用者執行)

```
task                                              | why
uv run python src/main.py --cores 10 --force     | 1066 支股票 revenue/margins 快取空，重跑讓新資料上 PNG
```

## Tier 1 — 真會咬人的

```
item                                                  | why
驗證 multiprocessing worker 有跑 setup_logger()       | fork→OK，spawn→workers 內 logging 可能失效；Python 3.14 macOS 預設可能是 spawn，未驗證
JSON cache 原子寫入 (tempfile + rename)               | 剛才發生過「200 OK 空陣列」寫成假資料；rename 可搭配 sanity check 避免寫入空 JSON 當 cache
revenue/profitability 的 `to=base_ts` 加 smoke test   | 這 bug 是 silent failure（200 OK 空陣列），沒 assert 很容易復發
--force 要不要自動連帶 --reload                       | 目前 --force 只重畫但吃快取；cache 若還在 24h 內且內容有問題，--force 救不了
```

## Tier 2 — 品質提升

```
item                                        | why
--cores 預設改 os.cpu_count()               | 硬 code 10 不一定適合所有環境
FetchConfig.cache_ttl_seconds 可設定        | 24h hardcode；抓快一點或慢一點都只改一處
gen_list.py 加 --dry-run                    | cleanup_obsolete_data 會直接 os.remove，誤刪無法救
filter.py 條件可設定 (EPS/revYOY 門檻)     | 目前寫死 `.iloc[:3] > 0`；改 config 易測試不同策略
del_wrong.py --mode check 的 exit code      | 目前只 warn，不 fail；可做 crawl 後自動健康檢查
ruff 基本規則 (E/F/I)                       | 幾分鐘就能設定；統一 import 排序、未使用變數
```

## Tier 3 — 基礎設施

```
item                        | why
最低限度 pytest (utils/)    | CLAUDE.md 有 `uv add --dev pytest`；先從 utils 開始成本低
OTC (tpex.org.tw) 支援      | src/crawl.fetch_otc_data 目前是 pass；上櫃股完全沒資料
rate.py 用 column name      | `frames[0]` + 固定欄名順序，table 結構一變就爆
```

## 效能優化 (可選)

```
id | target                  | potential          | risk | status
A2 | plot 層 subplot 結構重整| warm savefig -15%? | 中   | pending
```

A1（savefig bbox=tight 移除，-40%）、A3（增量跳過）、A4（fetch ThreadPoolExecutor，-54% cold）、CNYESFetcher requests.Session 重用（cold fetch_phase -33%）已完成。

## 已知問題 (外部 / 上游)

```
issue                                                | impact           | action
src/fetch.get_price 讀 column "21"                   | 取值依賴假設     | 查 CNYES 文件 / 實測欄位意義
stock 3454 的 investors CNYES 偶發 500               | 單支股票遺失圖   | 上游問題，容錯已處理
README Python 3.12+ vs pyproject 要 3.14+            | 文件不一致       | 看要改哪一邊（CLAUDE.md 預設 3.12）
```

## Ops

```
task                            | cadence
crawl.py 每日更新                | 交易日每天跑一次（有 argparse 支援自動追趕缺漏日期）
gen_list.py                    | 每季或偵測到新股票時跑一次
main.py                        | crawl 後跑；增量跳過會幫忙省時
```

## P3 / 不急

```
item                                       | note
docstring 中英統一 (CLAUDE.md 要求繁中)   | 不影響行為，純文字工程，逐步處理
```

## 已評估後不做

```
item                                       | reason
fetch.py 5 個 get_* 改資料驅動             | 每個 method 才 3-4 行；抽象成本 > 收益
抽 parallel_map() 共用 Pool 樣板           | 只 2 個 caller；DRY 未痛
```
