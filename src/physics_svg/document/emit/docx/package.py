"""The OPC container: a .docx is a zip of XML parts that reference each other.

Minimal on purpose — Word fills in everything it is not given, and every part
that ships is a part that can go stale. What is here is what a document
cannot open without, plus the two that carry our own decisions (`styles.xml`,
`settings.xml`).

**The package is byte-stable.** Zip entries carry a fixed timestamp, parts are
written in a fixed order, and the document properties hold a fixed date
instead of "now". Two builds of the same draft produce the same file, which
is what makes a golden test of a binary format possible at all — the same
reason `num()` exists in `draw/text.py`.
"""

from __future__ import annotations

import zipfile
from dataclasses import dataclass
from io import BytesIO

from physics_svg.document.emit.docx.wml import el, escape

_DECLARATION = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\r\n'

#: 1980-01-01, the earliest a zip entry can hold. Any real timestamp would
#: make two builds of the same draft differ.
_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
#: The same, for the document properties Word shows in the file dialog.
_CREATED = "1980-01-01T00:00:00Z"

_PACKAGE_RELS = "http://schemas.openxmlformats.org/package/2006/relationships"
_OFFICE_RELS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"

_WORD_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml"


@dataclass(frozen=True)
class Part:
    """One file inside the package."""

    path: str
    content_type: str
    body: str


def core_properties(title: str) -> str:
    """`docProps/core.xml`.

    The title goes into the file's properties, not onto the sheet: what the
    sheet is called is a `heading` block, exactly as in HTML. The renderer
    does not draw anything the author did not ask for.
    """
    return el(
        "cp:coreProperties",
        {
            "xmlns:cp": "http://schemas.openxmlformats.org/package/2006/metadata/core-properties",
            "xmlns:dc": "http://purl.org/dc/elements/1.1/",
            "xmlns:dcterms": "http://purl.org/dc/terms/",
            "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
        },
        el("dc:title", children=escape(title))
        + el("dcterms:created", {"xsi:type": "dcterms:W3CDTF"}, _CREATED)
        + el("dcterms:modified", {"xsi:type": "dcterms:W3CDTF"}, _CREATED),
    )


def _relationships(entries: list[tuple[str, str, str]]) -> str:
    return el(
        "Relationships",
        {"xmlns": _PACKAGE_RELS},
        "".join(
            el("Relationship", {"Id": rid, "Type": kind, "Target": target})
            for rid, kind, target in entries
        ),
    )


def _content_types(parts: list[Part]) -> str:
    defaults = el(
        "Default",
        {
            "Extension": "rels",
            "ContentType": "application/vnd.openxmlformats-package.relationships+xml",
        },
    ) + el("Default", {"Extension": "xml", "ContentType": "application/xml"})
    overrides = "".join(
        el("Override", {"PartName": f"/{part.path}", "ContentType": part.content_type})
        for part in parts
        if part.content_type
    )
    return el(
        "Types",
        {"xmlns": "http://schemas.openxmlformats.org/package/2006/content-types"},
        defaults + overrides,
    )


def build_package(document_xml: str, styles_xml: str, settings_xml: str, title: str) -> bytes:
    """The finished .docx."""
    parts = [
        Part("word/document.xml", f"{_WORD_TYPE}.document.main+xml", document_xml),
        Part("word/styles.xml", f"{_WORD_TYPE}.styles+xml", styles_xml),
        Part("word/settings.xml", f"{_WORD_TYPE}.settings+xml", settings_xml),
        Part(
            "docProps/core.xml",
            "application/vnd.openxmlformats-package.core-properties+xml",
            core_properties(title),
        ),
    ]
    root_rels = _relationships(
        [
            ("rId1", f"{_OFFICE_RELS}/officeDocument", "word/document.xml"),
            (
                "rId2",
                "http://schemas.openxmlformats.org/package/2006/"
                "relationships/metadata/core-properties",
                "docProps/core.xml",
            ),
        ]
    )
    document_rels = _relationships(
        [
            ("rId1", f"{_OFFICE_RELS}/styles", "styles.xml"),
            ("rId2", f"{_OFFICE_RELS}/settings", "settings.xml"),
        ]
    )
    files = [
        Part("[Content_Types].xml", "", _content_types(parts)),
        Part("_rels/.rels", "", root_rels),
        Part("word/_rels/document.xml.rels", "", document_rels),
        *parts,
    ]

    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as package:
        for file in files:
            info = zipfile.ZipInfo(file.path, date_time=_TIMESTAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            # Fixed permissions too: the default is taken from the umask of
            # whoever ran the build.
            info.external_attr = 0o600 << 16
            package.writestr(info, _DECLARATION + file.body)
    return buffer.getvalue()
