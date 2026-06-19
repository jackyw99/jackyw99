# 美股個股歷史資訊趴蟲程式 / US Stock Historical Data Scraper

抓取美股個股的歷史股價 (OHLCV、調整後收盤、股息、分割)，存成 **JSON**，
並自動上傳到 **Google Drive**。

Scrapes US stock historical data (OHLCV, adjusted close, dividends, splits),
saves it as **JSON**, and uploads it to **Google Drive**.

資料來源 / Data source: **Yahoo Finance** (透過 `yfinance` 套件，免 API key)。

---

## 功能 / Features

- 一次抓取多檔股票 / Batch-fetch multiple tickers
- 可調整期間與間隔 / Configurable `period` & `interval`
- 整理成乾淨、可讀的 JSON / Clean, human-readable JSON output
- 自動上傳 Google Drive，同名檔自動更新 (不產生重複檔) / Auto-upload to Drive, updates in place
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
# 抓 AAPL、MSFT 最近一年的日線，下載並上傳 Drive
python -m stock_scraper.main --tickers AAPL MSFT --period 1y --interval 1d

# 只下載成 JSON，不上傳
python -m stock_scraper.main --tickers NVDA --period 5y --no-upload

# 指定 Drive 資料夾
python -m stock_scraper.main --tickers TSLA --drive-folder-id 1AbCdEf...
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
  "tickers": ["AAPL", "MSFT", "NVDA"],
  "period": "1y",
  "interval": "1d",
  "output_dir": "output",
  "upload_to_drive": true,
  "drive_folder_id": "",
  "credentials_file": "credentials.json",
  "token_file": "token.json"
}
```

### 參數說明 / Parameter reference

| 參數 / Flag        | 說明 / Description                                        | 範例 / Example          |
| ------------------ | -------------------------------------------------------- | ----------------------- |
| `--tickers`        | 股票代號 (可多個) / tickers                              | `AAPL MSFT NVDA`        |
| `--period`         | 期間 / time span                                         | `1d,5d,1mo,6mo,1y,5y,max` |
| `--interval`       | 間隔 / candle interval                                   | `1d,1wk,1mo` (日內 `1m/5m` 僅近期) |
| `--output-dir`     | 本地輸出資料夾 / local output folder                    | `output`                |
| `--drive-folder-id`| Drive 資料夾 ID                                          | `1AbC...`               |
| `--no-upload`      | 只下載不上傳 / download only                             | —                       |
| `--config`         | 設定檔路徑 / config path                                 | `config.json`           |

---

## 4. 輸出格式 / Output format

檔名格式：`<TICKER>_<interval>_<YYYYMMDD>.json`，例如 `AAPL_1d_20260619.json`。

```json
{
  "ticker": "AAPL",
  "period": "1y",
  "interval": "1d",
  "source": "Yahoo Finance (yfinance)",
  "downloaded_at": "2026-06-19T08:00:00+00:00",
  "record_count": 251,
  "meta": {
    "shortName": "Apple Inc.",
    "sector": "Technology",
    "currency": "USD",
    "exchange": "NMS"
  },
  "history": [
    {
      "date": "2025-06-19",
      "open": 210.12,
      "high": 212.40,
      "low": 209.80,
      "close": 211.55,
      "adj_close": 211.55,
      "volume": 51234000,
      "dividends": 0.0,
      "stock_splits": 0.0
    }
  ]
}
```

---

## 5. 專案結構 / Project layout

```
us-stock-scraper/
├── README.md
├── requirements.txt
├── config.example.json      # 複製成 config.json 使用
├── .gitignore
└── stock_scraper/
    ├── __init__.py
    ├── scraper.py           # 抓取 + 整理資料
    ├── gdrive.py            # Google Drive 上傳
    └── main.py              # CLI 進入點
```

---

## 6. 常見問題 / FAQ

- **抓不到資料 / no data returned**：確認代號正確 (美股，如 `AAPL`)，並確認有網路。
- **日內資料 (1m/5m) 失敗**：Yahoo 只提供近期日內資料，請縮短 `period` (如 `5d`)。
- **第一次上傳卡在瀏覽器授權**：請在跳出的瀏覽器視窗完成 Google 登入與授權。
- **想排程每天自動跑**：用 Windows 工作排程器 / cron 呼叫
  `python -m stock_scraper.main --config config.json` 即可。

---

## 免責聲明 / Disclaimer

本程式僅供個人學習與研究使用。資料由 Yahoo Finance 提供，請遵守其服務條款；
不保證資料即時性與正確性，請勿用於商業或實際投資決策。
For personal/educational use only. Data provided by Yahoo Finance — respect their
terms of service. No warranty on accuracy or timeliness.
