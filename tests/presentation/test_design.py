"""The design system of the player, in the parts Python can check.

Whether a slide *looks* right is decided by eyes (`tools/slide_sheet.py`,
`evals/presentation.md`). What the suite can hold is the discipline the
system rests on, and it is exactly the discipline that erodes first: a size
typed straight into a rule, a grey nudged one step lighter, a scale step
that stops being a scale step.

The numbers here are not decoration. Contrast norms come from WCAG 2.1; the
reading threshold comes from ISO 9241-303 by way of `docs/slide-design.md`
§2 — with the frame 16:9 and the back row of a classroom seven to eight
metres away, 1cqh is about 4.6 angular minutes, and comfortable reading
starts at 20.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

import physics_svg.presentation.emit as emit

PLAYER = Path(emit.__file__).parent / "player" / "player.html"

#: Class-facing text must not go below this; `--t-xs` is chrome the teacher
#: reads from a metre away and is exempt.
READABLE_CQH = 3.6
#: The step of the modular scale.
RATIO = 1.25


def style() -> str:
    css = PLAYER.read_text(encoding="utf-8").split("<style>", 1)[1].split("</style>", 1)[0]
    return re.sub(r"/\*.*?\*/", "", css, flags=re.S)


def declarations() -> list[str]:
    """Ordinary declarations — everything that is not defining a token."""
    parts = (part.strip() for part in re.split(r"[;{}]", style()))
    return [part for part in parts if part and not part.startswith("--")]


def tokens(selector: str) -> dict[str, str]:
    """The custom properties one rule declares."""
    block = re.search(re.escape(selector) + r"\s*\{(.*?)\n  \}", style(), re.S)
    assert block is not None, f"в плеере нет блока {selector}"
    return dict(re.findall(r"--([\w-]+):\s*([^;]+);", block.group(1)))


def cqh(value: str) -> float:
    found = re.fullmatch(r"([\d.]+)cqh", value.strip())
    assert found is not None, f"{value!r} — не размер в cqh"
    return float(found.group(1))


def luminance(hex_colour: str) -> float:
    raw = hex_colour.strip().lstrip("#")
    if len(raw) == 3:
        raw = "".join(char * 2 for char in raw)
    channels = []
    for index in (0, 2, 4):
        part = int(raw[index : index + 2], 16) / 255
        channels.append(part / 12.92 if part <= 0.04045 else ((part + 0.055) / 1.055) ** 2.4)
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def contrast(front: str, back: str) -> float:
    light, dark = sorted((luminance(front), luminance(back)), reverse=True)
    return (light + 0.05) / (dark + 0.05)


class TestOnlyTokens:
    """Размеры и цвета живут в одном месте — иначе системы нет.

    Правило проверяемое и потому живучее: цвет и размер шрифта попадают в
    плеер только как значение токена. Тогда новый вид слайда собирается из
    готовых величин, а не заводит двенадцатый оттенок серого.
    """

    def test_no_colour_outside_a_token(self) -> None:
        loose = [line for line in declarations() if re.search(r"#[0-9a-fA-F]{3,8}\b", line)]
        assert not loose, f"цвет мимо токена: {loose}"

    def test_no_size_outside_a_token(self) -> None:
        loose = [line for line in declarations() if re.search(r"(?<![\w-])[\d.]+cqh", line)]
        assert not loose, f"размер мимо токена: {loose}"

    def test_every_font_size_is_a_scale_step(self) -> None:
        sizes = [line for line in declarations() if line.startswith("font-size")]
        assert sizes, "в плеере не осталось ни одного font-size — что-то не так с разбором"
        loose = [line for line in sizes if "var(--t-" not in line]
        assert not loose, f"кегль мимо шкалы: {loose}"


class TestScale:
    """Шкала — это шкала, а не семь произвольных чисел."""

    STEPS = ["t-xs", "t-s", "t-m", "t-l", "t-xl", "t-xxl", "t-hero"]

    def test_steps_follow_the_ratio(self) -> None:
        sizes = [cqh(tokens(":root")[name]) for name in self.STEPS]
        for smaller, larger in zip(sizes, sizes[1:]):
            assert larger / smaller == pytest.approx(RATIO, abs=0.02), (
                f"ступень {smaller}→{larger} выпала из шага {RATIO}"
            )

    def test_body_text_clears_the_comfort_threshold(self) -> None:
        # 4.4cqh ≈ 24 pt ≈ 20 угловых минут с последней парты (§2).
        assert cqh(tokens(":root")["t-m"]) >= 4.4

    def test_nothing_class_facing_is_smaller_than_the_floor(self) -> None:
        for name in self.STEPS[1:]:  # t-xs — служебное, его читают с метра
            assert cqh(tokens(":root")[name]) >= READABLE_CQH

    def test_the_dense_step_shifts_the_scale_and_stops(self) -> None:
        """Уплотнение — одна ступень вниз, а не свободная подгонка.

        И именно ступень **шкалы**: иначе иерархия заголовка и текста
        схлопнется ровно на том слайде, где текста больше всего.
        """
        root = tokens(":root")
        dense = tokens(".slide[data-dense]")
        order = [name for name in self.STEPS if name in dense]
        assert order, "у уплотнения не осталось ни одной ступени"
        for name in order:
            below = self.STEPS[self.STEPS.index(name) - 1]
            assert cqh(dense[name]) == pytest.approx(cqh(root[below]), abs=0.01), (
                f"{name} при уплотнении не встал на ступень {below}"
            )


class TestContrast:
    """Пары, на которых держатся обещания §5 — с их нормами.

    Проверяются те, что несут текст или управление. Декоративные линейки
    (`--line`, `--accent-line`) нормы не имеют: их видно толщиной, а не
    контрастом, и требовать от них 3:1 значило бы сделать рамку чернее
    текста рядом.
    """

    #: front, back, норма, за что отвечает
    PAIRS = [
        ("ink", "paper", 7.0, "основной текст"),
        ("ink-soft", "paper", 4.5, "расшифровки и второй план"),
        ("ink-faint", "paper", 4.5, "счётчик и служебное"),
        ("accent", "paper", 4.5, "кикер, номер задачи, линейка ячейки"),
        ("accent", "accent-soft", 4.5, "текст на плашке ответа"),
        ("paper", "panel", 7.0, "разделитель этапа и панель этапов"),
    ]

    @pytest.mark.parametrize("front, back, norm, what", PAIRS)
    def test_pair_meets_its_norm(self, front: str, back: str, norm: float, what: str) -> None:
        palette = tokens(":root")
        found = contrast(palette[front], palette[back])
        assert found >= norm, f"{what}: {front} на {back} даёт {found:.2f}:1, нужно {norm}:1"

    def test_the_dark_remote_stays_readable(self) -> None:
        """Пульт переключается под тёмным слайдом — и там у него своя пара."""
        dark = tokens("#stage:has(.slide-section.active)")
        found = contrast(dark["chrome-ink"], dark["chrome"])
        assert found >= 4.5, f"пульт на тёмном слайде даёт {found:.2f}:1"
