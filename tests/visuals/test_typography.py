"""No renderer picks a label size of its own.

A size written into a renderer is a decision about how far away the picture
will be read from, taken by code that has no way of knowing. Every label in
the library therefore gets its size from the medium the canvas carries
(docs/visual-scale.md §6.1), and this test is what keeps it that way — the
counterpart of the rule `tests/presentation/test_design.py` holds over the
player's stylesheet.

The check is structural, not numeric: `major_length=9` is a tick nine units
long and has nothing to do with the step that happens to be 9 too. What it
forbids is a literal standing where a *size* is expected — and a `Text` with
no size at all, which would inherit the primitive's own default and drift
just as silently.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

PACKAGE = Path(__file__).resolve().parents[2] / "src" / "physics_svg"

#: Where labels are drawn. `draw/` is excluded on purpose: it holds the
#: primitive and the scale themselves, and `SHEET` is defined there in
#: numbers by definition.
SOURCES = sorted((PACKAGE / "visuals").rglob("*.py")) + sorted((PACKAGE / "elements").glob("*.py"))

#: Keywords that name a label size wherever they appear.
SIZE_KEYWORDS = ("size", "label_size")


def _is_literal(node: ast.expr) -> bool:
    if isinstance(node, ast.Constant):
        return isinstance(node.value, (int, float)) and not isinstance(node.value, bool)
    # -7 arrives as a unary minus over a constant.
    return isinstance(node, ast.UnaryOp) and _is_literal(node.operand)


def _called(node: ast.Call) -> str:
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    return ""


@pytest.mark.parametrize("path", SOURCES, ids=lambda p: p.name)
class TestLabelSizes:
    def test_no_size_is_a_literal(self, path: Path) -> None:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        offenders = [
            f"{path.name}:{node.lineno} {_called(node)}({keyword.arg}=…)"
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            for keyword in node.keywords
            if keyword.arg in SIZE_KEYWORDS and _is_literal(keyword.value)
        ]
        # `Text(at, content, size, ...)` — the size also travels third.
        offenders += [
            f"{path.name}:{node.lineno} Text(…)"
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and _called(node) == "Text"
            and len(node.args) >= 3
            and _is_literal(node.args[2])
        ]
        assert not offenders, (
            "кегль подписи взят числом, а не ступенью носителя: " + ", ".join(offenders)
        )

    def test_every_label_states_its_size(self, path: Path) -> None:
        """A `Text` without a size falls back on the primitive's default —
        the same silent drift, one level down."""
        tree = ast.parse(path.read_text(encoding="utf-8"))
        offenders = [
            f"{path.name}:{node.lineno}"
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and _called(node) == "Text"
            and len(node.args) < 3
            and not any(keyword.arg == "size" for keyword in node.keywords)
        ]
        assert not offenders, "подпись без кегля: " + ", ".join(offenders)
