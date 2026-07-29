"""Declarative validation on plain dataclasses and type annotations.

One model layer serves three purposes at once: it is the typed tree the
renderers work with, the validator that rejects a malformed draft, and the
source of the published JSON Schema. There is no second representation and
no code generation — the annotations *are* the schema.

Writing a spec:

    @spec
    class Series:
        points: list[Point] = field(min_items=1, doc="Точки серии")
        style: Literal["solid", "dashed", "dotted"] = "solid"

        def check(self) -> None:
            if self.style == "dotted" and len(self.points) < 3:
                raise Invalid("пунктиру нужно хотя бы три точки", field="points")

Rules the kernel enforces for every spec, so individual models never repeat
them: unknown keys are errors (with a "did you mean" hint), missing required
fields are errors, closed vocabularies are `Literal`, and **all** problems
in a document are reported together rather than one per run.

Supported annotations: `str`, `bool`, `int`, `float`, `Number`, `Literal`,
`Optional[X]`, `list[X]`, `dict[str, X]`, fixed and variadic tuples, nested
specs, and unions of specs discriminated by their `type` literal.
"""

from __future__ import annotations

import dataclasses
import difflib
from dataclasses import dataclass
from typing import (
    Any,
    Literal,
    TypeVar,
    Union,
    get_args,
    get_origin,
    get_type_hints,
)

from physics_svg.schema.errors import Invalid, Path, Problem, SchemaError

try:  # Python 3.10+ writes unions as `X | Y`, whose origin is UnionType
    from types import UnionType

    UNION_ORIGINS: tuple[object, ...] = (Union, UnionType)
except ImportError:  # pragma: no cover - 3.9 and older
    UNION_ORIGINS = (Union,)

#: JSON numbers: authors write `3` and `3.5` interchangeably and both are
#: valid physics data, so the library has one numeric annotation.
Number = Union[int, float]

#: Marker for "this value failed; a problem is already recorded". Distinct
#: from `None`, which is a legitimate value for optional fields.
_FAIL: Any = object()

#: Field metadata key holding our constraints.
_META_KEY = "physics_svg.spec"

T = TypeVar("T")


# --- declaring specs ----------------------------------------------------


@dataclass(frozen=True)
class Constraints:
    doc: str = ""
    gt: float | None = None
    ge: float | None = None
    lt: float | None = None
    le: float | None = None
    min_items: int | None = None
    max_items: int | None = None
    min_length: int | None = None
    max_length: int | None = None


def field(
    *,
    default: Any = dataclasses.MISSING,
    default_factory: Any = dataclasses.MISSING,
    doc: str = "",
    gt: float | None = None,
    ge: float | None = None,
    lt: float | None = None,
    le: float | None = None,
    min_items: int | None = None,
    max_items: int | None = None,
    min_length: int | None = None,
    max_length: int | None = None,
) -> Any:
    """Declare a spec field with its constraints and documentation.

    `doc` is not decoration: it is published in the JSON Schema and reused by
    the generated reference, so it should read as an instruction to the
    author, in Russian.
    """
    constraints = Constraints(
        doc=doc,
        gt=gt,
        ge=ge,
        lt=lt,
        le=le,
        min_items=min_items,
        max_items=max_items,
        min_length=min_length,
        max_length=max_length,
    )
    metadata = {_META_KEY: constraints}
    if default is not dataclasses.MISSING:
        return dataclasses.field(default=default, metadata=metadata)
    if default_factory is not dataclasses.MISSING:
        return dataclasses.field(default_factory=default_factory, metadata=metadata)
    return dataclasses.field(metadata=metadata)


def spec(cls: type[T]) -> type[T]:
    """Turn a class into an immutable, validatable spec."""
    frozen = dataclasses.dataclass(frozen=True)(cls)
    setattr(frozen, "__is_spec__", True)
    return frozen


def is_spec(obj: Any) -> bool:
    return isinstance(obj, type) and getattr(obj, "__is_spec__", False)


@dataclass(frozen=True)
class FieldMeta:
    name: str
    annotation: Any
    required: bool
    constraints: Constraints


