"""Author text -> inline runs. Shared by every genre of the skill.

The project's escaping rule says models hold **raw author text** and escaping
happens at the point of interpolation. With several output surfaces that
point is inside a backend, so the text has to arrive there still raw — and
the three things an author may type into it have to be recognised first:

* `<sup>`/`<sub>`, the only markup allowed in any text field (that is how
  indices and powers are written, see references/symbols.md);
* a run of three or more underscores, which is a place to write;
* a formula between dollars, `$…$` or `$$…$$`.

These conventions are one vocabulary for the whole skill: a teacher writes a
formula the same way in a worksheet and on a slide. That is why this module
sits above the genres — `document/` builds its layout from these runs, and a
presentation emits them as JSON. Genre-specific inline elements (a gap to
fill, an answer slot) are not conventions of author text and live with their
genre, in `document/layout.py`.

Malformed markup is normalised the way a browser already showed it: an
unclosed `<sup>` reaches the end of the string, a stray `</sub>` closes
nothing and disappears. A lone dollar stays a dollar, which is what KaTeX
does too — a formula needs a matching pair on the same line.

The JSON form of a run — the wire contract a non-Python consumer reads
(`runs_json`), with defaults omitted:

    {"t": "При "}                        plain text
    {"t": "x", "script": "sub"}          <sub>…</sub>
    {"math": "v = v_0 + at"}             $…$
    {"math": "\\\\frac{v^2}{2a}", "display": true}   $$…$$
    {"blank": 5}                         _____ (a ruled space, as typed)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal, Union

#: Where a run sits relative to the baseline. Authors type `<sup>`/`<sub>`
#: in any text field; `parse_inline` turns those into runs.
Script = Literal["", "sup", "sub"]


@dataclass(frozen=True)
class Run:
    """A stretch of author text. Raw, unescaped — escaping is a backend's
    job, which is what keeps the same string printable as HTML and as XML."""

    text: str
    script: Script = ""


@dataclass(frozen=True)
class Blank:
    """A ruled space inside a line of text, as wide as the author typed it.

    Carries no answer and never reaches the answers section: it is ruling the
    paper, not asking a question.
    """

    width_ch: int


@dataclass(frozen=True)
class Math:
    """A formula, carried as the LaTeX the author typed.

    Raw, like `Run.text`, and for the same reason: the backends need
    different things from it. HTML prints the delimiters back and lets KaTeX
    typeset in the browser; Word translates a subset of LaTeX into OMML.
    `display` is `$$…$$` — a formula on a line of its own.
    """

    latex: str
    display: bool = False


#: What author text parses into. Genres may put more things on a line —
#: `document/layout.py` widens this union with its own controls — but only
#: these three come out of the text itself.
Piece = Union[Run, Blank, Math]

#: A line's worth of parsed author text.
Text = tuple[Piece, ...]

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
    parts: list[Piece] = []
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


def runs_json(runs: Text) -> list[dict[str, object]]:
    """The JSON form of parsed runs — the module docstring's wire contract.

    Defaults are omitted, so the common case stays short: a plain run is
    `{"t": …}`, an inline formula `{"math": …}`. The text is still raw
    author text; JSON string escaping is the serialiser's job, the same
    division of labour as with the HTML and XML backends.
    """
    result: list[dict[str, object]] = []
    for piece in runs:
        if isinstance(piece, Run):
            item: dict[str, object] = {"t": piece.text}
            if piece.script:
                item["script"] = piece.script
        elif isinstance(piece, Math):
            item = {"math": piece.latex}
            if piece.display:
                item["display"] = True
        else:
            item = {"blank": piece.width_ch}
        result.append(item)
    return result
