#!/usr/bin/env python3
"""
generate_example.py — демо-сборка полной работы.

Запуск:
  python scripts/generate_example.py
  python scripts/generate_example.py --topic "Машинное обучение в финансах" --output examples/demo_мло

Создаёт:
  - plan.md
  - references.bib + bibliography_gost.txt
  - images/*.png
  - 00_Введение.md ... 50_Заключение.md + article.md
  - thesis.docx + thesis.pdf
  - quarto/ (исходники Quarto)
"""

import argparse
import pathlib
import sys

# чтобы импорт работал из корня
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "src"))

from diploma_builder.pipeline import create_project_from_topic, DiplomaPipeline


def main():
    parser = argparse.ArgumentParser(description="Демо-сборка дипломной работы")
    parser.add_argument("--topic", type=str, default="Цифровая трансформация государственного управления в Российской Федерации", help="Тема работы")
    parser.add_argument("--type", type=str, default="диплом", choices=["курсовая", "диплом", "вкр_бакалавр", "магистерская", "статья"])
    parser.add_argument("--discipline", type=str, default="Информационные системы")
    parser.add_argument("--author", type=str, default="Иванов И.И., ИВТ-21")
    parser.add_argument("--output", type=str, default="examples/demo_цифровизация")
    parser.add_argument("--search-rows", type=int, default=15)
    parser.add_argument("--verify", action="store_true", help="Проверять DOI (медленнее)")
    parser.add_argument("--no-pdf", action="store_true")
    parser.add_argument("--no-docx", action="store_true")
    args = parser.parse_args()

    print("=" * 70)
    print(f"Тема: {args.topic}")
    print(f"Тип: {args.type} | Дисциплина: {args.discipline} | Автор: {args.author}")
    print(f"Вывод: {args.output}")
    print("=" * 70)

    cfg = create_project_from_topic(topic=args.topic, work_type=args.type, discipline=args.discipline, author_fio=args.author, output_dir=args.output)

    pipeline = DiplomaPipeline(cfg)
    results = pipeline.run(with_search=True, with_figures=True, with_docx=not args.no_docx, with_pdf=not args.no_pdf, with_quarto=True, search_rows=args.search_rows, verify_sources=args.verify)

    print("\n" + "=" * 70)
    print("АРТЕФАКТЫ:")
    for k, v in results.items():
        vp = pathlib.Path(v)
        if vp.exists():
            if vp.is_file():
                print(f"  ✓ {k}: {vp} ({vp.stat().st_size/1024:.1f} КБ)")
            else:
                files = list(vp.glob("**/*"))
                print(f"  ✓ {k}: {vp} ({len(files)} файлов)")
        else:
            print(f"  - {k}: {v} (не найдено)")

    # Проверка DOCX/PDF на валидность
    if not args.no_docx:
        docx = pathlib.Path(args.output) / "thesis.docx"
        if docx.exists() and docx.stat().st_size > 50000:
            print(f"\n✓ DOCX проверка пройдена: {docx.stat().st_size/1024:.1f} КБ > 50 КБ")
        else:
            print(f"\n⚠️ DOCX мал или отсутствует: {docx.stat().st_size if docx.exists() else 'нет'}")

    if not args.no_pdf:
        pdf = pathlib.Path(args.output) / "thesis.pdf"
        if pdf.exists() and pdf.stat().st_size > 50000:
            print(f"✓ PDF проверка пройдена: {pdf.stat().st_size/1024:.1f} КБ > 50 КБ")
        else:
            print(f"⚠️ PDF мал или отсутствует: {pdf.stat().st_size if pdf.exists() else 'нет'}")

    print("\nДля запуска веб-интерфейса:")
    print("  python -m diploma_builder.cli serve --port 8000")
    print("=" * 70)


if __name__ == "__main__":
    main()

