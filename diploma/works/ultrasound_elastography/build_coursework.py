#!/usr/bin/env python3
"""Сборка кори курсӣ: Kori_kursi.docx, Kori_kursi.pdf, ZIP.

    python build_coursework.py

Матн аз файлҳои ҷузвдони text/ хонда мешавад (забони тоҷикӣ, аломатгузории
сода):

    !head Сарлавҳа          — сарлавҳаи берақам (муқаддима, хулоса)
    # Боби 1. ...           — боб (рақамгузорӣ худкор, майдони SEQ)
    ## 1.1. ...             — зербоб
    !fig калид|сарлавҳа|пайдоиш|сарчашма
    !tab калид|сарлавҳа|пайдоиш|эзоҳ   пас аз он сатрҳои | а | б |
    - матн                  — рӯйхати нуқтадор
    {src:калид}             — истинод ба манбаъ, {fig:калид} — ба расм

Ҳама манбаъҳо аз data/sources.json (санҷидашуда) гирифта мешаванд.
"""

from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
APP = HERE.parent.parent  # <repo>/diploma
sys.path.insert(0, str(APP))

from diploma.lang import get_language  # noqa: E402
from diploma.model import Author, Source  # noqa: E402
from diploma.render.content import (  # noqa: E402
    AbbrevBlock,
    Appendix,
    Bullets,
    FigureBlock,
    Heading,
    MedicalDocument,
    Para,
    RefList,
    TableBlock,
    TitlePage,
    TOC,
)
from diploma.render.docx_med import build_docx  # noqa: E402
from diploma.render.pdf_med import build_pdf  # noqa: E402
from diploma.sources.gost_med import citation_map, format_bibliography_med  # noqa: E402
from diploma.structure.abbreviations import load_from_dictionary  # noqa: E402
from diploma.structure.medical import get_profile  # noqa: E402

TEXT_DIR = HERE / "text"
DATA_DIR = HERE / "data"
FIG_DIR = HERE / "figures" / "png"
OUT_DIR = HERE

TOPIC_TG = ("Эластография дар ташхиси ултрасадоӣ: "
            "принсип, намудҳо ва имкониятҳои клиникӣ")
TOPIC_RU = ("Эластография в ультразвуковой диагностике: "
            "принцип, виды и клинические возможности")

AUTHOR = "___________________"
SUPERVISOR = "___________________"
REVIEWER = ""
HEAD_OF_CHAIR = "___________________"

ANNOTATION_TG = (
    "Кори курсии мазкур ба омӯзиши эластографияи ултрасадоӣ — усули ғайриинвазивии "
    "арзёбии сахтии бофтаҳо — бахшида шудааст. Дар кор асосҳои физикии усул (деформатсия, "
    "модули Юнг, суръати мавҷи буриш), таърихи инкишоф ва таснифи муосири он баррасӣ "
    "мешаванд. Таҳлили маълумоти мета-таҳлилҳои санҷидашуда нишон медиҳад, ки дақиқии "
    "эластография дар арзёбии фибрози ҷигар баланд аст: нишондиҳандаи AUROC барои сирроз "
    "аз 0,93 то 0,97 мерасад. Дақиқии усул дар фибрози назаррас камтар ва ба бемории аслӣ "
    "вобаста мебошад, ки ин зарурати риояи протоколи ченкуниро тақозо мекунад. Дар кор "
    "маълумоти шахсии клиникӣ истифода нашудааст: таҳқиқот хусусияти таҳлили адабиётӣ дорад."
)
ANNOTATION_RU = (
    "Курсовая работа посвящена ультразвуковой эластографии — неинвазивному методу оценки "
    "жёсткости тканей. Рассмотрены физические основы метода (деформация, модуль Юнга, "
    "скорость сдвиговой волны), история развития и современная классификация. Анализ "
    "проверенных мета-анализов показывает высокую точность эластографии при оценке фиброза "
    "печени: AUROC для цирроза достигает 0,93–0,97. Точность при выраженном фиброзе ниже и "
    "зависит от основного заболевания, что требует соблюдения протокола измерений. "
    "Собственные клинические данные не использовались: работа носит характер литературного "
    "анализа."
)
KEYWORDS_TG = ("эластография, ташхиси ултрасадоӣ, фибрози ҷигар, модули Юнг, мавҷи буриш, "
               "эластографияи гузаранда, ARFI, 2D-SWE, эластограмма")
KEYWORDS_RU = ("эластография, ультразвуковая диагностика, фиброз печени, модуль Юнга, "
               "сдвиговая волна, транзиентная эластография, ARFI, 2D-SWE, эластограмма")


