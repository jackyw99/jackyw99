"""
主程式：抓取美股個股歷史資料 -> 存成 JSON -> 上傳 Google Drive。
Entry point: scrape US stock history -> save as JSON -> upload to Google Drive.

用法 / Usage:
    # 用設定檔
    python -m stock_scraper.main --config config.json

    # 直接用命令列參數
    python -m stock_scraper.main --tickers AAPL MSFT --period 1y --interval 1d

    # 只下載不上傳
    python -m stock_scraper.main --tickers AAPL --no-upload
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from typing import Any

from . import __version__
from .scraper import fetch_stock_history

logger = logging.getLogger("stock_scraper")

DEFAULT_CONFIG: dict[str, Any] = {
    "tickers": ["AAPL"],
    "period": "1y",
    "interval": "1d",
    "output_dir": "output",
    "upload_to_drive": True,
    "drive_folder_id": "",
    "credentials_file": "credentials.json",
    "token_file": "token.json",
}


def load_config(path: str | None) -> dict[str, Any]:
    """讀取設定檔並與預設值合併。"""
    config = dict(DEFAULT_CONFIG)
    if path:
        if not os.path.exists(path):
            raise FileNotFoundError(f"找不到設定檔 {path} / config file not found")
        with open(path, "r", encoding="utf-8") as fh:
            config.update(json.load(fh))
    return config


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="美股個股歷史資訊趴蟲程式 (下載並存到 Google Drive)",
    )
    parser.add_argument("--config", help="JSON 設定檔路徑 / path to JSON config")
    parser.add_argument("--tickers", nargs="+", help="股票代號清單，例如 AAPL MSFT")
    parser.add_argument("--period", help="期間 (1d,5d,1mo,1y,5y,max...)")
    parser.add_argument("--interval", help="間隔 (1d,1wk,1mo...)")
    parser.add_argument("--output-dir", help="本地輸出資料夾")
    parser.add_argument("--drive-folder-id", help="Google Drive 目標資料夾 ID")
    parser.add_argument(
        "--no-upload", action="store_true", help="只下載成 JSON，不上傳 Google Drive"
    )
    parser.add_argument(
        "--upload", action="store_true", help="強制上傳 Google Drive (覆寫設定)"
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser.parse_args(argv)


def merge_cli_into_config(config: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    """命令列參數優先於設定檔。"""
    if args.tickers:
        config["tickers"] = args.tickers
    if args.period:
        config["period"] = args.period
    if args.interval:
        config["interval"] = args.interval
    if args.output_dir:
        config["output_dir"] = args.output_dir
    if args.drive_folder_id is not None and args.drive_folder_id != "":
        config["drive_folder_id"] = args.drive_folder_id
    if args.no_upload:
        config["upload_to_drive"] = False
    if args.upload:
        config["upload_to_drive"] = True
    return config


def save_json(data: dict[str, Any], output_dir: str, ticker: str) -> str:
    """把資料存成本地 JSON 檔，回傳檔案路徑。"""
    os.makedirs(output_dir, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d")
    filename = f"{ticker}_{data['interval']}_{stamp}.json"
    path = os.path.join(output_dir, filename)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
    logger.info("已儲存 %s (%d 筆)", path, data["record_count"])
    return path


def run(config: dict[str, Any]) -> int:
    tickers = config["tickers"]
    if not tickers:
        logger.error("沒有指定任何股票代號 / no tickers given")
        return 2

    upload = config.get("upload_to_drive", False)
    uploader = None
    if upload:
        # 延後 import，沒裝 Google 套件也能在 --no-upload 模式下使用
        from .gdrive import upload_json

        uploader = upload_json

    failures = 0
    for ticker in tickers:
        try:
            data = fetch_stock_history(
                ticker, period=config["period"], interval=config["interval"]
            )
            path = save_json(data, config["output_dir"], data["ticker"])
            if uploader:
                link = uploader(
                    path,
                    folder_id=config.get("drive_folder_id", ""),
                    credentials_file=config.get("credentials_file", "credentials.json"),
                    token_file=config.get("token_file", "token.json"),
                )
                logger.info("%s 已上傳: %s", data["ticker"], link)
        except Exception as exc:  # noqa: BLE001 - 單一代號失敗不該中斷整批
            failures += 1
            logger.error("處理 %s 失敗: %s", ticker, exc)

    total = len(tickers)
    logger.info("完成: 成功 %d / 共 %d (失敗 %d)", total - failures, total, failures)
    return 1 if failures == total else 0


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )
    args = parse_args(argv)
    try:
        config = load_config(args.config)
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        logger.error("讀取設定失敗: %s", exc)
        return 2
    config = merge_cli_into_config(config, args)
    return run(config)


if __name__ == "__main__":
    sys.exit(main())
