"""Formulas: from the dollars an author types to what each backend does.

Three separate promises, and they fail in different ways, so they are checked
apart from one another:

* the page does not move — a formula in HTML is what it always was, dollars
  and all, because KaTeX finds them in the finished file;
* the subset really is translated — `x_0^2` has to come out as one script
  pair and not as three characters;
* what is not translated is *said*, not swallowed. That is the promise the
  whole design of the fallback rests on.
"""

from __future__ import annotations

import io
import re
import zipfile

import docx
import pytest

from physics_svg.document import build_document, build_docx, parse_block, parse_document
from physics_svg.document.emit.docx.omml import Delim, Frac, Rad, Row, Scripts, Sym, convert, parse
from physics_svg.document.emit.html import inline as html_inline
from physics_svg.document.layout import Math, Run
from physics_svg.inline import parse_inline
from physics_svg.schema import SchemaError

DOC = parse_document({"title": "Проба"})


def text_block(body: str) -> dict:
    return {"type": "text", "body": body}


def document_xml(*raw_blocks: dict) -> str:
    blocks = [parse_block(raw, f"b{i}") for i, raw in enumerate(raw_blocks)]
    data = build_docx(DOC, blocks).data
    with zipfile.ZipFile(io.BytesIO(data)) as package:
        return package.read("word/document.xml").decode()


class TestReading:
    """Where a formula begins and ends. A dollar is a common character, so
    getting this wrong would turn prices and text into maths."""

    def test_a_pair_of_dollars_is_a_formula(self) -> None:
        parts = parse_inline("энергия $E = mc^2$ равна")
        assert parts == (Run("энергия "), Math("E = mc^2"), Run(" равна"))

    def test_double_dollars_are_a_display_formula(self) -> None:
        (part,) = parse_inline("$$x$$")
        assert part == Math("x", display=True)

    def test_a_lone_dollar_stays_a_dollar(self) -> None:
        assert parse_inline("цена 5 $") == (Run("цена 5 $"),)

    def test_a_formula_does_not_cross_a_line(self) -> None:
        # Otherwise one unclosed dollar would swallow the rest of the text.
        parts = parse_inline("первая $строка\nвторая$ строка")
        assert all(isinstance(part, Run) for part in parts)

    def test_underscores_inside_a_formula_are_not_ruling(self) -> None:
        # In `text` a run of underscores is a place to write — but inside a
        # formula it belongs to the LaTeX, and the formula is read first.
        (part,) = parse_inline("$a___b$", blanks=True)
        assert part == Math("a___b")

    def test_markup_around_a_formula_still_works(self) -> None:
        parts = parse_inline("υ<sub>0</sub> и $x$")
        assert Math("x") in parts
        assert Run("0", "sub") in parts


class TestThePageDoesNotMove:
    """The invariant of the phase: HTML is what it was before formulas became
    a layout element. The golden pages cover the example; this states why."""

    def test_a_formula_is_printed_back_with_its_dollars(self) -> None:
        assert html_inline(parse_inline("$x^2$")) == "$x^2$"
        assert html_inline(parse_inline("$$x$$")) == "$$x$$"

    def test_a_formula_is_escaped_exactly_as_plain_text_was(self) -> None:
        body = "сравни $a<b$ и <sup>2</sup>"
        assert html_inline(parse_inline(body)) == "сравни $a&lt;b$ и <sup>2</sup>"

    def test_the_page_is_the_same_string_as_before_the_split(self) -> None:
        # Same text, once as a formula and once as characters the parser is
        # not allowed to touch: the page has to come out identical.
        formula = build_document(DOC, [parse_block(text_block("$a+b$"), "b")])
        plain = build_document(DOC, [parse_block(text_block("(a+b)"), "b")])
        assert formula.replace("$a+b$", "(a+b)") == plain


class TestParsing:
    def test_a_power_and_an_index_are_one_pair(self) -> None:
        assert parse("x_0^2") == Scripts(Sym("x"), Sym("2"), Sym("0"))

    def test_a_group_is_one_argument(self) -> None:
        assert parse("x^{10}") == Scripts(Sym("x"), Row((Sym("1"), Sym("0"))))

    def test_a_bare_script_takes_one_symbol(self) -> None:
        # TeX's own rule: `x^23` is x squared, then three.
        assert parse("x^23") == Row((Scripts(Sym("x"), Sym("2")), Sym("3")))

    def test_a_fraction_without_braces_is_still_a_fraction(self) -> None:
        assert parse(r"\frac12") == Frac(Sym("1"), Sym("2"))

    def test_a_root_may_carry_a_degree(self) -> None:
        assert parse(r"\sqrt[3]{x}") == Rad(Sym("x"), Sym("3"))

    def test_a_command_becomes_its_symbol(self) -> None:
        assert parse(r"\upsilon\cdot\alpha") == Row((Sym("υ"), Sym("·"), Sym("α")))

    def test_text_keeps_its_spaces_and_stays_upright(self) -> None:
        assert parse(r"\text{м / с}") == Sym("м / с", upright=True)

    def test_spaces_outside_text_are_ignored(self) -> None:
        assert parse("a b") == parse("ab")

    def test_brackets_that_match_can_grow(self) -> None:
        assert parse(r"(x)") == Delim(Sym("x"))
        assert parse(r"\left(x\right)") == Delim(Sym("x"))

    def test_an_odd_bracket_is_just_a_character(self) -> None:
        # «(0; 5]» is a range, not a broken formula.
        assert isinstance(parse("(0; 5]"), Row)


