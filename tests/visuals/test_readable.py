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

from library import EACH_EXAMPLE, EXAMPLES
from physics_svg.presentation.pptx import design, layouts
from physics_svg.visuals import label_metrics

#: The boxes a slide offers an illustration, narrowest first.
BOXES = {
    "content_split": layouts.CONTENT_SPLIT.picture,
    "content_stack": layouts.CONTENT_STACK.picture,
    "content_figure": layouts.CONTENT_FIGURE.picture,
}


def fitted(model: object, box: tuple[float, float, float, float]) -> float:
    """The smallest label in points once the picture is fitted into `box`."""
    size, width, height = label_metrics(model)
    _, _, box_width, box_height = box
    return size * min(box_width / width, box_height / height)


@EACH_EXAMPLE
def test_the_chosen_place_is_legible(example) -> None:
    """Wherever the rule puts this picture, its smallest label reads."""
    size, _, _ = label_metrics(example.model)
    if not size:  # ruled paper carries no labels at all
        return
    assert layouts.CONTENT_SPLIT.picture is not None
    beside_text = layouts.reads_in(layouts.CONTENT_SPLIT.picture, example.model)
    box = BOXES["content_split"] if beside_text else BOXES["content_stack"]
    assert box is not None
    actual = fitted(example.model, box)
    assert actual >= design.SMALL, (
        f"{example.name}: подпись {actual:.1f} pt при пороге {design.SMALL:.0f} — "
        "ни рядом с текстом, ни над ним не читается"
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


def test_moving_a_picture_out_of_the_column_helps() -> None:
    """The rule only ever moves a picture to a place that is better for it.

    Worth stating because the obvious version of this rule — «wide pictures
    go above the text» — is wrong, and the measurement said so: what decides
    is not the proportion but the proportion times the picture's own label
    share. A balance at 2,1 to 1 reads in the column (its numbers are a
    large part of a short picture); a graph at 1,8 to 1 does not. So the
    invariant worth holding is not about shape at all — it is that the move
    is never a downgrade.
    """
    assert layouts.CONTENT_SPLIT.picture is not None
    assert layouts.CONTENT_STACK.picture is not None
    moved = [
        example
        for example in EXAMPLES
        if label_metrics(example.model)[0]
        and not layouts.reads_in(layouts.CONTENT_SPLIT.picture, example.model)
    ]
    assert moved, "правило перестало кого-либо переставлять — проверь порог"
    for example in moved:
        in_column = fitted(example.model, layouts.CONTENT_SPLIT.picture)
        above = fitted(example.model, layouts.CONTENT_STACK.picture)
        assert above > in_column, example.name


def test_the_board_scale_is_the_sheet_scale_enlarged() -> None:
    """Every step grows and the ladder keeps its order: a picture on a board
    is the same drawing set larger, not a different drawing."""
    from physics_svg.draw import BOARD, SHEET

    assert all(board > sheet for board, sheet in zip(BOARD.steps, SHEET.steps))
    assert list(BOARD.steps) == sorted(set(BOARD.steps))
