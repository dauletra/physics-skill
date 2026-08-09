"""The parts a .pptx is made of, and how they point at each other.

The counterpart of `document/emit/docx/package.py`: what is generic — the
zip, the content types, the relationship files — comes from
`physics_svg.ooxml`; what is here is the list of parts a *presentation*
cannot open without, and the graph between them.

That graph is the part worth reading twice, because PowerPoint checks it and
says nothing useful when it fails:

    _rels/.rels          -> ppt/presentation.xml, docProps/core.xml
    presentation.xml     -> the master, every slide, the theme
    slideMaster1.xml     -> every layout, the theme
    slideLayoutN.xml     -> the master
    slideN.xml           -> the layout it stands on

Both directions are required. A slide that names its layout while the master
does not name that layout is a file PowerPoint offers to repair.
"""

from __future__ import annotations

from typing import Sequence

from physics_svg.ooxml import (
    CORE_PROPERTIES_REL,
    CORE_PROPERTIES_TYPE,
    OFFICE_RELS,
    Part,
    content_types,
    core_properties,
    el,
    relationships,
    zip_package,
)
from physics_svg.presentation.pptx import design
from physics_svg.presentation.pptx.layouts import LAYOUTS, layout_index
from physics_svg.presentation.pptx.master import MASTER_ID, slide_master
from physics_svg.presentation.pptx.slide import NS, Slide, slide
from physics_svg.presentation.pptx.theme import theme

_TYPE = "application/vnd.openxmlformats-officedocument.presentationml"
_THEME_TYPE = "application/vnd.openxmlformats-officedocument.theme+xml"

#: Slide ids in `p:sldIdLst` must be at least 256; PowerPoint's own files
#: start there.
_FIRST_SLIDE_ID = 256


def presentation(slide_rels: Sequence[str], master_rel: str) -> str:
    """`ppt/presentation.xml` — the deck's table of contents and its size.

    Order inside the element is fixed by the schema: masters, slides, then
    the two sizes. `p:notesSz` is the slide's own size swapped, which is what
    makes a notes page portrait.
    """
    masters = el("p:sldMasterId", {"id": MASTER_ID, "r:id": master_rel})
    slides = "".join(
        el("p:sldId", {"id": _FIRST_SLIDE_ID + index, "r:id": rid})
        for index, rid in enumerate(slide_rels)
    )
    return el(
        "p:presentation",
        NS,
        el("p:sldMasterIdLst", children=masters)
        + el("p:sldIdLst", children=slides)
        + el("p:sldSz", {"cx": design.SLIDE_WIDTH, "cy": design.SLIDE_HEIGHT})
        + el("p:notesSz", {"cx": design.NOTES_WIDTH, "cy": design.NOTES_HEIGHT}),
    )


def build_pptx(slides: Sequence[Slide], *, title: str) -> bytes:
    """The finished .pptx.

    An empty list still produces a valid deck of one blank slide: a
    presentation with no slides at all opens, but there is nothing to look
    at, and every phase of docs/pptx.md is accepted by looking.
    """
    deck = list(slides) or [slide()]

    # Relationship ids of ppt/presentation.xml: the master first, then the
    # layouts, then the slides, then the theme. Fixed rather than clever, so
    # that a golden file changes only when the deck does.
    master_rel = "rId1"
    slide_rels = [f"rId{index + 2}" for index in range(len(deck))]
    theme_rel = f"rId{len(deck) + 2}"
    layout_rels = [f"rId{index + 1}" for index in range(len(LAYOUTS))]
    master_theme_rel = f"rId{len(LAYOUTS) + 1}"

    parts = [
        Part(
            "ppt/presentation.xml",
            f"{_TYPE}.presentation.main+xml",
            presentation(slide_rels, master_rel),
        ),
        Part(
            "ppt/slideMasters/slideMaster1.xml",
            f"{_TYPE}.slideMaster+xml",
            slide_master(layout_rels),
        ),
        *[
            Part(
                f"ppt/slideLayouts/slideLayout{index + 1}.xml",
                f"{_TYPE}.slideLayout+xml",
                layout.xml(),
            )
            for index, layout in enumerate(LAYOUTS)
        ],
        *[
            Part(f"ppt/slides/slide{index + 1}.xml", f"{_TYPE}.slide+xml", item.xml())
            for index, item in enumerate(deck)
        ],
        Part("ppt/theme/theme1.xml", _THEME_TYPE, theme()),
        Part("docProps/core.xml", CORE_PROPERTIES_TYPE, core_properties(title)),
    ]

    files = [
        Part("[Content_Types].xml", "", content_types(parts)),
        Part(
            "_rels/.rels",
            "",
            relationships(
                [
                    ("rId1", f"{OFFICE_RELS}/officeDocument", "ppt/presentation.xml"),
                    ("rId2", CORE_PROPERTIES_REL, "docProps/core.xml"),
                ]
            ),
        ),
        Part(
            "ppt/_rels/presentation.xml.rels",
            "",
            relationships(
                [
                    (master_rel, f"{OFFICE_RELS}/slideMaster", "slideMasters/slideMaster1.xml"),
                    *[
                        (rid, f"{OFFICE_RELS}/slide", f"slides/slide{index + 1}.xml")
                        for index, rid in enumerate(slide_rels)
                    ],
                    (theme_rel, f"{OFFICE_RELS}/theme", "theme/theme1.xml"),
                ]
            ),
        ),
        Part(
            "ppt/slideMasters/_rels/slideMaster1.xml.rels",
            "",
            relationships(
                [
                    *[
                        (
                            rid,
                            f"{OFFICE_RELS}/slideLayout",
                            f"../slideLayouts/slideLayout{index + 1}.xml",
                        )
                        for index, rid in enumerate(layout_rels)
                    ],
                    (master_theme_rel, f"{OFFICE_RELS}/theme", "../theme/theme1.xml"),
                ]
            ),
        ),
        *[
            Part(
                f"ppt/slideLayouts/_rels/slideLayout{index + 1}.xml.rels",
                "",
                relationships(
                    [("rId1", f"{OFFICE_RELS}/slideMaster", "../slideMasters/slideMaster1.xml")]
                ),
            )
            for index in range(len(LAYOUTS))
        ],
        *[
            Part(
                f"ppt/slides/_rels/slide{index + 1}.xml.rels",
                "",
                relationships(
                    [
                        (
                            "rId1",
                            f"{OFFICE_RELS}/slideLayout",
                            f"../slideLayouts/slideLayout{layout_index(item.layout)}.xml",
                        )
                    ]
                ),
            )
            for index, item in enumerate(deck)
        ],
        *parts,
    ]
    return zip_package(files)
