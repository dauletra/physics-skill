"""Validation kernel: one declarative model layer, no second representation.

A spec class is the typed tree renderers consume, the validator that rejects
a malformed draft, and the source of the published JSON Schema. See
kernel.py for how to write one.
"""

from physics_svg.schema.errors import Invalid, Path, Problem, SchemaError
from physics_svg.schema.jsonschema import emit_schema
from physics_svg.schema.kernel import (
    Constraints,
    Deferred,
    FieldMeta,
    Number,
    SpecMeta,
    build_registry,
    field,
    is_spec,
    parse,
    spec,
    spec_meta,
)

__all__ = [
    "Constraints",
    "Deferred",
    "FieldMeta",
    "Invalid",
    "Number",
    "Path",
    "Problem",
    "SchemaError",
    "SpecMeta",
    "build_registry",
    "emit_schema",
    "field",
    "is_spec",
    "parse",
    "spec",
    "spec_meta",
]
