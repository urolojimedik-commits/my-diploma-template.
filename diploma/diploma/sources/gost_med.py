"""Библиография для медицинской работы: ГОСТ Р 7.0.5-2008 + PMID/DOI.

Отличия от общего модуля ``sources/gost.py``:

* в описание добавляется PMID (идентификатор PubMed) — для медицинских работ
  это обычное требование кафедр;
* источник без DOI или PMID в список литературы **не попадает** (политика
  ``require_doi_or_pmid`` в ``config/medicine.yml``): проверяемая ссылка важнее
  количества ссылок;
* клинические рекомендации (ВОЗ, МЗ РТ, EAU, ESC, AHA, KDIGO) помечаются и при
  желании выносятся в начало списка (``prefer_guidelines``);
* описание не «улучшается» и не дополняется: чего нет в записи — того нет в
  списке. Отсутствующие элементы помечаются как требующие уточнения.

Названия и фамилии сохраняются в языке оригинала (требование ГОСТ Р 7.0.5-2008);
перевод даётся в квадратных скобках ТОЛЬКО если он указан автором записи.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from ..model import Source
from .gost import authors_gost, format_reference, _is_ru

PMID_RE = re.compile(r"^\d{7,8}$")
DOI_RE = re.compile(r"^10\.\d{4,9}/[-._;()/:a-z0-9]+$", re.IGNORECASE)

# Клинические рекомендации: издатели/слова в названии
GUIDELINE_HINTS = (
    "guideline", "recommendation", "клинические рекомендации", "guidelines",
    "консенсус", "consensus", "стандарт", "протокол", "дастур",
)
GUIDELINE_BODIES = ("WHO", "ВОЗ", "МЗ РТ", "EAU", "ESC", "AHA", "KDIGO", "NICE", "МЗ РФ")


@dataclass
class SourceIssue:
    key: str
    level: str  # error | warn | info
    code: str
    message: str

    def __str__(self) -> str:
        return f"[{self.level}] {self.key}: {self.message}"


# --------------------------------------------------------------------------- #
# Проверки
# --------------------------------------------------------------------------- #


def is_valid_doi(doi: str | None) -> bool:
    return bool(doi) and bool(DOI_RE.match(doi.strip()))


def is_valid_pmid(pmid: str | None) -> bool:
    return bool(pmid) and bool(PMID_RE.match(str(pmid).strip()))


def is_guideline(source: Source) -> bool:
    text = f"{source.title or ''} {source.venue or ''} {source.publisher or ''}".lower()
    if any(h in text for h in GUIDELINE_HINTS):
        return True
    return any(b.lower() in text for b in GUIDELINE_BODIES)


def check_source(source: Source, policy=None) -> list[SourceIssue]:
    """Проверяет запись на пригодность для списка литературы.

    Возвращает список замечаний; уровень ``error`` означает, что запись нельзя
    цитировать в тексте.
    """
    from ..structure.medical import get_profile

    policy = policy or get_profile().source_policy
    issues: list[SourceIssue] = []

    has_id = is_valid_doi(source.doi) or is_valid_pmid(source.pmid)
    if policy.require_doi_or_pmid and not has_id:
        issues.append(
            SourceIssue(
                source.key, "error", "no_doi_pmid",
                "Нет ни DOI, ни PMID — запись нельзя цитировать.",
            )
        )
    if source.doi and not is_valid_doi(source.doi):
        issues.append(
            SourceIssue(source.key, "error", "bad_doi", f"Некорректный DOI: {source.doi}")
        )
    if source.pmid and not is_valid_pmid(source.pmid):
        issues.append(
            SourceIssue(source.key, "warn", "bad_pmid", f"Некорректный PMID: {source.pmid}")
        )
    if policy.verify_doi and not source.verified:
        issues.append(
            SourceIssue(
                source.key, "error", "unverified",
                "Запись не прошла проверку (Crossref/PubMed) — в текст не включается.",
            )
        )
    if source.year and source.year < policy.min_year:
        issues.append(
            SourceIssue(
                source.key, "warn", "old_source",
                f"Год {source.year} старше порога {policy.min_year} "
                "(допустимо только как исторический/классический источник).",
            )
        )
    if not source.authors:
        issues.append(
            SourceIssue(source.key, "warn", "no_authors", "Не указаны авторы (допустимо для рекомендаций).")
        )
    if not (source.title or "").strip():
        issues.append(SourceIssue(source.key, "error", "no_title", "Нет названия."))
    if not source.year:
        issues.append(SourceIssue(source.key, "warn", "no_year", "Не указан год."))
    return issues


def citable(sources: list[Source], policy=None) -> list[Source]:
    """Только записи, которые можно цитировать: без ошибок уровня error."""
    out = []
    for s in sources:
        if any(i.level == "error" for i in check_source(s, policy)):
            continue
        out.append(s)
    return out


def audit(sources: list[Source], policy=None) -> list[SourceIssue]:
    issues: list[SourceIssue] = []
    for s in sources:
        issues.extend(check_source(s, policy))
    return issues


# --------------------------------------------------------------------------- #
# Форматирование
# --------------------------------------------------------------------------- #


def _ids(source: Source) -> list[str]:
    bits = []
    if is_valid_doi(source.doi):
        bits.append(f"DOI: {source.doi.strip()}")
    if is_valid_pmid(source.pmid):
        bits.append(f"PMID: {str(source.pmid).strip()}")
    return bits


def format_gost_med(
    source: Source, style: str = "gost", access_date: str = "", lang: str = "tg"
) -> str:
    """ГОСТ Р 7.0.5-2008 + PMID/DOI. Названия — в языке оригинала."""
    from ..lang import get_language

    text = format_reference(source, style=style, access_date=access_date).rstrip(".")
    for bit in _ids(source):
        if bit.split(":")[0] + ":" in text:  # уже есть (добавил gost.py)
            continue
        text += ". " + bit
    if is_guideline(source):
        text += f". ({get_language(lang).t('guidelines_note')})"
    return text.strip() + "."


def sort_key_med(source: Source) -> tuple:
    """ГОСТ-порядок: кириллица, затем латиница; рекомендации — в начало."""
    lead = "0" if is_guideline(source) else "1"
    base = source.authors[0].family if source.authors else (source.title or "")
    group = "0" if (_is_ru(base) or source.language in ("ru", "tg")) else "1"
    return (lead, group, base.lower(), source.year or 0)


def format_bibliography_med(
    sources: list[Source],
    style: str = "gost",
    access_date: str = "",
    policy=None,
    sort_alphabetically: bool = True,
    lang: str = "tg",
) -> list[str]:
    """Готовый нумерованный список литературы (только пригодные записи)."""
    items = citable(sources, policy)
    if sort_alphabetically:
        items = sorted(items, key=sort_key_med)
    out = []
    for i, s in enumerate(items, start=1):
        out.append(
            f"{i}. {format_gost_med(s, style=style, access_date=access_date, lang=lang)}"
        )
    return out


def citation_map(sources: list[Source], policy=None) -> dict[str, int]:
    """Ключ источника → номер в списке литературы (для ссылок в тексте)."""
    items = citable(sources, policy)
    items = sorted(items, key=sort_key_med)
    return {s.key: i for i, s in enumerate(items, start=1)}


def stats(sources: list[Source], policy=None) -> dict:
    """Сводка по корпусу источников для протокола проверки (приложение А)."""
    cit = citable(sources, policy)
    years = [s.year for s in cit if s.year]
    return {
        "total": len(sources),
        "citable": len(cit),
        "rejected": len(sources) - len(cit),
        "with_doi": sum(1 for s in cit if is_valid_doi(s.doi)),
        "with_pmid": sum(1 for s in cit if is_valid_pmid(s.pmid)),
        "guidelines": sum(1 for s in cit if is_guideline(s)),
        "years": (min(years), max(years)) if years else (None, None),
    }


def verification_table(sources: list[Source], policy=None) -> list[dict]:
    """Строки приложения «Протокол проверки источников»."""
    from ..structure.medical import get_profile

    policy = policy or get_profile().source_policy
    rows = []
    for s in sources:
        issues = check_source(s, policy)
        rows.append(
            {
                "key": s.key,
                "authors": authors_gost(s) or "—",
                "title": (s.title or "")[:80],
                "year": s.year or "—",
                "doi": s.doi or "—",
                "pmid": s.pmid or "—",
                "verified": "ҳа" if s.verified else "не",
                "via": s.verified_via or "—",
                "status": "қабул" if not any(i.level == "error" for i in issues) else "рад",
                "notes": "; ".join(i.code for i in issues) or "—",
            }
        )
    return rows
