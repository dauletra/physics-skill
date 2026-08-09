"""The two ladders of a medium — label size and service grey — and the canvas
that carries them.

They are what keeps a size and a shade out of a renderer's source. These
tests hold the two things that make them worth having: the sheet rungs are
exactly what the library has always drawn with (so no picture moves when
renderers start reading them), and a rung is genuinely a rung — each ladder
runs one way, with no two roles sharing a value by accident.
"""

from dataclasses import replace

from physics_svg.draw import BOARD, SHEET, Canvas

#: The sizes found in the renderers before the scale existed, in the order
#: docs/visual-scale.md §6.1 names them. Written out rather than derived:
#: the point of the test is to disagree with the code, not to echo it.
LIBRARY_SIZES = (6.0, 7.0, 8.0, 9.0, 10.0, 15.0)
#: Likewise the greys, strongest first: a field's border, the ruling itself,
#: a chart's grid, a sub-division.
LIBRARY_GREYS = ("#888", "#bbb", "#ccc", "#e6e6e6")


def brightness(colour: str) -> int:
    """How light the grey is, 0..255. Every one of them is a true grey, so
    one channel says everything."""
    raw = colour.lstrip("#")
    return int(raw[0] * 2 if len(raw) == 3 else raw[:2], 16)


class TestSheet:
    def test_steps_are_what_the_library_already_drew(self) -> None:
        assert SHEET.steps == LIBRARY_SIZES

    def test_every_role_names_its_own_step(self) -> None:
        assert SHEET.steps == (
            SHEET.micro,
            SHEET.label,
            SHEET.caption,
            SHEET.number,
            SHEET.axis,
            SHEET.display,
        )

    def test_the_scale_ascends(self) -> None:
        """A role that is not larger than the one below it is not a step."""
        assert list(SHEET.steps) == sorted(set(SHEET.steps))


class TestServiceGrey:
    def test_greys_are_what_the_library_already_drew(self) -> None:
        assert SHEET.greys == LIBRARY_GREYS

    def test_the_ladder_only_gets_lighter(self) -> None:
        """A sub-division must not read heavier than the division it divides,
        on either medium — that is the whole point of having rungs."""
        for medium in (SHEET, BOARD):
            steps = [brightness(grey) for grey in medium.greys]
            assert steps == sorted(set(steps)), medium.name

    def test_the_board_darkens_every_rung(self) -> None:
        """On a lit panel the faintest grey of paper is not faint, it is
        absent (docs/visual-scale.md §3.7)."""
        for sheet, board in zip(SHEET.greys, BOARD.greys):
            assert brightness(board) < brightness(sheet)


class TestCanvasCarriesIt:
    def test_the_sheet_is_the_default(self) -> None:
        """Every caller that existed before the scale keeps drawing on paper."""
        assert Canvas().medium is SHEET

    def test_a_canvas_keeps_the_medium_it_was_given(self) -> None:
        other = replace(SHEET, name="other")
        assert Canvas("s1", other).medium is other

    def test_the_scope_still_comes_first(self) -> None:
        assert Canvas("s1").uid("hatch") == "s1-hatch"
