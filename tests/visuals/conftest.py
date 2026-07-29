"""Shared access to every registered type and every example spec.

Tests here are written against the registry rather than against a list of
types, so a new illustration is covered the moment its package exists — that
is the whole point of the registry.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterator, NamedTuple

import pytest

from physics_svg.visuals import VisualType, load_all, parse_visual


class Example(NamedTuple):
    type: VisualType
    path: Path

    @property
    def name(self) -> str:
        return f"{self.type.tag}/{self.path.stem}"

    @property
    def raw(self) -> Any:
        return json.loads(self.path.read_text(encoding="utf-8"))

    @property
    def model(self) -> Any:
        return parse_visual(self.raw, self.path.name)


def all_examples() -> Iterator[Example]:
    for entry in load_all().values():
        for path in entry.specs:
            yield Example(entry, path)


EXAMPLES = list(all_examples())
TYPES = list(load_all().values())


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    if "example" in metafunc.fixturenames:
        metafunc.parametrize("example", EXAMPLES, ids=[e.name for e in EXAMPLES])
    if "visual_type" in metafunc.fixturenames:
        metafunc.parametrize("visual_type", TYPES, ids=[t.tag for t in TYPES])
