"""
抓取美股個股歷史資料的核心模組。
Core module for scraping US stock historical data.

支援多種資料來源 (yahoo / stooq / alphavantage)，可選擇是否一併抓取基本面，
最後整理成方便儲存的 JSON 結構。
Supports multiple data sources, optionally includes fundamentals, and
organises everything into a JSON-friendly structure.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from .fundamentals import fetch_fundamentals
from .sources import fetch_records

logger = logging.getLogger(__name__)

_SOURCE_LABEL = {
    "yahoo": "Yahoo Finance (yfinance)",
    "stooq": "Stooq (stooq.com)",
    "alphavantage": "Alpha Vantage",
}


def fetch_stock_history(
    ticker: str,
    period: str = "1y",
    interval: str = "1d",
    source: str = "yahoo",
    include_fundamentals: bool = False,
) -> dict[str, Any]:
    """
    抓取單一美股代號的歷史資料 (與可選的基本面)。
    Fetch historical data (and optional fundamentals) for one US ticker.

    Args:
        ticker:               股票代號，例如 "AMSC"。
        period:               期間，例如 1d,5d,1mo,1y,5y,max。
        interval:             間隔，例如 1d,1wk,1mo。
        source:               資料來源 yahoo / stooq / alphavantage。
        include_fundamentals: 是否一併抓取基本面 (僅 yahoo 支援)。

    Returns:
        可直接存成 JSON 的 dict。
    """
    symbol = ticker.strip().upper()
    if not symbol:
        raise ValueError("ticker 不可為空 / ticker must not be empty")

    logger.info(
        "抓取 %s 歷史資料 (source=%s, period=%s, interval=%s)...",
        symbol, source, period, interval,
    )
    records, meta = fetch_records(symbol, period, interval, source)

    data: dict[str, Any] = {
        "ticker": symbol,
        "period": period,
        "interval": interval,
        "source": _SOURCE_LABEL.get(source.lower(), source),
        "downloaded_at": datetime.now(timezone.utc).isoformat(),
        "record_count": len(records),
        "meta": meta,
        "history": records,
    }

    if include_fundamentals:
        if source.lower() == "yahoo":
            logger.info("抓取 %s 的基本面資料...", symbol)
            data["fundamentals"] = fetch_fundamentals(symbol)
        else:
            logger.warning("基本面資料僅支援 yahoo 來源，已略過 %s", symbol)
            data["fundamentals"] = None

    return data
