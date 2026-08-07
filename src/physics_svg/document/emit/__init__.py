"""Backends: one layout, one file per output format.

A backend is the only place that knows what markup looks like. Everything
above it — components, questions, containers, numbering — works in the
vocabulary of `document/layout.py` and never sees a tag.
"""

from __future__ import annotations

from physics_svg.document.emit.html import page, render_source

__all__ = ["page", "render_source"]