@dataclass(frozen=True)
class SpecMeta:
    cls: type
    fields: dict[str, FieldMeta]

    @property
    def tag(self) -> str | None:
        """Value of the `type` discriminator, if the spec has one."""
        meta = self.fields.get("type")
        if meta is None or get_origin(meta.annotation) is not Literal:
            return None
        args = get_args(meta.annotation)
        return str(args[0]) if len(args) == 1 else None


_META_CACHE: dict[type, SpecMeta] = {}


def spec_meta(cls: type) -> SpecMeta:
    cached = _META_CACHE.get(cls)
    if cached is not None:
        return cached
    hints = get_type_hints(cls)
    fields: dict[str, FieldMeta] = {}
    for f in dataclasses.fields(cls):
        constraints = f.metadata.get(_META_KEY, Constraints())
        required = f.default is dataclasses.MISSING and f.default_factory is dataclasses.MISSING
        fields[f.name] = FieldMeta(f.name, hints[f.name], required, constraints)
    meta = SpecMeta(cls, fields)
    _META_CACHE[cls] = meta
    return meta


# --- parsing ------------------------------------------------------------


def parse(annotation: Any, data: object, *, name: str = "") -> Any:
    """Validate raw JSON data against a spec (or any supported annotation).

    Raises `SchemaError` listing every problem found, each with the path to
    the offending value.
    """
    problems: list[Problem] = []
    root = Path((name,)) if name else Path()
    value = _build(annotation, data, root, problems)
    if problems:
        raise SchemaError(problems)
    return value


def _build(annotation: Any, value: object, path: Path, problems: list[Problem]) -> Any:
    if is_spec(annotation):
        return _build_spec(annotation, value, path, problems)

    origin = get_origin(annotation)
    if origin is Literal:
        return _build_literal(annotation, value, path, problems)
    if origin in UNION_ORIGINS:
        return _build_union(annotation, value, path, problems)
    if origin in (list, tuple):
        return _build_sequence(annotation, origin, value, path, problems)
    if origin is dict:
        return _build_mapping(annotation, value, path, problems)
    if annotation in (str, bool, int, float):
        return _build_scalar(annotation, value, path, problems)

    raise TypeError(f"unsupported annotation in spec: {annotation!r}")


def _build_spec(cls: type, value: object, path: Path, problems: list[Problem]) -> Any:
    if not isinstance(value, dict):
        problems.append(Problem(path, f"ожидается объект, получено {_describe(value)}"))
        return _FAIL
    meta = spec_meta(cls)
    kwargs: dict[str, Any] = {}
    ok = True

    for name, fmeta in meta.fields.items():
        if name not in value:
            if fmeta.required:
                problems.append(Problem(path, f"отсутствует обязательное поле '{name}'"))
                ok = False
            continue
        built = _build(fmeta.annotation, value[name], path.child(name), problems)
        if built is _FAIL:
            ok = False
            continue
        if not _check_constraints(fmeta.constraints, built, path.child(name), problems):
            ok = False
            continue
        kwargs[name] = built

    for key in value:
        if key not in meta.fields:
            problems.append(Problem(path, _unknown_field(str(key), list(meta.fields))))
            ok = False

    if not ok:
        return _FAIL

    instance = cls(**kwargs)
    check = getattr(instance, "check", None)
    if callable(check):
        try:
            check()
        except Invalid as exc:
            location = path.child(exc.field) if exc.field else path
            problems.append(Problem(location, exc.message))
            return _FAIL
    return instance


def _build_literal(annotation: Any, value: object, path: Path, problems: list[Problem]) -> Any:
    allowed = get_args(annotation)
    if value in allowed and type(value) in {type(a) for a in allowed}:
        return value
    options = ", ".join(_literal_repr(a) for a in allowed)
    hint = ""
    if isinstance(value, str):
        close = difflib.get_close_matches(value, [str(a) for a in allowed], n=1, cutoff=0.6)
        if close:
            hint = f"; возможно, имелось в виду '{close[0]}'"
    problems.append(
        Problem(path, f"недопустимое значение {_value_repr(value)}; допустимы: {options}{hint}")
    )
    return _FAIL


