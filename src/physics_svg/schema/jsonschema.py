"""JSON Schema emission from the same annotations the validator reads.

The published schema is what gives editor autocomplete to anyone forking the
project, and what a dev-only test uses to check our kernel against an
independent implementation: the same fixtures are validated both by
`schema.parse` and by a third-party JSON Schema library, so a divergence
between what we accept and what we document shows up as a test failure
rather than as a surprised contributor.

Draft 2020-12.
"""

from __future__ import annotations

from typing import Any, Literal, get_args, get_origin

from physics_svg.schema.kernel import (
    UNION_ORIGINS,
    Constraints,
    FieldMeta,
    is_spec,
    spec_meta,
)

SCHEMA_DIALECT = "https://json-schema.org/draft/2020-12/schema"


def emit_schema(roots: dict[str, Any], title: str = "") -> dict[str, Any]:
    """Schema for one or more root annotations.

    `roots` maps a name (`"document"`, `"block"`, `"visual"`) to the
    annotation describing it; every spec reachable from them lands in
    `$defs`, so the document and its blocks share one set of definitions.
    """
    defs: dict[str, Any] = {}
    schema: dict[str, Any] = {"$schema": SCHEMA_DIALECT}
    if title:
        schema["title"] = title
    if len(roots) == 1:
        schema.update(_schema_for(next(iter(roots.values())), defs))
    else:
        for name, annotation in roots.items():
            schema[name] = _schema_for(annotation, defs)
    if defs:
        schema["$defs"] = dict(sorted(defs.items()))
    return schema


def _schema_for(annotation: Any, defs: dict[str, Any]) -> dict[str, Any]:
    if is_spec(annotation):
        return {"$ref": f"#/$defs/{_register(annotation, defs)}"}

    origin = get_origin(annotation)
    if origin is Literal:
        return _literal_schema(get_args(annotation))
    if origin in UNION_ORIGINS:
        return _union_schema(annotation, defs)
    if origin is list:
        args = get_args(annotation)
        return {"type": "array", "items": _schema_for(args[0], defs)} if args else {"type": "array"}
    if origin is tuple:
        return _tuple_schema(annotation, defs)
    if origin is dict:
        return {
            "type": "object",
            "additionalProperties": _schema_for(get_args(annotation)[1], defs),
        }
    return {
        str: {"type": "string"},
        bool: {"type": "boolean"},
        int: {"type": "integer"},
        float: {"type": "number"},
    }[annotation]


def _register(cls: type, defs: dict[str, Any]) -> str:
    name = cls.__name__
    if name in defs:
        return name
    defs[name] = {}  # placeholder first: specs may reference each other
    meta = spec_meta(cls)
    properties: dict[str, Any] = {}
    required: list[str] = []
    for field_name, fmeta in meta.fields.items():
        properties[field_name] = _field_schema(fmeta, defs)
        if fmeta.required:
            required.append(field_name)
    definition: dict[str, Any] = {
        "type": "object",
        "properties": properties,
        "additionalProperties": False,
    }
    if required:
        definition["required"] = required
    doc = (cls.__doc__ or "").strip()
    if doc:
        definition["description"] = doc
    defs[name] = definition
    return name


def _field_schema(fmeta: FieldMeta, defs: dict[str, Any]) -> dict[str, Any]:
    schema = dict(_schema_for(fmeta.annotation, defs))
    keywords = _constraint_keywords(fmeta.constraints)
    if "$ref" in schema and keywords:
        # A `$ref` beside other keywords is legal in 2020-12 but confuses some
        # editors; wrapping keeps autocomplete working everywhere.
        return {"allOf": [schema], **keywords}
    schema.update(keywords)
    return schema


def _constraint_keywords(constraints: Constraints) -> dict[str, Any]:
    keywords: dict[str, Any] = {}
    if constraints.doc:
        keywords["description"] = constraints.doc
    if constraints.gt is not None:
        keywords["exclusiveMinimum"] = constraints.gt
    if constraints.ge is not None:
        keywords["minimum"] = constraints.ge
    if constraints.lt is not None:
        keywords["exclusiveMaximum"] = constraints.lt
    if constraints.le is not None:
        keywords["maximum"] = constraints.le
    if constraints.min_items is not None:
        keywords["minItems"] = constraints.min_items
    if constraints.max_items is not None:
        keywords["maxItems"] = constraints.max_items
    if constraints.min_length is not None:
        keywords["minLength"] = constraints.min_length
    if constraints.max_length is not None:
        keywords["maxLength"] = constraints.max_length
    return keywords


def _literal_schema(values: tuple[Any, ...]) -> dict[str, Any]:
    if len(values) == 1:
        return {"const": values[0]}
    return {"enum": list(values)}


def _union_schema(annotation: Any, defs: dict[str, Any]) -> dict[str, Any]:
    args = get_args(annotation)
    members = [a for a in args if a is not type(None)]
    nullable = len(members) != len(args)

    if {a for a in members} == {int, float}:
        schema: dict[str, Any] = {"type": "number"}
    elif len(members) == 1:
        schema = _schema_for(members[0], defs)
    else:
        schema = {"oneOf": [_schema_for(member, defs) for member in members]}
        if all(is_spec(member) for member in members):
            # Not a validation keyword, but editors and generators use it to
            # pick the right variant from `type` instead of trying all.
            schema["discriminator"] = {"propertyName": "type"}
    if nullable:
        return {"anyOf": [schema, {"type": "null"}]}
    return schema


def _tuple_schema(annotation: Any, defs: dict[str, Any]) -> dict[str, Any]:
    args = get_args(annotation)
    if len(args) == 2 and args[1] is Ellipsis:
        return {"type": "array", "items": _schema_for(args[0], defs)}
    return {
        "type": "array",
        "prefixItems": [_schema_for(arg, defs) for arg in args],
        "minItems": len(args),
        "maxItems": len(args),
    }
