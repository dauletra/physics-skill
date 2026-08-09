"""WordprocessingML fragments — the only place in the Word backend that
writes angle brackets.

The same role `draw/nodes.py` plays for SVG. If a `f'<w:p'` appears anywhere
else, a constructor is missing here.

Three things this module owns, because getting any of them wrong makes Word
refuse to open the file — silently, with no hint of what is wrong:

* **Order.** `w:pPr` and `w:rPr` are XML *sequences*, not sets: underline
  comes after size, `vertAlign` last, tabs before spacing. Properties are
  therefore assembled from a fixed list of known names, never from the order
  a caller happened to pass them in — and an unknown name is a bug, raised
  immediately.
* **Escaping.** `&`, `<`, `>`, and — through `draw.clean` — the control
  characters XML 1.0 does not allow at all. This is the Word counterpart of
  `esc()` in the HTML backend: the layout carries raw author text and it is
  escaped here.
* **`xml:space="preserve"`** on every `w:t`. Without it Word eats the space
  before a ruled blank and the line slides into the word.
"""

from __future__ import annotations

from typing import Iterable, Optional

from physics_svg.ooxml import el, escape

#: The subsets of CT_PPr / CT_RPr / … the backend uses, in schema order.
P_ORDER = (
    "w:pStyle",
    "w:keepNext",
    "w:pBdr",
    "w:shd",
    "w:tabs",
    "w:spacing",
    "w:ind",
    "w:jc",
)
R_ORDER = (
    "w:rStyle",
    "w:rFonts",
    "w:b",
    "w:i",
    "w:color",
    "w:sz",
    "w:szCs",
    "w:u",
    "w:vertAlign",
    "w:lang",
)
_TBL_ORDER = (
    "w:tblW",
    "w:jc",
    "w:tblInd",
    "w:tblBorders",
    "w:tblLayout",
    "w:tblCellMar",
    "w:tblLook",
)
_TR_ORDER = ("w:cantSplit", "w:trHeight", "w:tblHeader")
_TC_ORDER = ("w:tcW", "w:tcBorders", "w:shd", "w:tcMar", "w:vAlign")


def props(tag: str, order: tuple[str, ...], parts: dict[str, str]) -> str:
    """A property container with its children put in schema order.

    An unknown property name is a programming error: it would silently land
    in the wrong place in the sequence, and Word would reject the document
    without saying which element it disliked.
    """
    unknown = [name for name in parts if name not in order]
    if unknown:
        raise ValueError(f"{tag}: unknown properties {unknown}; add them to the schema order")
    body = "".join(parts[name] for name in order if name in parts)
    return el(tag, children=body) if body else ""


# --- runs ---------------------------------------------------------------


def run(
    text: str = "",
    *,
    bold: bool = False,
    italic: bool = False,
    underline: bool = False,
    script: str = "",
    font: Optional[str] = None,
    size: Optional[int] = None,
    color: Optional[str] = None,
    content: str = "",
) -> str:
    """One run. `content` replaces the text for runs that carry an element
    instead — a tab, later a drawing."""
    parts: dict[str, str] = {}
    if font is not None:
        parts["w:rFonts"] = el("w:rFonts", {"w:ascii": font, "w:hAnsi": font, "w:cs": font})
    if bold:
        parts["w:b"] = el("w:b")
    if italic:
        parts["w:i"] = el("w:i")
    if color is not None:
        parts["w:color"] = el("w:color", {"w:val": color})
    if size is not None:
        parts["w:sz"] = el("w:sz", {"w:val": size})
        parts["w:szCs"] = el("w:szCs", {"w:val": size})
    if underline:
        parts["w:u"] = el("w:u", {"w:val": "single"})
    if script:
        parts["w:vertAlign"] = el("w:vertAlign", {"w:val": "superscript" if script == "sup" else "subscript"})
    body = props("w:rPr", R_ORDER, parts)
    body += content if content else el("w:t", {"xml:space": "preserve"}, escape(text))
    return el("w:r", children=body)


def tab_run() -> str:
    return el("w:r", children=el("w:tab"))


# --- paragraphs ---------------------------------------------------------


