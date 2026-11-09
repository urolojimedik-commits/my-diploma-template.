"""Шаг 3. Поиск и отбор реальных научных источников.

Порядок работы:

1. По ключевым словам темы строятся поисковые запросы (русские термины
   переводятся словарём ``ru_en``).
2. Опрашиваются сетевые провайдеры (Crossref → Semantic Scholar → OpenAlex →
   arXiv). При отсутствии сети их результаты просто отсутствуют.
3. К результатам всегда добавляется локальный проверенный корпус
   (``data/seed_sources.json``) — он же обеспечивает работу офлайн.
4. Записи дедуплицируются по DOI (затем по нормализованному названию),
   ранжируются по релевантности и проверяются (см. ``verify.py``).
5. Непроверенные источники **не попадают** ни в текст, ни в список
   литературы — о них сообщается в протоколе проверки.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from ..model import Source, Topic
from ..ru_en import to_english
from .providers import (
    DEFAULT_ONLINE_PROVIDERS,
    ProviderUnavailable,
    SeedProvider,
    dedupe_key,
    search_provider,
)
from .verify import VerificationResult, verify_sources


@dataclass
class SearchReport:
    queries: list[str] = field(default_factory=list)
    providers_used: list[str] = field(default_factory=list)
    providers_failed: list[str] = field(default_factory=list)
    candidates: int = 0
    sources: list[Source] = field(default_factory=list)
    verification: list[VerificationResult] = field(default_factory=list)
    offline: bool = False
    warnings: list[str] = field(default_factory=list)

    def summary(self) -> str:
        lines = [
            f"Запросы: {'; '.join(self.queries) if self.queries else '—'}",
            f"Провайдеры: {', '.join(self.providers_used) if self.providers_used else 'нет (офлайн)'}",
            f"Недоступны: {', '.join(self.providers_failed) if self.providers_failed else '—'}",
            f"Найдено кандидатов: {self.candidates}",
            f"Прошло проверку и отобрано: {len(self.sources)}",
        ]
        lines += [f"! {w}" for w in self.warnings]
        return "\n".join(lines)


def build_queries(topic: Topic) -> list[str]:
    """Формирует компактные английские запросы из ключевых слов темы."""
    en_terms: list[str] = []
    for k in topic.keywords_en:
        for part in re.split(r"[,\s]+", k):
            part = part.strip()
            if len(part) > 2 and part.lower() not in {t.lower() for t in en_terms}:
                en_terms.append(part)
    if not en_terms:
        en_terms = [to_english(topic.title)]
    queries: list[str] = []
    # 1) полный запрос (не более 8 терминов)
    queries.append(" ".join(en_terms[:8]))
    # 2) ядро темы: первые 4 термина
    if len(en_terms) > 4:
        queries.append(" ".join(en_terms[:4]))
    # 3) попарные сочетания — расширяют покрытие
    for i in range(0, min(len(en_terms) - 1, 6), 2):
        queries.append(" ".join(en_terms[i : i + 2]))
    seen: set[str] = set()
    return [q for q in queries if q and not (q in seen or seen.add(q))]


def _tokens(text: str) -> set[str]:
    return {t for t in re.split(r"\W+", (text or "").lower()) if len(t) > 2}


def relevance(source: Source, topic: Topic) -> float:
    """Эвристическая релевантность: пересечение терминов + «свежесть»."""
    query_tokens: set[str] = set()
    for k in topic.keywords_en:
        query_tokens |= _tokens(k)
    for k in topic.keywords_ru:
        query_tokens |= _tokens(k)
    if not query_tokens:
        return 0.0
    title_tokens = _tokens(source.title) | _tokens(source.title_ru)
    abstract_tokens = _tokens(source.abstract) | _tokens(source.summary_ru) | _tokens(
        " ".join(source.facts)
    )
    tag_tokens = _tokens(" ".join(source.tags))
    score = 0.0
    for t in query_tokens:
        if t in title_tokens:
            score += 3.0
        if t in abstract_tokens:
            score += 1.0
        if t in tag_tokens:
            score += 2.0
    score /= max(len(query_tokens), 1)
    if source.year:
        if source.year >= 2021:
            score += 0.6
        elif source.year >= 2015:
            score += 0.3
    if source.language == "ru":
        score += 0.1  # для русскоязычной работы полезны и русские источники
    if source.type in {"preprint", "component"}:
        score -= 0.3
    return round(score, 4)


def dedupe(sources: list[Source]) -> list[Source]:
    """Дедупликация: DOI важнее названия; проверенные записи вытесняют сырые."""
    best: dict[str, Source] = {}
    for s in sources:
        k = dedupe_key(s)
        cur = best.get(k)
        if cur is None:
            best[k] = s
            continue
        cur_score = (2 if cur.verified else 0) + (1 if cur.summary_ru else 0) + cur.relevance
        new_score = (2 if s.verified else 0) + (1 if s.summary_ru else 0) + s.relevance
        if new_score > cur_score:
            best[k] = s
    return list(best.values())


def merge_sources(base: list[Source], extra: list[Source]) -> list[Source]:
    return dedupe(base + extra)


def search_sources(
    topic: Topic,
    max_sources: int = 20,
    offline: bool = False,
    providers: list[str] | None = None,
    verify: bool = True,
    allow_unverified: bool = False,
) -> SearchReport:
    """Основная точка входа шага 3."""
    report = SearchReport(offline=offline)
    report.queries = build_queries(topic)

    # --- локальный проверенный корпус (работает всегда) ---
    seed = SeedProvider().load()
    if seed:
        report.providers_used.append("seed(локальный проверенный корпус)")

    candidates: list[Source] = list(seed)

    # --- сетевые провайдеры ---
    if not offline:
        for name in providers or DEFAULT_ONLINE_PROVIDERS:
            got_any = False
            for q in report.queries[:3]:
                try:
                    found = search_provider(name, q, max_results=15)
                except ProviderUnavailable as exc:
                    if name not in report.providers_failed:
                        report.providers_failed.append(f"{name}: {exc}")
                    break
                if found:
                    got_any = True
                    candidates += found
            if got_any and name not in report.providers_used:
                report.providers_used.append(name)
            elif not got_any and name not in report.providers_failed:
                report.providers_failed.append(name)

    for s in candidates:
        s.relevance = relevance(s, topic)
    candidates = dedupe(candidates)
    report.candidates = len(candidates)

    if not candidates:
        report.warnings.append(
            "Источников не найдено. Текст будет содержать явные пометки "
            "«ТРЕБУЕТСЯ ИСТОЧНИК» вместо ссылок: выдумывать ссылки система не умеет."
        )
        return report

    # --- проверка и отбор ---
    allow_network = not offline
    if verify:
        verified, log = verify_sources(candidates, allow_network=allow_network)
        report.verification = log
        rejected = [r for r in log if not r.verified]
        if rejected and not allow_network:
            report.warnings.append(
                f"{len(rejected)} источников не имеют штампа проверки и сеть недоступна: "
                "они исключены из текста и списка литературы."
            )
        pool = verified if not allow_unverified else verified + [r.source for r in rejected]
    else:
        pool = candidates
        report.warnings.append("Проверка DOI отключена (--no-verify): ссылки не подтверждены.")

    pool.sort(key=lambda s: (s.relevance, s.year or 0), reverse=True)
    report.sources = pool[:max_sources]
    return report
