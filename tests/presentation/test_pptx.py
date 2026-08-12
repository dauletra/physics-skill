"""The .pptx package: is it a package at all.

PowerPoint's failure mode is the reason these tests exist. A part that is
not typed, a relationship pointing at nothing, an `r:id` no `.rels` file
declares — any of them and the file opens as «PowerPoint found a problem
with the content», with no word about which part it disliked.

None of this proves the deck *looks* right, and one test here cannot: that
is `evals/pptx.md`, by hand, in real PowerPoint. What these prove is that
the container holds together, which is the part a person cannot check by
looking.
"""

from __future__ import annotations

import io
import os
import zipfile
from pathlib import Path
from xml.dom import minidom
from xml.etree import ElementTree as ET

import pytest

from physics_svg.ooxml import PACKAGE_RELS
from physics_svg.presentation.pptx import build_pptx, design, layouts, slide

CONTENT_TYPES = "http://schemas.openxmlformats.org/package/2006/content-types"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"

GOLDEN = Path(__file__).resolve().parents[1] / "golden" / "presentation"
REGENERATE = os.environ.get("REGEN_GOLDEN") == "1"


@pytest.fixture(scope="module")
def package() -> zipfile.ZipFile:
    return zipfile.ZipFile(io.BytesIO(build_pptx([slide(), slide()], title="Урок")))


def read(package: zipfile.ZipFile, path: str) -> ET.Element:
    return ET.fromstring(package.read(path).decode("utf-8"))


def rels_of(package: zipfile.ZipFile, part: str) -> dict[str, str]:
    """The relationships declared for one part, as id -> target."""
    folder, _, name = part.rpartition("/")
    path = f"{folder}/_rels/{name}.rels" if folder else f"_rels/{name}.rels"
    if path not in package.namelist():
        return {}
    root = read(package, path)
    return {
        entry.attrib["Id"]: entry.attrib["Target"]
        for entry in root.findall(f"{{{PACKAGE_RELS}}}Relationship")
    }


def resolve(part: str, target: str) -> str:
    """A relationship target as a path inside the package."""
    base = part.rpartition("/")[0]
    for step in target.split("/"):
        if step == "..":
            base = base.rpartition("/")[0]
        else:
            base = f"{base}/{step}" if base else step
    return base


class TestPackage:
    def test_every_part_is_well_formed_xml(self, package: zipfile.ZipFile) -> None:
        for name in package.namelist():
            ET.fromstring(package.read(name).decode("utf-8"))

    def test_every_part_is_typed(self, package: zipfile.ZipFile) -> None:
        """An untyped part is a part PowerPoint refuses to load."""
        root = read(package, "[Content_Types].xml")
        defaults = {
            entry.attrib["Extension"] for entry in root.findall(f"{{{CONTENT_TYPES}}}Default")
        }
        overrides = {
            entry.attrib["PartName"].lstrip("/")
            for entry in root.findall(f"{{{CONTENT_TYPES}}}Override")
        }
        untyped = [
            name
            for name in package.namelist()
            if name != "[Content_Types].xml"
            and name not in overrides
            and name.rpartition(".")[2] not in defaults
        ]
        assert not untyped, f"части без типа содержимого: {untyped}"

    def test_every_relationship_points_at_something(self, package: zipfile.ZipFile) -> None:
        names = set(package.namelist())
        broken = []
        for part in [name for name in names if name.endswith(".rels")]:
            owner = part.replace("_rels/", "").removesuffix(".rels")
            for rid, target in rels_of(package, owner).items():
                if resolve(owner, target) not in names:
                    broken.append(f"{owner} {rid} -> {target}")
        assert not broken, f"отношения в никуда: {broken}"

    def test_shape_ids_are_unique_inside_a_part(self, package: zipfile.ZipFile) -> None:
        """Two shapes with one id is a slide PowerPoint renumbers on save —
        silently, and not necessarily the way it was meant. A picture is a few
        dozen shapes and a slide of tasks holds four pictures, so this stops
        being theoretical the moment cells exist."""
        for part in [name for name in package.namelist() if name.endswith(".xml")]:
            ids = [
                node.attrib["id"]
                for node in read(package, part).iter()
                if node.tag.endswith("}cNvPr") and "id" in node.attrib
            ]
            assert len(ids) == len(set(ids)), f"{part}: повторяющиеся id фигур"

    def test_every_referenced_id_is_declared(self, package: zipfile.ZipFile) -> None:
        """`r:id` on a slide list or a layout list must exist in the part's
        own `.rels`, and this is the mistake that is easiest to make."""
        missing = []
        for part in [name for name in package.namelist() if name.endswith(".xml")]:
            declared = rels_of(package, part)
            for element in read(package, part).iter():
                rid = element.attrib.get(f"{{{R_NS}}}id")
                if rid is not None and rid not in declared:
                    missing.append(f"{part}: {element.tag} -> {rid}")
        assert not missing, f"ссылки на необъявленные отношения: {missing}"


