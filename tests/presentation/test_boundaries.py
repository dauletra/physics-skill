"""The genre boundary: `presentation/` and `document/` never import each
other (docs/presentation.md §2).

What they share — illustrations, the inline conventions, the validation
kernel — lives below both. A crossing import would quietly turn "parallel
but separate" into a dependency, so it is a test rather than a review note.
"""

from __future__ import annotations

from pathlib import Path

import physics_svg

PACKAGE = Path(physics_svg.__file__).parent


def imports_of(package: str) -> dict[str, str]:
    """Source files of a package that mention the other genre, by offender."""
    forbidden = {"document": "physics_svg.presentation", "presentation": "physics_svg.document"}
    other = forbidden[package]
    return {
        str(path.relative_to(PACKAGE)): other
        for path in (PACKAGE / package).rglob("*.py")
        if other in path.read_text(encoding="utf-8")
    }


def test_the_document_does_not_know_the_presentation_exists() -> None:
    assert imports_of("document") == {}


def test_the_presentation_does_not_know_the_document_exists() -> None:
    assert imports_of("presentation") == {}
