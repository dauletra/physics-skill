from components.list import ListComponent
from questions.base import Question
from render_helpers import answer_block, blank, esc


class ClassifyQuestion(Question):
    """Классифицировать. `answer` — категория → список объектов (каждый
    объект `items` встречается ровно в одном списке одной категории)."""

    type = "classify"

    def __init__(self, items, categories, answer=None, **kwargs):
        super().__init__(**kwargs)
        self.items = items
        self.categories = categories
        self.answer = answer or {}

    def validate(self) -> None:
        seen = []
        for values in self.answer.values():
            seen.extend(values)
        if sorted(seen) != sorted(self.items):
            raise ValueError(
                f"classify: answer values {sorted(seen)} do not partition items {sorted(self.items)}"
            )

    def render(self, mode, lang) -> str:
        if mode == "teacher":
            items_html = ListComponent(items=[esc(item) for item in self.items], marker="none", columns="single").render()
            summary = "; ".join(
                f"{esc(category)}: {', '.join(esc(v) for v in values)}"
                for category, values in self.answer.items()
            )
            return items_html + answer_block(lang, summary)
        rows = [f'<span class="tf-line"><span class="tf-statement">{esc(item)}</span>{blank(30)}</span>' for item in self.items]
        return ListComponent(items=rows, marker="none", columns="single").render()

    @classmethod
    def from_dict(cls, data: dict) -> "ClassifyQuestion":
        return cls(
            prompt=data.get("prompt", ""),
            label=data.get("label"),
            points=data.get("points"),
            items=data["items"],
            categories=data["categories"],
            answer=data.get("answer", {}),
        )
