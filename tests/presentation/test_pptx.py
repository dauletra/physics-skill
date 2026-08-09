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
from physics_svg.presentation.pptx import build_pptx, slide

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
