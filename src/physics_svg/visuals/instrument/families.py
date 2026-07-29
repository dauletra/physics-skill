"""Instrument kinds and the scale geometry families they belong to.

Fifteen kinds share seven geometries. A new instrument whose scale looks like
one that already exists is a line in `FAMILIES` plus a body-drawing branch —
not a new model and not a new set of limits.

The readability limits live here, next to the geometry they constrain, and
not in the spec: how many ticks fit before they merge is a property of the
drawing, and the spec merely has to respect it.
"""

from __future__ import annotations

from typing import Literal

Kind = Literal[
    "ruler", "cylinder", "thermometer", "dynamometer",
    "ammeter", "voltmeter", "manometer", "scale_dial", "speedometer",
    "stopwatch", "caliper", "balance",
    "multimeter", "digital_scale", "digital_stopwatch",
]

Family = Literal["strip", "column", "dial", "clock", "vernier", "balance", "digital"]

FAMILIES: dict[str, Family] = {
    "ruler": "strip",
    "cylinder": "column",
    "thermometer": "column",
    "dynamometer": "column",
    "ammeter": "dial",
    "voltmeter": "dial",
    "manometer": "dial",
    "scale_dial": "dial",
    "speedometer": "dial",
    "stopwatch": "clock",
    "caliper": "vernier",
    "balance": "balance",
    "multimeter": "digital",
    "digital_scale": "digital",
    "digital_stopwatch": "digital",
}

#: Ticks packed tighter than this merge at the size the family is drawn. A
#: ruler tolerates millimetre density; a column or a 120-degree arc does not,
#: and a full stopwatch circle fits more than an arc. On a caliper the limit
#: protects the vernier: the bar shows a fragment of the scale (usually
#: 0..40 mm), or the vernier marks run together. Balances and digital
#: displays have no ticks, so their limit is only technical — `step` there
#: means the smallest weight and the display resolution respectively.
MAX_DIVISIONS: dict[str, int] = {
    "strip": 150, "column": 60, "dial": 60, "clock": 150,
    "vernier": 40, "balance": 10**6, "digital": 10**6,
}

#: How many numbered ticks stay readable. A ruler traditionally carries more
#: numbers (every centimetre) than an arc or a column; a full stopwatch face
#: takes up to twelve, like a clock. Families absent from this table have no
#: ticks at all, which is what makes `label_step` an error on them.
MAX_LABELS: dict[str, int] = {"strip": 16, "column": 8, "dial": 8, "clock": 12, "vernier": 6}

#: A dual-range instrument prints two rows of numbers on one arc, so it is
#: thinned harder — exactly as a real 0-3 A meter is numbered 0, 1, 2, 3.
DUAL_SCALE_MAX_LABELS = 5

#: Accuracy classes per GOST 8.401 — a closed list. An arbitrary number is an
#: error rather than "some class": the reduced error a student computes
#: (delta = class x range / 100) is only defined for these.
ACCURACY_CLASSES = (0.05, 0.1, 0.2, 0.5, 1.0, 1.5, 2.5, 4.0)

#: Instruments with terminals — the only ones where multiple ranges mean
#: anything.
ELECTRIC_KINDS = ("ammeter", "voltmeter")


def family_of(kind: str) -> str:
    return FAMILIES[kind]


def has_ticks(kind: str) -> bool:
    return FAMILIES[kind] in MAX_LABELS
