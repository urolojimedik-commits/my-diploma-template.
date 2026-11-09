"""Проверка источников.

Главное правило системы: **в текст и в список литературы попадают только
проверенные источники**. Проверка означает, что DOI действительно существует и
метаданные, присланные реестром, совпадают с ожидаемыми (год, название).

Проверка выполняется двумя способами:

1. ``verify_doi_registry`` — resolv DOI через ``https://doi.org/api/handles/``
   (не зависит от Crossref);
2. ``verify_via_crossref`` — запрос метаданных в Crossref и сверка полей.

Если сеть недоступна, используется штамп проверки из локального корпуса
(``verified_via`` / ``verified_at``). Источник без штампа и без возможности
проверки получает ``verified=False`` и в текст не попадает — вместо него в
отчёт выводится явное предупреждение.
"""

from __future__ import annotations

import json
import re
import urllib.parse
from dataclasses import dataclass

from ..model import Source
from .providers import (
    CrossrefProvider,
    ProviderUnavailable,
    clean_text,
    http_get_json,
    http_get_text,
)


@dataclass
class VerificationResult:
    source: Source
    verified: bool
    method: str  # doi-handle | crossref | seed-stamp | network-unavailable | not-found
    detail: str = ""


def verify_doi_registry(doi: str, timeout: int = 15) -> bool:
    """Проверяет, зарегистрирован ли DOI в реестре doi.org."""
    url = f"https://doi.org/api/handles/{urllib.parse.quote(doi)}"
    try:
        data = json.loads(http_get_text(url, timeout=timeout))
    except (ProviderUnavailable, json.JSONDecodeError):
        raise ProviderUnavailable("doi.org недоступен")
    return int(data.get("responseCode", 0)) == 1


def verify_via_crossref(source: Source, timeout: int = 20) -> VerificationResult:
    """Сверяет метаданные источника с записью Crossref."""
    if not source.doi:
        return VerificationResult(source, False, "no-doi", "DOI отсутствует")
    try:
        found = CrossrefProvider().by_doi(source.doi)
    except ProviderUnavailable as exc:
        return VerificationResult(source, False, "network-unavailable", str(exc))
    except Exception as exc:  # нестандартный ответ API
        return VerificationResult(source, False, "network-unavailable", f"Ошибка Crossref: {exc}")
    if not found:
        return VerificationResult(source, False, "not-found", "DOI не найден в Crossref")
    title_a = re.sub(r"\W+", "", source.title.lower())
    title_b = re.sub(r"\W+", "", found.title.lower())
    title_match = title_a[:60] and title_b[:60] and (
        title_a[:60] == title_b[:60] or title_a in title_b or title_b in title_a
    )
    year_match = (source.year is None) or (found.year is None) or (source.year == found.year)
    if title_match and year_match:
        # обогащаем запись достоверными данными реестра
        source.title = found.title or source.title
        source.venue = source.venue or found.venue
        source.volume = source.volume or found.volume
        source.pages = source.pages or found.pages
        source.publisher = source.publisher or found.publisher
        if not source.authors and found.authors:
            source.authors = found.authors
        source.year = source.year or found.year
        source.verified = True
        source.verified_via = "crossref-api"
        return VerificationResult(source, True, "crossref", "Метаданные совпали")
    return VerificationResult(
        source,
        False,
        "mismatch",
        f"Расхождение: Crossref — «{found.title}», {found.year}",
    )


def verify_source(source: Source, allow_network: bool = True) -> VerificationResult:
    """Проверяет один источник, учитывая офлайн-режим и имеющиеся штампы."""
    if source.verified and source.verified_via:
        return VerificationResult(source, True, "seed-stamp", f"Проверен: {source.verified_via}")
    if not allow_network:
        return VerificationResult(
            source, False, "network-unavailable", "Нет сети и нет штампа проверки"
        )
    result = verify_via_crossref(source)
    if result.verified:
        return result
    if source.doi:
        try:
            if verify_doi_registry(source.doi):
                source.verified = True
                source.verified_via = "doi-handle"
                return VerificationResult(source, True, "doi-handle", "DOI зарегистрирован")
        except ProviderUnavailable as exc:
            return VerificationResult(source, False, "network-unavailable", str(exc))
    return result


def verify_sources(
    sources: list[Source], allow_network: bool = True
) -> tuple[list[Source], list[VerificationResult]]:
    """Проверяет список источников.

    Возвращает ``(пригодные для цитирования, протокол проверки)``.
    """
    good: list[Source] = []
    log: list[VerificationResult] = []
    for s in sources:
        res = verify_source(s, allow_network=allow_network)
        log.append(res)
        if res.verified:
            good.append(s)
    return good, log


def verification_report(log: list[VerificationResult]) -> str:
    lines = ["# Протокол проверки источников", ""]
    lines.append("| Источник | DOI | Статус | Способ | Примечание |")
    lines.append("| --- | --- | --- | --- | --- |")
    for r in log:
        status = "проверен" if r.verified else "не прошёл проверку"
        lines.append(
            f"| {clean_text(r.source.title)[:60]} | {r.source.doi or '—'} | {status} | "
            f"{r.method} | {r.detail} |"
        )
    return "\n".join(lines) + "\n"
