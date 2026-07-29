"""Shared access to every registered type and every example spec.

Tests here are written against the registry rather than against a list of
types, so a new illustration is covered the moment its package exists — that
is the whole point of the registry.

Not a `conftest.py` on purpose: several test directories would each want one,
and a bare `from conftest import ...` then resolves to whichever was imported
first. Named modules keep that unambiguous.
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


#: Ready-made parametrisations: put `pytestmark = EACH_EXAMPLE` on a module or
#: a class instead of repeating the id list.
EACH_EXAMPLE = pytest.mark.parametrize("example", EXAMPLES, ids=[e.name for e in EXAMPLES])
EACH_TYPE = pytest.mark.parametrize("visual_type", TYPES, ids=[t.tag for t in TYPES])