class TestDeck:
    def test_the_master_and_its_layout_name_each_other(
        self, package: zipfile.ZipFile
    ) -> None:
        """One direction is not enough: PowerPoint offers to repair a file
        whose layout is not listed by the master it belongs to."""
        master = "ppt/slideMasters/slideMaster1.xml"
        layout = "ppt/slideLayouts/slideLayout1.xml"
        assert layout in {
            resolve(master, target) for target in rels_of(package, master).values()
        }
        assert master in {
            resolve(layout, target) for target in rels_of(package, layout).values()
        }

    def test_every_slide_is_listed_and_stands_on_a_layout(
        self, package: zipfile.ZipFile
    ) -> None:
        presentation = "ppt/presentation.xml"
        listed = {
            resolve(presentation, target)
            for rid, target in rels_of(package, presentation).items()
            if target.startswith("slides/")
        }
        actual = {name for name in package.namelist() if name.startswith("ppt/slides/slide")}
        assert listed == actual
        for name in actual:
            assert rels_of(package, name), f"{name} не стоит ни на одном макете"

    def test_the_frame_is_sixteen_by_nine(self, package: zipfile.ZipFile) -> None:
        root = read(package, "ppt/presentation.xml")
        size = root.find(
            "{http://schemas.openxmlformats.org/presentationml/2006/main}sldSz"
        )
        assert size is not None
        width, height = int(size.attrib["cx"]), int(size.attrib["cy"])
        assert width / height == pytest.approx(16 / 9)

    def test_an_empty_deck_still_has_a_slide(self) -> None:
        """Nothing to look at is a phase that cannot be accepted, and every
        phase of docs/pptx.md is accepted by looking."""
        empty = zipfile.ZipFile(io.BytesIO(build_pptx([], title="Пусто")))
        assert "ppt/slides/slide1.xml" in empty.namelist()


class TestLayouts:
    """Geometry of the layouts themselves, which nothing else can catch.

    PowerPoint places what it is told and says nothing about two boxes on top
    of each other; the file is valid and the slide is wrong. So the arithmetic
    of `layouts.py` is checked here rather than discovered on a panel.
    """

    @staticmethod
    def boxes(layout: object) -> list[tuple[str, tuple[float, float, float, float]]]:
        named = [(place.name, place.box) for place in getattr(layout, "places")]
        picture = getattr(layout, "picture")
        named += [("Иллюстрация", picture)] if picture else []
        return named + [
            (f"ячейка {index + 1}", box)
            for index, box in enumerate(getattr(layout, "cells"))
        ]

    @pytest.mark.parametrize("layout", layouts.LAYOUTS, ids=[e.name for e in layouts.LAYOUTS])
    def test_no_two_boxes_share_room(self, layout: object) -> None:
        entries = self.boxes(layout)
        for index, (name, box) in enumerate(entries):
            for other_name, other in entries[index + 1 :]:
                x, y, width, height = box
                ox, oy, owidth, oheight = other
                apart = x + width <= ox or ox + owidth <= x or y + height <= oy or oy + oheight <= y
                assert apart, f"{getattr(layout, 'name')}: «{name}» и «{other_name}» наложились"

    @pytest.mark.parametrize("layout", layouts.LAYOUTS, ids=[e.name for e in layouts.LAYOUTS])
    def test_every_box_is_inside_the_frame(self, layout: object) -> None:
        for name, (x, y, width, height) in self.boxes(layout):
            assert x >= 0 and y >= 0, f"{getattr(layout, 'name')}: «{name}» начинается за кадром"
            assert x + width <= layouts.WIDTH + 1e-6, f"{getattr(layout, 'name')}: «{name}» шире кадра"
            assert y + height <= layouts.HEIGHT + 1e-6, f"{getattr(layout, 'name')}: «{name}» ниже кадра"


