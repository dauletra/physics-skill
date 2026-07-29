"""A measuring instrument with a scale.

The spec describes what a problem needs to state: the range, the division
value, the reading. It deliberately does **not** describe the drawing — how
many ticks get numbers, where the needle pivots, how wide the body is are
all decisions of the renderer.

The metrology fields (`accuracy_class`, `ranges`, `vernier`, `weights`) exist
because they carry the physics of measurement-error problems, not because
they change the picture: each of them is something a student computes with.
"""

from __future__ import annotations

from typing import Literal, Optional

from physics_svg.elements import division_count
from physics_svg.schema import Invalid, Number, field, spec
from physics_svg.visuals.instrument.families import (
    ACCURACY_CLASSES,
    DUAL_SCALE_MAX_LABELS,
    ELECTRIC_KINDS,
    MAX_DIVISIONS,
    MAX_LABELS,
    Kind,
    family_of,
    has_ticks,
)

#: Tolerance for "is this value a whole multiple of that one" on data that
#: arrived as JSON floats.
_EPS = 1e-6


@spec
class InstrumentSpec:
    """Измерительный прибор со шкалой."""

    type: Literal["instrument"]
    kind: Kind = field(doc="Вид прибора: линейка, мензурка, амперметр…")
    unit: str = field(min_length=1, doc="Единица измерения: «см», «А», «°C»")
    min: Number = field(doc="Начало шкалы")
    max: Number = field(doc="Предел измерения")
    step: Number = field(
        gt=0,
        doc="Цена деления — всегда явно: это данное задачи, а не производная рисунка",
    )
    id: Optional[str] = None
    label_step: Optional[Number] = field(
        default=None,
        gt=0,
        doc="Шаг подписанных штрихов в единицах величины; не задан — рендерер "
        "прореживает подписи сам",
    )
    value: Optional[Number] = field(default=None, doc="Показание прибора")
    caption: Optional[str] = field(default=None, doc="Подпись под рисунком")
    accuracy_class: Optional[Number] = field(
        default=None, doc="Класс точности по ГОСТ 8.401 — печатается на шкале стрелочного прибора"
    )
    ranges: Optional[list[Number]] = field(
        default=None,
        min_items=2,
        max_items=2,
        doc="Два предела двухпредельного прибора: на одной дуге две шкалы",
    )
    vernier: Optional[Literal[10, 20]] = field(
        default=None, doc="Число делений нониуса штангенциркуля: 10 → 0,1 мм; 20 → 0,05 мм"
    )
    weights: Optional[list[Number]] = field(
        default=None,
        min_items=1,
        max_items=4,
        doc="Гири на правой чашке рычажных весов, повторы разрешены",
    )

    @property
    def family(self) -> str:
        return family_of(self.kind)

    @property
    def divisions(self) -> int:
        return division_count(self.min, self.max, self.step)

    @property
    def max_labels(self) -> int:
        if self.ranges:
            return DUAL_SCALE_MAX_LABELS
        return MAX_LABELS[self.family]

    @property
    def vernier_divisions(self) -> int:
        return self.vernier or 10

    def check(self) -> None:
        self._check_scale()
        self._check_labels()
        self._check_reading()
        self._check_metrology()
        self._check_caliper()
        self._check_balance()

    # --- the scale itself ---

    def _check_scale(self) -> None:
        if not self.min < self.max:
            raise Invalid(
                f"начало шкалы должно быть меньше предела, получено [{self.min}, {self.max}]",
                field="min",
            )
        exact = (self.max - self.min) / self.step
        if abs(exact - round(exact)) > _EPS * max(exact, 1):
            raise Invalid(
                f"цена деления {self.step} должна укладываться в шкалу нацело: "
                f"(max - min) / step = {exact}",
                field="step",
            )
        limit = MAX_DIVISIONS[self.family]
        if not 2 <= self.divisions <= limit:
            raise Invalid(
                f"у прибора '{self.kind}' на шкале должно быть от 2 до {limit} делений, "
                f"получено {self.divisions}",
                field="step",
            )

    def _check_labels(self) -> None:
        if self.label_step is None:
            return
        if not has_ticks(self.kind):
            raise Invalid(
                f"'label_step' рисуется только на приборах со штриховой шкалой, "
                f"а не на '{self.kind}'",
                field="label_step",
            )
        ratio = self.label_step / self.step
        if abs(ratio - round(ratio)) > _EPS or round(ratio) < 1:
            raise Invalid(
                f"шаг подписей {self.label_step} должен быть кратен цене деления "
                f"{self.step}: подписи стоят на штрихах",
                field="label_step",
            )
        labels = self.divisions // round(ratio) + 1
        if labels > self.max_labels:
            raise Invalid(
                f"шаг подписей {self.label_step} даёт {labels} подписей — больше "
                f"читаемого предела {self.max_labels} для '{self.kind}'; возьми шаг крупнее",
                field="label_step",
            )

    def _check_reading(self) -> None:
        # Whether the reading is a multiple of the division value is
        # deliberately NOT checked: a needle between ticks is the whole point
        # of reading-error problems.
        if self.value is not None and not (self.min <= self.value <= self.max):
            raise Invalid(
                f"показание {self.value} вне шкалы [{self.min}, {self.max}]", field="value"
            )

    # --- metrology ---

    def _check_metrology(self) -> None:
        if self.family == "digital" and self.value is not None:
            # A display does not show "between ticks": the reading is always a
            # multiple of the resolution.
            offset = (self.value - self.min) / self.step
            if abs(offset - round(offset)) > _EPS:
                raise Invalid(
                    f"показание цифрового табло должно быть кратно дискретности "
                    f"{self.step}, получено {self.value}",
                    field="value",
                )
        if self.accuracy_class is not None:
            if self.family != "dial":
                raise Invalid(
                    f"класс точности рисуется только на стрелочных приборах, "
                    f"а не на '{self.kind}'",
                    field="accuracy_class",
                )
            if not any(abs(self.accuracy_class - c) < 1e-9 for c in ACCURACY_CLASSES):
                raise Invalid(
                    f"класс точности должен быть одним из {list(ACCURACY_CLASSES)}, "
                    f"получено {self.accuracy_class}",
                    field="accuracy_class",
                )
        if self.ranges is not None:
            self._check_ranges(self.ranges)

    def _check_ranges(self, ranges: list[float]) -> None:
        if self.kind not in ELECTRIC_KINDS:
            raise Invalid(
                "двухпредельная шкала есть только у "
                f"{'/'.join(ELECTRIC_KINDS)}, а не у '{self.kind}'",
                field="ranges",
            )
        if any(r <= 0 for r in ranges):
            raise Invalid(f"пределы должны быть положительными, получено {ranges}", field="ranges")
        if sorted(set(ranges)) != list(ranges):
            raise Invalid(
                f"пределы должны строго возрастать, получено {ranges}", field="ranges"
            )
        # Both scales share one arc. A negative `min` is the scale running
        # past zero (as on a real J0407), and both rows of numbers continue
        # to the left of zero by the same rule.
        if self.min > 0:
            raise Invalid(
                f"двухпредельный прибор должен начинаться с нуля или ниже, получено {self.min}",
                field="min",
            )
        if abs(self.max - ranges[-1]) > 1e-9:
            raise Invalid(
                f"'max' должен совпадать с большим пределом {ranges[-1]}: min/max/step "
                f"описывают внешнюю шкалу, получено {self.max}",
                field="max",
            )
        inner_step = self.step * ranges[0] / ranges[-1]
        if abs(inner_step * 100 - round(inner_step * 100)) > _EPS:
            raise Invalid(
                f"пределы {ranges} дают некруглую внутреннюю шкалу: её цена деления "
                f"вышла бы {inner_step}; подписи читаемы до сотых",
                field="ranges",
            )

    # --- kind-specific equipment ---

    def _check_caliper(self) -> None:
        if self.kind != "caliper":
            if self.vernier is not None:
                raise Invalid(
                    f"'vernier' есть только у штангенциркуля, а не у '{self.kind}'",
                    field="vernier",
                )
            return
        precision = self.step / self.vernier_divisions
        if self.value is None:
            return
        offset = (self.value - self.min) / precision
        # Without this the coinciding vernier mark is undefined and the
        # drawing becomes ambiguous.
        if abs(offset - round(offset)) > _EPS:
            raise Invalid(
                f"показание штангенциркуля должно быть кратно точности нониуса "
                f"{precision} (цена деления {self.step} / {self.vernier_divisions} делений), "
                f"получено {self.value}",
                field="value",
            )
        fits = self.max - (self.vernier_divisions - 1) * self.step
        if self.value > fits + 1e-9:
            raise Invalid(
                f"нониус должен помещаться на штанге: показание не больше {fits} "
                f"(max - {self.vernier_divisions - 1}*step), получено {self.value}",
                field="value",
            )

    def _check_balance(self) -> None:
        if self.kind != "balance":
            if self.weights is not None:
                raise Invalid(
                    f"'weights' есть только у рычажных весов, а не у '{self.kind}'",
                    field="weights",
                )
            return
        if self.min != 0:
            raise Invalid(f"шкала весов начинается с нуля, получено {self.min}", field="min")
        if self.weights is None:
            return
        for i, weight in enumerate(self.weights):
            if weight <= 0:
                raise Invalid(
                    f"масса гири должна быть положительной, получено {weight} в weights[{i}]",
                    field="weights",
                )
            ratio = weight / self.step
            # `step` is the smallest weight of the set, so every weight is a
            # multiple of it — otherwise it is not the unit of the set.
            if abs(ratio - round(ratio)) > _EPS or weight < self.step - 1e-9:
                raise Invalid(
                    f"гиря {weight} (weights[{i}]) должна быть кратна наименьшей гире "
                    f"набора step = {self.step}",
                    field="weights",
                )
        total = sum(self.weights)
        if total > self.max + 1e-9:
            raise Invalid(
                f"сумма гирь {total} больше предела взвешивания {self.max}", field="weights"
            )
