"""The label scale: six named steps, and the canvas that carries them.

The scale is what keeps a label size out of a renderer's source. These
tests hold the two things that make it worth having: the sheet steps are
exactly the sizes the library has always drawn at (so no picture moves when
renderers start reading them), and a step is genuinely a step — the scale
ascends, with no two roles sharing a value by accident.
"""

from physics_svg.draw import SHEET, Canvas, Medium

#: The sizes found in the renderers before the scale existed, in the order
#: docs/visual-scale.md §6.1 names them. Written out rather than derived:
#: the point of the test is to disagree with the code, not to echo it.
LIBRARY_SIZES = (6.0, 7.0, 8.0, 9.0, 10.0, 15.0)


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


class TestCanvasCarriesIt:
    def test_the_sheet_is_the_default(self) -> None:
        """Every caller that existed before the scale keeps drawing on paper."""
        assert Canvas().medium is SHEET

    def test_a_canvas_keeps_the_medium_it_was_given(self) -> None:
        other = Medium("board", 9.0, 10.5, 12.0, 13.5, 15.0, 19.0)
        assert Canvas("s1", other).medium is other

    def test_the_scope_still_comes_first(self) -> None:
        assert Canvas("s1").uid("hatch") == "s1-hatch"
