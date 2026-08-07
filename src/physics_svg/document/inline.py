"""Author text -> inline runs.

The project's escaping rule says models hold **raw author text** and escaping
happens at the point of interpolation. With two output formats that point is
inside a backend, so the text has to arrive there still raw — and the three
things an author may type into it have to be recognised first:

* `<sup>`/`<sub>`, the only markup allowed in any text field (that is how
  indices and powers are written, see references/symbols.md);
* a run of three or more underscores, which is a place to write;
* a formula between dollars, `$…$` or `$$…$$`.

The first two were previously recognised while building HTML — one inside
`esc()`, the other by a substitution over already-escaped markup. The third
was not recognised at all: the dollars travelled as text, KaTeX found them in
the finished page, and Word printed them as typed. Here all three are
recognised once, and a backend receives structure instead of characters.

Malformed markup is normalised the way a browser already showed it: an
unclosed `<sup>` reaches the end of the string, a stray `</sub>` closes
nothing and disappears. A lone dollar stays a dollar, which is what KaTeX
does too — a formula needs a matching pair on the same line.
"""

from __future__ import annotations

import re

from physics_svg.document.layout import Blank, Inline, Math, Run, Script, Text

#: A run of underscores is a ruled space, as wide as it was typed. Three is
#: the shortest run that cannot be a typo or an em dash typed by hand.
_BLANK = r"_{3,}"
_TAGS = r"</?(?:sup|sub)>"

#: `$$…$$` before `$…$`, so that a display formula is not read as an inline
#: one wrapping an empty string. Neither crosses a line break: an unclosed
#: dollar has to stop somewhere, and a line is where a reader stops too.
_MATH = r"\$\$(?P<display>[^\n]+?)\$\$|\$(?P<inline>[^$\n]+?)\$"

_WITH_BLANKS = re.compile(f"{_MATH}|{_TAGS}|{_BLANK}")
_TAGS_ONLY = re.compile(f"{_MATH}|{_TAGS}")


def parse_inline(raw: object, *, blanks: bool = False) -> Text:
    """Split author text into runs.

    `blanks` says whether underscores are ruling. They are in a `text`
    component, and they are not in a `fill_text` template: there a gap is
    written `___имя___`, and bare underscores the author typed are literal.
    """
    text = str(raw if raw is not None else "")
    pattern = _WITH_BLANKS if blanks else _TAGS_ONLY
    parts: list[Inline] = []
    open_scripts: list[Script] = []
    position = 0
    for found in pattern.finditer(text):
        chunk = text[position : found.start()]
        if chunk:
            parts.append(Run(chunk, _innermost(open_scripts)))
        token = found.group()
        if found.group("display") is not None:
            parts.append(Math(found.group("display"), display=True))
        elif found.group("inline") is not None:
            parts.append(Math(found.group("inline")))
        elif token.startswith("_"):
            parts.append(Blank(len(token)))
        elif token.startswith("</"):
            if open_scripts:
                open_scripts.pop()
        else:
            open_scripts.append(token[1:-1])  # type: ignore[arg-type]
        position = found.end()
    tail = text[position:]
    if tail:
        parts.append(Run(tail, _innermost(open_scripts)))
    return tuple(parts)


def _innermost(open_scripts: list[Script]) -> Script:
    return open_scripts[-1] if open_scripts else ""


def math_spans(text: str) -> list[tuple[int, int]]:
    """Where the formulas are — the pairs of dollars `parse_inline` reads.

    Published so that a question can refuse to put something inside one
    without inventing a second idea of where a formula begins.
    """
    return [
        found.span()
        for found in re.finditer(_MATH, text)
        if found.group("display") is not None or found.group("inline") is not None
    ]
