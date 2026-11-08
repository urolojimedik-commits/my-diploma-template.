#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_coursework.py — Санҷиши худкори кори курсӣ аз рӯи ҷадвали санҷиш (банди 7).

Истифода:
    python coursework/scripts/check_coursework.py coursework/01_Elastografiya.md

Месанҷад:
  * ҳаҷм (аломатҳо → саҳифа),
  * сохтори кор (муқаддима, 3 банд, хулоса, адабиёт, замимаҳо),
  * шумораи ҷадвалҳо дар ҳар банд,
  * иқтибосҳо дар шакли [N, M-б.],
  * шумораи манбаъҳо дар рӯйхати адабиёт,
  * ҷумлаи миёна (калима) ва ҷумлаҳои аз 18 калима дароз,
  * ибораҳои холии манъшуда,
  * ҷойҳои «______» ва «[дақиқ кардан лозим]».
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

CHARS_PER_PAGE = 1900

BAD_PHRASES = [
    "муҳим аст қайд кардан",
    "бояд тазаккур дод",
    "бояд тааққуф кардан",
    "имрӯзҳои мо",
    "бе баҳс",
    "зарур аст зикр кардан",
    "гуфтан мумкин аст",
    "қобили таваҷҷуҳ аст",
]

CITATION_RE = re.compile(r"\[\d+(\s*[,;]\s*\d+)*(\s*,\s*\d+(-\d+)?-?б\.)?\]")
TABLE_CAPTION_RE = re.compile(r"^Ҷадвали\s+\d+\.\d+", re.MULTILINE)


def strip_markup(text: str, keep_tables: bool = False) -> str:
    """Markdown-ро ба матни оддӣ табдил медиҳад.

    keep_tables=True — матни ҷадвалҳо низ мемонад (барои ҳисоби ҳаҷм,
    зеро Word онро дар «Characters (with spaces)» мешуморад).
    """
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    if keep_tables:
        # сатрҳои ҷудокунандаи ҷадвал (| :--- | --- |) хориҷ мешаванд
        text = re.sub(r"^\s*\|[\s:|-]+\|\s*$", "", text, flags=re.M)
        text = re.sub(r"\|", " ", text)
    else:
        text = re.sub(r"\|[^\n]*\|", " ", text)
    text = re.sub(r"^#{1,6}\s*", "", text, flags=re.M)
    text = re.sub(r"[*_`>]", "", text)
    return text


def sentences(text: str):
    """Ҷумлаҳои воқеиро ҷудо мекунад.

    Танҳо порчаҳое ҳисобида мешаванд, ки:
      * бо аломати хотима (. ! ? …) тамом мешаванд,
      * на кам аз 4 калима доранд.
    Ҳамин тавр сарлавҳаҳо, номгӯйҳо ва порчаҳои кӯтоҳи ҷадвалӣ
    ба ҳисоби миёнаи дарозии ҷумла ворид намешаванд.
    """
    parts = re.split(r"(?<=[.!?…])\s+|\n+", text)
    out = []
    for p in parts:
        p = p.strip()
        if not p or not re.search(r"[.!?…]$", p):
            continue
        n = len(p.split())
        if n >= 4:
            out.append(p)
    return out


def section_ranges(lines):
    """Диапазони сатрҳо барои ҳар банди асосӣ (сарлавҳаи #-дор)."""
    idx = [(i, l.strip()) for i, l in enumerate(lines) if re.match(r"^#\s+\S", l.strip())]
    ranges = {}
    for n, (i, title) in enumerate(idx):
        end = idx[n + 1][0] if n + 1 < len(idx) else len(lines)
        key = re.sub(r"^#\s+", "", title)
        ranges[key] = lines[i:end]
    return ranges


