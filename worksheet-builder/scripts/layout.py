"""Layout DSL: `Task.layout` партиционирует `Task.items` на строки — см.
"Layout DSL" в references/task-schema.md. Каждый элемент — либо целое N (N
элементов идут в одну строку, поровну делят ширину), либо список явных
процентов (длина = число элементов в строке, сумма = 100)."""


def partition_layout(items, layout):
    if not layout:
        return [1] * len(items)
    total = sum(row if isinstance(row, int) else len(row) for row in layout)
    if total != len(items):
        raise ValueError(f"layout describes {total} item(s) but there are {len(items)}")
    return layout
