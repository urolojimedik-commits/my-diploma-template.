"""
cli.py — командная строка.

Примеры:
  python -m diploma_builder.cli --topic "Цифровизация госуправления" --type диплом --build
  python -m diploma_builder.cli --config project.yaml --build --no-pdf
  python -m diploma_builder.cli search --topic "машинное обучение" --rows 10
  python -m diploma_builder.cli serve --port 8000
"""

from __future__ import annotations

import argparse
import pathlib
import sys

from .config import WorkType
from .pipeline import create_project_from_topic, DiplomaPipeline
from .planner import Planner
from .search import SourceSearcher


def cmd_build(args):
    if args.config:
        import yaml

        data = yaml.safe_load(pathlib.Path(args.config).read_text(encoding="utf-8"))
        # восстановление ProjectConfig
        from .config import ProjectConfig

        cfg = ProjectConfig.from_dict(data)
        cfg.output_dir = pathlib.Path(args.output or data.get("output_dir", "output"))
        if args.topic:
            cfg.topic = args.topic
    else:
        if not args.topic:
            print("Ошибка: укажите --topic или --config")
            sys.exit(1)
        cfg = create_project_from_topic(
            topic=args.topic,
            work_type=args.type,
            discipline=args.discipline,
            author_fio=args.author,
            output_dir=args.output,
        )

    pipeline = DiplomaPipeline(cfg)
    pipeline.run(
        with_search=not args.no_search,
        with_figures=not args.no_figures,
        with_docx=not args.no_docx,
        with_pdf=not args.no_pdf,
        with_quarto=not args.no_quarto,
        search_rows=args.search_rows,
        verify_sources=args.verify,
    )


def cmd_plan(args):
    cfg = create_project_from_topic(topic=args.topic, work_type=args.type, discipline=args.discipline, output_dir=args.output)
    planner = Planner(cfg)
    planner.generate()
    md = planner.to_markdown()
    print(md)
    out = pathlib.Path(args.output) / "plan.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(md, encoding="utf-8")
    print(f"\nПлан сохранён → {out}")


def cmd_search(args):
    searcher = SourceSearcher()
    sources = searcher.search(args.topic, rows=args.rows, verify=args.verify)
    print(f"\nНайдено {len(sources)} источников:")
    for i, s in enumerate(sources, 1):
        v = "✓" if s.verified else "○"
        print(f"{i}. {v} {s.key} | {s.authors[0] if s.authors else ''} ({s.year})")
        print(f"   {s.title}")
        if s.doi:
            print(f"   DOI: {s.doi} | {s.journal or s.publisher or ''}")
        print()
    # сохранение
    if args.output:
        import json

        pathlib.Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump([s.__dict__ for s in sources], f, ensure_ascii=False, indent=2)
        print(f"Сохранено → {args.output}")


def cmd_serve(args):
    # запуск Flask
    from .web.app import create_app

    app = create_app()
    print(f"Запуск веб-интерфейса на http://0.0.0.0:{args.port}")
    # важно: host 0.0.0.0 для preview
    app.run(host="0.0.0.0", port=args.port, debug=args.debug)


def main():
    parser = argparse.ArgumentParser(description="diploma_builder — автоматизация курсовых/дипломов", prog="diploma_builder")
    sub = parser.add_subparsers(dest="command")

    # build (default)
    p_build = sub.add_parser("build", help="Собрать работу (план→источники→текст→DOCX/PDF)")
    p_build.add_argument("--topic", type=str, help="Тема работы")
    p_build.add_argument("--type", type=str, default="диплом", choices=["курсовая", "диплом", "вкр_бакалавр", "магистерская", "статья"], help="Тип работы")
    p_build.add_argument("--discipline", type=str, default="Информационные системы", help="Дисциплина")
    p_build.add_argument("--author", type=str, default="Иванов И.И.", help="ФИО автора")
    p_build.add_argument("--config", type=str, help="YAML конфиг проекта")
    p_build.add_argument("--output", type=str, default="output", help="Папка вывода")
    p_build.add_argument("--search-rows", type=int, default=15, help="Сколько источников искать")
    p_build.add_argument("--verify", action="store_true", help="Проверять DOI")
    p_build.add_argument("--no-search", action="store_true", help="Пропустить поиск")
    p_build.add_argument("--no-figures", action="store_true", help="Пропустить графики")
    p_build.add_argument("--no-docx", action="store_true", help="Пропустить DOCX")
    p_build.add_argument("--no-pdf", action="store_true", help="Пропустить PDF")
    p_build.add_argument("--no-quarto", action="store_true", help="Пропустить Quarto")

    # plan
    p_plan = sub.add_parser("plan", help="Только план")
    p_plan.add_argument("--topic", required=True, type=str, help="Тема")
    p_plan.add_argument("--type", type=str, default="диплом")
    p_plan.add_argument("--discipline", type=str, default="Информационные системы")
    p_plan.add_argument("--output", type=str, default="output")

    # search
    p_search = sub.add_parser("search", help="Поиск источников")
    p_search.add_argument("--topic", required=True, type=str)
    p_search.add_argument("--rows", type=int, default=10)
    p_search.add_argument("--verify", action="store_true")
    p_search.add_argument("--output", type=str, help="JSON для сохранения")

    # serve
    p_serve = sub.add_parser("serve", help="Запустить веб-интерфейс")
    p_serve.add_argument("--port", type=int, default=8000)
    p_serve.add_argument("--debug", action="store_true")

    # Если вызваны без subcommand, но с --topic — считаем build
    # Добавим глобальные аргументы для удобства
    parser.add_argument("--topic", type=str, help="Тема (shortcut для build)")
    parser.add_argument("--type", type=str, default="диплом")
    parser.add_argument("--discipline", type=str, default="Информационные системы")
    parser.add_argument("--author", type=str, default="Иванов И.И.")
    parser.add_argument("--output", type=str, default="output")
    parser.add_argument("--build", action="store_true", help="Собрать (для совместимости)")

    args = parser.parse_args()

    # shortcut: если указаны --topic без команды — build
    if args.command is None:
        if args.topic or args.build:
            # переопределим
            class Shim:
                pass

            shim = Shim()
            shim.topic = args.topic
            shim.type = args.type
            shim.discipline = args.discipline
            shim.author = args.author
            shim.config = None
            shim.output = args.output
            shim.search_rows = 15
            shim.verify = False
            shim.no_search = False
            shim.no_figures = False
            shim.no_docx = False
            shim.no_pdf = False
            shim.no_quarto = False
            cmd_build(shim)
            return
        parser.print_help()
        return

    if args.command == "build":
        cmd_build(args)
    elif args.command == "plan":
        cmd_plan(args)
    elif args.command == "search":
        cmd_search(args)
    elif args.command == "serve":
        cmd_serve(args)


if __name__ == "__main__":
    main()

