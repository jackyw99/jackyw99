# -*- coding: utf-8 -*-
"""Parse weekly Hsinchu transaction raw text (raw/wN_<range>.txt) into
structured CSV + Markdown, and build a combined all-weeks CSV for tracking.

Handles both bullet styles ("•" with 建物面積：X坪 and "*" with 建物X坪),
and extracts the bolded *result* of unit-price formulas when present.
資料僅供內部參考，請勿外傳。
"""
import csv
import glob
import os
import re

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(BASE, "raw")
DATA = os.path.join(BASE, "data")

HEADER = ["編號", "標題", "社區", "地址", "行政區", "成交總價(萬)",
          "成交單價(萬/坪)", "樓層", "屋齡", "建物坪數", "車位"]

DISTRICT_RE = re.compile(r"(?:新竹[市縣]|苗栗縣)([一-鿿]{1,3}[區鄉鎮市])")
CITY_RE = re.compile(r"(新竹市|新竹縣|苗栗縣)")
COMMUNITY_RE = re.compile(r"[【『「](.+?)[】』」]")


def district(addr):
    m = DISTRICT_RE.search(addr)
    return m.group(1) if m else ""


def city(addr):
    m = CITY_RE.search(addr)
    return m.group(1) if m else ""


def split_records(text):
    """Split a week's text into per-record blocks starting with 'N.'."""
    blocks, cur = [], []
    for line in text.splitlines():
        if re.match(r"^\s*\d+\.\s*\S", line) and "地址" not in line:
            if cur:
                blocks.append("\n".join(cur))
            cur = [line]
        elif cur:
            cur.append(line)
    if cur:
        blocks.append("\n".join(cur))
    return blocks


def parse_record(block):
    lines = [l.strip().lstrip("*•").strip() for l in block.splitlines() if l.strip()]
    text = "\n".join(lines)
    no = re.match(r"^(\d+)\.", lines[0]).group(1)
    title = re.sub(r"^\d+\.\s*", "", lines[0]).strip()

    def grab(pat):
        m = re.search(pat, text)
        return m.group(1).strip() if m else ""

    addr = grab(r"地址[:：]\s*(.+)")
    total = grab(r"成交總價[\s:：]*([0-9.]+)\s*萬")
    # unit price: prefer bolded *result*
    mstar = re.search(r"\*\s*(-?[0-9.]+)\s*\*", text)
    if mstar:
        unit = mstar.group(1)
    else:
        unit = grab(r"成交單價[\s:：]*(-?[0-9]+(?:\.[0-9]+)?)\s*萬")
    floor = grab(r"建物資訊[:：]\s*(.+?)樓")
    age = grab(r"屋齡[:：]\s*([0-9.]+)\s*年")
    area = grab(r"建物(?:面積)?[:：]?\s*([0-9]+\.[0-9]+)\s*坪")
    incl = grab(r"含車位\s*([0-9]+\.[0-9]+)\s*坪")
    if "無車位" in text:
        park = "無車位"
    elif "有車位" in text or "含車位" in text:
        park = "有車位/含車位%s坪" % incl if incl else "有車位"
    else:
        park = ""
    # community: bracketed name in address, else blank
    cm = COMMUNITY_RE.search(addr)
    comm = cm.group(1) if cm else ""
    return [no, title, comm, addr, district(addr), total, unit,
            floor, age or "未提供", area, park]


def process():
    os.makedirs(DATA, exist_ok=True)
    per_week = []
    for path in sorted(glob.glob(os.path.join(RAW, "w*_*.txt"))):
        rng = re.search(r"w\d+_(.+)\.txt", os.path.basename(path)).group(1)
        with open(path, encoding="utf-8") as f:
            rows = [parse_record(b) for b in split_records(f.read())]
        # write CSV
        csv_path = os.path.join(DATA, "hsinchu-transactions-%s.csv" % rng)
        with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(HEADER)
            w.writerows(rows)
        # write MD
        write_md(rng, rows)
        per_week.append((rng, rows))
        print("%s: %d records -> %s" % (rng, len(rows), os.path.basename(csv_path)))
    build_combined()


def write_md(rng, rows):
    d = rng.replace("_", " ~ ").replace("-", "/")
    totals = [float(r[5]) for r in rows if r[5]]
    n = len(rows)
    counts = {}
    for r in rows:
        k = r[4] or "其他"
        counts[k] = counts.get(k, 0) + 1
    L = ["# 新竹成交資訊 %s" % d, "",
         "> 建坪扣除車位（單價為概抓，會因所扣除之車位價格差異而有所不同）。",
         "> 資料僅供內部參考，**請勿外傳**。", "",
         "## 摘要", "",
         "- 筆數：%d 筆" % n]
    if totals:
        L.append("- 總價區間：%g 萬 ~ %g 萬｜中位數約 %g 萬"
                 % (min(totals), max(totals), sorted(totals)[n // 2]))
    L += ["", "### 行政區分布", "", "| 行政區 | 筆數 |", "| --- | ---: |"]
    for k, c in sorted(counts.items(), key=lambda x: -x[1]):
        L.append("| %s | %d |" % (k, c))
    L += ["", "## 成交明細", "",
          "| # | 標題 | 社區 | 地址 | 行政區 | 總價(萬) | 單價(萬/坪) | 樓層 | 屋齡 | 建物(坪) | 車位 |",
          "| ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | ---: | --- |"]
    for r in rows:
        cells = [c.replace("|", "｜") for c in r]
        L.append("| " + " | ".join(cells) + " |")
    with open(os.path.join(DATA, "hsinchu-transactions-%s.md" % rng), "w",
              encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")


def build_combined():
    """Concatenate every per-week CSV into one tracking file with 週期/縣市."""
    out = os.path.join(DATA, "hsinchu-transactions-ALL.csv")
    cols = ["週期", "縣市"] + HEADER
    seen = sorted(glob.glob(os.path.join(DATA, "hsinchu-transactions-2026-*.csv")))
    with open(out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(cols)
        total = 0
        for path in seen:
            rng = re.search(r"transactions-(2026-.+)\.csv", os.path.basename(path)).group(1)
            with open(path, encoding="utf-8-sig") as g:
                r = csv.reader(g)
                next(r)  # header
                for row in r:
                    if not row:
                        continue
                    addr = row[3] if len(row) > 3 else ""
                    w.writerow([rng, city(addr)] + row)
                    total += 1
    print("combined -> %s (%d rows across %d weeks)" % (os.path.basename(out), total, len(seen)))


if __name__ == "__main__":
    process()