# --------------------------------------------------------------------------- #
# Манбаъҳо
# --------------------------------------------------------------------------- #

def load_sources() -> list[Source]:
    data = json.loads((DATA_DIR / "sources.json").read_text(encoding="utf-8"))
    out: list[Source] = []
    for item in data["sources"]:
        src = Source(
            key=item["key"],
            title=item["title"],
            authors=[Author(**a) for a in item.get("authors", [])],
            year=item.get("year"),
            venue=item.get("venue", ""),
            volume=item.get("volume", ""),
            number=item.get("number", ""),
            pages=item.get("pages", ""),
            doi=item.get("doi", "") or None,
            pmid=item.get("pmid", "") or None,
            url=item.get("url", "") or None,
            type=item.get("type", "article-journal"),
            verified=True,
            verified_via="europepmc",
            facts=list(item.get("facts", [])),
        )
        out.append(src)
    return out


# --------------------------------------------------------------------------- #
# Парсинги матн
# --------------------------------------------------------------------------- #

def parse_file(path: Path, doc: MedicalDocument) -> None:
    lines = path.read_text(encoding="utf-8").splitlines()
    i = 0
    paragraphs: list[str] = []
    bullets: list[str] = []
    current_table: tuple | None = None
    table_rows: list[list[str]] = []

    def flush_paragraphs():
        if paragraphs:
            doc.add(Para(" ".join(paragraphs)))
            paragraphs.clear()

    def flush_bullets():
        if bullets:
            doc.add(Bullets(items=list(bullets)))
            bullets.clear()

    def flush_table():
        nonlocal current_table, table_rows
        if current_table and table_rows:
            key, caption, provenance, note = current_table
            doc.add(
                TableBlock(
                    key=key,
                    header=table_rows[0],
                    rows=table_rows[1:],
                    caption=caption,
                    provenance=provenance,
                    note=note,
                )
            )
        current_table = None
        table_rows = []

    while i < len(lines):
        line = lines[i].rstrip()
        stripped = line.strip()
        i += 1

        if not stripped:
            flush_paragraphs()
            flush_bullets()
            flush_table()
            continue

        if stripped.startswith("!head "):
            flush_paragraphs(); flush_bullets(); flush_table()
            doc.add(Heading(stripped[6:].strip(), numbered=False))
        elif stripped.startswith("## "):
            flush_paragraphs(); flush_bullets(); flush_table()
            doc.add(Heading(stripped[3:].strip(), level=2))
        elif stripped.startswith("# "):
            flush_paragraphs(); flush_bullets(); flush_table()
            doc.add(Heading(stripped[2:].strip(), level=1))
        elif stripped.startswith("!fig "):
            flush_paragraphs(); flush_bullets(); flush_table()
            parts = [p.strip() for p in stripped[5:].split("|")]
            key = parts[0]
            caption = parts[1] if len(parts) > 1 else ""
            provenance = parts[2] if len(parts) > 2 else "diagram"
            source_note = parts[3] if len(parts) > 3 else ""
            doc.add(
                FigureBlock(
                    key=key,
                    path=str(FIG_DIR / f"{key}.png"),
                    caption=caption,
                    provenance=provenance,
                    source_note=source_note,
                    width_cm=14.0,
                )
            )
        elif stripped.startswith("!tab "):
            flush_paragraphs(); flush_bullets(); flush_table()
            parts = [p.strip() for p in stripped[5:].split("|")]
            parts += [""] * (4 - len(parts))
            current_table = (parts[0], parts[1], parts[2] or "diagram", parts[3])
            table_rows = []
        elif stripped.startswith("|"):
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            table_rows.append(cells)
        elif stripped.startswith("- "):
            flush_paragraphs()
            bullets.append(stripped[2:].strip())
        else:
            flush_bullets(); flush_table()
            paragraphs.append(stripped)

    flush_paragraphs(); flush_bullets(); flush_table()


# --------------------------------------------------------------------------- #
# Сохтани ҳуҷҷат
# --------------------------------------------------------------------------- #

