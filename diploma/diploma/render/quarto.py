"""Экспорт проекта Quarto (шаг 8, «родной» путь для пользователей Quarto).

Если у пользователя установлен Quarto, он получает классический проект:
``_quarto.yml`` + ``index.qmd`` + ``references.bib`` + CSL + ``media/``.
Рендер выполняется командами ``quarto render`` (docx / pdf / html / epub).

Встроенный рендерер (Pandoc + ReportLab) при этом остаётся основным:
он работает без установки Quarto и LaTeX.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from ..sources.bibtex import write_bibtex

QUARTO_YML = """project:
  type: default
  render:
    - index.qmd

format:
  docx:
    output-file: {output_docx}
    toc: true
    reference-doc: _reference.docx
  pdf:
    output-file: {output_pdf}
    pdf-engine: xelatex
    toc: true
    toc-depth: 2
    documentclass: scrreprt
    geometry:
      - a4paper
      - left=30mm
      - right=15mm
      - top=20mm
      - bottom=20mm
    fontsize: 14pt
    linestretch: 1.5
    fig-pos: H
  html:
    toc: true
    embed-resources: true
  epub:
    toc: true

lang: ru-RU
bibliography: references.bib
csl: assets/gost.csl
link-citations: true
toc-title: Содержание
crossref:
  fig-title: Рисунок
  tbl-title: Таблица
  fig-prefix: рис.
  tbl-prefix: табл.
  chapters: true
execute:
  freeze: false
"""

README = """# Проект Quarto для работы «{title}»

Проект создан системой автоматизации подготовки курсовых и дипломных работ.
Ссылки в тексте оставлены в виде `[@key]`, поэтому список литературы
формирует сам Quarto (CSL: ГОСТ Р 7.0.5-2008, `assets/gost.csl`).

## Сборка

```bash
quarto render            # все форматы
quarto render --to docx  # только Word
quarto render --to pdf   # только PDF (нужен XeLaTeX/TinyTeX)
```

## Состав

- `index.qmd` — текст работы;
- `references.bib` — библиография (все записи с DOI, проверены);
- `media/` — рисунки;
- `data/` — наборы данных, по которым построены графики;
- `assets/gost.csl` — стиль цитирования.

Если Quarto не установлен, итоговые DOCX и PDF уже собраны встроенным
рендерером и лежат в каталоге сборки выше.
"""


def export_quarto_project(
    markdown: str,
    out_dir: Path,
    sources: list,
    media_dir: Path | Path | None = None,
    title: str = "Работа",
    csl_source: Path | None = None,
) -> Path:
    """Пишет готовый проект Quarto в ``out_dir``."""
    out_dir = Path(out_dir)
    (out_dir / "media").mkdir(parents=True, exist_ok=True)
    (out_dir / "data").mkdir(parents=True, exist_ok=True)
    (out_dir / "assets").mkdir(parents=True, exist_ok=True)

    (out_dir / "index.qmd").write_text(markdown, encoding="utf-8")
    write_bibtex(sources, out_dir / "references.bib")

    (out_dir / "_quarto.yml").write_text(
        QUARTO_YML.format(output_docx="work.docx", output_pdf="work.pdf"), encoding="utf-8"
    )
    (out_dir / "README.md").write_text(README.format(title=title), encoding="utf-8")

    if csl_source and Path(csl_source).exists():
        shutil.copy(csl_source, out_dir / "assets" / "gost.csl")
    if media_dir and Path(media_dir).exists():
        for f in Path(media_dir).iterdir():
            if f.is_file():
                shutil.copy(f, out_dir / "media" / f.name)
    return out_dir
