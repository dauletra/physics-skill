"""The Word backend: layout -> .docx.

Same input as the HTML backend and the same document decisions; only the
format differs. What Word adds is what the on-screen page deliberately does
not do — a real page, real margins, and a document a teacher can edit before
printing.
"""

from __future__ import annotations

from physics_svg.document.emit.docx.emit import Unsupported, body_xml
from physics_svg.document.emit.docx.package import build_package
from physics_svg.document.emit.docx.styles import W_NAMESPACE, settings_xml, styles_xml
from physics_svg.document.emit.docx.wml import el
from physics_svg.document.layout import Block

#: Everything the body may mention. Word refuses a document whose namespaces
#: are not declared on the root; illustrations bring four of them and
#: formulas the fifth.
_NAMESPACES: dict[str, object] = {
    "xmlns:w": W_NAMESPACE,
    "xmlns:r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "xmlns:m": "http://schemas.openxmlformats.org/officeDocument/2006/math",
    "xmlns:wp": (
        "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
    ),
    "xmlns:a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "xmlns:wpg": "http://schemas.microsoft.com/office/word/2010/wordprocessingGroup",
    "xmlns:wps": "http://schemas.microsoft.com/office/word/2010/wordprocessingShape",
}


def document(title: str, blocks: tuple[Block, ...]) -> tuple[bytes, tuple[str, ...]]:
    """The whole document as one .docx file, and what the build has to say
    about it — see `render.build_docx`."""
    content, notes = body_xml(blocks)
    body = el("w:document", _NAMESPACES, el("w:body", children=content))
    return build_package(body, styles_xml(), settings_xml(), title), notes


__all__ = ["Unsupported", "document"]
