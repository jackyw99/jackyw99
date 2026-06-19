# GitHub Actions 自動抓 AMSC 並上傳 Google Drive — 逐步教學

這份教學帶你「完全免費」用 GitHub Actions 每天自動抓美股（第一隻測試股 **AMSC**）
存成 JSON 並上傳到你的 Google Drive。你的 `jackyw99/jackyw99` 是公開 repo，
GitHub Actions 對公開 repo **無限分鐘、完全免費**。

> 全程約 15 分鐘。需要用到 Google Service Account（自動化用的機器人帳號），
> 它需要一個 GCP 專案——但**只是拿來開 Drive API，不會產生費用**。

---

## 總覽 / 你會做這些事

1. 建立 GCP 專案並啟用 **Google Drive API**
2. 建立 **Service Account** 並下載金鑰 JSON
3. 在 Google Drive 建一個資料夾，**共用**給 Service Account
4. 把金鑰與資料夾 ID 設成 **GitHub Secrets**
5. 到 **Actions** 手動觸發，確認 AMSC 的 JSON 出現在 Drive

---

## 步驟 1：建立 GCP 專案並啟用 Drive API

1. 開啟 [Google Cloud Console](https://console.cloud.google.com/) 並用你的 Google 帳號登入
   （jackyw99@gmail.com）。
2. 左上角專案選單 → **New Project** → 取名例如 `stock-scraper` → **Create**。
3. 確認右上角已切換到這個新專案。
4. 搜尋列輸入 **Google Drive API** → 進入 → 按 **Enable**。

> 只啟用 API 不會收費；Drive API 本身免費。

---

## 步驟 2：建立 Service Account 並下載金鑰

1. 左側選單 → **APIs & Services** → **Credentials**。
2. **Create Credentials** → **Service account**。
3. 名稱填 `drive-uploader` → **Create and Continue** → 角色可略過 → **Done**。
4. 在 Service accounts 清單點剛建立的帳號 → 上方 **KEYS** 分頁 →
   **Add Key** → **Create new key** → 選 **JSON** → **Create**。
5. 瀏覽器會下載一個 `.json` 檔（例如 `stock-scraper-xxxx.json`）。**這就是金鑰，請妥善保管、不要外流**。
6. 打開這個 JSON，記下裡面的 `client_email`（長得像
   `drive-uploader@stock-scraper.iam.gserviceaccount.com`），下一步要用。

---

## 步驟 3：建立 Drive 資料夾並共用給 Service Account

Service Account 有「自己的」Drive 空間，看不到你的檔案，所以要把目標資料夾共用給它。

1. 開啟 [Google Drive](https://drive.google.com/) → 新增一個資料夾，例如 `美股資料`。
2. 進入該資料夾，看網址列：
   `https://drive.google.com/drive/folders/`**`1AbCdEfGhIjKlMnOpQrStUvWxYz`**
   後面那串就是 **資料夾 ID**，記下來。
3. 對資料夾按右鍵 → **共用 / Share** → 把步驟 2 的 `client_email` 貼進去 →
   權限選 **編輯者 / Editor** → 送出。

> 沒做共用的話，上傳會成功但檔案會跑到 Service Account 自己的空間，你在自己 Drive 看不到。

---

## 步驟 4：設定 GitHub Secrets

1. 打開你的 repo：`https://github.com/jackyw99/jackyw99`
2. **Settings** → 左側 **Secrets and variables** → **Actions** → **New repository secret**。
3. 依序新增以下 secrets：

   | Name | 內容 |
   |---|---|
   | `GOOGLE_SERVICE_ACCOUNT_JSON` | 把步驟 2 下載的金鑰 JSON **整個檔案內容**貼進去（從 `{` 到 `}` 全部）|
   | `DRIVE_FOLDER_ID` | 步驟 3 記下的資料夾 ID |
   | `ALPHAVANTAGE_API_KEY` | （選填）只有想用 alphavantage 來源才需要 |

4. （選填）若想改預設股票清單：到同頁的 **Variables** 分頁 → **New variable** →
   名稱 `STOCK_TICKERS`、值例如 `AMSC AAPL MSFT NVDA`。

---

## 步驟 5：手動觸發，驗證 AMSC

1. repo 上方 **Actions** 分頁 → 左側點 **Scrape US stocks to Google Drive**。
2. 右側 **Run workflow** 按鈕 → tickers 可留白（預設含 AMSC）或自行輸入 →
   再按綠色 **Run workflow**。
3. 點進這次執行 → 看 **Scrape and upload** 這步的 log，應該會看到
   `AMSC 已上傳: https://drive.google.com/...`。
4. 回到你的 Drive `美股資料` 資料夾，應該會出現 `AMSC_1d_YYYYMMDD.json`。
5. 之後每個交易日（UTC 22:30 / 台灣隔天早上 06:30）會自動執行，不必再手動。

> 工作流程也會把 JSON 存成 **Actions artifact**，即使 Drive 設定有誤，也能在
> 該次執行頁面下方下載檔案來檢查。

---

## 常見問題

- **看到 `missing service account secret`**：`GOOGLE_SERVICE_ACCOUNT_JSON` 沒設定或貼錯，
  請確認貼的是金鑰 JSON 全文。
- **執行成功但 Drive 看不到檔案**：多半是資料夾沒共用給 `client_email`，或
  `DRIVE_FOLDER_ID` 填錯（回步驟 3 檢查）。
- **抓不到某些代號**：確認是美股代號；可改 `--source stooq` 當備援。
- **想改排程時間**：編輯 `.github/workflows/scrape-stocks.yml` 裡的 `cron`
  （格式為 UTC 時間）。

---

完成後，你就有一條「每天自動抓美股 → 存 JSON → 進 Google Drive」的免費流水線了 🎉
