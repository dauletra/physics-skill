"""Number formatting and text escaping — the two things every generator needs
and nobody should reimplement.

Escaping rule for the whole project: models store **raw author text**, and
escaping happens at the point of interpolation. `esc()` is the HTML gate and
`svg_text()` the SVG one; both let literal `<sup>`/`<sub>` through, because
that is how the author writes indices and powers (see references/symbols.md)
without opening arbitrary markup.
"""

from __future__ import annotations

import html
import re

#: Font stack shared by the document CSS and every standalone SVG, so a
#: picture looks the same inside a worksheet and on a slide.
FONT_STACK = "PT Sans, Segoe UI, Verdana, Arial, sans-serif"

#: Tags an author may type literally in any text field.
INLINE_TAGS = ("sup", "sub")

#: Superscript/subscript are drawn at this fraction of the parent font size.
_SUPSUB_RATIO = 0.72

#: Mean advance width of PT Sans as a fraction of the font size. SVG has no
#: way to measure text without a client, so every layout that must reserve
#: room for a label estimates it with this.
_MEAN_ADVANCE = 0.55

_SUPSUB_RE = re.compile(r"</?(?:sup|sub)>")


def num(value: float) -> str:
    """Canonical number formatting for coordinates and scale labels.

    Integers lose the `.0`, fractions lose trailing zeros and float noise
    (`0.30000000000000004`), and negative zero never reaches the output.
    """
    if abs(value - round(value)) < 1e-9:
        rounded = int(round(value))
        return str(rounded if rounded != 0 else 0)
    text = f"{value:.2f}".rstrip("0").rstrip(".")
    return "0" if text in ("-0", "") else text


def fixed(value: float, decimals: int) -> str:
    """Fixed-point formatting for digital displays, where trailing zeros are
    the point (`12.40` on a 0.01-discrete instrument, not `12.4`)."""
    return f"{value:.{decimals}f}"


def esc(text: object) -> str:
    """Escape author text for HTML, keeping literal `<sup>`/`<sub>`."""
    escaped = html.escape(str(text if text is not None else ""))
    for tag in INLINE_TAGS:
        escaped = escaped.replace(f"&lt;{tag}&gt;", f"<{tag}>")
        escaped = escaped.replace(f"&lt;/{tag}&gt;", f"</{tag}>")
    return escaped


def svg_text(raw: object, size: float) -> str:
    """Escape author text for an SVG `<text>` element.

    HTML tags are invalid inside `<text>` and silently break rendering, so
    `<sup>`/`<sub>` become `<tspan>` with a shifted baseline. The nested size
    is derived from the parent `size`, which is why callers pass it: a
    superscript on a 15pt display and on a 7pt tick label must not be the
    same absolute size.
    """
    escaped = esc(raw)
    small = num(size * _SUPSUB_RATIO)
    escaped = escaped.replace("<sup>", f'<tspan baseline-shift="super" font-size="{small}">')
    escaped = escaped.replace("<sub>", f'<tspan baseline-shift="sub" font-size="{small}">')
    return escaped.replace("</sup>", "</tspan>").replace("</sub>", "</tspan>")


def text_width(raw: str, size: float) -> float:
    """Estimated rendered width of a label, in user units.

    An estimate is all that is available without a font engine; layouts that
    depend on it should leave slack rather than butt labels together.
    """
    plain = _SUPSUB_RE.sub("", str(raw))
    return len(plain) * _MEAN_ADVANCE * size


def split_scripts(raw: object) -> list[tuple[str, str]]:
    """Author text as (chunk, script) pairs, where script is "", "sup" or "sub".

    `svg_text()` turns the same markup into shifted `tspan`s; a backend of
    native shapes needs the structure instead. Both read the one syntax an
    author may type, which is why the splitting lives here rather than in
    either backend.
    """
    parts: list[tuple[str, str]] = []
    script = ""
    position = 0
    text = str(raw if raw is not None else "")
    for found in _SUPSUB_RE.finditer(text):
        chunk = text[position : found.start()]
        if chunk:
            parts.append((chunk, script))
        tag = found.group()
        script = "" if tag.startswith("</") else tag[1:-1]
        position = found.end()
    tail = text[position:]
    if tail:
        parts.append((tail, script))
    return parts
