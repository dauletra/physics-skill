"""Can the class read the labels — measured, not judged.

An illustration is drawn once and shown twice, and on a board it is fitted
into whatever rectangle the slide gives it. So the size a label ends up at
is not a property of the picture alone: it is the picture's own proportion
times the room it gets (docs/visual-scale.md §2).

The threshold is `design.SMALL` — the smallest step the class-facing scale
has, 19 pt, which is about 17 angular minutes from the back row. Below it a
label is not small, it is unread.

What is tested here is therefore not «is the picture big enough» but **does
the rule that chooses where to put it work**: every spec in the library,
placed by the same procedure a lesson uses, must come out legible. That is
the strongest thing a test can say, and it still says nothing about how the
slide *looks* — six metres and `evals/pptx.md` say that.
"""

from __future__ import annotations

import pytest

from library import EACH_EXAMPLE, EXAMPLES
from physics_svg.draw import BOARD, SHEET, Canvas, Medium, overlapping_labels
from physics_svg.presentation.pptx import design, layouts
from physics_svg.visuals import label_metrics, render_to_canvas

#: Every kind that carries a picture offers it the same choice — beside the
#: text or above it — and each pair of boxes has to work on its own. A task
#: keeps a band at the foot of the frame for its answer, so it has less
#: height to give away than an explanation does; the rule is one, the room
#: is not.
PLACEMENTS = {
    "content": (layouts.CONTENT_SPLIT, layouts.CONTENT_STACK),
    "board_task": (layouts.TASK_SPLIT, layouts.TASK_STACK),
}

EACH_PLACEMENT = pytest.mark.parametrize(
    "beside,above",
    [pair for pair in PLACEMENTS.values()],
    ids=list(PLACEMENTS),
)


def box_of(layout: object) -> tuple[float, float, float, float]:
    picture = getattr(layout, "picture")
    assert picture is not None, layout
    return picture  # type: ignore[no-any-return]


def fitted(model: object, box: tuple[float, float, float, float]) -> float:
    """The smallest label in points once the picture is fitted into `box`."""
    size, width, height = label_metrics(model)
    _, _, box_width, box_height = box
    return size * min(box_width / width, box_height / height)


@EACH_EXAMPLE
@EACH_PLACEMENT
def test_the_chosen_place_is_legible(example, beside, above) -> None:
    """Wherever the rule puts this picture, its smallest label reads."""
    size, _, _ = label_metrics(example.model)
    if not size:  # ruled paper carries no labels at all
        return
    box = box_of(beside if layouts.reads_in(box_of(beside), example.model) else above)
    actual = fitted(example.model, box)
    assert actual >= design.SMALL, (
        f"{example.name} на «{beside.name}»/«{above.name}»: подпись {actual:.1f} pt "
        f"при пороге {design.SMALL:.0f} — ни рядом с текстом, ни над ним не читается"
    )


@EACH_EXAMPLE
def test_a_picture_alone_gets_the_frame(example) -> None:
    """A slide whose whole point is the picture puts nothing beside it, and
    there the library must be legible without any rule at all."""
    size, _, _ = label_metrics(example.model)
    if not size:
        return
    assert layouts.CONTENT_FIGURE.picture is not None
    actual = fitted(example.model, layouts.CONTENT_FIGURE.picture)
    assert actual >= design.SMALL, f"{example.name}: {actual:.1f} pt во всю ширину кадра"


@EACH_PLACEMENT
def test_moving_a_picture_out_of_the_column_helps(beside, above) -> None:
    """The rule only ever moves a picture to a place that is better for it.

    Worth stating because the obvious version of this rule — «wide pictures
    go above the text» — is wrong, and the measurement said so: what decides
    is not the proportion but the proportion times the picture's own label
    share. A balance at 2,1 to 1 reads in the column (its numbers are a
    large part of a short picture); a graph at 1,8 to 1 does not. So the
    invariant worth holding is not about shape at all — it is that the move
    is never a downgrade.
    """
    moved = [
        example
        for example in EXAMPLES
        if label_metrics(example.model)[0]
        and not layouts.reads_in(box_of(beside), example.model)
    ]
    assert moved, f"{beside.name}: правило перестало кого-либо переставлять — проверь порог"
    for example in moved:
        assert fitted(example.model, box_of(above)) > fitted(
            example.model, box_of(beside)
        ), example.name


@EACH_EXAMPLE
@pytest.mark.parametrize("medium", [SHEET, BOARD], ids=["sheet", "board"])
def test_no_label_is_written_over_another(example, medium: Medium) -> None:
    """A label under a label is a label that is not there.

    Over the whole library, on both media. Nothing here is a matter of taste:
    the boxes either share area or they do not, and a picture that fails this
    is a picture where a number cannot be read at all.
    """
    canvas = Canvas(medium=medium)
    render_to_canvas(example.model, canvas)
    found = overlapping_labels(canvas)
    assert not found, f"{example.name} на носителе «{medium.name}»: {', '.join(found)}"


def test_the_board_scale_is_the_sheet_scale_enlarged() -> None:
    """Every step grows and the ladder keeps its order: a picture on a board
    is the same drawing set larger, not a different drawing."""
    assert all(board > sheet for board, sheet in zip(BOARD.steps, SHEET.steps))
    assert list(BOARD.steps) == sorted(set(BOARD.steps))


#: What a service line has to clear against the slide's paper to be a line at
#: all, by rung. Not WCAG text minima — a gridline is not text, and it is
#: *supposed* to be weaker than the drawing over it. These say only that it
#: exists: on a lit panel in a lit room, below about 1,4:1 there is nothing
#: to see (docs/visual-scale.md §6.5). The final call is eyes on a real
#: panel — `evals/pptx.md` — and these hold the floor under that call.
BOARD_GREY_FLOOR = (4.0, 2.6, 2.0, 1.4)


def contrast(one: str, other: str) -> float:
    values = sorted(_luminance(colour) for colour in (one, other))
    return (values[1] + 0.05) / (values[0] + 0.05)


def _luminance(colour: str) -> float:
    raw = colour.lstrip("#")
    if len(raw) == 3:
        raw = "".join(channel * 2 for channel in raw)
    linear = [
        value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4
        for value in (int(raw[i : i + 2], 16) / 255 for i in (0, 2, 4))
    ]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def test_the_board_greys_survive_a_lit_panel() -> None:
    """Measured against the paper a slide actually has, rung by rung."""
    paper = f"#{design.PAPER}"
    for grey, floor in zip(BOARD.greys, BOARD_GREY_FLOOR):
        assert contrast(paper, grey) >= floor, f"{grey}: {contrast(paper, grey):.2f} при {floor}"


def test_the_sheet_greys_would_not_have_survived_it() -> None:
    """Why the ladder had to move at all. Paper is right to set a ruling
    faint — it lives under a pencil and goes through a photocopier — and that
    is exactly what makes it disappear on a panel."""
    paper = f"#{design.PAPER}"
    assert any(
        contrast(paper, grey) < floor for grey, floor in zip(SHEET.greys, BOARD_GREY_FLOOR)
    )