def _build_union(annotation: Any, value: object, path: Path, problems: list[Problem]) -> Any:
    args = [a for a in get_args(annotation) if a is not type(None)]
    optional = len(args) != len(get_args(annotation))
    if value is None:
        if optional:
            return None
        problems.append(Problem(path, f"ожидается {_type_name(annotation)}, получено null"))
        return _FAIL

    if all(is_spec(a) for a in args):
        return _build_tagged_union(args, value, path, problems)

    # A plain scalar union (`Number`, `str | int`): the first member that
    # accepts the value wins, and only a single message is reported if none
    # does — inner attempts must not leak their own problems.
    for member in args:
        attempt: list[Problem] = []
        built = _build(member, value, path, attempt)
        if built is not _FAIL and not attempt:
            return built
    problems.append(
        Problem(path, f"ожидается {_type_name(annotation)}, получено {_describe(value)}")
    )
    return _FAIL


def _build_tagged_union(
    members: list[Any], value: object, path: Path, problems: list[Problem]
) -> Any:
    by_tag: dict[str, Any] = {}
    for candidate in members:
        candidate_tag = spec_meta(candidate).tag
        if candidate_tag is not None:
            by_tag[candidate_tag] = candidate
    if not isinstance(value, dict):
        problems.append(Problem(path, f"ожидается объект, получено {_describe(value)}"))
        return _FAIL
    tag = value.get("type")
    if tag is None:
        problems.append(Problem(path, "у блока нет поля 'type'"))
        return _FAIL
    member = by_tag.get(tag) if isinstance(tag, str) else None
    if member is None:
        known = ", ".join(sorted(by_tag))
        hint = ""
        if isinstance(tag, str):
            close = difflib.get_close_matches(tag, list(by_tag), n=1, cutoff=0.6)
            if close:
                hint = f"; возможно, имелось в виду '{close[0]}'"
        problems.append(
            Problem(path, f"неизвестный тип блока {_value_repr(tag)}; известны: {known}{hint}")
        )
        return _FAIL
    return _build_spec(member, value, path, problems)


def _build_sequence(
    annotation: Any, origin: Any, value: object, path: Path, problems: list[Problem]
) -> Any:
    if not isinstance(value, list):
        problems.append(Problem(path, f"ожидается список, получено {_describe(value)}"))
        return _FAIL
    args = get_args(annotation)

    if origin is tuple and not (len(args) == 2 and args[1] is Ellipsis):
        if len(value) != len(args):
            problems.append(
                Problem(path, f"ожидается список из {len(args)} элементов, получено {len(value)}")
            )
            return _FAIL
        item_annotations: list[Any] = list(args)
    else:
        item = args[0] if args else Any
        item_annotations = [item] * len(value)

    items = []
    ok = True
    for i, (item_annotation, raw) in enumerate(zip(item_annotations, value)):
        built = _build(item_annotation, raw, path.index(i), problems)
        if built is _FAIL:
            ok = False
        else:
            items.append(built)
    if not ok:
        return _FAIL
    return tuple(items) if origin is tuple else items


def _build_mapping(annotation: Any, value: object, path: Path, problems: list[Problem]) -> Any:
    if not isinstance(value, dict):
        problems.append(Problem(path, f"ожидается объект, получено {_describe(value)}"))
        return _FAIL
    _, value_annotation = get_args(annotation)
    result = {}
    ok = True
    for key, raw in value.items():
        if not isinstance(key, str):
            problems.append(Problem(path, f"ключ {_value_repr(key)} должен быть строкой"))
            ok = False
            continue
        built = _build(value_annotation, raw, path.child(key), problems)
        if built is _FAIL:
            ok = False
        else:
            result[key] = built
    return result if ok else _FAIL


def _build_scalar(annotation: Any, value: object, path: Path, problems: list[Problem]) -> Any:
    # `bool` is a subclass of `int` in Python but never a number in JSON data:
    # accepting `true` where a length is expected would be a silent disaster.
    if annotation is bool:
        if isinstance(value, bool):
            return value
    elif annotation is int:
        if isinstance(value, int) and not isinstance(value, bool):
            return value
    elif annotation is float:
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return float(value)
    elif annotation is str:
        if isinstance(value, str):
            return value
    problems.append(
        Problem(path, f"ожидается {_type_name(annotation)}, получено {_describe(value)}")
    )
    return _FAIL


