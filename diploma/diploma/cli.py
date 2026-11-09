"""Командная строка системы подготовки курсовых и дипломных работ.

Примеры:

.. code-block:: bash

    python -m diploma generate --topic "Применение машинного обучения ..." \\
        --type diploma --author "Иванов И. И." --out build/demo
    python -m diploma search --topic "..." --offline
    python -m diploma plan --topic "..."
    python -m diploma web --port 8000
    python -m diploma check
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .pipeline import TOTAL_STEPS, run_pipeline
from .settings import APP_DIR, Settings, load_dotenv

DEF_TOPIC = (
    "Применение методов машинного обучения для автоматизированной диагностики "
    "мочекаменной болезни по данным компьютерной томографии"
)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="diploma",
        description="Система автоматизации подготовки курсовых и дипломных работ",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = p.add_subparsers(dest="command")

    def add_common(sp: argparse.ArgumentParser) -> None:
        sp.add_argument("--topic", "-t", default=DEF_TOPIC, help="тема работы")
        sp.add_argument(
            "--type",
            default="diploma",
            choices=["diploma", "bachelor", "master", "course"],
            help="тип работы (по умолчанию diploma)",
        )
        sp.add_argument("--out", "-o", default=str(APP_DIR / "build" / "demo"), help="каталог сборки")
        sp.add_argument("--bib-style", default="gost", choices=["gost", "apa", "ieee", "vancouver"])
        sp.add_argument("--max-sources", type=int, default=20)
        sp.add_argument("--offline", action="store_true", help="не обращаться к сети")
        sp.add_argument("--no-verify", action="store_true", help="не проверять DOI")
        sp.add_argument("--pdf-engine", default="auto", choices=["auto", "latex", "builtin"])
        sp.add_argument("--author", default="Иванов И. И.")
        sp.add_argument("--group", default="")
        sp.add_argument("--chair", default="")
        sp.add_argument("--supervisor", default="")
        sp.add_argument("--institution", default="")
        sp.add_argument("--city", default="")
        sp.add_argument("--year", type=int, default=None)
        sp.add_argument("--text-backend", default="deterministic", choices=["deterministic", "llm"])
        sp.add_argument("--llm-model", default="")
        sp.add_argument("--llm-base-url", default="")
        sp.add_argument("--no-zip", action="store_true")
        sp.add_argument("--no-quarto", action="store_true")
        sp.add_argument("--dpi", type=int, default=200)

    g = sub.add_parser("generate", help="полный конвейер: тема → DOCX и PDF")
    add_common(g)

    pl = sub.add_parser("plan", help="построить план и структуру")
    add_common(pl)

    se = sub.add_parser("search", help="поиск и проверка источников")
    add_common(se)
    se.add_argument("--json", action="store_true", help="вывести результат в JSON")

    web = sub.add_parser("web", help="веб-интерфейс со скачиванием")
    web.add_argument("--host", default="0.0.0.0")
    web.add_argument("--port", type=int, default=8000)
    web.add_argument("--out", "-o", default=str(APP_DIR / "build" / "jobs"))

    sub.add_parser("check", help="проверить окружение (Pandoc, Quarto, LaTeX, шрифты)")
    return p


def _settings_from_args(args) -> Settings:
    return Settings(
        topic=args.topic,
        work_type=args.type,
        out_dir=Path(args.out),
        bib_style=args.bib_style,
        max_sources=args.max_sources,
        search_offline=args.offline,
        verify_doi=not args.no_verify,
        pdf_engine=getattr(args, "pdf_engine", "auto"),
        author=args.author,
        group=args.group,
        chair=args.chair,
        supervisor=args.supervisor,
        institution=args.institution,
        city=args.city,
        year=args.year,
        text_backend=args.text_backend,
        llm_model=args.llm_model,
        llm_base_url=args.llm_base_url,
        make_zip=not args.no_zip,
        export_quarto=not args.no_quarto,
        figure_dpi=args.dpi,
    )


def _progress(step: int, total: int, message: str) -> None:
    print(f"[{step}/{total}] {message}")


def cmd_generate(args) -> int:
    st = _settings_from_args(args)
    result = run_pipeline(st, progress=_progress)
    print()
    print("=" * 72)
    print(f"Тема: {result.document.topic.title}")
    print(f"Разделов: {len(list(result.document.plan.walk()))}; "
          f"источников: {len(result.document.sources)}; "
          f"рисунков: {len(result.document.figures)}; таблиц: {len(result.document.tables)}")
    if result.search_report:
        print()
        print(result.search_report.summary())
    print()
    print("Файлы:")
    for label, path in result.files.items():
        size = Path(path).stat().st_size if Path(path).is_file() else 0
        print(f"  {label:<22} {path}" + (f"  ({size/1024:.0f} КБ)" if size else ""))
    if result.warnings:
        print()
        print("Предупреждения:")
        for w in result.warnings:
            print("  !", w)
    print("=" * 72)
    return 0


def cmd_plan(args) -> int:
    from .outline import build_plan, plan_to_markdown
    from .topic import build_topic

    topic = build_topic(args.topic, args.type)
    plan = build_plan(topic, args.type)
    print(plan_to_markdown(plan))
    print("Объект:", topic.object_ru)
    print("Предмет:", topic.subject_ru)
    print("Цель:", topic.goal_ru)
    print("Методы:", ", ".join(topic.methods_ru))
    return 0


def cmd_search(args) -> int:
    from .sources.search import search_sources
    from .topic import build_topic

    topic = build_topic(args.topic, args.type)
    report = search_sources(
        topic,
        max_sources=args.max_sources,
        offline=args.offline,
        verify=not args.no_verify,
    )
    print(report.summary())
    print()
    for i, s in enumerate(report.sources, start=1):
        print(f"{i:>2}. {s.authors_ru} ({s.year}) — {s.title_display}")
        print(f"    {s.venue} | DOI: {s.doi or '—'} | проверен: {s.verified}")
    if args.json:
        print()
        print(json.dumps([s.to_dict() for s in report.sources], ensure_ascii=False, indent=2))
    return 0


def cmd_check(args) -> int:
    from .sources.providers import SeedProvider
    from .settings import has_latex, has_pandoc, has_quarto

    print("Окружение системы")
    print("-" * 60)
    print(f"Python            : {sys.version.split()[0]}")
    print(f"Pandoc            : {'да' if has_pandoc() else 'НЕТ'}")
    from .render.pandoc_utils import pandoc_version

    print(f"  версия          : {pandoc_version() or '—'}")
    print(f"Quarto            : {'да' if has_quarto() else 'нет (экспорт проекта доступен)'}")
    print(f"LaTeX (PDF)       : {'да' if has_latex() else 'нет — используется встроенный PDF-рендерер'}")
    seed = SeedProvider().load()
    print(f"Проверенный корпус: {len(seed)} записей, все с DOI: "
          f"{all(s.doi for s in seed)}")
    try:
        import matplotlib  # noqa: F401

        print("matplotlib        : да")
    except ImportError:
        print("matplotlib        : НЕТ")
    try:
        import docx  # noqa: F401

        print("python-docx       : да")
    except ImportError:
        print("python-docx       : НЕТ")
    try:
        import reportlab  # noqa: F401

        print("reportlab         : да")
    except ImportError:
        print("reportlab         : НЕТ")
    return 0


def cmd_web(args) -> int:
    from .web.server import serve

    serve(host=args.host, port=args.port, out_root=Path(args.out))
    return 0


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 1
    return {
        "generate": cmd_generate,
        "plan": cmd_plan,
        "search": cmd_search,
        "check": cmd_check,
        "web": cmd_web,
    }[args.command](args)
