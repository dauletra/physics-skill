"""Drawing the instruments.

Seven builders, one per scale geometry. What they no longer contain is the
tick loop: where the marks go and which of them are numbered is `elements.
scale`, so a builder is the body of the instrument plus the placement of its
axis. Adding a kind whose scale already exists is a branch in the body
drawing, nothing more.

The caption is drawn inside the SVG, positioned under the measured content.
It used to be HTML beside the picture, with a second implementation for
standalone files.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Callable

from physics_svg.draw import (
    BLACK,
    BODY,
    HEAVY,
    LINE,
    OUTLINE,
    SHEET,
    SOLID,
    THIN,
    WHITE,
    BBox,
    Canvas,
    Circle,
    Line,
    Medium,
    Node,
    PathBuilder,
    Pt,
    Rect,
    Style,
    Text,
    fixed,
    num,
    polar,
    text_width,
)
from physics_svg.elements import ArcAxis, LinearAxis, hatch, liquid, scale_marks, tick_layout
from physics_svg.elements.scale import Tick
from physics_svg.visuals.instrument.model import InstrumentSpec
from physics_svg.visuals.registry import Layout

#: The dial arc runs from 150 to 30 textbook degrees, so the needle sweeps
#: through the vertical over 120 degrees.
DIAL_START, DIAL_END = 150.0, 30.0
#: A stopwatch face starts at the top and goes clockwise, all the way round.
CLOCK_START, CLOCK_END = 90.0, -270.0

#: A real minus sign (U+2212), not a hyphen and not an HTML entity: `Text`
#: escapes what it is given, so markup written by hand would show through.
_MINUS = "−"

#: Everything below exists to clear a number, so it is measured in that
#: number's height rather than in units: at a larger scale the numbers move
#: off the scale line instead of onto it. Each ratio is the tuned sheet value
#: over the sheet step it was tuned against, which makes it exactly the old
#: number on paper — what the goldens hold it to.

#: How far the caption hangs below the instrument.
_CAPTION_DROP = 10.0 / SHEET.caption

#: A number beside a vertical scale drops by this to sit on its tick instead
#: of above it.
_COLUMN_LABEL_SHIFT = 2.4 / SHEET.label

#: The dial: numbers inside the arc, the second row of a dual range, and the
#: unit's baseline inside the circle that rings it.
_DIAL_LABEL_DISTANCE = 14.0 / SHEET.label
_DIAL_LABEL_SHIFT = 2.5 / SHEET.label
_DIAL_INNER_ROW = 11.0 / SHEET.label
_UNIT_BASELINE = 2.8 / SHEET.caption

#: The clock face: the numbers stand on a ring of their own, the tick circle
#: clears them from outside, and the rim clears the ticks. So the face is as
#: wide as its numbers need — the alternative was numbers marching inward onto
#: the pivot and onto the unit written above it.
_CLOCK_LABEL_RING = 33.0
_CLOCK_LABEL_DISTANCE = -14.0 / SHEET.label
_CLOCK_LABEL_SHIFT = 2.4 / SHEET.label
_CLOCK_RIM_GAP = 7.0
_CLOCK_NEEDLE_GAP = 9.0
#: Where the unit is written on the face, and where the crown sits above it.
_CLOCK_UNIT_DROP = 21.0
_CLOCK_CROWN_LIFT = 14.0
_CLOCK_STEM = 5.0

#: The ruler: numbers hanging under the top edge, the unit a line below them,
#: and the bottom edge clearing that.
_RULER_LABEL_DISTANCE = 17.5 / SHEET.label
_RULER_UNIT_ROW = 10.0 / SHEET.label
_RULER_UNIT_LIFT = 3.5 / SHEET.label

#: The caliper: numbers inside the bar above its lower edge, the unit a line
#: above them, the bar's top edge clearing the unit, and the index of the
#: vernier under its own marks. The unit used to sit at a fixed 8,5 from the
#: top edge, which put it three quarters of a line from the numbers — they
#: touched on paper and overlapped outright on a board.
_CALIPER_LABEL_DISTANCE = 9.5 / SHEET.label
_CALIPER_UNIT_ROW = 1.2
_CALIPER_UNIT_LIFT = 0.9
_VERNIER_INDEX_DROP = 14.5 / SHEET.micro

#: The weight on a balance pan carries its mass just above it, and two masses
#: keep this much white between them when they are what sets the spacing.
_WEIGHT_LABEL_LIFT = 4.0 / SHEET.micro
_WEIGHT_LABEL_AIR = 0.1

#: The dial's terminals: the sign beside a socket, and the caption above one.
_TERMINAL_SIGN_GAP = 8.0 / SHEET.caption
_TERMINAL_SIGN_DROP = 3.0 / SHEET.caption
_TERMINAL_LABEL_LIFT = 6.0 / SHEET.micro

#: The accuracy class in the corner of a dial, off the bottom edge.
_CLASS_LIFT = 5.5 / SHEET.label


def render(model: InstrumentSpec, canvas: Canvas) -> Layout:
    _BUILDERS[model.family](model, canvas)
    if model.caption:
        # Placed against what has actually been drawn, so a caption never
        # overlaps a tall instrument nor floats away from a short one.
        box = canvas.content_box()
        if box is not None:
            size = canvas.medium.caption
            canvas.add(
                Text(
                    Pt(box.center.x, box.y1 + _CAPTION_DROP * size),
                    model.caption,
                    size,
                    "middle",
                )
            )
    return Layout(padding=2.0)


# --- shared helpers -----------------------------------------------------


def _ticks(model: InstrumentSpec, medium: Medium) -> tuple[Tick, ...]:
    """The scale's marks, with the ceiling on numbers lowered to the medium.

    `model.max_labels` is how many numbers a face of this family holds at the
    sheet step, and it is also what the model **validates** an author's pinned
    step against — which is why the renderer lowers a copy of it and never the
    thing itself. One spec cannot be valid for a worksheet and invalid for a
    slide (docs/visual-scale.md §3.6): the board is allowed to print fewer
    numbers than it is permitted, never to refuse the spec.

    An author who pinned the step is obeyed on both media, crowding and all —
    that step is usually the question ("determine the scale division"), and
    thinning it away would change what the picture asks.
    """
    return tick_layout(
        model.min,
        model.max,
        model.step,
        max_labels=max(2, int(model.max_labels * SHEET.label / medium.label)),
        label_step=model.label_step,
    )


def _value_fraction(model: InstrumentSpec) -> float:
    """Where the reading sits along the scale; an unset value rests at zero."""
    if model.value is None:
        return 0.0
    return (model.value - model.min) / (model.max - model.min)


def _unit(at: Pt, model: InstrumentSpec, size: float, anchor: str = "middle") -> Node:
    return Text(at, model.unit, size, anchor)


# --- strip: ruler -------------------------------------------------------


def _build_ruler(model: InstrumentSpec, canvas: Canvas) -> None:
    """A ruler. Ticks hang down from the top edge of the body; `value` is the
    right-hand end of a hatched block lying on that edge from the scale zero
    — the setup for "measure the length" and "write it with its error".

    The body is as deep as what is written in it: a row of numbers under the
    top edge, the unit a line below them, and the bottom edge clearing that.
    Held at 31 units the two rows walked into each other as the scale grew —
    the numbers hang from the top and the unit sits off the bottom, so a
    fixed depth is a promise the label height gets to break.
    """
    body_top = 17.5
    left, right = 12.0, 208.0
    label = canvas.medium.label
    unit_baseline = body_top + (_RULER_LABEL_DISTANCE + _RULER_UNIT_ROW) * label
    body_bottom = unit_baseline + _RULER_UNIT_LIFT * label
    canvas.add(Rect(Pt(1.5, body_top), 217, body_bottom - body_top, BODY, radius=2))
    axis = LinearAxis(Pt(left, body_top), Pt(right, body_top), Pt(0, 1))
    canvas.extend(
        scale_marks(
            axis,
            _ticks(model, canvas.medium),
            major_length=9,
            minor_length=5,
            # The half-way tick, like the 5 mm mark on a real ruler.
            mid_length=7,
            label_distance=_RULER_LABEL_DISTANCE * label,
            label_size=label,
        )
    )
    canvas.add(_unit(Pt(right, unit_baseline), model, label, anchor="end"))
    if model.value is not None:
        end = left + _value_fraction(model) * (right - left)
        canvas.add(Rect(Pt(left, 4.5), end - left, 13, BODY))
        canvas.extend(hatch(BBox(left, 4.5, end, body_top)))


# --- column: cylinder, thermometer, dynamometer -------------------------


def _column_axis(scale_x: float, top: float, bottom: float, tick_dir: float) -> LinearAxis:
    """Vertical scale: fraction 0 is the bottom of the scale, as on the
    instrument itself."""
    return LinearAxis(Pt(scale_x, bottom), Pt(scale_x, top), Pt(tick_dir, 0))


def _column_marks(
    model: InstrumentSpec,
    axis: LinearAxis,
    label_direction: Pt,
    label_distance: float,
    label_anchor: str,
    medium: Medium,
) -> list[Node]:
    """`label_distance` arrives in label heights: how far the number stands
    off the wall it is written beside."""
    label = medium.label
    return scale_marks(
        axis,
        _ticks(model, medium),
        major_length=9,
        minor_length=5.5,
        label_distance=label_distance * label,
        label_direction=label_direction,
        label_anchor=label_anchor,
        label_shift=_COLUMN_LABEL_SHIFT * label,
        label_size=label,
        major_style=Style(stroke=BLACK, width=0.8),
    )


def _build_cylinder(model: InstrumentSpec, canvas: Canvas) -> None:
    """A measuring cylinder: a vessel open at the top, scale on the left
    wall, liquid shown by a meniscus line and level hatching."""
    left, right, top, bottom = 20.0, 56.0, 8.0, 148.0
    canvas.add(
        PathBuilder()
        .move(Pt(left, top))
        .line(Pt(left, bottom))
        .line(Pt(right, bottom))
        .line(Pt(right, top))
        .build(OUTLINE)
    )
    label = canvas.medium.label
    axis = _column_axis(left, top=18, bottom=138, tick_dir=1)
    canvas.extend(_column_marks(model, axis, Pt(-1, 0), 3 / SHEET.label, "end", canvas.medium))
    canvas.add(_unit(Pt(right + 2, top + 5), model, label, anchor="start"))
    if model.value is not None:
        level = axis.point(_value_fraction(model)).y
        canvas.add(Line(Pt(left + 1, level), Pt(right - 1, level), OUTLINE))
        canvas.extend(liquid(BBox(left, level, right, bottom - 2)))


def _build_thermometer(model: InstrumentSpec, canvas: Canvas) -> None:
    """A thermometer: tube with a bulb, scale to the right of the tube, the
    column filled from the bulb up to the reading."""
    cx = 32.0
    tube_top, tube_bottom = 12.5, 130.0
    bulb_y, bulb_r = 141.0, 9.5
    canvas.add(
        Rect(Pt(cx - 6, tube_top), 12, tube_bottom - tube_top, BODY, radius=6),
        Circle(Pt(cx, bulb_y), bulb_r, BODY),
    )
    label = canvas.medium.label
    axis = _column_axis(cx + 6, top=22, bottom=122, tick_dir=1)
    canvas.extend(_column_marks(model, axis, Pt(1, 0), 8.5 / SHEET.label, "start", canvas.medium))
    canvas.add(_unit(Pt(cx, 8.8), model, label))
    column_top = axis.point(_value_fraction(model)).y if model.value is not None else tube_bottom - 4
    canvas.add(
        Rect(Pt(cx - 2.5, column_top), 5, tube_bottom - 2 - column_top, SOLID),
        Circle(Pt(cx, bulb_y), bulb_r - 3, SOLID),
    )


def _build_dynamometer(model: InstrumentSpec, canvas: Canvas) -> None:
    """A spring balance: body with a suspension ring and a hook, scale down
    the middle, the reading marked by a horizontal pointer."""
    cx = 38.0
    body_left, body_right = 22.0, 54.0
    body_top, body_bottom = 16.0, 128.0
    canvas.add(
        Circle(Pt(cx, 8), 4.5, LINE),
        Line(Pt(cx, 12.5), Pt(cx, body_top), LINE),
        Line(Pt(cx, body_bottom), Pt(cx, 138), LINE),
        PathBuilder()
        .move(Pt(cx, 138))
        .curve(Pt(cx + 8, 140), Pt(cx + 8, 152), Pt(cx - 1, 152))
        .curve(Pt(cx - 6, 152), Pt(cx - 8, 148), Pt(cx - 7, 145))
        .build(OUTLINE),
        Rect(Pt(body_left, body_top), body_right - body_left, body_bottom - body_top, BODY, radius=3),
        _unit(Pt(cx + 8, body_top + 10), model, canvas.medium.label),
    )
    scale_x = cx + 2
    axis = _column_axis(scale_x, top=body_top + 14, bottom=body_bottom - 8, tick_dir=1)
    canvas.extend(
        _column_marks(model, axis, Pt(-1, 0), 3.5 / SHEET.label, "end", canvas.medium)
    )
    pointer_y = axis.point(_value_fraction(model)).y
    canvas.add(
        Line(Pt(body_left + 3, pointer_y), Pt(scale_x + 9, pointer_y), Style(stroke=BLACK, width=1.3))
    )


# --- dial: ammeter, voltmeter, manometer, dial scales, speedometer ------


def _build_dial(model: InstrumentSpec, canvas: Canvas) -> None:
    """A needle instrument: body, arc scale, needle from the pivot to the
    reading. Electrical ones carry the unit in a circle and terminals; the
    others just print the unit.

    A dual-range instrument shares one arc between two scales: the outer row
    of numbers is the larger range, the inner one is the same tick times the
    ratio of ranges, and there are three terminals — the common one and one
    per range. Which one the wire is in is a matter for the problem text, not
    for the drawing.
    """
    center = Pt(80.0, 88.0)
    r_arc, r_needle = 58.0, 52.0
    label, caption = canvas.medium.label, canvas.medium.caption
    electric = model.kind in ("ammeter", "voltmeter")
    # Three labelled terminals need a row of their own: with the body at its
    # normal height their captions would sit on the needle pivot.
    body_height = 116.0 if model.ranges else 107.0
    canvas.add(Rect(Pt(1.5, 1.5), 157, body_height, BODY, radius=6))
    axis = ArcAxis(center, r_arc, DIAL_START, DIAL_END)
    canvas.add(_arc_path(axis, LINE))
    ticks = _ticks(model, canvas.medium)
    canvas.extend(
        scale_marks(
            axis,
            ticks,
            major_length=7.5,
            minor_length=4.5,
            label_distance=_DIAL_LABEL_DISTANCE * label,
            label_shift=_DIAL_LABEL_SHIFT * label,
            label_size=label,
        )
    )
    if model.ranges:
        ratio = model.ranges[0] / model.ranges[-1]
        for tick in ticks:
            if tick.labeled:
                at = axis.point(tick.fraction) - axis.outward(tick.fraction) * (
                    _DIAL_INNER_ROW * label
                )
                canvas.add(
                    Text(
                        at.shifted(0, _DIAL_LABEL_SHIFT * label),
                        num(tick.value * ratio),
                        label,
                    )
                )

    # A circled unit, as on school electrical meters — but only for a short
    # one: "дел." on a multi-range scale does not fit and is set as text.
    if electric and len(model.unit) <= 2:
        canvas.add(Circle(Pt(center.x, 66), 8, Style(stroke=BLACK, width=0.8, fill=WHITE)))
    canvas.add(_unit(Pt(center.x, 66 + _UNIT_BASELINE * caption), model, caption))

    canvas.add(
        Line(center, polar(center, r_needle, axis.angle(_value_fraction(model))), HEAVY),
        Circle(center, 3.5, SOLID),
    )
    if model.accuracy_class is not None:
        # As on a real scale: just the number in the corner. Decoding the
        # marking is the problem's job, not the drawing's.
        canvas.add(
            Text(
                Pt(10, body_height - _CLASS_LIFT * label),
                num(model.accuracy_class),
                label,
                "start",
            )
        )
    if electric:
        canvas.extend(_terminals(model, body_height, canvas.medium))


def _terminals(model: InstrumentSpec, body_height: float, medium: Medium) -> list[Node]:
    socket = Style(stroke=BLACK, width=1, fill=WHITE)
    nodes: list[Node] = []
    if not model.ranges:
        # Two terminals, signs beside them.
        for x, sign in ((58.0, "+"), (102.0, _MINUS)):
            gap = _TERMINAL_SIGN_GAP * medium.caption
            nodes.append(Circle(Pt(x, 99), 3, socket))
            nodes.append(
                Text(
                    Pt(
                        x + (-gap if sign == "+" else gap),
                        99 + _TERMINAL_SIGN_DROP * medium.caption,
                    ),
                    sign,
                    medium.caption,
                )
            )
        return nodes
    # A common terminal plus one per range, each captioned above its socket.
    labels = [_MINUS] + [f"{num(r)}{model.unit}" for r in model.ranges]
    socket_y = body_height - 9
    for i, label in enumerate(labels):
        x = 36 + i * 88 / (len(labels) - 1)
        nodes.append(Circle(Pt(x, socket_y), 3, socket))
        nodes.append(
            Text(Pt(x, socket_y - _TERMINAL_LABEL_LIFT * medium.micro), label, medium.micro)
        )
    return nodes


def _arc_path(axis: ArcAxis, style: Style) -> Node:
    return (
        PathBuilder()
        .arc(axis.center, axis.radius, axis.start_deg, axis.end_deg)
        .build(style)
    )


# --- clock: stopwatch ---------------------------------------------------


def _build_stopwatch(model: InstrumentSpec, canvas: Canvas) -> None:
    """A mechanical stopwatch: a full circular scale, zero at the top, going
    clockwise. Zero and the limit are the same point, so the zero tick is not
    drawn and the number at the top is the limit — as on the real thing.

    The face is sized from the inside out. The numbers keep their ring, the
    ticks stand off it by the height of a number, and the rim clears the
    ticks; so a larger scale makes a larger watch instead of pushing its
    numbers in towards the pivot, which is where the unit is written.
    """
    center = Pt(60.0, 74.0)
    label = canvas.medium.label
    r_ticks = _CLOCK_LABEL_RING - _CLOCK_LABEL_DISTANCE * label
    r_rim = r_ticks + _CLOCK_RIM_GAP
    crown_top = center.y - r_rim - _CLOCK_CROWN_LIFT
    canvas.add(
        Rect(Pt(center.x - 5, crown_top), 10, 9, BODY, radius=1.5),
        Line(Pt(center.x, center.y - r_rim - _CLOCK_STEM), Pt(center.x, center.y - r_rim), OUTLINE),
        Circle(center, r_rim, BODY.with_(width=1.2)),
    )
    axis = ArcAxis(center, r_ticks, CLOCK_START, CLOCK_END)
    canvas.extend(
        scale_marks(
            axis,
            _ticks(model, canvas.medium),
            # Ticks point inward on a closed face.
            major_length=-7,
            minor_length=-4,
            label_distance=_CLOCK_LABEL_DISTANCE * label,
            label_shift=_CLOCK_LABEL_SHIFT * label,
            label_size=label,
            skip=(0,),
        )
    )
    canvas.add(
        _unit(Pt(center.x, center.y + _CLOCK_UNIT_DROP), model, label),
        Line(
            center,
            polar(center, r_ticks - _CLOCK_NEEDLE_GAP, axis.angle(_value_fraction(model))),
            Style(stroke=BLACK, width=1.3),
        ),
        Circle(center, 3, SOLID),
    )


# --- vernier: caliper ---------------------------------------------------


def _build_caliper(model: InstrumentSpec, canvas: Canvas) -> None:
    """A vernier caliper: the bar with its scale, the sliding frame with the
    vernier under it, jaws pointing down and a hatched part between them.

    Vernier mark i sits at `value + i*step*(v-1)/v`, so for a reading of
    `n*step + k*(step/v)` exactly mark k lines up with a bar tick — the
    classic reading by coincidence. The precision is not printed: the student
    derives it from the number of vernier divisions.

    The bar carries two rows inside it — the numbers along its lower edge and
    the unit above them — so its top edge is set by what it has to hold. It
    grows upwards on purpose: everything below the lower edge (the jaws, the
    sliding frame, the vernier) is measured from that edge and stays put.
    """
    left, right = 14.0, 206.0
    bar_bottom = 40.0
    frame_bottom, jaw_bottom = 58.0, 78.0
    divisions = model.vernier_divisions
    label, micro = canvas.medium.label, canvas.medium.micro
    unit_baseline = bar_bottom - (_CALIPER_LABEL_DISTANCE + _CALIPER_UNIT_ROW) * label
    bar_top = unit_baseline - _CALIPER_UNIT_LIFT * label
    value = model.value if model.value is not None else model.min

    def at(quantity: float) -> float:
        return left + (quantity - model.min) / (model.max - model.min) * (right - left)

    x_value = at(value)
    canvas.add(
        Rect(Pt(2, bar_top), 216, bar_bottom - bar_top, BODY),
        # Fixed jaw: its measuring face is at the scale zero.
        Rect(Pt(left - 6, bar_bottom), 6, jaw_bottom - bar_bottom, BODY),
    )
    axis = LinearAxis(Pt(left, bar_bottom), Pt(right, bar_bottom), Pt(0, -1))
    canvas.extend(
        scale_marks(
            axis,
            _ticks(model, canvas.medium),
            major_length=7,
            minor_length=4.5,
            label_distance=_CALIPER_LABEL_DISTANCE * label,
            label_size=label,
        )
    )
    canvas.add(_unit(Pt(right, unit_baseline), model, label, anchor="end"))

    frame_width = at(value + (divisions - 1) * model.step) - x_value + 8
    canvas.add(
        Rect(Pt(x_value, bar_bottom), frame_width, frame_bottom - bar_bottom, BODY),
        # Sliding jaw: measuring face on its left.
        Rect(Pt(x_value, bar_bottom), 6, jaw_bottom - bar_bottom, BODY),
    )
    for i in range(divisions + 1):
        x = at(value + i * model.step * (divisions - 1) / divisions)
        marked = i in (0, divisions // 2, divisions)
        canvas.add(
            Line(
                Pt(x, bar_bottom),
                Pt(x, bar_bottom + (6.0 if marked else 4.0)),
                LINE if marked else THIN,
            )
        )
        if marked:
            canvas.add(Text(Pt(x, bar_bottom + _VERNIER_INDEX_DROP * micro), str(i), micro))
    if model.value is not None and model.value > model.min:
        canvas.add(Rect(Pt(left, 60), x_value - left, 14, BODY))
        canvas.extend(hatch(BBox(left, 60, x_value, 74)))


# --- balance: beam balance with weights ---------------------------------


def _build_balance(model: InstrumentSpec, canvas: Canvas) -> None:
    """A beam balance: stand on a base, a level beam on its pivot, two pans
    on cords; the hatched body (`value`) on the left, the weights on the
    right, drawn largest first.

    It is always drawn **balanced**, with the pointer on its mark: the
    picture states the problem rather than simulating it, and whether the
    masses actually agree is the business of the problem text.
    """
    cx, beam_y = 85.0, 28.0
    left, right = cx - 58.0, cx + 58.0
    pan_y = beam_y + 30.0
    canvas.add(
        Rect(Pt(cx - 26, 74), 52, 5, BODY),
        Line(Pt(cx, 74), Pt(cx, beam_y), HEAVY),
        # Pointer and its index mark.
        Line(Pt(cx - 4, 52), Pt(cx + 4, 52), THIN),
        Line(Pt(left, beam_y), Pt(right, beam_y), Style(stroke=BLACK, width=1.8)),
        Line(Pt(cx, beam_y), Pt(cx, 50), LINE),
        Circle(Pt(cx, beam_y), 2.5, SOLID),
    )
    for end in (left, right):
        canvas.add(
            Line(Pt(end, beam_y), Pt(end - 20, pan_y), Style(stroke=BLACK, width=0.7)),
            Line(Pt(end, beam_y), Pt(end + 20, pan_y), Style(stroke=BLACK, width=0.7)),
            Line(Pt(end - 20, pan_y), Pt(end + 20, pan_y), OUTLINE),
        )
    if model.value is not None:
        canvas.add(Rect(Pt(left - 11, pan_y - 13), 22, 13, BODY))
        canvas.extend(hatch(BBox(left - 11, pan_y - 13, left + 11, pan_y)))
    if model.weights:
        canvas.extend(_weights(model.weights, right, pan_y, canvas.medium.micro))


def _weights(
    weights: list[float], center_x: float, pan_y: float, micro: float
) -> list[Node]:
    """Weights on the pan: heaviest first, height proportional to mass, a
    small knob on top and the mass written above.

    Two weights stand a body's width apart unless their masses are written
    wider than that, in which case they stand as far apart as the writing —
    the weights are all one size but «100» is not the width of «5», and on a
    board the numbers outgrow the bodies they name.
    """
    ordered = sorted(weights, reverse=True)
    biggest = ordered[0]
    width, gap = 8.0, 2.0
    widths = [text_width(num(weight), micro) for weight in ordered]
    pitches = [
        max(width + gap, (widths[i] + widths[i + 1]) / 2 + _WEIGHT_LABEL_AIR * micro)
        for i in range(len(ordered) - 1)
    ]
    x = center_x - (width + sum(pitches)) / 2
    nodes: list[Node] = []
    for index, weight in enumerate(ordered):
        height = 6.0 + 8.0 * weight / biggest
        top = pan_y - height
        nodes.append(Rect(Pt(x, top), width, height, BODY))
        nodes.append(Rect(Pt(x + width / 2 - 1.5, top - 2), 3, 2, SOLID))
        nodes.append(
            Text(Pt(x + width / 2, top - _WEIGHT_LABEL_LIFT * micro), num(weight), micro)
        )
        if index < len(pitches):
            x += pitches[index]
    return nodes


# --- digital: multimeter, digital scale, digital stopwatch --------------


def _build_digital(model: InstrumentSpec, canvas: Canvas) -> None:
    """A digital instrument: body with a display. The reading is printed to
    the number of decimals of `step`, which here means the **resolution** —
    the unit of the last digit: 12.47 at a step of 0.01. The measuring range
    is set small under the display."""
    canvas.add(
        Rect(Pt(1.5, 1.5), 147, 61, BODY, radius=5),
        Rect(Pt(10, 10), 130, 28, BODY),
    )
    # Exact decimal representation rather than `num`: that one drops anything
    # finer than hundredths, so a step of 0.001 would print zero decimals.
    exponent = Decimal(str(model.step)).normalize().as_tuple().exponent
    decimals = max(0, -int(exponent))
    value = model.value if model.value is not None else 0
    canvas.add(
        Text(
            Pt(116, 31.5),
            fixed(value, decimals),
            canvas.medium.display,
            "end",
            Style(fill=BLACK, font_weight="bold", letter_spacing=1),
        ),
        _unit(Pt(136, 31.5), model, canvas.medium.caption),
        Text(
            Pt(10, 55),
            f"{num(model.min)}…{num(model.max)} {model.unit}",
            canvas.medium.label,
            "start",
        ),
    )


_BUILDERS: dict[str, Callable[[InstrumentSpec, Canvas], None]] = {
    "strip": _build_ruler,
    "column": lambda model, canvas: _COLUMN_BUILDERS[model.kind](model, canvas),
    "dial": _build_dial,
    "clock": _build_stopwatch,
    "vernier": _build_caliper,
    "balance": _build_balance,
    "digital": _build_digital,
}

_COLUMN_BUILDERS: dict[str, Callable[[InstrumentSpec, Canvas], None]] = {
    "cylinder": _build_cylinder,
    "thermometer": _build_thermometer,
    "dynamometer": _build_dynamometer,
}
