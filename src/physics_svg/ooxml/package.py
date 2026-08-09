"""The OPC container: an Office file is a zip of XML parts that reference
each other.

A .docx and a .pptx differ in *which* parts they hold and what those parts
say; they do not differ in how a part is declared, related or zipped. That
common half lives here, and each backend brings its own list of parts.

**The package is byte-stable.** Zip entries carry a fixed timestamp, parts
are written in the order the backend lists them, and the properties hold a
fixed date instead of "now". Two builds of the same draft produce the same
file, which is what makes a golden test of a binary format possible at all —
the same reason `num()` exists in `draw/text.py`.
"""

from __future__ import annotations

import zipfile
from dataclasses import dataclass
from io import BytesIO
from typing import Sequence

from physics_svg.ooxml.element import el, escape

_DECLARATION = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\r\n'

#: 1980-01-01, the earliest a zip entry can hold. Any real timestamp would
#: make two builds of the same draft differ.
_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
#: The same, for the properties Office shows in the file dialog.
_CREATED = "1980-01-01T00:00:00Z"

#: Relationship namespaces. The first names relationships as a package
#: concept, the second the kinds Office parts relate to each other by.
PACKAGE_RELS = "http://schemas.openxmlformats.org/package/2006/relationships"
OFFICE_RELS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"

CORE_PROPERTIES_TYPE = "application/vnd.openxmlformats-package.core-properties+xml"
CORE_PROPERTIES_REL = (
    "http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties"
)


@dataclass(frozen=True)
class Part:
    """One file inside the package. An empty `content_type` means the part is
    declared by a default rule rather than an override — that is the case for
    `[Content_Types].xml` itself and for every `.rels`."""

    path: str
    content_type: str
    body: str


def relationships(entries: Sequence[tuple[str, str, str]]) -> str:
    """A `.rels` part from (id, kind, target) triples."""
    return el(
        "Relationships",
        {"xmlns": PACKAGE_RELS},
        "".join(
            el("Relationship", {"Id": rid, "Type": kind, "Target": target})
            for rid, kind, target in entries
        ),
    )


def content_types(parts: Sequence[Part]) -> str:
    """`[Content_Types].xml` — every part typed, or Office will not open it."""
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


def core_properties(title: str) -> str:
    """`docProps/core.xml`.

    The title goes into the file's properties, not onto the page: what the
    material is called is a block of its own, in both genres. The backend
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


def zip_package(files: Sequence[Part]) -> bytes:
    """The finished Office file: every part, declared and zipped."""
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