class TestLesson:
    """A deck built from real slide models, not from hand-written XML."""

    @staticmethod
    def deck(*slides: object) -> zipfile.ZipFile:
        from physics_svg.presentation import parse_presentation, parse_slide
        from physics_svg.presentation.pptx.deck import build_deck

        models = [parse_slide(item, f"s{index}") for index, item in enumerate(slides)]
        data, _ = build_deck(parse_presentation({"title": "Урок"}), models)
        return zipfile.ZipFile(io.BytesIO(data))

    @staticmethod
    def texts(package: zipfile.ZipFile, part: str) -> list[str]:
        return [
            node.text or ""
            for node in read(package, part).iter(
                "{http://schemas.openxmlformats.org/drawingml/2006/main}t"
            )
        ]

    def test_the_title_reaches_its_slide(self) -> None:
        package = self.deck(
            {"type": "title", "text": "Равноускоренное движение", "subtitle": "9 класс"}
        )
        assert self.texts(package, "ppt/slides/slide1.xml") == [
            "Равноускоренное движение",
            "9 класс",
        ]

    def test_a_slide_stands_on_the_layout_of_its_kind(self) -> None:
        package = self.deck(
            {"type": "title", "text": "Урок"},
            {"type": "section", "text": "Разбор"},
            {"type": "content", "heading": "Скорость", "text": "Определение"},
        )
        wanted = ["slideLayout1.xml", "slideLayout2.xml", "slideLayout3.xml"]
        for index, layout in enumerate(wanted, start=1):
            targets = rels_of(package, f"ppt/slides/slide{index}.xml").values()
            assert any(target.endswith(layout) for target in targets), index

    def test_a_list_becomes_bulleted_paragraphs(self) -> None:
        package = self.deck(
            {"type": "content", "heading": "Признаки", "items": ["раз", "два"]}
        )
        body = read(package, "ppt/slides/slide1.xml")
        bullets = list(body.iter("{http://schemas.openxmlformats.org/drawingml/2006/main}buChar"))
        assert len(bullets) == 2
        assert self.texts(package, "ppt/slides/slide1.xml") == ["Признаки", "раз", "два"]

    def test_an_index_is_lifted_off_the_baseline(self) -> None:
        """`<sub>` is the author's own syntax, and it has to survive into a
        deck the same way it survives into a sheet."""
        package = self.deck({"type": "content", "text": "скорость υ<sub>0</sub> в начале"})
        properties = [
            node.attrib.get("baseline")
            for node in read(package, "ppt/slides/slide1.xml").iter(
                "{http://schemas.openxmlformats.org/drawingml/2006/main}rPr"
            )
        ]
        assert "-25000" in properties

    def test_an_answer_names_itself(self) -> None:
        """«12 с» alone under a task is a number of unclear origin, so the
        word is part of the answer and the value is what carries the weight."""
        package = self.deck(
            {"type": "board_task", "text": "За какое время?", "answer": "12 с"}
        )
        assert self.texts(package, "ppt/slides/slide1.xml") == [
            "За какое время?",
            "Ответ: ",
            "12 с",
        ]
        runs = read(package, "ppt/slides/slide1.xml").iter(
            "{http://schemas.openxmlformats.org/drawingml/2006/main}rPr"
        )
        assert [node.attrib.get("b") for node in runs] == [None, None, "1"]

    def test_a_task_without_an_answer_leaves_the_band_empty(self) -> None:
        """The band stays on the layout — the class looks for the answer in
        one place — but nothing is written into it, so a task whose result is
        a drawing on the board shows no stray «Ответ:»."""
        package = self.deck({"type": "board_task", "text": "Постройте график."})
        assert self.texts(package, "ppt/slides/slide1.xml") == ["Постройте график."]

    def test_a_task_picture_goes_where_it_reads(self) -> None:
        """The same measurement the explanation slide makes, against the
        shorter box a task leaves after its answer band."""
        graph = {
            "type": "graph",
            "x_label": "t, с",
            "y_label": "υ, м/с",
            "x_range": [0, 6],
            "y_range": [0, 8],
            "series": [{"points": [[0, 0], [6, 8]]}],
        }
        package = self.deck({"type": "board_task", "text": "Найдите путь.", "visual": graph})
        targets = rels_of(package, "ppt/slides/slide1.xml").values()
        wanted = layouts.layout_index("task_stack")
        assert any(target.endswith(f"slideLayout{wanted}.xml") for target in targets)

    def test_the_genre_is_named_on_the_layout(self) -> None:
        """«Задача» belongs to the kind, not to the slide: it is written once
        on the layout, where no author can retype it."""
        package = self.deck({"type": "board_task", "text": "Задание"})
        part = f"ppt/slideLayouts/slideLayout{layouts.layout_index('task')}.xml"
        assert "Задача" in self.texts(package, part)
        assert "Задача" not in self.texts(package, "ppt/slides/slide1.xml")

    def test_a_set_of_tasks_numbers_itself(self) -> None:
        """The number is where the task stands, not something the data
        carries — exactly as on a sheet."""
        package = self.deck(
            {"type": "tasks", "tasks": [{"text": "Первая"}, {"text": "Вторая"}]}
        )
        assert self.texts(package, "ppt/slides/slide1.xml") == [
            "Задачи",  # no heading, so the genre names the slide
            "1. ",
            "Первая",
            "2. ",
            "Вторая",
        ]

    @pytest.mark.parametrize(
        "count,layout",
        [(2, "cells_2"), (3, "cells_3_square"), (4, "cells_4")],
    )
    def test_a_set_folds_instead_of_thinning(self, count: int, layout: str) -> None:
        """Two stand side by side; three and four go into two rows, because a
        column narrower than half the frame is not read from the back row."""
        package = self.deck(
            {"type": "tasks", "tasks": [{"text": f"Задача {i}"} for i in range(count)]}
        )
        targets = rels_of(package, "ppt/slides/slide1.xml").values()
        wanted = layouts.layout_index(layout)
        assert any(target.endswith(f"slideLayout{wanted}.xml") for target in targets)

    def test_the_horizon_carries_one_line(self) -> None:
        """A heading if there is one, the genre word if there is not — never
        both, because a heading already says what the slide is."""
        cases = [{"label": "Было", "text": "раз"}, {"label": "Стало", "text": "два"}]
        without = self.texts(self.deck({"type": "compare", "cases": cases}), "ppt/slides/slide1.xml")
        titled = self.texts(
            self.deck({"type": "compare", "heading": "Найдите разницу", "cases": cases}),
            "ppt/slides/slide1.xml",
        )
        assert without[0] == "Сравнение"
        assert titled[0] == "Найдите разницу" and "Сравнение" not in titled

    def test_a_slide_full_of_pictures_keeps_its_ids_apart(self) -> None:
        """The case the empty deck cannot show: every picture is a few dozen
        shapes, and they all live in one slide part."""
        graph = {
            "type": "graph",
            "x_label": "t, с",
            "y_label": "υ, м/с",
            "x_range": [0, 6],
            "y_range": [0, 8],
            "series": [{"points": [[0, 0], [6, 8]]}],
        }
        package = self.deck(
            {
                "type": "tasks",
                "tasks": [
                    {"text": "Первая", "visual": graph, "answer": "12 м"},
                    {"text": "Вторая", "visual": graph, "answer": "8 м"},
                ],
            }
        )
        ids = [
            node.attrib["id"]
            for node in read(package, "ppt/slides/slide1.xml").iter()
            if node.tag.endswith("}cNvPr") and "id" in node.attrib
        ]
        assert len(ids) > 50, "картинки не нарисовались — тест ничего не проверяет"
        assert len(ids) == len(set(ids)), "повторяющиеся id фигур на слайде"

    def test_a_formula_is_a_formula(self) -> None:
        """OMML, not a picture and not a line of TeX — the whole of P5. The
        `mc:` envelope is what lets a slide hold maths at all, and the
        fallback is what a reader older than 2010 shows instead."""
        package = self.deck({"type": "formula", "formula": "$v = \\frac{s}{t}$"})
        body = package.read("ppt/slides/slide1.xml").decode()
        assert "<m:f>" in body and "<m:num>" in body and "<m:den>" in body
        assert "mc:AlternateContent" in body and "<mc:Fallback>" in body
        # Display form: a fraction at full height, not squeezed into a line.
        assert "<m:oMathPara" in body

    def test_a_formula_brings_its_own_namespaces(self) -> None:
        """A slide part declares neither `m:` nor `w:`, and an undeclared
        prefix is a file PowerPoint refuses outright."""
        package = self.deck({"type": "formula", "formula": "$a = 2$"})
        # Parsing is the assertion: ElementTree rejects an unbound prefix.
        read(package, "ppt/slides/slide1.xml")

    def test_a_formula_outside_the_subset_is_said_out_loud(self) -> None:
        """The deck is finished and correct; what it could not express is
        named, exactly as the Word backend names it."""
        from physics_svg.presentation import parse_presentation, parse_slide
        from physics_svg.presentation.pptx.deck import build_deck

        models = [parse_slide({"type": "formula", "formula": "$\\int_0^1 x dx$"}, "s1")]
        data, notes = build_deck(parse_presentation({"title": "Урок"}), models)
        assert data, "колода всё равно собирается"
        assert notes and "слайд 1" in notes[0]
        body = zipfile.ZipFile(io.BytesIO(data)).read("ppt/slides/slide1.xml").decode()
        assert "$\\int_0^1 x dx$" in body, "текст автора попадает на слайд как есть"

    def test_the_steps_of_an_example_are_numbered_by_powerpoint(self) -> None:
        """Not drawn into the text: a teacher who inserts a step gets the
        rest renumbered instead of a list that lies."""
        package = self.deck(
            {"type": "example", "text": "Условие", "steps": ["Раз", "Два"]}
        )
        body = package.read("ppt/slides/slide1.xml").decode()
        assert body.count('<a:buAutoNum type="arabicPeriod"/>') == 2
        assert "1." not in self.texts(package, "ppt/slides/slide1.xml")

    def test_an_answer_waits_for_a_click(self) -> None:
        """A task whose answer is already on the screen is not a task."""
        package = self.deck(
            {"type": "board_task", "text": "За какое время?", "answer": "12 с"}
        )
        body = package.read("ppt/slides/slide1.xml").decode()
        assert "<p:timing>" in body
        assert 'nodeType="clickEffect"' in body
        assert 'presetClass="entr"' in body

    def test_a_slide_with_nothing_to_reveal_has_no_timing(self) -> None:
        """The most fragile XML the deck writes is simply absent where it is
        not needed, so a slide that does not animate cannot be broken by it."""
        for quiet in (
            {"type": "content", "text": "Объяснение"},
            {"type": "board_task", "text": "Постройте график."},
        ):
            body = self.deck(quiet).read("ppt/slides/slide1.xml").decode()
            assert "p:timing" not in body, quiet["type"]

    def test_the_answer_is_the_last_click(self) -> None:
        """PowerPoint has one queue and no key that skips it, so an answer
        anywhere but last could be opened by a teacher who only meant to show
        the next step (docs/pptx.md §6.2)."""
        package = self.deck(
            {
                "type": "example",
                "text": "Условие",
                "steps": ["Раз", "Два"],
                "answer": "25 м",
            }
        )
        targets = [
            node.attrib["spid"]
            for node in read(package, "ppt/slides/slide1.xml").iter(
                "{http://schemas.openxmlformats.org/presentationml/2006/main}spTgt"
            )
        ]
        assert targets == ["3", "3", "4"], "шаги, потом ответ"

    @pytest.mark.parametrize(
        "slide",
        [
            {"type": "board_task", "text": "Задача", "answer": "12 с"},
            {"type": "example", "text": "У", "steps": ["Раз", "Два"], "answer": "5 м"},
            {
                "type": "tasks",
                "tasks": [
                    {"text": "Первая", "answer": "1"},
                    {"text": "Вторая", "answer": "2"},
                ],
            },
        ],
        ids=["board_task", "example", "tasks"],
    )
    def test_the_timing_tree_points_at_shapes_that_exist(self, slide: dict) -> None:
        """A dangling `spid` is the classic way to lose a slide show — and
        unlike the show itself, it is checkable. The node ids inside the tree
        have to be distinct for the same reason."""
        package = self.deck(slide)
        root = read(package, "ppt/slides/slide1.xml")
        p = "{http://schemas.openxmlformats.org/presentationml/2006/main}"
        shapes = {
            node.attrib["id"]
            for node in root.iter()
            if node.tag.endswith("}cNvPr") and "id" in node.attrib
        }
        targets = {node.attrib["spid"] for node in root.iter(f"{p}spTgt")}
        assert targets, "анимации нет — тест ничего не проверяет"
        assert targets <= shapes, f"анимация целится в несуществующие фигуры: {targets - shapes}"
        builds = {node.attrib["spid"] for node in root.iter(f"{p}bldP")}
        assert builds <= shapes
        node_ids = [node.attrib["id"] for node in root.iter(f"{p}cTn")]
        assert len(node_ids) == len(set(node_ids)), "повторяющиеся id узлов анимации"


