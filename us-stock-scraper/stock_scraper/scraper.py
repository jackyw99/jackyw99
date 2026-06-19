"""
抓取美股個股歷史資料的核心模組。
Core module for scraping US stock historical data.

使用 yfinance (Yahoo Finance) 取得每日 OHLCV 與股息/分割資訊，
並整理成方便儲存的 JSON 結構。
Uses yfinance (Yahoo Finance) to obtain daily OHLCV plus
dividends/splits, then organises it into a JSON-friendly structure.
"""

from __future__ import annotations

import logging
import math
from datetime import datetime, timezone
from typing import Any

import yfinance as yf

logger = logging.getLogger(__name__)


def _clean(value: Any) -> Any:
    """把 NaN / NaT / numpy 型別轉成可序列化為 JSON 的值。"""
    if value is None:
        return None
    # pandas/np NaN
    if isinstance(value, float) and math.isnan(value):
        return None
    # numpy scalar -> python scalar
    if hasattr(value, "item"):
        try:
            return value.item()
        except (ValueError, AttributeError):
            pass
    return value


def fetch_stock_history(
    ticker: str,
    period: str = "1y",
    interval: str = "1d",
) -> dict[str, Any]:
    """
    抓取單一美股代號的歷史資料。
    Fetch historical data for a single US stock ticker.

    Args:
        ticker:   股票代號，例如 "AAPL"。
        period:   期間，例如 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max。
        interval: 間隔，例如 1d, 1wk, 1mo (日內 1m/5m 僅支援近期)。

    Returns:
        一個可直接存成 JSON 的 dict。
    """
    symbol = ticker.strip().upper()
    if not symbol:
        raise ValueError("ticker 不可為空 / ticker must not be empty")

    logger.info("抓取 %s 的歷史資料 (period=%s, interval=%s)...", symbol, period, interval)

    tk = yf.Ticker(symbol)
    hist = tk.history(period=period, interval=interval, auto_adjust=False)

    if hist is None or hist.empty:
        raise ValueError(
            f"找不到 {symbol} 的資料，請確認代號是否正確 / no data returned for {symbol}"
        )

    records: list[dict[str, Any]] = []
    for ts, row in hist.iterrows():
        # ts 可能帶有時區，統一輸出為 ISO 日期字串
        date_str = ts.strftime("%Y-%m-%d") if hasattr(ts, "strftime") else str(ts)
        records.append(
            {
                "date": date_str,
                "open": _clean(row.get("Open")),
                "high": _clean(row.get("High")),
                "low": _clean(row.get("Low")),
                "close": _clean(row.get("Close")),
                "adj_close": _clean(row.get("Adj Close")),
                "volume": _clean(row.get("Volume")),
                "dividends": _clean(row.get("Dividends")),
                "stock_splits": _clean(row.get("Stock Splits")),
            }
        )

    # 嘗試取得基本公司資訊 (失敗不影響主流程)
    meta: dict[str, Any] = {}
    try:
        info = tk.info or {}
        for key in ("shortName", "longName", "sector", "industry", "currency", "exchange"):
            if info.get(key) is not None:
                meta[key] = info[key]
    except Exception as exc:  # noqa: BLE001 - info 常因 API 變動而失敗，可忽略
        logger.warning("無法取得 %s 的公司資訊: %s", symbol, exc)

    return {
        "ticker": symbol,
        "period": period,
        "interval": interval,
        "source": "Yahoo Finance (yfinance)",
        "downloaded_at": datetime.now(timezone.utc).isoformat(),
        "record_count": len(records),
        "meta": meta,
        "history": records,
    }
