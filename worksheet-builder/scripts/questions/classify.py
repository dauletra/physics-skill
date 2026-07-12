from components.list import ListComponent
from questions.base import Question, envelope
from render_helpers import answer_block, blank, esc


class ClassifyQuestion(Question):
    """Классифицировать. `category` — инлайн у каждого объекта, значение из
    `categories`; категория без объектов допустима (категория-дистрактор)."""

    type = "classify"

    def __init__(self, items, categories, **kwargs):
        super().__init__(**kwargs)
        self.items = items
        self.categories = categories

    def validate(self) -> None:
        if not self.categories:
            raise ValueError("classify: categories must be non-empty")
        if not self.items:
            raise ValueError("classify: items must be non-empty")
        for i, item in enumerate(self.items):
            if not isinstance(item, dict) or "text" not in item:
                raise ValueError(f"classify: items[{i}] must be an object with 'text'")
            if item.get("category") not in self.categories:
                raise ValueError(
                    f"classify: items[{i}].category {item.get('category')!r} not found in categories {self.categories}"
                )

    def render_body(self, mode, lang) -> str:
        if mode == "teacher":
            items_html = ListComponent(
                items=[esc(item["text"]) for item in self.items], marker="none", columns="single"
            ).render()
            # Сводка по категориям в авторском порядке `categories`; пустая
            # категория (дистрактор) показывается прочерком.
            groups = []
            for category in self.categories:
                texts = [item["text"] for item in self.items if item["category"] == category]
                groups.append(f"{esc(category)}: {', '.join(esc(t) for t in texts) if texts else '—'}")
            return items_html + answer_block(lang, "; ".join(groups))
        rows = [
            f'<span class="tf-line"><span class="tf-statement">{esc(item["text"])}</span>{blank(30)}</span>'
            for item in self.items
        ]
        return ListComponent(items=rows, marker="none", columns="single").render()

    @classmethod
    def from_dict(cls, data: dict) -> "ClassifyQuestion":
        return cls(
            items=data["items"],
            categories=data["categories"],
            **envelope(data),
        )
