"""
多種美股歷史資料來源。
Multiple US stock historical-data sources.

每個 fetch_* 函式都回傳 (records, meta)：
  records: list[dict]，欄位見 utils.RECORD_FIELDS
  meta:    dict，來源相關的補充資訊

來源 / sources:
  - yahoo        : yfinance (Yahoo Finance)，免 API key，含調整後收盤/股息/分割
  - stooq        : stooq.com CSV，免 API key (僅 OHLCV)
  - alphavantage : Alpha Vantage，需環境變數 ALPHAVANTAGE_API_KEY
"""

from __future__ import annotations

import csv
import io
import logging
import os
import urllib.parse
import urllib.request
from datetime import datetime
from typing import Any

from .utils import clean, empty_record, period_to_start_date

logger = logging.getLogger(__name__)

VALID_SOURCES = ("yahoo", "stooq", "alphavantage")


# --------------------------------------------------------------------------- #
# Yahoo Finance (yfinance)
# --------------------------------------------------------------------------- #
def fetch_yahoo(ticker: str, period: str, interval: str) -> tuple[list[dict], dict]:
    import yfinance as yf  # 延後 import，沒裝也能用其他來源

    tk = yf.Ticker(ticker)
    hist = tk.history(period=period, interval=interval, auto_adjust=False)
    if hist is None or hist.empty:
        raise ValueError(f"Yahoo 找不到 {ticker} 的資料 / no data for {ticker}")

    records: list[dict[str, Any]] = []
    for ts, row in hist.iterrows():
        rec = empty_record(ts.strftime("%Y-%m-%d") if hasattr(ts, "strftime") else str(ts))
        rec.update(
            open=clean(row.get("Open")),
            high=clean(row.get("High")),
            low=clean(row.get("Low")),
            close=clean(row.get("Close")),
            adj_close=clean(row.get("Adj Close")),
            volume=clean(row.get("Volume")),
            dividends=clean(row.get("Dividends")),
            stock_splits=clean(row.get("Stock Splits")),
        )
        records.append(rec)

    meta: dict[str, Any] = {}
    try:
        info = tk.info or {}
        for key in ("shortName", "longName", "sector", "industry", "currency", "exchange"):
            if info.get(key) is not None:
                meta[key] = info[key]
    except Exception as exc:  # noqa: BLE001
        logger.warning("無法取得 %s 的公司資訊: %s", ticker, exc)
    return records, meta


# --------------------------------------------------------------------------- #
# Stooq (CSV, no API key)
# --------------------------------------------------------------------------- #
_STOOQ_INTERVAL = {"1d": "d", "1wk": "w", "1mo": "m"}


def _http_get(url: str, timeout: int = 30) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 stock-scraper"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 - 固定 https 來源
        return resp.read().decode("utf-8", errors="replace")


def fetch_stooq(ticker: str, period: str, interval: str) -> tuple[list[dict], dict]:
    sym = ticker.lower()
    if "." not in sym:
        sym = f"{sym}.us"  # 美股在 stooq 的代號後綴
    i = _STOOQ_INTERVAL.get(interval, "d")
    url = f"https://stooq.com/q/d/l/?s={urllib.parse.quote(sym)}&i={i}"

    text = _http_get(url)
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames or "Date" not in reader.fieldnames:
        raise ValueError(
            f"Stooq 找不到 {ticker} 的資料 (回應: {text[:80]!r}) / no data for {ticker}"
        )

    start = period_to_start_date(period)
    records: list[dict[str, Any]] = []
    for row in reader:
        d = row.get("Date")
        if not d:
            continue
        if start is not None and datetime.strptime(d, "%Y-%m-%d").date() < start:
            continue
        rec = empty_record(d)
        rec.update(
            open=_to_float(row.get("Open")),
            high=_to_float(row.get("High")),
            low=_to_float(row.get("Low")),
            close=_to_float(row.get("Close")),
            adj_close=_to_float(row.get("Close")),  # stooq 已是調整後價格
            volume=_to_float(row.get("Volume")),
        )
        records.append(rec)

    if not records:
        raise ValueError(f"Stooq 沒有回傳 {ticker} 在此期間的資料 / empty range for {ticker}")
    return records, {"symbol": sym}


# --------------------------------------------------------------------------- #
# Alpha Vantage (needs API key)
# --------------------------------------------------------------------------- #
_AV_FUNC = {
    "1d": ("TIME_SERIES_DAILY", "Time Series (Daily)"),
    "1wk": ("TIME_SERIES_WEEKLY", "Weekly Time Series"),
    "1mo": ("TIME_SERIES_MONTHLY", "Monthly Time Series"),
}


def fetch_alphavantage(ticker: str, period: str, interval: str) -> tuple[list[dict], dict]:
    import json

    api_key = os.environ.get("ALPHAVANTAGE_API_KEY")
    if not api_key:
        raise RuntimeError(
            "使用 alphavantage 來源需設定環境變數 ALPHAVANTAGE_API_KEY / "
            "set ALPHAVANTAGE_API_KEY to use the alphavantage source"
        )
    func, key = _AV_FUNC.get(interval, _AV_FUNC["1d"])
    params = {
        "function": func,
        "symbol": ticker.upper(),
        "outputsize": "full",
        "apikey": api_key,
    }
    url = "https://www.alphavantage.co/query?" + urllib.parse.urlencode(params)
    payload = json.loads(_http_get(url))

    if key not in payload:
        note = payload.get("Note") or payload.get("Error Message") or str(payload)[:120]
        raise ValueError(f"Alpha Vantage 無資料 {ticker}: {note}")

    start = period_to_start_date(period)
    records: list[dict[str, Any]] = []
    for d, row in payload[key].items():
        if start is not None and datetime.strptime(d, "%Y-%m-%d").date() < start:
            continue
        rec = empty_record(d)
        rec.update(
            open=_to_float(row.get("1. open")),
            high=_to_float(row.get("2. high")),
            low=_to_float(row.get("3. low")),
            close=_to_float(row.get("4. close")),
            adj_close=_to_float(row.get("4. close")),
            volume=_to_float(row.get("5. volume")),
        )
        records.append(rec)

    records.sort(key=lambda r: r["date"])  # AV 是新到舊，統一成舊到新
    if not records:
        raise ValueError(f"Alpha Vantage 沒有回傳 {ticker} 在此期間的資料")
    return records, payload.get("Meta Data", {})


def _to_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


# --------------------------------------------------------------------------- #
# Dispatcher
# --------------------------------------------------------------------------- #
def fetch_records(
    ticker: str, period: str, interval: str, source: str
) -> tuple[list[dict], dict]:
    source = (source or "yahoo").lower()
    if source == "yahoo":
        return fetch_yahoo(ticker, period, interval)
    if source == "stooq":
        return fetch_stooq(ticker, period, interval)
    if source == "alphavantage":
        return fetch_alphavantage(ticker, period, interval)
    raise ValueError(f"未知的資料來源 {source!r}，可用: {VALID_SOURCES}")
