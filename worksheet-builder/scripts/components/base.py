"""Чистые компоненты — только отрисовка, никакого знания об
ответе/правильности/режиме ученик-учитель (см. references/task-schema.md).

Правило экранирования: компонент хранит уже HTML-безопасный текст.
`from_dict()` (сырой JSON-блок из `Task.blocks`) вызывает `esc()` на
авторском тексте; классы вопросов, которые строят компонент программно,
сами эскейпят пользовательский текст до передачи в конструктор — `render()`
самого компонента ничего повторно не эскейпит."""

from abc import ABC, abstractmethod


class Component(ABC):
    @abstractmethod
    def render(self) -> str: ...

    @classmethod
    @abstractmethod
    def from_dict(cls, data: dict) -> "Component": ...
