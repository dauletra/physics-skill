"""The design system of the deck, in the units PowerPoint counts in.

Nothing here is new: this is the system worked out for the player in
docs/slide-design.md, converted once. The player measured everything in
`cqh` — percent of the frame's height — because a web page has no absolute
size. A slide does: 16:9 is exactly 960 × 540 pt, so **1 cqh = 5,4 pt**, and
the whole scale converts by that one number (docs/pptx.md §5.3).

Why the conversion is worth keeping rather than re-choosing: the sizes were
not picked by eye. They come from the angular size of a character seen from
the back row of a classroom — comfortable reading is 20–22 angular minutes,
which at 7–8 metres is where `--t-m` = 24 pt lands. The platform changed;
the classroom did not.

What is deliberately **not** here: `--hud-zone`. It reserved a strip at the
bottom of the frame for the player's own buttons, and PowerPoint keeps its
controls outside the slide. Those nine percent of height come back to the
content — and pay for the margin the theme font costs us (docs/pptx.md §6.4).
"""

from __future__ import annotations

from physics_svg.draw.shapes import EMU_PER_PT

#: A 16:9 slide, in EMU. 13⅓ × 7½ inches — what PowerPoint calls widescreen
#: and what every classroom panel is.
SLIDE_WIDTH = 12192000
SLIDE_HEIGHT = 6858000

#: Notes pages are portrait, and their size is the slide's, swapped.
NOTES_WIDTH = 6858000
NOTES_HEIGHT = 9144000

#: Points per cqh: 540 pt of height, a hundred cqh in it.
PT_PER_CQH = 5.4


def cqh(value: float) -> float:
    """A player token in points."""
    return value * PT_PER_CQH


def sz(points: float) -> int:
    """A font size as OOXML writes it — hundredths of a point."""
    return round(points * 100)


def emu(points: float) -> int:
    return round(points * EMU_PER_PT)


#: The seven steps of docs/slide-design.md §5.3, in points. A step below
#: `TEXT` is for what the teacher reads from a metre away, never the class.
HERO = cqh(11.0)  # 59 pt — the lesson's title
DISPLAY = cqh(8.8)  # 48 pt — a stage divider, a formula standing alone
HEADING = cqh(7.0)  # 38 pt — the heading of a slide
LEAD = cqh(5.6)  # 30 pt — the statement of a problem
TEXT = cqh(4.5)  # 24 pt — body text, lists, cells, answers
SMALL = cqh(3.6)  # 19 pt — a legend, a caption under a cell
TINY = cqh(2.9)  # 16 pt — the kicker naming the genre

#: Leading for body text, as a multiple of the size.
LEADING = 1.45

#: Margins of the frame, in points.
PAD_Y = cqh(6.0)
PAD_X = cqh(7.0)

#: The floor an illustration is never squeezed below.
VISUAL_MIN = cqh(38.0)

#: Colours, straight from docs/slide-design.md §5.1–5.2. The palette is one
#: accent and a ladder of greys; the theme has six accent slots to fill and
#: no way to leave them empty, so the rest of the palette lives in them.
INK = "15181D"  # 16,9:1 on paper — body text
INK_SOFT = "4A5261"  # 7,5:1 — second plane
INK_FAINT = "69727E"  # 4,6:1 — the auxiliary
PAPER = "F7F9FB"  # not pure white: it glares less on a lit panel
PAPER_SUNK = "EDF1F6"  # a cell, a plate
LINE = "D3DAE3"  # rules and cell borders
PANEL = "1C2733"  # the stage divider's fill
ACCENT = "1B5FA8"  # 6,1:1 — the only chromatic token
ACCENT_SOFT = "E4EDF7"
ACCENT_LINE = "B9CEE6"

#: The theme font. A stack is not available — OOXML takes one name — so this
#: is a decision rather than a preference, and its cost is written down in
#: docs/pptx.md §6.4: off Windows it is substituted, metrics shift, and
#: nothing here can measure that.
FONT = "Segoe UI"
