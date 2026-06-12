# 新竹房地產成交資訊 / Hsinchu Real-Estate Closed Transactions

每週彙整新竹地區成交資訊，提供 Markdown（易讀）與 CSV（可匯入試算表）兩種格式，
並彙總為單一 `hsinchu-transactions-ALL.csv` 供房市追蹤分析。

## 檔案

| 期間 | 筆數 | Markdown | CSV |
| --- | ---: | --- | --- |
| 2026/01/13 ~ 01/19 | 72 | [md](hsinchu-transactions-2026-01-13_01-19.md) | [csv](hsinchu-transactions-2026-01-13_01-19.csv) |
| 2026/01/20 ~ 01/26 | 62 | [md](hsinchu-transactions-2026-01-20_01-26.md) | [csv](hsinchu-transactions-2026-01-20_01-26.csv) |
| 2026/01/27 ~ 02/02 | 51 | [md](hsinchu-transactions-2026-01-27_02-02.md) | [csv](hsinchu-transactions-2026-01-27_02-02.csv) |
| 2026/02/03 ~ 02/09 | 59 | [md](hsinchu-transactions-2026-02-03_02-09.md) | [csv](hsinchu-transactions-2026-02-03_02-09.csv) |
| 2026/02/10 ~ 02/16 | 38 | [md](hsinchu-transactions-2026-02-10_02-16.md) | [csv](hsinchu-transactions-2026-02-10_02-16.csv) |
| 2026/02/24 ~ 03/02 | 38 | [md](hsinchu-transactions-2026-02-24_03-02.md) | [csv](hsinchu-transactions-2026-02-24_03-02.csv) |
| 2026/03/10 ~ 03/16 | 63 | [md](hsinchu-transactions-2026-03-10_03-16.md) | [csv](hsinchu-transactions-2026-03-10_03-16.csv) |
| 2026/05/26 ~ 06/01 | 84 | [md](hsinchu-transactions-2026-05-26_06-01.md) | [csv](hsinchu-transactions-2026-05-26_06-01.csv) |
| 2026/06/02 ~ 06/08 | 61 | [md](hsinchu-transactions-2026-06-02_06-08.md) | [csv](hsinchu-transactions-2026-06-02_06-08.csv) |
| **合計** | **528** | — | [**ALL.csv**](hsinchu-transactions-ALL.csv) |

`hsinchu-transactions-ALL.csv` 額外含 `週期`、`縣市` 兩欄，方便依時間/區域做樞紐分析、追蹤趨勢。

## 我的物件追蹤

以 `ALL.csv` 為比較基準，自動估算並追蹤自有物件（德鑫御天地 14D）合理售價：

| 檔案 | 說明 |
| --- | --- |
| [my-property-14D.md](my-property-14D.md) | 物件資料、本期估值、建議掛牌價、估值快照紀錄、待辦 |
| [my-property-14D-log.csv](my-property-14D-log.csv) | 每次執行累積的估值快照（趨勢用） |

每週新資料併入後重新執行即更新估值並新增一筆快照：

```bash
python3 scripts/track_property.py        # 預設今日；或帶入 YYYY-MM-DD
```

## 欄位說明

| 欄位 | 說明 |
| --- | --- |
| 週期 | （僅 ALL）成交資料所屬週別 |
| 縣市 | （僅 ALL）由地址解析（新竹市／新竹縣／苗栗縣） |
| 編號 | 該週清單序號 |
| 標題 | 物件銷售標題 |
| 社區 | 社區/建案名稱（由地址【】解析，無則留空） |
| 地址 | 門牌地址 |
| 行政區 | 由地址解析之行政區 |
| 成交總價(萬) | 成交總價，單位：萬元 |
| 成交單價(萬/坪) | 建坪扣除車位後之概估單價；原文為公式者取其計算結果 |
| 樓層 | 所在樓層 / 總樓層 |
| 屋齡 | 屋齡（年）；原文未載則為「未提供」 |
| 建物坪數 | 建物總坪數（含車位） |
| 車位 | 車位情形與含車位坪數 |

## 重新產生

原始貼文存於 `raw/wN_<期間>.txt`，以 Python 解析器自動轉換，避免人工抄寫錯誤：

```bash
python3 scripts/parse_weekly.py        # 解析全部週別 + 產生 ALL 彙總
python3 scripts/gen_hsinchu_2026_05_26.py  # 5/26 該週（獨立來源）
```

> 單價為概抓，會因所扣除之車位價格差異而有所不同。資料僅供內部參考，**請勿外傳**。
