"""
bibliography.py — формирование списка литературы (BibTeX + ГОСТ).
"""

from __future__ import annotations

import pathlib
import re
from typing import List

from .config import SourceRecord


class BibliographyManager:
    """Управляет библиографией."""

    def __init__(self, sources: List[SourceRecord]):
        self.sources = sources

    def sort_gost(self) -> List[SourceRecord]:
        """Сортировка по ГОСТ: по алфавиту (русские → латиница), потом по году."""

        def sort_key(s: SourceRecord):
            # русские первые (проверяем первый символ фамилии)
            first = s.authors[0] if s.authors else s.title
            is_russian = bool(re.search(r"[а-яА-Я]", first))
            return (0 if is_russian else 1, first.lower(), s.year)

        return sorted(self.sources, key=sort_key)

    def to_bibtex(self, output_path: pathlib.Path) -> pathlib.Path:
        """Сохраняет references.bib."""
        output_path = pathlib.Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        # проверка уникальности ключей
        seen_keys = set()
        unique_sources = []
        for s in self.sources:
            key = s.key
            orig = key
            i = 1
            while key in seen_keys:
                key = f"{orig}{i}"
                i += 1
            if key != s.key:
                s.key = key
            seen_keys.add(key)
            unique_sources.append(s)

        content = "% Автоматически сгенерировано diploma_builder\n"
        content += "% Проверено DOI: только записи с verified=True прошли проверку Crossref\n"
        content += "% Учебные примеры помечены в title\n\n"
        for s in unique_sources:
            content += s.to_bibtex() + "\n\n"
        output_path.write_text(content, encoding="utf-8")
        print(f"[bibliography] BibTeX → {output_path} ({len(unique_sources)} записей)")
        return output_path

    def to_gost_list(self, output_path: pathlib.Path = None) -> List[str]:
        """Возвращает список строк ГОСТ."""
        sorted_sources = self.sort_gost()
        gost_lines = []
        for i, s in enumerate(sorted_sources, 1):
            gost_lines.append(s.to_gost(i))
        if output_path:
            output_path = pathlib.Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text("\n\n".join(gost_lines), encoding="utf-8")
            print(f"[bibliography] ГОСТ список → {output_path}")
        return gost_lines

    def to_markdown_bibliography(self) -> str:
        """Markdown для вставки в Quarto."""
        lines = ["# Список использованных источников", ""]
        gost = self.to_gost_list()
        for line in gost:
            lines.append(line)
            lines.append("")
        return "\n".join(lines)

    def verify_all(self, verbose: bool = True) -> dict:
        """Статистика по верификации."""
        total = len(self.sources)
        verified = sum(1 for s in self.sources if s.verified and s.doi)
        with_doi = sum(1 for s in self.sources if s.doi)
        synthetic = sum(1 for s in self.sources if "учебный пример" in s.title.lower())
        stats = {
            "total": total,
            "verified": verified,
            "with_doi": with_doi,
            "synthetic": synthetic,
            "verified_pct": round(verified / with_doi * 100, 1) if with_doi else 0,
        }
        if verbose:
            print(f"[bibliography] Всего: {total}, с DOI: {with_doi}, верифицировано: {verified} ({stats['verified_pct']}%), учебных: {synthetic}")
        return stats

    def check_citations(self, text: str) -> dict:
        """Проверяет, что все @cite в тексте есть в библиографии."""
        cites = re.findall(r"@([a-zA-Z0-9_]+)", text)
        keys = {s.key for s in self.sources}
        missing = [c for c in cites if c not in keys]
        unused = [k for k in keys if k not in cites]
        return {"cited": cites, "missing": missing, "unused": unused, "keys": keys}

