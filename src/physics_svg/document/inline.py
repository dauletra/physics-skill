"""Author text -> inline runs.

The project's escaping rule says models hold **raw author text** and escaping
happens at the point of interpolation. With two output formats that point is
inside a backend, so the text has to arrive there still raw — and the two
things an author may type into it have to be recognised first:

* `<sup>`/`<sub>`, the only markup allowed in any text field (that is how
  indices and powers are written, see references/symbols.md);
* a run of three or more underscores, which is a place to write.

Both were previously recognised while building HTML — one inside `esc()`, the
other by a substitution over already-escaped markup. Here they are recognised
once, and a backend receives structure instead of tags.

Malformed markup is normalised the way a browser already showed it: an
unclosed `<sup>` reaches the end of the string, a stray `</sub>` closes
nothing and disappears.
"""

from __future__ import annotations

import re

from physics_svg.document.layout import Blank, Inline, Run, Script, Text

#: A run of underscores is a ruled space, as wide as it was typed. Three is
#: the shortest run that cannot be a typo or an em dash typed by hand.
_BLANK = r"_{3,}"
_TAGS = r"</?(?:sup|sub)>"

_WITH_BLANKS = re.compile(f"{_TAGS}|{_BLANK}")
_TAGS_ONLY = re.compile(_TAGS)


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
        if token.startswith("_"):
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
