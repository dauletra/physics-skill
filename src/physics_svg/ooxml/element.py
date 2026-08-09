"""XML elements and the escaping every Office format needs.

Word and PowerPoint are both zips of XML, and both are unforgiving in the
same way: a stray `&` or a control character makes the file unopenable with
no hint of what went wrong. That rule is one rule, so it lives in one place
rather than once per backend.

What is **not** here: anything that knows a vocabulary. `w:pPr` ordering
belongs to `document/emit/docx/wml.py`, a slide's shape tree belongs to the
presentation backend. This module knows angle brackets and nothing else.
"""

from __future__ import annotations

from typing import Mapping, Optional

from physics_svg.draw import clean


def escape(value: object) -> str:
    """Author text -> XML text.

    `clean()` first: the characters XML cannot hold are the drawing layer's
    rule too, and one definition of «what author text may contain» is the
    point — a node has two serialisers and they must agree.
    """
    text = clean(value)
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def el(tag: str, attrs: Optional[Mapping[str, object]] = None, children: str = "") -> str:
    """One element. Attribute order is the caller's, and callers pass literals,
    so the output is byte-stable across runs.

    `Mapping`, not `dict`: a caller with a `dict[str, str]` of namespaces has
    one that every slide-like part reuses, and an invariant `dict[str, object]`
    would make it copy the thing on every call.
    """
    rendered = "".join(f' {name}="{escape(value)}"' for name, value in (attrs or {}).items())
    if not children:
        return f"<{tag}{rendered}/>"
    return f"<{tag}{rendered}>{children}</{tag}>"