def main(path: Path):
    raw = path.read_text(encoding="utf-8")
    lines = raw.splitlines()
    plain = strip_markup(raw, keep_tables=True)
    plain_nometa = strip_markup(raw)

    body = plain
    body = body.replace("МУНДАРИҶА", "")
    n_chars = len(re.sub(r"\s+", " ", body).strip())
    pages = n_chars / CHARS_PER_PAGE

    tables = len(re.findall(r"^Ҷадвали\s+\d+\.\d+", raw, flags=re.MULTILINE))
    citations = CITATION_RE.findall(raw)
    placeholders = raw.count("______") + raw.count("[дақиқ кардан лозим]")

    # рӯйхати адабиёт (аз сарлавҳаи «РӮЙХАТИ АДАБИЁТ» то «ЗАМИМАҲО»/охир)
    m = re.search(r"#+\s*РӮЙХАТИ АДАБИЁТ(.*?)(?=\n#\s|\Z)", raw, flags=re.S)
    ref_block = m.group(1) if m else ""
    refs = len(re.findall(r"^\s*\d+[.)]\s+\S", ref_block, flags=re.M))

    secs = section_ranges(lines)
    has = {
        "муқаддима": any("МУҚАДДИМА" in k for k in secs),
        "банд 1": any(k.startswith("БАНДИ 1") for k in secs),
        "банд 2": any(k.startswith("БАНДИ 2") for k in secs),
        "банд 3": any(k.startswith("БАНДИ 3") for k in secs),
        "хулоса": any("ХУЛОСА" in k for k in secs),
        "адабиёт": any("АДАБИЁТ" in k for k in secs),
        "замимаҳо": any("ЗАМИМА" in k for k in secs),
    }

    # ҷадвалҳо дар ҳар банд
    tables_per_chapter = {}
    for k, block in secs.items():
        if k.startswith("БАНДИ"):
            txt = "\n".join(block)
            tables_per_chapter[k.split(".")[0]] = len(
                re.findall(r"^Ҷадвали\s+\d+\.\d+", txt, flags=re.MULTILINE)
            )

    sents = sentences(plain_nometa)
    lens = [len(s.split()) for s in sents]
    avg = sum(lens) / len(lens) if lens else 0
    too_long = [s for s in sents if len(s.split()) > 18]

    bad = {ph: len(re.findall(re.escape(ph), plain, flags=re.I)) for ph in BAD_PHRASES}
    bad_sum = sum(bad.values())

    def mark(ok):
        return "✅ ҳа" if ok else "❌ не"

    print(f"\n📄 Файл: {path.name}")
    print("=" * 62)

    print(f"1. Ҳаҷм ................. {n_chars:,} аломат ≈ {pages:.1f} саҳифа  "
          f"{'✅' if 30 <= pages <= 38 else '⚠️'} (меъёр 30–38)")
    print(f"2. Сохтор ............... " + ", ".join(f"{k}:{mark(v)}" for k, v in has.items()))
    print(f"3. Ҷадвалҳо ............. {tables}  "
          + " | ".join(f"{k}: {v}" for k, v in tables_per_chapter.items()))
    print(f"4. Иқтибосҳо ............ {len(citations)}  {mark(len(citations) >= pages / 3)}")
    print(f"5. Манбаъҳо ............. {refs}  {mark(20 <= refs <= 25)} (меъёр 20–25)")
    print(f"6. Ҷумлаи миёна ......... {avg:.1f} калима  {mark(8 <= avg <= 16)} (меъёр 8–14)")
    print(f"   Ҷумлаҳои >18 калима .. {len(too_long)}")
    print(f"7. Ибораҳои холӣ ........ {bad_sum}  {mark(bad_sum == 0)}")
    for ph, c in bad.items():
        if c:
            print(f"      ⚠️ «{ph}» — {c} маротиба")
    print(f"8. Ҷойҳои «______» ...... {placeholders}  (бояд худатон пур кунед)")
    print("=" * 62)

    if too_long:
        print("\nҶумлаҳои аз 18 калима дароз (ба 2–3 ҷумла ҷудо кунед):")
        for s in too_long[:5]:
            print(f"  • ({len(s.split())} к.) {s[:150]}…" if len(s) > 150 else f"  • ({len(s.split())} к.) {s}")

    # ҳадди нихоӣ
    ok_all = (
        30 <= pages <= 38 and all(has.values()) and bad_sum == 0
        and 20 <= refs <= 25 and len(citations) >= pages / 3
        and all(v >= 1 for v in tables_per_chapter.values())
    )
    print("\n" + ("🎉 Ҳамаи меъёрҳои асосӣ иҷро шуданд." if ok_all
                  else "🛠 Баъзе меъёрҳо иҷро нашудаанд — болоро бинед."))
    return 0 if ok_all else 1


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    sys.exit(main(Path(sys.argv[1])))
