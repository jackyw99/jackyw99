# -*- coding: utf-8 -*-
"""我的物件估值追蹤 — 德鑫御天地 14D（自強三路63號）。

以 hsinchu-transactions-ALL.csv 為比較基準，挑選「竹北市・電梯大樓・有車位・
類似坪數與屋齡」的成交，回推本戶扣車位單價，估算合理成交價，並把每次執行的
估值快照累積到 my-property-14D-log.csv，方便長期追蹤趨勢。

每週有新資料併入 ALL.csv 後，重新執行即可更新估值並新增一筆快照：
    python3 scripts/track_property.py [YYYY-MM-DD]
"""
import csv
import os
import re
import sys
import statistics as st
from datetime import date

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")
ALL = os.path.join(DATA, "hsinchu-transactions-ALL.csv")
LOG = os.path.join(DATA, "my-property-14D-log.csv")
MD = os.path.join(DATA, "my-property-14D.md")

# ── 本戶資料（來源：591 實價登錄交易明細）────────────────────────────
UNIT = {
    "社區": "德鑫御天地",
    "地址": "新竹縣竹北市自強三路63號 14樓（D戶）",
    "建物含車位坪": 56.69,
    "車位坪": 9.12,
    "車位類別": "坡道平面",
    "室內坪": 33.22,
    "共有坪": 14.35,
    "格局": "3房2廳2衛",
    "屋齡": 13.0,
    "樓層": "14/19F（高樓層）",
    "取得": "2013/02 成交 930 萬（扣車位單價 19.5 萬/坪）",
}
UNIT["扣車位建坪"] = round(UNIT["建物含車位坪"] - UNIT["車位坪"], 2)

# ── 比較基準篩選條件 ───────────────────────────────────────────────
FILTER = dict(行政區="竹北市", 最低總樓層=10, 建坪下限=40, 建坪上限=75,
              屋齡下限=8, 屋齡上限=18, 單價下限=30, 單價上限=90)
CAR_PRICE = 200          # 竹北平面車位估價（萬），用於回推含車位總價
FLOOR_PREMIUM = 0.0      # 14/19 中高樓層溢價（保守取 0，估值落在中位）


def _num(s):
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def _floors(s):
    return _num(s.split("/")[1].replace("樓", "")) if "/" in s else None


def _age(s):
    m = re.search(r"([\d.]+)", s or "")
    return float(m.group(1)) if m else None


def comparables(rows):
    out = []
    for r in rows:
        if r["行政區"] != FILTER["行政區"]:
            continue
        if "有車位" not in r["車位"]:
            continue
        area, age = _num(r["建物坪數"]), _age(r["屋齡"])
        tf, up = _floors(r["樓層"]), _num(r["成交單價(萬/坪)"])
        if None in (area, age, tf, up):
            continue
        if tf < FILTER["最低總樓層"]:
            continue
        if not FILTER["建坪下限"] <= area <= FILTER["建坪上限"]:
            continue
        if not FILTER["屋齡下限"] <= age <= FILTER["屋齡上限"]:
            continue
        if not FILTER["單價下限"] <= up <= FILTER["單價上限"]:
            continue
        out.append(up)
    return sorted(out)


def quart(vals, q):
    return vals[min(len(vals) - 1, int(len(vals) * q))]


def value(unit_price):
    """扣車位單價 → 含車位合理總價（萬）。"""
    return round(unit_price * (1 + FLOOR_PREMIUM) * UNIT["扣車位建坪"] + CAR_PRICE)


