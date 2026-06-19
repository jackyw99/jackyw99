# 美股個股歷史資訊趴蟲程式 / US Stock Historical Data Scraper

抓取美股個股的歷史股價 (OHLCV、調整後收盤、股息、分割)，存成 **JSON**，
並自動上傳到 **Google Drive**。

Scrapes US stock historical data (OHLCV, adjusted close, dividends, splits),
saves it as **JSON**, and uploads it to **Google Drive**.

資料來源 / Data sources: **Yahoo Finance** (預設)、**Stooq**、**Alpha Vantage**。
第一隻測試股票為 **AMSC** (American Superconductor)。

---

## 功能 / Features

- 一次抓取多檔股票 / Batch-fetch multiple tickers
- 可調整期間與間隔 / Configurable `period` & `interval`
- **多種資料來源**：yahoo / stooq / alphavantage / **Multiple data sources**
- **基本面資料**：本益比、市值、殖利率、ROE 與年度財報 / **Fundamentals**: PE, market cap, dividend yield, ROE, annual statements
- 整理成乾淨、可讀的 JSON / Clean, human-readable JSON output
- 自動上傳 Google Drive，同名檔自動更新 (不產生重複檔) / Auto-upload to Drive, updates in place
- **GitHub Actions 每日自動排程** / **Daily automation via GitHub Actions**
- 設定檔或命令列參數皆可 / Config file **or** CLI flags
- 單一代號失敗不影響其他代號 / One failed ticker won't stop the batch

---

## 1. 安裝 / Installation

需要 Python 3.9 以上 / Requires Python 3.9+.

```bash
cd us-stock-scraper
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

---

## 2. 設定 Google Drive 憑證 / Set up Google Drive credentials

只有要上傳到 Drive 時才需要。若只想下載 JSON，請加 `--no-upload` 跳過。
Only needed for uploading. To just download JSON, use `--no-upload`.

### 方法 A：OAuth 使用者授權 (適合個人電腦) / OAuth (for personal use)

1. 前往 [Google Cloud Console](https://console.cloud.google.com/) 建立專案。
2. 啟用 **Google Drive API** (APIs & Services → Library → Google Drive API → Enable)。
3. 建立 OAuth 用戶端 ID：APIs & Services → Credentials → Create Credentials →
   **OAuth client ID** → Application type 選 **Desktop app**。
4. 下載 JSON，改名為 `credentials.json`，放到本資料夾。
5. 第一次執行程式時會開啟瀏覽器要你登入授權，成功後會自動產生 `token.json`
   (之後就不必再登入)。

### 方法 B：Service Account (適合伺服器/排程自動化) / Service Account

1. 在 Cloud Console 建立 Service Account 並下載金鑰 JSON。
2. 設定環境變數指向該檔：
   ```bash
   # Windows (PowerShell)
   $env:GOOGLE_SERVICE_ACCOUNT="C:\path\to\service_account.json"
   # macOS / Linux
   export GOOGLE_SERVICE_ACCOUNT=/path/to/service_account.json
   ```
3. 在 Google Drive 上把目標資料夾「共用」給該 Service Account 的 email，
   並把資料夾 ID 填到設定的 `drive_folder_id`。

> ⚠️ `credentials.json`、`token.json`、`service_account.json` 已列入 `.gitignore`，
> 請勿上傳到 GitHub。/ These secret files are git-ignored — never commit them.

### 如何取得資料夾 ID / How to find the Drive folder ID

在瀏覽器打開該 Drive 資料夾，網址最後一段就是 ID：
`https://drive.google.com/drive/folders/`**`<這串就是 folder id>`**
留空 (`""`) 則上傳到 Drive 根目錄。

---

## 3. 使用方式 / Usage

### 用命令列參數 / With CLI flags

```bash
# 抓 AMSC (第一隻測試股票) 最近一年日線 + 基本面，下載並上傳 Drive
python -m stock_scraper.main --tickers AMSC --period 1y --with-fundamentals

# 一次多檔
python -m stock_scraper.main --tickers AMSC AAPL MSFT --period 1y --interval 1d

# 只下載成 JSON，不上傳
python -m stock_scraper.main --tickers AMSC --period 5y --no-upload

# 換資料來源 (免 API key 的 Stooq)
python -m stock_scraper.main --tickers AMSC --source stooq --no-upload

# 用 Alpha Vantage (需先設定 ALPHAVANTAGE_API_KEY)
python -m stock_scraper.main --tickers AMSC --source alphavantage --no-upload
```

### 用設定檔 / With a config file

```bash
cp config.example.json config.json   # Windows: copy config.example.json config.json
# 編輯 config.json 後執行：
python -m stock_scraper.main --config config.json
```

`config.json` 範例：

```json
{
  "tickers": ["AMSC", "AAPL", "MSFT", "NVDA"],
  "period": "1y",
  "interval": "1d",
  "source": "yahoo",
  "include_fundamentals": true,
  "output_dir": "output",
  "upload_to_drive": true,
  "drive_folder_id": "",
  "credentials_file": "credentials.json",
  "token_file": "token.json"
}
```

### 參數說明 / Parameter reference

| 參數 / Flag          | 說明 / Description                                | 範例 / Example          |
| -------------------- | ------------------------------------------------- | ----------------------- |
| `--tickers`          | 股票代號 (可多個) / tickers                       | `AMSC AAPL MSFT`        |
| `--period`           | 期間 / time span                                  | `1d,5d,1mo,6mo,1y,5y,max` |
| `--interval`         | 間隔 / candle interval                            | `1d,1wk,1mo` (日內 `1m/5m` 僅近期) |
| `--source`           | 資料來源 / data source                            | `yahoo`,`stooq`,`alphavantage` |
| `--with-fundamentals`| 一併抓基本面 (僅 yahoo) / fetch fundamentals      | —                       |
| `--output-dir`       | 本地輸出資料夾 / local output folder              | `output`                |
| `--drive-folder-id`  | Drive 資料夾 ID                                   | `1AbC...`               |
| `--no-upload`        | 只下載不上傳 / download only                      | —                       |
| `--config`           | 設定檔路徑 / config path                          | `config.json`           |

