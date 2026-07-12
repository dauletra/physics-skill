"""Уровень 3: классы вопросов — по одному на педагогический вид. Каждый
хранит контент и ответ вместе (своя JSON-форма, см. references/task-schema.md)
и сам решает, что передать компонентам уровня 2 в каждом режиме.

Буква (`label`) вычисляется и мутируется в `document.py` (сборка задания), не
самим классом — вопрос только знает, что с ней делать в своей строке
заголовка. `label`/`points` — чистая метаданные (для буквы и баллов), не
текст: описательный текст вопроса не хранится на объекте `Question` вообще —
это обычный `text`-элемент в `Task.items`, идущий перед этим вопросом, как
любой другой элемент уровня 2 (см. "Буквы и баллы" в task-schema.md)."""

from abc import ABC, abstractmethod
from typing import ClassVar, Literal, Optional

RenderMode = Literal["student", "teacher"]


class Question(ABC):
    type: ClassVar[str]

    def __init__(self, label: Optional[str] = None, points: Optional[int] = None):
        self.label = label
        self.points = points

    @abstractmethod
    def render(self, mode: RenderMode, lang: str) -> str: ...

    @classmethod
    @abstractmethod
    def from_dict(cls, data: dict) -> "Question": ...

    def validate(self) -> None:
        """Переопределяется в подклассах со своими инвариантами; по умолчанию
        нет дополнительных проверок сверх того, что сделал `from_dict`."""
        return None
