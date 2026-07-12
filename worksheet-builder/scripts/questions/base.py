"""Уровень 3: классы вопросов — по одному на педагогический вид. Каждый
хранит контент и ответ вместе (своя JSON-форма, см. references/task-schema.md)
и сам решает, что передать компонентам уровня 2 в каждом режиме.

Буква (`label`) вычисляется и мутируется в `document.py` (сборка задания), не
самим классом — вопрос только знает, что с ней делать в своей строке
заголовка. Строку заголовка (номер/буква + prompt + баллы) тоже строит
`document.py` через `label`/`prompt`/`points` этого объекта; `render()`
отдаёт только тело/ответ под этой строкой.

`prompt` хранится как `TextComponent`, не голая строка — тот же примитив,
что рендерит любой другой текстовый контент (эскейпинг делается один раз,
здесь, через `TextComponent.from_dict`), а не bespoke `esc()`-вызов внутри
`document.py`."""

from abc import ABC, abstractmethod
from typing import ClassVar, Literal, Optional

from components.text import TextComponent

RenderMode = Literal["student", "teacher"]


class Question(ABC):
    type: ClassVar[str]

    def __init__(self, prompt: str = "", label: Optional[str] = None, points: Optional[int] = None):
        self.prompt = TextComponent.from_dict({"body": prompt})
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
