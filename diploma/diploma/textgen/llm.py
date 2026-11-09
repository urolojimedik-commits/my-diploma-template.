"""Опциональный генератор текста через OpenAI-совместимый API.

По умолчанию система работает детерминированно (см. ``deterministic.py``) и не
требует ни ключей, ни сети. Этот модуль подключается, только если пользователь
сам указал модель и эндпоинт.

В промпте жёстко зафиксировано: писать можно **только** по переданным
источникам, каждое утверждение сопровождать ссылкой ``[@key]``, при
недостатке данных ставить пометку ``{{ТРЕБУЕТСЯ ИСТОЧНИК}}``. Выдуманные
факты, DOI и числа в инструкции прямо запрещены.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from ..model import Plan, Source, Topic
from .base import SectionContext, TextBackend

SYSTEM_PROMPT = (
    "Ты — научный редактор, пишущий раздел курсовой или дипломной работы на русском языке. "
    "Пиши строго академическим стилем, без вводных клише и без выдумывания. "
    "ПРАВИЛА: 1) использовать только факты из переданного списка источников; "
    "2) каждое фактическое утверждение сопровождать ссылкой в формате [@key]; "
    "3) не использовать DOI, числа, названия журналов и результаты, которых нет в переданных "
    "источниках; 4) если для утверждения нет данных, ставить пометку {{ТРЕБУЕТСЯ ИСТОЧНИК}}; "
    "5) возвращать только текст раздела в разметке Markdown, без заголовка раздела."
)


def _source_digest(source: Source) -> str:
    facts = "\n".join(f"  - {f}" for f in source.facts) or f"  - {source.summary_ru}"
    return (
        f"[{source.key}] {source.authors_ru} ({source.year_str}). "
        f"{source.title_display}. {source.venue or ''}. DOI: {source.doi or 'нет'}.\n"
        f"Проверенные утверждения:\n{facts}"
    )


class LLMBackend(TextBackend):
    name = "llm"

    def __init__(self, model: str = "", base_url: str = "", api_key: str | None = None,
                 temperature: float = 0.2, max_tokens: int = 2500, timeout: int = 120):
        self.model = model or os.environ.get("DIPLOMA_LLM_MODEL", "")
        self.base_url = (base_url or os.environ.get("DIPLOMA_LLM_BASE_URL", "")).rstrip("/")
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout

    def available(self) -> bool:
        return bool(self.model and self.base_url and self.api_key)

    def _chat(self, prompt: str) -> str:
        if not self.available():
            raise RuntimeError("LLM-генератор не настроен: укажите модель, base_url и ключ API")
        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"].strip()

    def _digest(self, sources: list[Source]) -> str:
        return "\n\n".join(_source_digest(s) for s in sources)

    def write_section(self, ctx: SectionContext) -> str:
        prompt = (
            f"Тема работы: {ctx.topic.title}\n"
            f"Объект: {ctx.topic.object_ru}; предмет: {ctx.topic.subject_ru}\n"
            f"Раздел: {ctx.section.title} (путь: {ctx.path})\n"
            f"Задача раздела: {ctx.section.goal}\n"
            f"Объём: около {ctx.section.target_words} слов.\n\n"
            f"Доступные проверенные источники:\n{self._digest(ctx.sources)}\n"
        )
        return self._chat(prompt)

    def write_introduction(self, topic: Topic, sources: list[Source], plan: Plan) -> str:
        prompt = (
            f"Тема работы: {topic.title}\n"
            f"Объект: {topic.object_ru}; предмет: {topic.subject_ru}; цель: {topic.goal_ru}\n"
            f"Задачи:\n" + "\n".join(f"- {t}" for t in topic.tasks_ru) + "\n"
            f"Методы: {', '.join(topic.methods_ru)}\n\n"
            f"Напиши раздел «Введение» (актуальность, объект, предмет, цель, задачи, методы, "
            f"структура работы). Доступные проверенные источники:\n{self._digest(sources)}"
        )
        return self._chat(prompt)

    def write_conclusion(self, topic: Topic, sources: list[Source], plan: Plan) -> str:
        prompt = (
            f"Тема работы: {topic.title}\nЦель: {topic.goal_ru}\n"
            f"Напиши «Заключение»: основные выводы, опираясь только на переданные источники; "
            f"отдельно отметь ограничения исследования.\n\n{self._digest(sources)}"
        )
        return self._chat(prompt)

    def write_annotation(self, topic: Topic, sources: list[Source]) -> str:
        prompt = (
            f"Напиши аннотацию (5-7 предложений) к работе «{topic.title}»; "
            f"объект: {topic.object_ru}, предмет: {topic.subject_ru}."
        )
        return self._chat(prompt)