class TestRefusal:
    """What the subset does not cover is named, not guessed at."""

    @pytest.mark.parametrize(
        "latex, fragment",
        [
            (r"\int_0^t x", r"\int"),
            (r"\begin{cases}x\end{cases}", r"\begin"),
            (r"\frac{a}{b", "}"),
            ("x^", "^"),
            ("   ", "пустая"),
        ],
    )
    def test_it_says_what_it_did_not_understand(self, latex: str, fragment: str) -> None:
        xml, reason = convert(latex)
        assert xml is None
        assert fragment in reason


class TestWord:
    def test_a_formula_becomes_omml(self) -> None:
        xml = document_xml(text_block(r"Энергия $E = \frac{mv^2}{2}$."))
        assert "<m:oMath>" in xml and "<m:f>" in xml
        assert "$" not in xml

    def test_a_display_formula_stands_on_its_own(self) -> None:
        assert "<m:oMathPara>" in document_xml(text_block(r"Формула $$x^2$$."))

    def test_an_untranslatable_formula_is_printed_as_typed(self) -> None:
        xml = document_xml(text_block(r"Интеграл $\int_0^t$ здесь."))
        assert "<m:oMath>" not in xml
        assert r"$\int_0^t$" in xml

    def test_the_build_reports_what_it_could_not_translate(self) -> None:
        blocks = [
            parse_block(
                {
                    "type": "task",
                    "blocks": [text_block(r"Интеграл $\int_0^t$."), {"type": "open"}],
                },
                "t",
            )
        ]
        notes = build_docx(DOC, blocks).notes
        assert len(notes) == 1
        assert "задание 1" in notes[0] and r"\int" in notes[0]

    def test_a_translated_formula_is_reported_about_nothing(self) -> None:
        assert build_docx(DOC, [parse_block(text_block("$x^2$"), "b")]).notes == ()

    def test_formulas_reach_every_corner_of_the_document(self) -> None:
        """A formula is part of the text, so it travels wherever text does —
        a statement, an option, a table cell, an answer."""
        xml = document_xml(
            {"type": "table", "headers": [r"$\frac{a}{b}$"], "rows": [[r"$x^2$"]]},
            {
                "type": "task",
                "blocks": [
                    text_block("Условие."),
                    {
                        "type": "choice",
                        "options": [{"text": r"$\sqrt{2}$", "correct": True}, {"text": "нет"}],
                    },
                ],
            },
            {
                "type": "task",
                "blocks": [text_block("Вопрос."), {"type": "open", "answer": r"$\frac{1}{2}$"}],
            },
        )
        # Header, cell, option, and the answer in the section at the end.
        # (A `choice` answer names the letter, so the option's own formula is
        # printed once — in the body.)
        assert xml.count("<m:oMath>") == 4
        assert "<m:rad>" in xml

    def test_word_opens_a_document_with_a_formula(self) -> None:
        blocks = [parse_block(text_block(r"$\sqrt[3]{\frac{a}{b}}$"), "b")]
        docx.Document(io.BytesIO(build_docx(DOC, blocks).data))

    def test_the_maths_namespace_is_declared(self) -> None:
        # Word refuses a document whose namespaces are not on the root.
        assert 'xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math"' in (
            document_xml(text_block("$x$"))
        )

    def test_xml_in_a_formula_is_escaped(self) -> None:
        xml = document_xml(text_block(r"$a<b$ и $\text{<w:p>}$"))
        assert "<w:p>&" not in xml
        assert "&lt;" in xml
        assert re.search(r"<m:t[^>]*>&lt;w:p&gt;</m:t>", xml)


class TestGapInsideAFormula:
    """A named gap splits the LaTeX in two and neither half is a formula any
    more. It used to be a warning in the reference; now it does not build."""

    def test_it_is_refused_with_the_path_to_the_block(self) -> None:
        with pytest.raises(SchemaError) as info:
            parse_block(
                {
                    "type": "task",
                    "id": "t",
                    "blocks": [
                        text_block("Условие."),
                        {
                            "type": "fill_text",
                            "template": r"$\upsilon = ___v___$ м/с",
                            "blanks": {"v": "5"},
                        },
                    ],
                },
                "t",
            )
        message = str(info.value)
        assert "внутри формулы" in message and "___v___" in message

    def test_a_gap_beside_a_formula_is_fine(self) -> None:
        parse_block(
            {
                "type": "task",
                "id": "t",
                "blocks": [
                    text_block("Вставьте пропущенное."),
                    {
                        "type": "fill_text",
                        "template": r"Скорость ___v___ м/с, энергия $E = mc^2$",
                        "blanks": {"v": "5"},
                    },
                ],
            },
            "t",
        )