class TestDesignIsDocumented:
    """`docs/slide-metrics.md` is where a number is looked up, so it has to
    be the number.

    The page exists because the alternative was reading 57 КБ about a player
    that no longer runs to find out what size body text is. A short page only
    stays worth opening while it is true, and prose does not fail a build —
    so it is checked here, against the module it describes.
    """

    @staticmethod
    def _cells(row: str) -> list[str]:
        return [cell.strip() for cell in row.strip().strip("|").split("|")]

    @staticmethod
    def _number(cell: str) -> float:
        """The page writes numbers the way the rest of it is written — in
        Russian, with a comma."""
        return float(cell.strip("*").replace(",", "."))

    def rows(self) -> dict[str, list[str]]:
        page = (
            Path(__file__).resolve().parents[2] / "docs" / "slide-metrics.md"
        ).read_text(encoding="utf-8")
        table = {}
        for line in page.splitlines():
            if line.startswith("| `") and "|" in line[3:]:
                cells = self._cells(line)
                table[cells[0].strip("`")] = cells[1:]
        return table

    def test_every_size_token_is_quoted_correctly(self) -> None:
        rows = self.rows()
        for name in ("HERO", "DISPLAY", "HEADING", "LEAD", "TEXT", "SMALL", "TINY"):
            assert name in rows, f"ступень {name} не описана в docs/slide-metrics.md"
            printed = self._number(rows[name][0])
            assert printed == round(getattr(design, name)), (
                f"{name}: на странице {printed} pt, в design.py {getattr(design, name)}"
            )

    def test_the_frame_and_the_colours_are_quoted_correctly(self) -> None:
        rows = self.rows()
        for name in ("PAD_Y", "PAD_X", "VISUAL_MIN"):
            assert self._number(rows[name][0]) == pytest.approx(getattr(design, name)), name
        for name in ("INK", "INK_SOFT", "INK_FAINT", "PAPER", "PAPER_SUNK", "LINE", "PANEL"):
            assert rows[name][0] == f"`#{getattr(design, name)}`", name

    def test_the_conversion_the_whole_scale_rests_on_is_named(self) -> None:
        page = (
            Path(__file__).resolve().parents[2] / "docs" / "slide-metrics.md"
        ).read_text(encoding="utf-8")
        assert f"1 cqh = {design.PT_PER_CQH} pt".replace(".", ",") in page
        assert f"×{design.LEADING}".replace(".", ",") in page


class TestStability:
    def test_two_builds_are_the_same_file(self) -> None:
        """A golden test of a binary format is only possible if the build is
        deterministic — the same reason `num()` exists in `draw/text.py`."""
        first = build_pptx([slide()], title="Урок")
        second = build_pptx([slide()], title="Урок")
        assert first == second

    def test_the_empty_deck_matches_its_golden(self) -> None:
        """Every part, formatted. The golden is the XML rather than the zip
        for the same reason the Word one is: a binary golden cannot be read
        in a diff, and being able to look at what changed is the point.
        """
        with zipfile.ZipFile(io.BytesIO(build_pptx([], title="Проверка"))) as deck:
            pretty = "".join(
                f"===== {name}\n"
                + minidom.parseString(deck.read(name).decode("utf-8")).toprettyxml(indent="  ")
                for name in deck.namelist()
            )
        path = GOLDEN / "empty.pptx.xml"
        if REGENERATE or not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(pretty, encoding="utf-8")
            if not REGENERATE:
                return
        assert pretty == path.read_text(encoding="utf-8"), (
            "колода разошлась с эталоном empty.pptx.xml; если изменение "
            "намеренное — REGEN_GOLDEN=1 и просмотри диф глазами"
        )