def para(
    runs: str = "",
    *,
    style: Optional[str] = None,
    indent: int = 0,
    hanging: int = 0,
    before: int = 0,
    after: int = 0,
    right_tab: Optional[int] = None,
    border_top: bool = False,
    border_bottom: bool = False,
) -> str:
    parts: dict[str, str] = {}
    if style is not None:
        parts["w:pStyle"] = el("w:pStyle", {"w:val": style})
    borders = ""
    if border_top:
        borders += el("w:top", _BORDER)
    if border_bottom:
        borders += el("w:bottom", _BORDER)
    if borders:
        parts["w:pBdr"] = el("w:pBdr", children=borders)
    if right_tab is not None:
        parts["w:tabs"] = el(
            "w:tabs", children=el("w:tab", {"w:val": "right", "w:pos": right_tab})
        )
    if before or after:
        spacing: dict[str, object] = {}
        if before:
            spacing["w:before"] = before
        if after:
            spacing["w:after"] = after
        parts["w:spacing"] = el("w:spacing", spacing)
    if indent or hanging:
        attrs: dict[str, object] = {"w:left": indent}
        if hanging:
            attrs["w:hanging"] = hanging
        parts["w:ind"] = el("w:ind", attrs)
    return el("w:p", children=props("w:pPr", P_ORDER, parts) + runs)


#: The rule under a divider and above the answers section: one weight for
#: both, because on the sheet they are the same line.
_BORDER = {"w:val": "single", "w:sz": 12, "w:space": 1, "w:color": "000000"}


# --- tables -------------------------------------------------------------


def table(
    rows: str,
    *,
    widths: Iterable[int],
    borders: bool,
    indent: int = 0,
    cell_margin: int = 0,
) -> str:
    """A table. Always fixed layout: an autofit table re-measures itself from
    the content and two rows of the same sheet stop lining up."""
    parts: dict[str, str] = {
        "w:tblW": el("w:tblW", {"w:w": sum(widths), "w:type": "dxa"}),
        "w:tblLayout": el("w:tblLayout", {"w:type": "fixed"}),
        "w:tblLook": el("w:tblLook", {"w:val": "0000"}),
    }
    if indent:
        parts["w:tblInd"] = el("w:tblInd", {"w:w": indent, "w:type": "dxa"})
    if borders:
        edges = "".join(
            el(f"w:{edge}", _BORDER_THIN)
            for edge in ("top", "left", "bottom", "right", "insideH", "insideV")
        )
        parts["w:tblBorders"] = el("w:tblBorders", children=edges)
    if cell_margin:
        margins = "".join(
            el(f"w:{side}", {"w:w": cell_margin, "w:type": "dxa"}) for side in ("left", "right")
        )
        parts["w:tblCellMar"] = el("w:tblCellMar", children=margins)
    grid = el(
        "w:tblGrid",
        children="".join(el("w:gridCol", {"w:w": width}) for width in widths),
    )
    return el("w:tbl", children=props("w:tblPr", _TBL_ORDER, parts) + grid + rows)


_BORDER_THIN = {"w:val": "single", "w:sz": 6, "w:space": 0, "w:color": "000000"}


def row(cells: str, *, header: bool = False) -> str:
    parts: dict[str, str] = {}
    if header:
        # A table that runs over a page break keeps its column names — the
        # one thing print gives that the on-screen sheet cannot.
        parts["w:tblHeader"] = el("w:tblHeader")
    return el("w:tr", children=props("w:trPr", _TR_ORDER, parts) + cells)


def cell(content: str, *, width: int, shade: Optional[str] = None) -> str:
    """One cell. A cell whose last child is not a paragraph is invalid — Word
    refuses the document — so the closing paragraph is added here rather than
    remembered by every caller."""
    parts: dict[str, str] = {"w:tcW": el("w:tcW", {"w:w": width, "w:type": "dxa"})}
    if shade is not None:
        parts["w:shd"] = el("w:shd", {"w:val": "clear", "w:color": "auto", "w:fill": shade})
    if not content.endswith("</w:p>"):
        content += el("w:p")
    return el("w:tc", children=props("w:tcPr", _TC_ORDER, parts) + content)
