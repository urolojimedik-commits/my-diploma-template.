#!/usr/bin/env python3
"""Демонстрация этапа 2: Word-документ медицинской работы на таджикском.

    python make_docx_demo.py [--out build/stage2/document.docx] [--frame]
                             [--continuous] [--lang tg|ru]

Собирает полноценный .docx:

* титульный лист по реквизитам из config/university.yml (флаг --frame
  добавляет рамку по ГОСТ 7.32-2017);
* содержание — полем Word TOC (обновляется в Word: Ctrl+A, F9);
* автонумерация «Боби 1», «1.1», «Расм 2.1», «Ҷадвал 2.1» — полями SEQ,
  а не вписанными цифрами;
* нумерация страниц внизу по центру, начиная со 2-й страницы;
* список сокращений, список литературы (ГОСТ Р 7.0.5-2008, с PMID/DOI),
  приложения.

Данные в демо-документе: числовые значения помечены как **учебный пример**
(синтетика) — реальные данные автор подставляет в config/work.yml и
data/patients.csv на этапе 3.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from diploma.lang import get_language
from diploma.model import Author, Source
from diploma.render.content import (
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
from diploma.render.docx_med import build_docx
from diploma.sources.gost_med import citation_map, format_bibliography_med
from diploma.structure.abbreviations import load_from_dictionary
from diploma.structure.medical import get_profile

HERE = Path(__file__).resolve().parent
MEDIA = HERE / "build" / "stage2" / "media"

# Источники — только проверенные DOI/PMID (см. data/seed_sources.json).
SOURCES = [
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
    Source(
        key="alelign2018",
        title="Kidney Stone Disease: An Update on Current Concepts",
        authors=[Author("Alelign", "T"), Author("Petros", "B")],
        year=2018,
        venue="Adv Urol",
        pages="3068365",
        doi="10.1155/2018/3068365",
        pmid="29515627",
        verified=True,
        verified_via="crossref",
    ),
]


def make_figure(path: Path) -> Path:
    """Учебный график на таджикском (данные смоделированы)."""
    import matplotlib

    matplotlib.use("Agg")
    from matplotlib import font_manager, rcParams
    import matplotlib.pyplot as plt

    fonts = Path(matplotlib.__file__).parent / "mpl-data" / "fonts" / "ttf"
    for name in ("DejaVuSerif.ttf", "DejaVuSans.ttf"):
        if (fonts / name).exists():
            font_manager.fontManager.addfont(str(fonts / name))
    rcParams["font.family"] = "DejaVu Serif"
    rcParams["axes.unicode_minus"] = False

    fig, ax = plt.subplots(figsize=(7, 4), dpi=200)
    groups = ["Гурӯҳи асосӣ", "Гурӯҳи назоратӣ"]
    values = [62.5, 41.3]
    bars = ax.bar(groups, values, color=["#2E6F9E", "#9EC7E8"])
    ax.set_ylabel("Самаранокӣ, %")
    ax.set_title("Муқоисаи самаранокии усулҳо (намунаи таълимӣ)")
    for bar, value in zip(bars, values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            value + 1,
            f"{value:.1f} %".replace(".", ","),
            ha="center",
        )
    ax.set_ylim(0, 75)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


def build_document(lang_code: str = "tg", continuous: bool = False, frame: bool = False) -> MedicalDocument:
    profile = get_profile()
    tg = get_language(lang_code)
    doc = MedicalDocument(meta={"lang": lang_code})
    doc.numbering = "continuous" if continuous else "per_chapter"

    # ------------------------------------------------------------ титульный
    doc.add(
        TitlePage(
            work_type="diploma",
            topic=(
                "Истифодаи усулҳои омӯзиши мошинӣ барои ташхиси автоматии "
                "бемории санги гурда"
            ),
            topic_ru=(
                "Применение методов машинного обучения для автоматической "
                "диагностики мочекаменной болезни"
            ),
            author="Алиев А. А.",
            supervisor="Петров П. П., н. и. тиб, дотсент",
            reviewer="Каримов К. К., н. и. тиб",
            head_of_chair="Раҳимов Р. Р., д. и. тиб, профессор",
            city=profile.university.get("city", "Хуҷанд"),
            year=2026,
            frame=frame,
        )
    )

    doc.add(TOC(levels="1-2", title=tg.t("contents")))

    # ------------------------------------------------------------ аннотатсия
    doc.add(Heading(tg.t("annotation"), numbered=False))
    doc.add(
        Para(
            "Дар кори хатмкунандагон масъалаи истифодаи усулҳои омӯзиши мошинӣ "
            "барои ташхиси автоматии бемории санги гурда баррасӣ мешавад. "
            "Мақсади кор — баҳодиҳии дақиқии моделҳои муосир дар асоси "
            "тасвирҳои томографияи компютерӣ. Маълумотҳо аз сарчашмаҳои "
            "санҷидашуда (DOI, PMID) гирифта шудаанд; натиҷаҳои ададӣ дар ин "
            "ҳуҷҷат танҳо ҳамчун намунаи таълимӣ оварда шудаанд.",
            style="annotation",
        )
    )
    doc.add(
        Para(
            f"{tg.t('keywords')}: санги гурда, томографияи компютерӣ, "
            "омӯзиши мошинӣ, ташхис.",
            style="note",
        )
    )

    # ------------------------------------------------------------ ихтисораҳо
    abbrev = load_from_dictionary()
    abbrev.scan_text("Усулҳои КТ, УЗИ ва МРТ истифода шуданд.")
    doc.add(AbbrevBlock(pairs=[(a.abbr, a.expansion(lang_code)) for a in abbrev.entries()]))

    # --------------------------------------------------------------- муқаддима
    doc.add(Heading(tg.t("introduction"), numbered=False))
    doc.add(
        Para(
            "Бемории санги гурда яке аз бемориҳои паҳншудаи системаи пешоб "
            "мебошад. Тибқи маълумотҳои адабиёт, сатҳи паҳншавӣ дар ҷаҳон "
            "тақрибан 12 %-ро ташкил медиҳад {src:alelign2018}. Усулҳои "
            "анъанавии ташхис вобаста ба таҷрибаи мутахассис буда, хавфи "
            "хато доранд."
        )
    )
    doc.add(
        Para(
            "Мақсади таҳқиқот — баланд бардоштани дақиқии ташхис бо роҳи "
            "истифодаи усулҳои омӯзиши мошинӣ."
        )
    )
    doc.add(Bullets(items=[
        "омӯхтани усулҳои мавҷудаи ташхис;",
        "муқоисаи моделҳои омӯзиши мошинӣ;",
        "баҳодиҳии дақиқӣ ва ҳассосият.",
    ]))

    # ------------------------------------------------------------------ боби 1
    doc.add(Heading("Баррасии адабиёт", level=1))
    doc.add(Heading("Вазъи муосири масъала", level=2))
    doc.add(
        Para(
            "Дар солҳои охир шумораи таҳқиқотҳо оид ба истифодаи шабакаҳои "
            "нейронӣ дар урология меафзояд. Дастурамали клиникии EAU аҳамияти "
            "дақиқии ташхиси визуалиро қайд мекунад {src:turk2016}."
        )
    )
    doc.add(Heading("Истифодаи технологияҳои иттилоотӣ дар тиб", level=2))
    doc.add(
        Para(
            "Моделҳои ёдгирии амиқ дар таҳлили тасвирҳои томографияи "
            "компютерӣ натиҷаҳои умедбахш нишон медиҳанд {src:yildirim2021}. "
            "Намунаи чунин муқоиса дар {fig:fig1} оварда шудааст."
        )
    )

    # ------------------------------------------------------------------ боби 2
    doc.add(Heading("Мавод ва усулҳои таҳқиқот", level=1))
    doc.add(Heading("Тарҳи таҳқиқот ва хусусияти беморон", level=2))
    doc.add(
        Para(
            "Маълумоти шахсии клиникии муаллиф то ҳол ворид нашудааст, бинобар "
            "ин ҷадвали хусусияти беморон бо ишораи «Маълумот нокифоя» пешниҳод "
            "мешавад: система рақамҳоро ихтироъ намекунад."
        )
    )
    doc.add(
        TableBlock(
            key="tbl1",
            header=["Нишондиҳанда", "Гурӯҳи асосӣ", "Гурӯҳи назоратӣ"],
            rows=[
                ["Шумораи беморон", tg.missing_data(), tg.missing_data()],
                ["Сину сол, сол", tg.missing_data(), tg.missing_data()],
            ],
            caption="Хусусияти беморон",
            provenance="unknown",
        )
    )
    doc.add(Heading("Усулҳои коркарди оморӣ", level=2))
    doc.add(
        Para(
            "Натиҷаҳо дар шакли M±SD ва Me [Q1; Q3] пешниҳод мешаванд; "
            "фарқият дар сатҳи p<0,05 аҳамиятнок ҳисоб мешавад."
        )
    )

    # ------------------------------------------------------------------ боби 3
    doc.add(Heading("Натиҷаҳои таҳқиқот", level=1))
    doc.add(Heading("Натиҷаҳои асосӣ", level=2))
    doc.add(
        Para(
            "Дар {fig:fig1} муқоисаи самаранокии усулҳо нишон дода шудааст. "
            "Рақамҳо танҳо барои намоиш (намунаи таълимӣ) истифода шудаанд."
        )
    )
    doc.add(
        FigureBlock(
            key="fig1",
            path=str(MEDIA / "fig1.png"),
            caption="Муқоисаи самаранокии усулҳои ташхис",
            provenance="synthetic",
            width_cm=14.0,
        )
    )
    doc.add(
        TableBlock(
            key="tbl2",
            header=["Усул", "Дақиқӣ, %", "Ҳассосият, %"],
            rows=[["Модели асосӣ", "96,8", "95,0"], ["Усули анъанавӣ", "81,8", "88,2"]],
            caption="Нишондиҳандаҳои дақиқӣ",
            provenance="real",
            source_note="Yildirim (DOI: 10.1016/j.compbiomed.2021.104569)",
        )
    )

    # ------------------------------------------------------------------ боби 4
    doc.add(Heading("Муҳокимаи натиҷаҳо", level=1))
    doc.add(Heading("Муқоиса бо маълумотҳои адабиёт", level=2))
    doc.add(
        Para(
            "Нишондиҳандаҳои бадастомада бо натиҷаҳои {src:yildirim2021} "
            "мувофиқат мекунанд. Маҳдудиятҳо: ҳаҷми интихоб ва якмарказии "
            "таҳқиқот."
        )
    )

    # ------------------------------------------------------------------ хулоса
    doc.add(Heading(tg.t("conclusion"), numbered=False))
    doc.add(Bullets(items=[
        "Усулҳои омӯзиши мошинӣ дақиқии ташхисро баланд мебардоранд.",
        "Барои ҷорӣ намудан санҷиш дар гурӯҳҳои калон лозим аст.",
    ]))

    # ---------------------------------------------------------------- тавсияҳо
    doc.add(Heading(tg.t("recommendations"), numbered=False))
    doc.add(Bullets(items=[
        "Истифодаи протоколҳои санҷидашудаи КТ дар таҷрибаи клиникӣ.",
        "Омӯзиши кадрҳо барои кор бо системаҳои иттилоотӣ.",
    ]))

    # ---------------------------------------------------------------- адабиёт
    doc.add(RefList(entries=format_bibliography_med(SOURCES, lang=lang_code)))

    # ---------------------------------------------------------------- замимаҳо
    doc.add(
        Appendix(
            title=tg.t("verification"),
            blocks=[
                TableBlock(
                    key="tblA1",
                    header=["Сарчашма", "DOI", "PMID", "Ҳолат"],
                    rows=[
                        [s.key, s.doi or "—", s.pmid or "—", "қабул" if s.verified else "рад"]
                        for s in SOURCES
                    ],
                    caption="Натиҷаи санҷиши сарчашмаҳо",
                    provenance="real",
                )
            ],
        )
    )
    return doc


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=str(HERE / "build" / "stage2" / "document.docx"))
    ap.add_argument("--frame", action="store_true", help="рамка на титульном листе (ГОСТ 7.32-2017)")
    ap.add_argument("--continuous", action="store_true", help="сквозная нумерация рисунков")
    ap.add_argument("--lang", default="tg", choices=["tg", "ru"])
    args = ap.parse_args()

    make_figure(MEDIA / "fig1.png")
    doc = build_document(lang_code=args.lang, continuous=args.continuous, frame=args.frame)
    path = build_docx(
        doc,
        args.out,
        citation_map=citation_map(SOURCES),
        lang_code=args.lang,
    )
    print(f"[ok] {path} ({path.stat().st_size} байт)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
