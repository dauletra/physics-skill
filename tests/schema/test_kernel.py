"""Validation kernel behaviour.

The kernel's job is not only to reject bad data but to reject it *usefully*:
with the path to the offending value, in the author's language, and with
every problem in the draft listed at once. A message that says only "invalid"
costs a whole edit-render cycle, so the message content is under test too.
"""

import pytest

from demo import Block, Folder, Graph, Note, Point, Series
from physics_svg.schema import SchemaError, parse, spec_meta

VALID_GRAPH = {
    "type": "graph",
    "x_label": "t, с",
    "y_range": [0, 20],
    "series": [{"points": [{"x": 0, "y": 0}, {"x": 2, "y": 10}], "label": "υ(t)"}],
}


def messages(exc: SchemaError) -> list[str]:
    return [str(problem) for problem in exc.problems]


def parse_fails(annotation: object, data: object, *, name: str = "") -> list[str]:
    with pytest.raises(SchemaError) as info:
        parse(annotation, data, name=name)
    return messages(info.value)


class TestHappyPath:
    def test_builds_a_typed_tree(self) -> None:
        graph = parse(Graph, VALID_GRAPH)
        assert isinstance(graph, Graph)
        assert isinstance(graph.series[0], Series)
        assert isinstance(graph.series[0].points[0], Point)
        assert graph.series[0].points[1].x == 2

    def test_defaults_fill_in(self) -> None:
        graph = parse(Graph, {"type": "graph", "x_label": "t", "y_range": [0, 1]})
        assert graph.series == []
        assert graph.grid == "ticks"
        assert graph.ticks is None

    def test_tuple_field_becomes_a_tuple(self) -> None:
        assert parse(Graph, VALID_GRAPH).y_range == (0, 20)

    def test_specs_are_immutable(self) -> None:
        graph = parse(Graph, VALID_GRAPH)
        with pytest.raises(Exception):
            graph.x_label = "другое"  # type: ignore[misc]

    def test_explicit_null_is_accepted_for_optional_fields(self) -> None:
        graph = parse(Graph, {**VALID_GRAPH, "ticks": None})
        assert graph.ticks is None


class TestFieldProblems:
    def test_missing_required_field(self) -> None:
        assert parse_fails(Graph, {"type": "graph", "x_label": "t"}) == [
            "отсутствует обязательное поле 'y_range'"
        ]

    def test_unknown_field_suggests_the_intended_one(self) -> None:
        problems = parse_fails(Graph, {**VALID_GRAPH, "x_labels": "t"})
        assert problems == ["неизвестное поле 'x_labels'; возможно, имелось в виду 'x_label'"]

    def test_unknown_field_without_a_close_match(self) -> None:
        assert parse_fails(Graph, {**VALID_GRAPH, "colour": "red"}) == [
            "неизвестное поле 'colour'"
        ]

    def test_wrong_scalar_type_names_both_sides(self) -> None:
        assert parse_fails(Graph, {**VALID_GRAPH, "x_label": 12}) == [
            "x_label: ожидается строка, получено число"
        ]

    def test_booleans_are_never_numbers(self) -> None:
        problems = parse_fails(Graph, {**VALID_GRAPH, "ticks": True})
        assert problems == ["ticks: ожидается целое число, получено true/false"]

    def test_numbers_accept_int_and_float_but_not_strings(self) -> None:
        assert parse(Point, {"x": 1, "y": 2.5}).y == 2.5
        assert parse_fails(Point, {"x": "1", "y": 2}) == ["x: ожидается число, получено строка"]

    def test_literal_lists_the_options_and_suggests(self) -> None:
        problems = parse_fails(Graph, {**VALID_GRAPH, "grid": "fien"})
        assert problems == [
            "grid: недопустимое значение 'fien'; допустимы: 'ticks', 'fine'; "
            "возможно, имелось в виду 'fine'"
        ]

    def test_numeric_constraints(self) -> None:
        assert parse_fails(Graph, {**VALID_GRAPH, "ticks": 0}) == ["ticks: должно быть больше 0"]
        assert parse_fails(Graph, {**VALID_GRAPH, "ticks": 21}) == [
            "ticks: должно быть не больше 20"
        ]

    def test_empty_string_constraint(self) -> None:
        assert parse_fails(Graph, {**VALID_GRAPH, "x_label": ""}) == [
            "x_label: строка не должна быть пустой"
        ]

    def test_list_length_constraint(self) -> None:
        data = {**VALID_GRAPH, "series": [{"points": []}]}
        assert parse_fails(Graph, data) == [
            "series[0] -> points: нужно хотя бы 1 элемент(ов), получено 0"
        ]

    def test_fixed_length_tuple(self) -> None:
        assert parse_fails(Graph, {**VALID_GRAPH, "y_range": [0]}) == [
            "y_range: ожидается список из 2 элементов, получено 1"
        ]

    def test_mapping_values_are_validated(self) -> None:
        assert parse_fails(Note, {"type": "note", "body": "x", "tags": {"a": 1}}) == [
            "tags -> a: ожидается строка, получено число"
        ]


