"""The document manifest — `document.json`.

The title of the page and the order of the top-level blocks, and nothing
else: everything that shows on the sheet is a block, the questionnaire header
included. The blocks themselves live one per file in `blocks/<id>.json`, so a
targeted edit touches one small file instead of the whole document.
"""

from __future__ import annotations

from typing import Any, Optional

from physics_svg.document.blocks import DOC_BLOCK
from physics_svg.schema import Invalid, field, parse, spec


@spec
class DocumentSpec:
    """Манифест документа."""

    title: str = field(
        default="",
        doc="Заголовок вкладки браузера; на листе название печатает блок "
        "'heading' с level 1",
    )
    order: Optional[list[str]] = field(
        default=None, doc="Порядок блоков: имена файлов из blocks/ без расширения"
    )

    def check(self) -> None:
        if self.order is not None and len(set(self.order)) != len(self.order):
            duplicated = sorted({name for name in self.order if self.order.count(name) > 1})
            raise Invalid(f"в 'order' повторяются блоки: {duplicated}", field="order")


def parse_document(data: object, name: str = "document.json") -> DocumentSpec:
    return parse(DocumentSpec, data, name=name)


def parse_block(data: object, name: str = "") -> Any:
    """Validate one top-level block — the content of one `blocks/*.json`."""
    return parse(DOC_BLOCK, data, name=name)
