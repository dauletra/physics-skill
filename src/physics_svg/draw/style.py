"""Stroke and fill presets.

Every illustration in the project is black and white on white paper: it gets
printed, photocopied and read at arm's length. Colour is therefore not a
parameter authors can reach — generators pick from the semantic presets
below, and a new preset is added only when an existing one is genuinely
wrong, not to make one picture prettier.

Widths are in user units; the whole library is calibrated so that one user
unit renders at `SCREEN_SCALE` px (see canvas.py), which keeps line weights
and font sizes consistent across every picture on a page.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

BLACK = "#000"
WHITE = "#fff"
#: Auxiliary rulings and grids: present, but never competing with what the
#: student writes on top of them.
GREY_STRONG = "#888"
GREY = "#bbb"
GREY_LIGHT = "#ccc"
GREY_FAINT = "#e6e6e6"


@dataclass(frozen=True)
class Style:
    """Presentation attributes of one node. `None` means "do not emit"."""

    stroke: str | None = None
    width: float | None = None
    dash: str | None = None
    fill: str | None = None
    opacity: float | None = None
    cap: str | None = None
    join: str | None = None
    #: Keep the stroke at a constant screen width regardless of the
    #: transform. Needed by rulings that stretch to the column width: an
    #: anisotropic scale would otherwise turn one side of a frame into a
    #: thread and the other into a bar.
    non_scaling: bool = False
    font_size: float | None = None
    font_weight: str | None = None
    letter_spacing: float | None = None

    def with_(self, **changes: object) -> "Style":
        return replace(self, **changes)  # type: ignore[arg-type]

    def attrs(self) -> str:
        from physics_svg.draw.text import num

        pairs: list[tuple[str, str]] = []
        if self.fill is not None:
            pairs.append(("fill", self.fill))
        if self.stroke is not None:
            pairs.append(("stroke", self.stroke))
        if self.width is not None:
            pairs.append(("stroke-width", num(self.width)))
        if self.dash is not None:
            pairs.append(("stroke-dasharray", self.dash))
        if self.cap is not None:
            pairs.append(("stroke-linecap", self.cap))
        if self.join is not None:
            pairs.append(("stroke-linejoin", self.join))
        if self.opacity is not None:
            pairs.append(("opacity", num(self.opacity)))
        if self.non_scaling:
            pairs.append(("vector-effect", "non-scaling-stroke"))
        if self.font_size is not None:
            pairs.append(("font-size", num(self.font_size)))
        if self.font_weight is not None:
            pairs.append(("font-weight", self.font_weight))
        if self.letter_spacing is not None:
            pairs.append(("letter-spacing", num(self.letter_spacing)))
        return "".join(f' {name}="{value}"' for name, value in pairs)


#: Hairline: hatching, fine grids — visible texture, not a contour.
HAIR = Style(stroke=BLACK, width=0.4, fill="none")
#: Minor scale ticks, thin construction lines.
THIN = Style(stroke=BLACK, width=0.5, fill="none")
#: Labelled scale ticks, pointers — the default drawing line.
LINE = Style(stroke=BLACK, width=0.9, fill="none")
#: Object contours: instrument bodies, blocks, frames.
OUTLINE = Style(stroke=BLACK, width=1.2, fill="none")
#: Axes, beams, needles — the load-bearing lines of a picture.
HEAVY = Style(stroke=BLACK, width=1.5, fill="none")
#: A solid body: white so that lines behind it are covered, outlined so its
#: edge reads on a photocopy.
BODY = Style(stroke=BLACK, width=1.0, fill=WHITE)
#: Filled marks: needle pivots, data points, arrow heads.
SOLID = Style(fill=BLACK)
#: Chart grid at labelled divisions.
GRID = Style(stroke=GREY_LIGHT, width=0.6, fill="none")
#: Sub-division grid inside one step.
GRID_FINE = Style(stroke=GREY_FAINT, width=0.4, fill="none")
#: Frame of a ruled writing area.
FRAME = Style(stroke=GREY_STRONG, width=0.7, fill="none")

#: Dash patterns available to series styles and construction lines.
DASH = {"solid": None, "dashed": "8,4", "dotted": "1,3"}
