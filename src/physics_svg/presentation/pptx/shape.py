"""Places on a slide, and the shapes that fill them.

A place — a *placeholder* — is declared once on the layout and filled on the
slide. That indirection is not decoration: it is what makes the deck behave
like a deck. «Сброс слайда» puts the text back where it belongs, the outline
view shows headings as headings, and a teacher who changes the master
changes the whole lesson instead of forty slides.

So the same `Place` is written twice, in two forms. On the layout it carries
geometry and the text style — where the box is, how big its text is, what
colour. On the slide it carries **only the text**: the style is inherited,
which is exactly what makes the deck editable at its master rather than
slide by slide (docs/pptx.md §5.3).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

from physics_svg.ooxml import el
from physics_svg.presentation.pptx import design
from physics_svg.presentation.pptx.text import text_body


@dataclass(frozen=True)
class Place:
    """One placeholder: where it sits and how its text is set.

    The box is in points, from the top left of the slide — the units the
    design system is written in (`design.py`), converted to EMU on the way
    out so that nothing above this module counts in EMU.
    """

    #: What PowerPoint calls the shape in the selection pane, in Russian:
    #: the teacher reads it.
    name: str
    #: `title`, `ctrTitle`, `subTitle` or `body`. The first three tell
    #: PowerPoint this text is the slide's heading — that is what the
    #: outline view and «Структура» read.
    kind: str
    box: tuple[float, float, float, float]
    size: float
    colour: str = design.INK
    idx: Optional[int] = None
    bold: bool = False
    #: `l`, `ctr` or `r`.
    align: str = "l"
    #: `t`, `ctr` or `b` — where the text sits inside its box.
    anchor: str = "t"
    leading: Optional[float] = None
    bullet: bool = False

    def _reference(self) -> str:
        attrs: dict[str, object] = {"type": self.kind}
        if self.idx is not None:
            attrs["idx"] = self.idx
        return el("p:ph", attrs)

    def _frame(self, number: int) -> str:
        return el(
            "p:nvSpPr",
            children=el("p:cNvPr", {"id": number, "name": self.name})
            + el("p:cNvSpPr", children=el("a:spLocks", {"noGrp": 1}))
            + el("p:nvPr", children=self._reference()),
        )

    def _geometry(self) -> str:
        x, y, width, height = (design.emu(value) for value in self.box)
        return el(
            "p:spPr",
            children=el(
                "a:xfrm",
                children=el("a:off", {"x": x, "y": y}) + el("a:ext", {"cx": width, "cy": height}),
            ),
        )

    def _defaults(self) -> str:
        """`a:lstStyle` — the style every paragraph in this place starts from."""
        properties: dict[str, object] = {"sz": design.sz(self.size)}
        if self.bold:
            properties["b"] = 1
        body = el("a:solidFill", children=el("a:srgbClr", {"val": self.colour}))
        body += el("a:latin", {"typeface": design.FONT})
        level = el("a:lnSpc", children=el("a:spcPct", {"val": round(self.leading * 100000)})) if (
            self.leading is not None
        ) else ""
        level += el("a:buChar", {"char": "—"}) if self.bullet else el("a:buNone")
        return el(
            "a:lstStyle",
            children=el(
                "a:lvl1pPr",
                {"marL": 0, "indent": 0, "algn": self.align},
                level + el("a:defRPr", properties, body),
            ),
        )

    def on_layout(self, number: int, prompt: str = "") -> str:
        """The place as the layout declares it: geometry, style, and the
        text PowerPoint shows in «Образец слайдов» so a person can see what
        the place is for."""
        from physics_svg.presentation.pptx.text import Style, paragraph

        content = paragraph(prompt, Style()) if prompt else el("a:p")
        return el(
            "p:sp",
            children=self._frame(number)
            + self._geometry()
            + el(
                "p:txBody",
                children=el(
                    "a:bodyPr",
                    {"wrap": "square", "anchor": self.anchor},
                    el("a:normAutofit"),
                )
                + self._defaults()
                + content,
            ),
        )

    def on_slide(self, number: int, paragraphs: Sequence[str]) -> str:
        """The place as a slide fills it: text and nothing else.

        No `a:xfrm` and no `a:lstStyle` — both are inherited. A slide that
        repeated them would look right and stop following its layout, which
        is the whole reason for having one.
        """
        return el(
            "p:sp",
            children=self._frame(number)
            + el("p:spPr")
            + text_body(paragraphs, anchor=self.anchor),
        )


def plain_shape(
    number: int,
    name: str,
    box: tuple[float, float, float, float],
    body: str = "",
    *,
    anchor: str = "t",
    fill: str = "",
) -> str:
    """A shape that is not a placeholder: geometry, fill, and whatever text
    it was given.

    Everything a slide shows should be a place a layout declared — that is
    what makes «Сброс слайда» work and what lets a teacher restyle a lesson
    at its master. This is for the exceptions, and there are only two: the
    hairline under the heading and the word that names the genre. Both belong
    to the layout, neither is text anybody edits.
    """
    x, y, width, height = (design.emu(value) for value in box)
    return el(
        "p:sp",
        children=el(
            "p:nvSpPr",
            children=el("p:cNvPr", {"id": number, "name": name})
            + el("p:cNvSpPr")
            + el("p:nvPr"),
        )
        + el(
            "p:spPr",
            children=el(
                "a:xfrm",
                children=el("a:off", {"x": x, "y": y}) + el("a:ext", {"cx": width, "cy": height}),
            )
            + el("a:prstGeom", {"prst": "rect"}, el("a:avLst"))
            + (fill or el("a:noFill"))
            + el("a:ln", children=el("a:noFill")),
        )
        + el(
            "p:txBody",
            children=el("a:bodyPr", {"wrap": "square", "anchor": anchor}, el("a:normAutofit"))
            + el("a:lstStyle")
            + (body or el("a:p")),
        ),
    )


def rule(y: float, *, colour: str = design.LINE, number: int = 90) -> str:
    """The hairline under a heading — the one horizon of docs/slide-design.md
    §6.1, drawn on the layout so that every slide of the lesson has it in the
    same place."""
    x, width = design.PAD_X, design.SLIDE_WIDTH / design.emu(1) - 2 * design.PAD_X
    return el(
        "p:sp",
        children=el(
            "p:nvSpPr",
            children=el("p:cNvPr", {"id": number, "name": "Линейка"})
            + el("p:cNvSpPr")
            + el("p:nvPr"),
        )
        + el(
            "p:spPr",
            children=el(
                "a:xfrm",
                children=el("a:off", {"x": design.emu(x), "y": design.emu(y)})
                + el("a:ext", {"cx": design.emu(width), "cy": design.emu(1)}),
            )
            + el("a:prstGeom", {"prst": "rect"}, el("a:avLst"))
            + el("a:solidFill", children=el("a:srgbClr", {"val": colour}))
            + el("a:ln", children=el("a:noFill")),
        )
        + el(
            "p:txBody",
            children=el("a:bodyPr") + el("a:lstStyle") + el("a:p"),
        ),
    )
