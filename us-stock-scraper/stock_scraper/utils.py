"""
共用工具：資料清理與期間換算。
Shared utilities: data cleaning and period helpers.
"""

from __future__ import annotations

import math
from datetime import date, datetime, timedelta
from typing import Any

# 統一的每日資料欄位 / canonical per-row fields
RECORD_FIELDS = (
    "date",
    "open",
    "high",
    "low",
    "close",
    "adj_close",
    "volume",
    "dividends",
    "stock_splits",
)


def clean(value: Any) -> Any:
    """把 NaN / numpy 型別轉成可序列化為 JSON 的值。"""
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    if hasattr(value, "item"):  # numpy scalar -> python scalar
        try:
            return value.item()
        except (ValueError, AttributeError):
            pass
    return value


def empty_record(date_str: str) -> dict[str, Any]:
    """建立一筆所有欄位皆為 None 的紀錄 (再覆寫有值的欄位)。"""
    row = {f: None for f in RECORD_FIELDS}
    row["date"] = date_str
    return row


def period_to_start_date(period: str, today: date | None = None) -> date | None:
    """
    把 yfinance 風格的 period 字串換算成起始日期 (給沒有 period 參數的來源用)。
    回傳 None 代表 "max" (不限制)。
    """
    today = today or datetime.utcnow().date()
    period = (period or "").strip().lower()
    table = {
        "1d": 1, "5d": 5,
        "1mo": 30, "3mo": 91, "6mo": 182,
        "1y": 365, "2y": 730, "5y": 1825, "10y": 3650,
    }
    if period in ("max", ""):
        return None
    if period == "ytd":
        return date(today.year, 1, 1)
    days = table.get(period)
    if days is None:
        # 不認得的格式就回退到一年
        days = 365
    return today - timedelta(days=days)
