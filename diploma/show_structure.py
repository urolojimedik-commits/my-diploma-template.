#!/usr/bin/env python3
"""Демонстрация этапа 1: структура медицинской работы на таджикском.

    python show_structure.py [--type diploma|course|master] [--out FILE]

Печатает (или сохраняет в Markdown) структуру IMRAD, список сокращений,
пример оформления списка литературы по ГОСТ Р 7.0.5-2008 и результат
проверки работы на соответствие требованиям из config/*.yml.

Никаких выдуманных данных: если собственных данных нет, скрипт это показывает.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from diploma.lang import get_language  # noqa: E402
from diploma.model import Author, Source, Topic  # noqa: E402
from diploma.sources.gost_med import format_bibliography_med, stats  # noqa: E402
from diploma.structure.abbreviations import load_from_dictionary  # noqa: E402
from diploma.structure.medical import check_work, get_profile, build_medical_plan  # noqa: E402
from diploma.structure.sections import flatten, next_figure_number  # noqa: E402

# Примеры записей — все с проверенными DOI/PMID (см. data/seed_sources.json).
SAMPLES = [
    Source(
        key="turk2016",
        title="EAU Guidelines on Diagnosis and Conservative Management of Urolithiasis",
        authors=[Author("Turk", "C")],
        year=2016,
        venue="Eur Urol",
        volume="69",
        pages="468-474",
        doi="10.1016/j.eururo.2015.07.040",
        pmid="26318714",
        verified=True,
        verified_via="crossref",
    ),
    Source(
        key="yildirim2021",
        title="Deep learning model for automated kidney stone detection using coronal CT images",
        authors=[Author("Yildirim", "K")],
        year=2021,
        venue="Comput Biol Med",
        volume="135",
        pages="104569",
        doi="10.1016/j.compbiomed.2021.104569",
        verified=True,
        verified_via="crossref",
    ),
]


def build_report(work_type: str) -> str:
    tg = get_language("tg")
    profile = get_profile()
    topic = Topic(raw="", title="", work_type=work_type)
    _, outline = build_medical_plan(topic, work_type=work_type)

    out: list[str] = []
    out.append(f"# Сохтори кор ({work_type})\n")
    out.append(
        f"Забони асосӣ: **{profile.main_language}** · "
        f"Библиография: {profile.gost.get('bibliography')} · "
        f"Сохтор: {profile.gost.get('report')}\n"
    )
    out.append("## Мундариҷа\n")
    for s in flatten(outline):
        if s.level == 1:
            out.append(f"- **{s.heading}**")
        elif s.level == 2:
            out.append(f"    - {s.heading}")
        else:
            out.append(f"- {s.heading}")
    out.append("")

    out.append("## Рақамгузории расмҳо ва ҷадвалҳо\n")
    counters: dict[str, int] = {}
    out.append(f"- {tg.figure_caption(next_figure_number(counters, 2), 'Намуна')}")
    out.append(f"- {tg.figure_caption(next_figure_number(counters, 2), 'Намуна')}")
    out.append(f"- {tg.table_caption(next_figure_number(counters, 3), 'Намуна', tg.own_data_label())}")
    out.append(f"- Пайдоиши маълумот: {tg.source_label()} / {tg.own_data_label()} / "
               f"{tg.missing_data()}")
    out.append("")

    out.append("## Рӯйхати ихтисораҳо (аз луғати истилоҳот)\n")
    for line in load_from_dictionary().render_lines("tg"):
        out.append(f"- {line}")
    out.append("")

    out.append("## Намунаи рӯйхати адабиёт (ГОСТ Р 7.0.5-2008)\n")
    for line in format_bibliography_med(SAMPLES):
        out.append(f"{line}\n")
    out.append(f"Омор: {stats(SAMPLES)}\n")

    out.append("## Санҷиши талабот\n")
    results = check_work(work_type, n_sources=len(SAMPLES), n_verified=len(SAMPLES))
    if not results:
        out.append("- Ҳама талаботҳо иҷро шудаанд.")
    for r in results:
        out.append(f"- [{r.level}] {r.code}: {r.message}")
        if r.question:
            out.append(f"    - **Саволи ба муаллиф:** {r.question}")
    return "\n".join(out) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--type", default="diploma", choices=["course", "diploma", "master"])
    ap.add_argument("--out", default="", help="сохранить отчёт в Markdown-файл")
    args = ap.parse_args()
    report = build_report(args.type)
    print(report)
    if args.out:
        Path(args.out).write_text(report, encoding="utf-8")
        print(f"[ok] ҳисобот: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
