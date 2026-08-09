"""The parts a .docx is made of.

Minimal on purpose — Word fills in everything it is not given, and every part
that ships is a part that can go stale. What is here is what a document
cannot open without, plus the two that carry our own decisions (`styles.xml`,
`settings.xml`).

How a part is declared, related and zipped is not Word's business and is not
here: that is `physics_svg.ooxml`, shared with the presentation backend.
"""

from __future__ import annotations

from physics_svg.ooxml import (
    CORE_PROPERTIES_REL,
    CORE_PROPERTIES_TYPE,
    OFFICE_RELS,
    Part,
    content_types,
    core_properties,
    relationships,
    zip_package,
)

_WORD_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml"


def build_package(document_xml: str, styles_xml: str, settings_xml: str, title: str) -> bytes:
    """The finished .docx."""
    parts = [
        Part("word/document.xml", f"{_WORD_TYPE}.document.main+xml", document_xml),
        Part("word/styles.xml", f"{_WORD_TYPE}.styles+xml", styles_xml),
        Part("word/settings.xml", f"{_WORD_TYPE}.settings+xml", settings_xml),
        Part("docProps/core.xml", CORE_PROPERTIES_TYPE, core_properties(title)),
    ]
    root_rels = relationships(
        [
            ("rId1", f"{OFFICE_RELS}/officeDocument", "word/document.xml"),
            ("rId2", CORE_PROPERTIES_REL, "docProps/core.xml"),
        ]
    )
    document_rels = relationships(
        [
            ("rId1", f"{OFFICE_RELS}/styles", "styles.xml"),
            ("rId2", f"{OFFICE_RELS}/settings", "settings.xml"),
        ]
    )
    files = [
        Part("[Content_Types].xml", "", content_types(parts)),
        Part("_rels/.rels", "", root_rels),
        Part("word/_rels/document.xml.rels", "", document_rels),
        *parts,
    ]
    return zip_package(files)
