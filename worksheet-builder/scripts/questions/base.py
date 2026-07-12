"""Классы вопросов — по одному на педагогический вид. Каждый хранит контент
и ответ вместе (естественные поля своего вида, ответ инлайн — см.
references/task-schema.md и schema-design-principles.md) и сам решает, что
передать чистым компонентам в каждом режиме.

Конверт одинаков у всех видов: `type` + опциональные `id`/`explanation`.
Нумерация и баллы на вопросе не живут — это метаданные контейнеров
(`Task`/`Part`, см. task.py/document.py). Описательный текст вопроса — не
поле на объекте, а обычный `text`-блок рядом в дереве."""

from abc import ABC, abstractmethod
from typing import ClassVar, Literal, Optional

from render_helpers import answer_block

RenderMode = Literal["student", "teacher"]


def envelope(data: dict) -> dict:
    """Общие поля конверта вопроса — передаются в `Question.__init__` из
    `from_dict` каждого подкласса."""
    return {"id": data.get("id"), "explanation": data.get("explanation")}


class Question(ABC):
    type: ClassVar[str]

    def __init__(self, id: Optional[str] = None, explanation: Optional[str] = None):
        self.id = id
        self.explanation = explanation

    def render(self, mode: RenderMode, lang: str) -> str:
        """Тело вопроса + (в тичер-режиме) `explanation` — единообразно для
        всех видов, подклассы реализуют только `render_body()`."""
        body = self.render_body(mode, lang)
        if mode == "teacher" and self.explanation:
            body += answer_block(lang, self.explanation)
        return body

    @abstractmethod
    def render_body(self, mode: RenderMode, lang: str) -> str: ...

    @classmethod
    @abstractmethod
    def from_dict(cls, data: dict) -> "Question": ...

    def validate(self) -> None:
        """Переопределяется в подклассах со своими инвариантами; по умолчанию
        нет дополнительных проверок сверх того, что сделал `from_dict`."""
        return None