class TestPaths:
    def test_path_points_at_the_exact_value(self) -> None:
        data = {
            **VALID_GRAPH,
            "series": [{"points": [{"x": 0, "y": 0}]}, {"points": [{"x": 0, "y": "нет"}]}],
        }
        assert parse_fails(Graph, data) == ["series[1] -> points[0] -> y: ожидается число, получено строка"]

    def test_root_name_prefixes_the_path(self) -> None:
        problems = parse_fails(Graph, {**VALID_GRAPH, "x_label": 1}, name="task-03")
        assert problems == ["task-03 -> x_label: ожидается строка, получено число"]

    def test_uses_an_ascii_arrow(self) -> None:
        # A Windows cp1251 console cannot print "→" and loses the whole message.
        problems = parse_fails(Graph, {**VALID_GRAPH, "series": [{"points": [{"x": "a", "y": 0}]}]})
        assert "→" not in problems[0]
        assert "->" in problems[0]


class TestAllProblemsAtOnce:
    def test_every_problem_in_a_draft_is_reported(self) -> None:
        data = {
            "type": "graph",
            "x_label": 5,
            "y_range": [10, 0],
            "grid": "нет",
            "extra": 1,
        }
        problems = parse_fails(Graph, data)
        assert len(problems) == 3
        assert any("x_label" in p for p in problems)
        assert any("grid" in p for p in problems)
        assert any("extra" in p for p in problems)

    def test_a_failed_field_does_not_hide_its_siblings(self) -> None:
        data = {
            **VALID_GRAPH,
            "series": [{"points": [{"x": "a", "y": 0}]}, {"points": [{"x": 0, "y": "b"}]}],
        }
        assert len(parse_fails(Graph, data)) == 2


class TestInvariants:
    def test_check_runs_after_the_fields_are_valid(self) -> None:
        assert parse_fails(Graph, {**VALID_GRAPH, "y_range": [20, 0]}) == [
            "y_range: диапазон должен быть [min, max] с min < max, получено [20, 0]"
        ]

    def test_check_is_skipped_when_a_field_is_broken(self) -> None:
        # Otherwise an invariant would read a field that never parsed.
        problems = parse_fails(Graph, {**VALID_GRAPH, "y_range": ["a", 0]})
        assert problems == ["y_range[0]: ожидается число, получено строка"]


class TestTaggedUnions:
    def test_dispatches_on_type(self) -> None:
        assert isinstance(parse(Block, VALID_GRAPH), Graph)
        assert isinstance(parse(Block, {"type": "note", "body": "текст"}), Note)

    def test_unknown_tag_lists_the_known_ones(self) -> None:
        problems = parse_fails(Block, {"type": "grath"})
        assert problems == [
            "неизвестный тип блока 'grath'; известны: graph, note; "
            "возможно, имелось в виду 'graph'"
        ]

    def test_missing_tag(self) -> None:
        assert parse_fails(Block, {"body": "x"}) == ["у блока нет поля 'type'"]

    def test_non_object_where_a_block_is_expected(self) -> None:
        assert parse_fails(Block, "graph") == ["ожидается объект, получено строка"]

    def test_errors_inside_the_chosen_member_keep_their_path(self) -> None:
        assert parse_fails(Block, {"type": "note", "body": ""}) == [
            "body: строка не должна быть пустой"
        ]


class TestMeta:
    def test_tag_is_read_from_the_literal(self) -> None:
        assert spec_meta(Graph).tag == "graph"
        assert spec_meta(Series).tag is None

    def test_required_flags(self) -> None:
        fields = spec_meta(Graph).fields
        assert fields["x_label"].required
        assert not fields["grid"].required

    def test_docs_are_kept_for_the_reference_and_schema(self) -> None:
        assert spec_meta(Graph).fields["y_range"].constraints.doc.startswith("Диапазон")


class TestNestedObjects:
    """An optional nested spec is not a choice between block types.

    Asking one for a `type` discriminator is the regression this guards: it
    made every document with a header fail to load.
    """

    def test_a_nested_object_parses(self) -> None:
        graph = parse(Graph, {**VALID_GRAPH, "source": {"title": "Учебник", "year": 2019}})
        assert graph.source is not None and graph.source.year == 2019

    def test_it_may_be_absent_or_null(self) -> None:
        assert parse(Graph, VALID_GRAPH).source is None
        assert parse(Graph, {**VALID_GRAPH, "source": None}).source is None

    def test_problems_inside_it_keep_the_path(self) -> None:
        assert parse_fails(Graph, {**VALID_GRAPH, "source": {"title": ""}}) == [
            "source -> title: строка не должна быть пустой"
        ]

    def test_it_is_not_asked_for_a_discriminator(self) -> None:
        problems = parse_fails(Graph, {**VALID_GRAPH, "source": {"year": 2019}})
        assert problems == ["source: отсутствует обязательное поле 'title'"]


class TestDeferredAnnotations:
    """Containers whose children come from a registry."""

    def test_children_are_resolved_at_parse_time(self) -> None:
        folder = parse(Folder, {"type": "folder", "children": [VALID_GRAPH]})
        assert isinstance(folder.children[0], Graph)

    def test_errors_inside_a_deferred_child_keep_their_path(self) -> None:
        problems = parse_fails(
            Folder, {"type": "folder", "children": [{**VALID_GRAPH, "x_label": 1}]}
        )
        assert problems == ["children[0] -> x_label: ожидается строка, получено число"]

    def test_constraints_still_apply_to_the_container(self) -> None:
        assert parse_fails(Folder, {"type": "folder", "children": []}) == [
            "children: нужно хотя бы 1 элемент(ов), получено 0"
        ]

    def test_a_deferred_union_reaches_the_published_schema(self) -> None:
        from physics_svg.schema import emit_schema

        schema = emit_schema({"folder": Folder})
        assert "Graph" in schema["$defs"] and "Note" in schema["$defs"]