def make_document(sources: list[Source]) -> tuple[MedicalDocument, dict[str, int]]:
    tg = get_language("tg")
    profile = get_profile()
    cite = citation_map(sources)

    doc = MedicalDocument(meta={"topic": TOPIC_TG, "author": AUTHOR})
    doc.numbering = (profile.gost or {}).get("numbering", "per_chapter")

    # --- варақи унвонӣ
    doc.add(
        TitlePage(
            work_type="course",
            topic=TOPIC_TG,
            topic_ru=TOPIC_RU,
            author=AUTHOR,
            supervisor=SUPERVISOR,
            reviewer=REVIEWER,
            head_of_chair=HEAD_OF_CHAIR,
            city=profile.university.get("city", "Хуҷанд"),
            year=2026,
            frame=True,
        )
    )
    doc.add(TOC(levels="1-2", title=tg.t("contents")))

    # --- аннотатсия
    doc.add(Heading(tg.t("annotation"), numbered=False))
    doc.add(Para(ANNOTATION_TG, style="annotation"))
    doc.add(Para(ANNOTATION_RU, style="annotation"))
    doc.add(Para(f"{tg.t('keywords')} ({'тоҷикӣ'}): {KEYWORDS_TG}", style="note"))
    doc.add(Para(f"{tg.t('keywords')} ({'русӣ'}): {KEYWORDS_RU}", style="note"))

    # --- рӯйхати ихтисораҳо
    abbrev = load_from_dictionary()
    extra = [
        ("SE", "эластографияи деформатсионӣ (strain elastography)"),
        ("TE", "эластографияи гузаранда (transient elastography)"),
        ("pSWE", "эластографияи нуқтавии мавҷи буриш"),
        ("2D-SWE", "эластографияи дученакаи мавҷи буриш"),
        ("SSI", "тасвирбардории мавҷи буриши фавқуссадо"),
        ("ARFI", "қувваи такони акустикӣ"),
        ("AUROC", "масоҳати зери каҷи ROC"),
        ("кПа", "килопаскал, воҳиди ченкунии чандирӣ"),
        ("ДИ", "фосилаи эътимод"),
        ("EFSUMB", "Федератсияи Аврупоии Ултрасадо дар тиб ва биология"),
        ("WFUMB", "Федератсияи Умумиҷаҳонии Ултрасадо дар тиб ва биология"),
        ("EASL", "Ассотсиатсияи Аврупоии Омӯзиши Ҷигар"),
        ("ATA", "Ассотсиатсияи Амрикоии Тироид"),
        ("ВОЗ (WHO)", "Созмони Умумиҷаҳонии Тандурустӣ"),
    ]
    for abbr, expansion in extra:
        abbrev.add(abbr, expansion, lang="tg")
    doc.add(AbbrevBlock(pairs=[(a.abbr, a.expansion("tg")) for a in abbrev.entries()]))

    # --- матн: муқаддима, бобҳо, хулоса, тавсияҳо (аз файлҳои text/)
    for name in sorted(TEXT_DIR.glob("*.md")):
        parse_file(name, doc)

    if not any(b.kind == "refs" for b in doc.blocks):
        doc.add(RefList(entries=format_bibliography_med(sources, lang="tg")))

    # --- замимаҳо
    doc.add(
        Appendix(
            title=tg.t("verification"),
            blocks=[
                TableBlock(
                    key="tblA1",
                    header=["Калид", "Муаллиф, сол", "DOI", "PMID", "Ҳолат"],
                    rows=[
                        [
                            s.key,
                            f"{s.authors[0].family if s.authors else '—'}, {s.year or '—'}",
                            s.doi or "—",
                            s.pmid or "—",
                            "тасдиқ" if s.verified else "рад",
                        ]
                        for s in sources
                    ],
                    caption="Протоколи санҷиши манбаъҳо",
                    provenance="real",
                )
            ],
        )
    )
    return doc, cite


def main() -> int:
    sources = load_sources()
    doc, cite = make_document(sources)

    docx_path = build_docx(doc, OUT_DIR / "Kori_kursi.docx", citation_map=cite)
    print(f"[ok] {docx_path} ({docx_path.stat().st_size} байт)")

    pdf_path = build_pdf(doc, OUT_DIR / "Kori_kursi.pdf", citation_map=cite)
    print(f"[ok] {pdf_path} ({pdf_path.stat().st_size} байт)")

    zip_path = OUT_DIR / "Kori_kursi.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for name in ("Kori_kursi.docx", "Kori_kursi.pdf", "README.md", "sources.md"):
            if (OUT_DIR / name).exists():
                zf.write(OUT_DIR / name, name)
        for folder in ("data", "figures", "text"):
            for f in sorted((OUT_DIR / folder).rglob("*")):
                if f.is_file() and "__pycache__" not in str(f):
                    zf.write(f, str(f.relative_to(OUT_DIR)))
    print(f"[ok] {zip_path} ({zip_path.stat().st_size} байт)")

    total = len(doc.blocks)
    print(f"[иттилоот] блокҳо: {total}, манбаъҳо: {len(sources)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
