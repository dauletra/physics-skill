"""The JSON form of parsed runs — the wire contract of `physics_svg.inline`.

`parse_inline` itself is exercised where its consumers live (formulas,
questions); this file pins the one thing a non-Python consumer reads: what a
run looks like as JSON. The form is a contract with players and servers that
never import this package, so a change here is a change of `format`, not a
refactoring.
"""

from __future__ import annotations

import json

from physics_svg.inline import Blank, Math, Run, parse_inline, runs_json


class TestShape:
    """One JSON object per run, defaults omitted — the short common case."""

    def test_plain_text_is_t(self) -> None:
        assert runs_json((Run("При движении"),)) == [{"t": "При движении"}]

    def test_script_is_named_only_when_present(self) -> None:
        assert runs_json((Run("x"), Run("0", "sub"))) == [
            {"t": "x"},
            {"t": "0", "script": "sub"},
        ]

    def test_inline_formula_is_math(self) -> None:
        assert runs_json((Math("v = v_0 + at"),)) == [{"math": "v = v_0 + at"}]

    def test_display_formula_says_so(self) -> None:
        assert runs_json((Math("x", display=True),)) == [{"math": "x", "display": True}]

    def test_blank_carries_its_width(self) -> None:
        assert runs_json((Blank(5),)) == [{"blank": 5}]

    def test_empty_text_is_an_empty_list(self) -> None:
        assert runs_json(()) == []


class TestFromAuthorText:
    """The whole road: what an author types is what a consumer receives."""

    def test_a_sentence_with_everything(self) -> None:
        runs = parse_inline("Путь $S$ тела<sup>*</sup>: _____", blanks=True)
        assert runs_json(runs) == [
            {"t": "Путь "},
            {"math": "S"},
            {"t": " тела"},
            {"t": "*", "script": "sup"},
            {"t": ": "},
            {"blank": 5},
        ]

    def test_text_stays_raw(self) -> None:
        # Escaping is the serialiser's job: the run carries the author's
        # characters, and json.dumps is what makes them safe on the wire.
        (item,) = runs_json(parse_inline("a < b & c"))
        assert item == {"t": "a < b & c"}
        assert json.loads(json.dumps(item)) == item