def main():
    snap = sys.argv[1] if len(sys.argv) > 1 else date.today().isoformat()
    rows = list(csv.DictReader(open(ALL, encoding="utf-8-sig")))
    weeks = sorted({r["週期"] for r in rows})
    comps = comparables(rows)
    n = len(comps)
    med, mean = st.median(comps), st.mean(comps)
    q1, q3 = quart(comps, 0.25), quart(comps, 0.75)

    est_low, est_mid, est_high = value(q1), value(med), value(q3)
    list_low = round(est_mid * 1.04, -1)      # 建議掛牌 = 成交中值 +4~8%
    list_high = round(est_mid * 1.08, -1)

    # 累積估值快照（依日期去重，後者覆蓋）
    log = {}
    if os.path.exists(LOG):
        for r in csv.DictReader(open(LOG, encoding="utf-8-sig")):
            log[r["快照日"]] = r
    log[snap] = {
        "快照日": snap, "最新週期": weeks[-1], "比較筆數": n,
        "扣車位單價中位": f"{med:.2f}", "估值中值(萬)": est_mid,
        "估值區間(萬)": f"{est_low}-{est_high}",
    }
    fields = ["快照日", "最新週期", "比較筆數", "扣車位單價中位",
              "估值中值(萬)", "估值區間(萬)"]
    with open(LOG, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for k in sorted(log):
            w.writerow(log[k])

    _write_md(snap, weeks, comps, n, med, mean, q1, q3,
              est_low, est_mid, est_high, list_low, list_high, log, fields)
    print(f"[{snap}] 比較 {n} 筆｜扣車位單價中位 {med:.2f} 萬｜"
          f"估值中值 {est_mid} 萬（{est_low}–{est_high}）｜"
          f"建議掛牌 {list_low:.0f}–{list_high:.0f} 萬")


def _write_md(snap, weeks, comps, n, med, mean, q1, q3,
              est_low, est_mid, est_high, list_low, list_high, log, fields):
    L = []
    L.append("# 我的物件估值追蹤 — 德鑫御天地 14D")
    L.append("")
    L.append(f"> 更新日：{snap}｜資料涵蓋週期：{weeks[0]} ~ {weeks[-1]}（{len(weeks)} 週、"
             f"{sum(1 for _ in open(ALL, encoding='utf-8-sig'))-1} 筆）")
    L.append("> 估值僅供參考，非正式估價；單價為建坪扣除車位之概估。")
    L.append("")
    L.append("## 物件資料（來源：591 實價登錄）")
    L.append("")
    L.append("| 項目 | 內容 |")
    L.append("| --- | --- |")
    for k in ["社區", "地址", "格局", "樓層", "屋齡"]:
        L.append(f"| {k} | {UNIT[k]} |")
    L.append(f"| 建物含車位 | {UNIT['建物含車位坪']} 坪（室內 {UNIT['室內坪']}／"
             f"共有 {UNIT['共有坪']}） |")
    L.append(f"| 車位 | {UNIT['車位類別']} {UNIT['車位坪']} 坪 |")
    L.append(f"| 扣車位建坪 | {UNIT['扣車位建坪']} 坪 |")
    L.append(f"| 取得紀錄 | {UNIT['取得']} |")
    L.append("")
    L.append("## 本期估值")
    L.append("")
    L.append(f"- 比較基準：竹北市・電梯大樓（≥10F）・有車位・建坪 "
             f"{FILTER['建坪下限']}–{FILTER['建坪上限']}・屋齡 "
             f"{FILTER['屋齡下限']}–{FILTER['屋齡上限']} 年，共 **{n} 筆**")
    L.append(f"- 扣車位單價：中位 **{med:.2f}** 萬｜平均 {mean:.2f}｜"
             f"Q1 {q1:.2f}／Q3 {q3:.2f}")
    L.append(f"- 車位估價：{CAR_PRICE} 萬（坡道平面）")
    L.append("")
    L.append("| 情境 | 扣車位單價 | 換算合理總價(含車位) |")
    L.append("| --- | ---: | ---: |")
    L.append(f"| 保守（Q1） | {q1:.2f} 萬 | **{est_low:,} 萬** |")
    L.append(f"| 中值（中位） | {med:.2f} 萬 | **{est_mid:,} 萬** |")
    L.append(f"| 樂觀（Q3） | {q3:.2f} 萬 | **{est_high:,} 萬** |")
    L.append("")
    L.append(f"### 建議")
    L.append(f"- **合理成交帶：約 {est_low:,}–{est_high:,} 萬**（中值 ~{est_mid:,} 萬）")
    L.append(f"- **建議掛牌價：約 {list_low:,.0f}–{list_high:,.0f} 萬**（含 4–8% 議價空間）")
    L.append(f"- 含車位單價回推：約 {est_mid/UNIT['建物含車位坪']:.1f} 萬/坪")
    L.append("")
    L.append("## 估值快照紀錄")
    L.append("")
    L.append("| " + " | ".join(fields) + " |")
    L.append("| " + " | ".join("---" for _ in fields) + " |")
    for kdate in sorted(log):
        r = log[kdate]
        L.append("| " + " | ".join(str(r[f]) for f in fields) + " |")
    L.append("")
    L.append("## 待辦")
    L.append("")
    L.append("- [ ] 與房仲聯繫、確認可售時程")
    L.append("- [ ] 決定掛牌價（參考上方建議帶）")
    L.append("- [ ] 取得 1–2 家房仲實際估價，與本表交叉比對")
    L.append("")
    with open(MD, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L))


if __name__ == "__main__":
    main()
