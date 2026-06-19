"""
抓取個股基本面資料 (Yahoo Finance)。
Fetch fundamental data for a stock (Yahoo Finance).

包含 / Includes:
  - key_stats : 常用估值/獲利指標 (本益比、市值、殖利率、ROE...)
  - income_statement / balance_sheet / cash_flow : 年度財報摘要
"""

from __future__ import annotations

import logging
from typing import Any

from .utils import clean

logger = logging.getLogger(__name__)

# 從 yfinance .info 取出的常用指標 / handy metrics from .info
_KEY_STATS = (
    "marketCap",
    "enterpriseValue",
    "trailingPE",
    "forwardPE",
    "priceToBook",
    "pegRatio",
    "dividendYield",
    "dividendRate",
    "beta",
    "fiftyTwoWeekHigh",
    "fiftyTwoWeekLow",
    "profitMargins",
    "returnOnEquity",
    "returnOnAssets",
    "totalRevenue",
    "revenueGrowth",
    "grossMargins",
    "operatingMargins",
    "earningsGrowth",
    "totalCash",
    "totalDebt",
    "freeCashflow",
    "sharesOutstanding",
    "bookValue",
    "trailingEps",
    "forwardEps",
)


def _statement_to_dict(df: Any) -> dict[str, dict[str, Any]]:
    """把 yfinance 的財報 DataFrame (列=科目, 欄=期間) 轉成 JSON 友善 dict。"""
    if df is None or getattr(df, "empty", True):
        return {}
    out: dict[str, dict[str, Any]] = {}
    for col in df.columns:
        # 欄名通常是 Timestamp，用日期字串當 key
        period_key = col.strftime("%Y-%m-%d") if hasattr(col, "strftime") else str(col)
        out[period_key] = {
            str(idx): clean(val) for idx, val in df[col].items()
        }
    return out


def fetch_fundamentals(ticker: str) -> dict[str, Any]:
    """
    回傳指定代號的基本面資料 (僅支援 Yahoo)。
    任何子項失敗都不會中斷，只會在該欄位留下空值並記錄警告。
    """
    import yfinance as yf

    tk = yf.Ticker(ticker)
    result: dict[str, Any] = {"key_stats": {}, "income_statement": {}, "balance_sheet": {}, "cash_flow": {}}

    try:
        info = tk.info or {}
        result["key_stats"] = {k: clean(info.get(k)) for k in _KEY_STATS if info.get(k) is not None}
    except Exception as exc:  # noqa: BLE001
        logger.warning("取得 %s 的 key_stats 失敗: %s", ticker, exc)

    for attr, out_key in (
        ("financials", "income_statement"),
        ("balance_sheet", "balance_sheet"),
        ("cashflow", "cash_flow"),
    ):
        try:
            result[out_key] = _statement_to_dict(getattr(tk, attr, None))
        except Exception as exc:  # noqa: BLE001
            logger.warning("取得 %s 的 %s 失敗: %s", ticker, out_key, exc)

    return result