def _check_constraints(
    constraints: Constraints, value: Any, path: Path, problems: list[Problem]
) -> bool:
    checks: list[tuple[bool, str]] = []
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if constraints.gt is not None:
            checks.append((value > constraints.gt, f"должно быть больше {constraints.gt}"))
        if constraints.ge is not None:
            checks.append((value >= constraints.ge, f"должно быть не меньше {constraints.ge}"))
        if constraints.lt is not None:
            checks.append((value < constraints.lt, f"должно быть меньше {constraints.lt}"))
        if constraints.le is not None:
            checks.append((value <= constraints.le, f"должно быть не больше {constraints.le}"))
    if isinstance(value, str):
        if constraints.min_length is not None:
            checks.append(
                (len(value) >= constraints.min_length, "строка не должна быть пустой")
                if constraints.min_length == 1
                else (
                    len(value) >= constraints.min_length,
                    f"длина строки должна быть не меньше {constraints.min_length}",
                )
            )
        if constraints.max_length is not None:
            checks.append(
                (
                    len(value) <= constraints.max_length,
                    f"длина строки должна быть не больше {constraints.max_length}",
                )
            )
    if isinstance(value, (list, tuple, dict)):
        if constraints.min_items is not None:
            checks.append(
                (
                    len(value) >= constraints.min_items,
                    f"нужно хотя бы {constraints.min_items} элемент(ов), получено {len(value)}",
                )
            )
        if constraints.max_items is not None:
            checks.append(
                (
                    len(value) <= constraints.max_items,
                    f"допустимо не больше {constraints.max_items} элемент(ов), "
                    f"получено {len(value)}",
                )
            )
    ok = True
    for passed, message in checks:
        if not passed:
            problems.append(Problem(path, message))
            ok = False
    return ok


# --- message helpers ----------------------------------------------------


def _unknown_field(key: str, known: list[str]) -> str:
    close = difflib.get_close_matches(key, known, n=1, cutoff=0.6)
    hint = f"; возможно, имелось в виду '{close[0]}'" if close else ""
    return f"неизвестное поле '{key}'{hint}"


def _describe(value: object) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true/false"
    if isinstance(value, (int, float)):
        return "число"
    if isinstance(value, str):
        return "строка"
    if isinstance(value, list):
        return "список"
    if isinstance(value, dict):
        return "объект"
    return type(value).__name__


def _type_name(annotation: Any) -> str:
    if annotation is str:
        return "строка"
    if annotation is bool:
        return "true/false"
    if annotation is int:
        return "целое число"
    if annotation is float:
        return "число"
    if is_spec(annotation):
        return "объект"
    origin = get_origin(annotation)
    if origin is Literal:
        return " или ".join(_literal_repr(a) for a in get_args(annotation))
    if origin in UNION_ORIGINS:
        args = [a for a in get_args(annotation) if a is not type(None)]
        if {a for a in args} == {int, float}:
            return "число"
        return " или ".join(_type_name(a) for a in args)
    if origin is list:
        return "список"
    if origin is tuple:
        return "список"
    if origin is dict:
        return "объект"
    return str(annotation)


def _literal_repr(value: object) -> str:
    return f"'{value}'" if isinstance(value, str) else str(value)


def _value_repr(value: object) -> str:
    return f"'{value}'" if isinstance(value, str) else _describe(value)


def build_registry(members: list[type]) -> dict[str, type]:
    """Map `type` tag -> spec class, for unions assembled at runtime."""
    registry: dict[str, type] = {}
    for member in members:
        tag = spec_meta(member).tag
        if tag is None:
            raise TypeError(f"{member.__name__} has no literal 'type' field")
        if tag in registry:
            raise TypeError(f"duplicate block type {tag!r}")
        registry[tag] = member
    return registry


__all__: list[str] = [
    "Constraints",
    "FieldMeta",
    "Invalid",
    "Number",
    "Path",
    "Problem",
    "SchemaError",
    "SpecMeta",
    "build_registry",
    "field",
    "is_spec",
    "parse",
    "spec",
    "spec_meta",
]
