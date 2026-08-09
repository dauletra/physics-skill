"""The slide master and the layouts that hang off it.

Every slide in PowerPoint stands on a layout, and every layout on a master.
This is not ceremony: it is where the deck's defaults live, and it is what
makes the file editable in the ordinary way — change the master and the
lesson follows.

For now there is one layout, blank. The layouts that carry the places a
slide fills — heading, body, illustration — arrive with the slide kinds in
P4 (docs/pptx.md §5.3); the master is written so that adding one is adding
an entry to two lists.

Two things PowerPoint refuses to open the file without, and neither is
obvious: the **colour map** (`p:clrMap`, which says that `bg1` means the
theme's `lt1`) and **`p:txStyles`** on the master. They are small and they
are mandatory.
"""

from __future__ import annotations

from typing import Sequence

from physics_svg.ooxml import el
from physics_svg.presentation.pptx import design
from physics_svg.presentation.pptx.slide import NS, shape_tree

#: Ids PowerPoint expects to be large and unique; the numbering is the one
#: its own files use.
_MASTER_ID = 2147483648
_LAYOUT_ID = 2147483649


def _background() -> str:
    return el(
        "p:bg",
        children=el(
            "p:bgPr",
            children=el("a:solidFill", children=el("a:schemeClr", {"val": "bg1"}))
            + el("a:effectLst"),
        ),
    )


def _text_styles() -> str:
    """Defaults for text that names no size of its own.

    The three lists are what the schema demands; the sizes are the steps of
    `design`, so that a shape added by hand on top of our deck starts from
    the system rather than from PowerPoint's 18 pt.
    """

    def level(points: float) -> str:
        return el(
            "a:lvl1pPr",
            children=el(
                "a:defRPr",
                {"sz": design.sz(points)},
                el("a:solidFill", children=el("a:schemeClr", {"val": "tx1"})),
            ),
        )

    return el(
        "p:txStyles",
        children=el("p:titleStyle", children=level(design.HEADING))
        + el("p:bodyStyle", children=level(design.TEXT))
        + el("p:otherStyle", children=level(design.SMALL)),
    )


def slide_master(layout_rels: Sequence[str]) -> str:
    """`ppt/slideMasters/slideMaster1.xml`."""
    layouts = "".join(
        el("p:sldLayoutId", {"id": _LAYOUT_ID + index, "r:id": rid})
        for index, rid in enumerate(layout_rels)
    )
    return el(
        "p:sldMaster",
        NS,
        el("p:cSld", children=_background() + shape_tree())
        + _colour_map()
        + el("p:sldLayoutIdLst", children=layouts)
        + _text_styles(),
    )


def _colour_map() -> str:
    """Which theme colour each named slot resolves to. Identity everywhere
    except the two pairs OOXML deliberately crosses."""
    return el(
        "p:clrMap",
        {
            "bg1": "lt1",
            "tx1": "dk1",
            "bg2": "lt2",
            "tx2": "dk2",
            "accent1": "accent1",
            "accent2": "accent2",
            "accent3": "accent3",
            "accent4": "accent4",
            "accent5": "accent5",
            "accent6": "accent6",
            "hlink": "hlink",
            "folHlink": "folHlink",
        },
    )


#: The master id used in `ppt/presentation.xml`.
MASTER_ID = _MASTER_ID
