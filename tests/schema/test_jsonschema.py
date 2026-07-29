"""The published JSON Schema, and an independent check of the kernel.

The schema is what gives editor autocomplete to a forking contributor, so it
has to be a faithful description of what the kernel accepts. Rather than
trust that by inspection, the cross-check below runs the same fixtures
through our kernel and through a third-party JSON Schema implementation.

The two are not equivalent by construction: cross-field invariants (`check()`)
are not expressible in JSON Schema, so the kernel is legitimately *stricter*.
The property under test is therefore one-directional and exactly what a stale
schema would break: **anything the published schema rejects, the kernel
rejects too.**
"""

import pytest

from demo import Block, Graph
from physics_svg.schema import SchemaError, emit_schema, parse

jsonschema = pytest.importorskip("jsonschema")

VALID_GRAPH = {
    "type": "graph",
    "x_label": "t, с",
    "y_range": [0, 20],
    "series": [{"points": [{"x": 0, "y": 0}, {"x": 2, "y": 10}], "style": "dashed"}],
    "ticks": 5,
}

VALID_NOTE = {"type": "note", "body": "текст", "tags": {"тема": "кинематика"}}

#: Drafts that are wrong in a way JSON Schema can express.
INVALID_DRAFTS = [
    {"type": "graph"},                                        # missing fields
    {**VALID_GRAPH, "x_label": 5},                            # wrong scalar type
    {**VALID_GRAPH, "grid": "fien"},                          # outside the vocabulary
    {**VALID_GRAPH, "unknown": 1},                            # unknown field
    {**VALID_GRAPH, "y_range": [0]},                          # short tuple
    {**VALID_GRAPH, "ticks": 0},                              # constraint
    {**VALID_GRAPH, "ticks": 99},                             # constraint
    {**VALID_GRAPH, "x_label": ""},                           # empty string
    {**VALID_GRAPH, "series": [{"points": []}]},              # empty list
    {"type": "unknown-block"},                                # unknown tag
    {"type": "note", "body": "x", "tags": {"a": 1}},          # mapping value type
]


@pytest.fixture(scope="module")
def block_schema() -> dict:
    return emit_schema({"block": Block}, title="Демо-схема")


@pytest.fixture(scope="module")
def validator(block_schema: dict) -> object:
    jsonschema.Draft202012Validator.check_schema(block_schema)
    return jsonschema.Draft202012Validator(block_schema)


class TestShape:
    def test_definitions_are_collected_and_sorted(self, block_schema: dict) -> None:
        assert list(block_schema["$defs"]) == ["Graph", "Note", "Point", "Series"]

    def test_specs_are_closed(self, block_schema: dict) -> None:
        assert block_schema["$defs"]["Graph"]["additionalProperties"] is False

    def test_required_fields_are_listed(self, block_schema: dict) -> None:
        assert block_schema["$defs"]["Graph"]["required"] == ["type", "x_label", "y_range"]

    def test_union_carries_a_discriminator_for_editors(self, block_schema: dict) -> None:
        assert block_schema["discriminator"] == {"propertyName": "type"}
        assert len(block_schema["oneOf"]) == 2

    def test_field_docs_reach_the_schema(self, block_schema: dict) -> None:
        y_range = block_schema["$defs"]["Graph"]["properties"]["y_range"]
        assert y_range["description"].startswith("Диапазон")
        assert y_range["prefixItems"] and y_range["minItems"] == 2

    def test_class_docstrings_describe_the_definition(self, block_schema: dict) -> None:
        assert block_schema["$defs"]["Note"]["description"] == "Текстовая врезка."

    def test_constraints_become_keywords(self, block_schema: dict) -> None:
        ticks = block_schema["$defs"]["Graph"]["properties"]["ticks"]
        assert ticks["exclusiveMinimum"] == 0
        assert ticks["maximum"] == 20
        # Optional means the value may be sent explicitly as null.
        assert {"type": "null"} in ticks["anyOf"]

    def test_literals_become_enums(self, block_schema: dict) -> None:
        assert block_schema["$defs"]["Graph"]["properties"]["grid"]["enum"] == ["ticks", "fine"]
        assert block_schema["$defs"]["Graph"]["properties"]["type"]["const"] == "graph"

    def test_several_roots_share_one_set_of_definitions(self) -> None:
        schema = emit_schema({"block": Block, "graph": Graph})
        assert set(schema) >= {"block", "graph", "$defs"}
        assert schema["graph"] == {"$ref": "#/$defs/Graph"}


class TestCrossCheck:
    @pytest.mark.parametrize("data", [VALID_GRAPH, VALID_NOTE])
    def test_valid_drafts_pass_both_implementations(self, validator, data: dict) -> None:
        validator.validate(data)
        parse(Block, data)

    @pytest.mark.parametrize("data", INVALID_DRAFTS)
    def test_whatever_the_schema_rejects_the_kernel_rejects(self, validator, data: dict) -> None:
        assert not validator.is_valid(data), "фикстура должна быть невалидной по схеме"
        with pytest.raises(SchemaError):
            parse(Block, data)

    def test_the_kernel_may_be_stricter_where_json_schema_cannot_reach(
        self, validator
    ) -> None:
        # A cross-field invariant: valid per schema, rejected by `check()`.
        reversed_range = {**VALID_GRAPH, "y_range": [20, 0]}
        assert validator.is_valid(reversed_range)
        with pytest.raises(SchemaError):
            parse(Block, reversed_range)