### 資料來源比較 / Data source comparison

| 來源 / Source  | API key | 調整後價/股息 | 基本面 | 備註 / Notes |
| -------------- | ------- | ------------- | ------ | ------------ |
| `yahoo` (預設) | 否 No   | ✅            | ✅     | 功能最完整   |
| `stooq`        | 否 No   | 部分 (僅調整後價) | ❌ | 穩定、純 CSV |
| `alphavantage` | 是 Yes  | ❌            | ❌     | 免費版有流量限制 (需 `ALPHAVANTAGE_API_KEY`) |

---

## 4. 輸出格式 / Output format

檔名格式：`<TICKER>_<interval>_<YYYYMMDD>.json`，例如 `AMSC_1d_20260619.json`。
完整範例見 [`samples/AMSC_sample.json`](samples/AMSC_sample.json) (數值為示意)。

```json
{
  "ticker": "AMSC",
  "period": "1y",
  "interval": "1d",
  "source": "Yahoo Finance (yfinance)",
  "downloaded_at": "2026-06-19T08:00:00+00:00",
  "record_count": 251,
  "meta": {
    "shortName": "American Superconductor Corp",
    "sector": "Industrials",
    "currency": "USD",
    "exchange": "NMS"
  },
  "history": [
    {
      "date": "2025-06-19",
      "open": 27.50, "high": 28.20, "low": 27.20,
      "close": 28.00, "adj_close": 28.00,
      "volume": 1000000, "dividends": 0.0, "stock_splits": 0.0
    }
  ],
  "fundamentals": {
    "key_stats": { "marketCap": 1200000000, "trailingPE": 55.3, "beta": 1.85 },
    "income_statement": { "2025-12-31": { "Total Revenue": 200000000, "Net Income": 15000000 } },
    "balance_sheet": { "...": {} },
    "cash_flow": { "...": {} }
  }
}
```

> `fundamentals` 只有在加上 `--with-fundamentals` (或設定 `include_fundamentals: true`)
> 且來源為 `yahoo` 時才會出現。

---

## 5. GitHub Actions 每日自動排程 / Daily automation

`.github/workflows/scrape-stocks.yml` 會每個交易日 (UTC 22:30，美股收盤後) 自動抓取
並上傳到 Google Drive，也可在 Actions 頁面手動觸發 (workflow_dispatch)。

### 需設定的 Secrets / Required repository secrets

到 GitHub repo → Settings → Secrets and variables → Actions 新增：

| 名稱 / Name                    | 必填 | 說明 / Description                                   |
| ------------------------------ | ---- | --------------------------------------------------- |
| `GOOGLE_SERVICE_ACCOUNT_JSON`  | ✅   | Service Account 金鑰 JSON 的**完整內容**            |
| `DRIVE_FOLDER_ID`              | 建議 | 上傳目標 Drive 資料夾 ID (要先共用給 SA 的 email)   |
| `ALPHAVANTAGE_API_KEY`        | 選填 | 若改用 alphavantage 來源才需要                      |

也可設定 Variable `STOCK_TICKERS` (例如 `AMSC AAPL MSFT`) 覆寫預設清單；
手動觸發時可直接在輸入框填 tickers 與 period。

> 設定 Drive 資料夾共用：在 Google Drive 對目標資料夾按「共用」，把 Service Account
> 的 email (在金鑰 JSON 的 `client_email`) 加為「編輯者」。

---

## 6. 專案結構 / Project layout

```
us-stock-scraper/
├── README.md
├── requirements.txt
├── config.example.json      # 複製成 config.json 使用
├── .gitignore
├── samples/
│   └── AMSC_sample.json     # 輸出範例 (示意數值)
└── stock_scraper/
    ├── __init__.py
    ├── scraper.py           # 抓取流程 + 整理成 JSON
    ├── sources.py           # 多來源 (yahoo / stooq / alphavantage)
    ├── fundamentals.py      # 基本面資料 (yahoo)
    ├── gdrive.py            # Google Drive 上傳
    ├── utils.py             # 共用工具
    └── main.py              # CLI 進入點

.github/workflows/scrape-stocks.yml   # 每日自動排程
```

---

## 7. 常見問題 / FAQ

- **抓不到資料 / no data returned**：確認代號正確 (美股，如 `AMSC`)，並確認有網路。
  也可改用其他來源 `--source stooq` 試試。
- **日內資料 (1m/5m) 失敗**：Yahoo 只提供近期日內資料，請縮短 `period` (如 `5d`)。
- **第一次上傳卡在瀏覽器授權**：請在跳出的瀏覽器視窗完成 Google 登入與授權。
- **Alpha Vantage 回傳 Note/限流**：免費版每分鐘/每日有上限，請降低頻率或改用 yahoo。
- **想在本機排程每天自動跑**：用 Windows 工作排程器 / cron 呼叫
  `python -m stock_scraper.main --config config.json`；或直接用內建的 GitHub Actions。

---

## 免責聲明 / Disclaimer

本程式僅供個人學習與研究使用。資料由 Yahoo Finance 提供，請遵守其服務條款；
不保證資料即時性與正確性，請勿用於商業或實際投資決策。
For personal/educational use only. Data provided by Yahoo Finance — respect their
terms of service. No warranty on accuracy or timeliness.
