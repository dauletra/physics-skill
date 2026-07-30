"""Release notes cut out of CHANGELOG.md.

The text published with a release is this file's own text, so the slicing is
checked against the real CHANGELOG and not only against a fixture: a section
that quietly swallows the document's preamble ships that preamble to teachers
as part of the release, and nothing downstream would notice.

The rest is the guard the release path leans on — a tag that disagrees with
the package version, or a version with no section at all, has to stop the
release before it publishes anything.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))

import release_notes  # noqa: E402
from physics_svg import __version__  # noqa: E402

CHANGELOG = (REPO / "CHANGELOG.md").read_text(encoding="utf-8")
#: Wording that belongs to the document, never to one release. Every phrase
#: here lives above the first version heading; finding one inside a slice
#: means a section reached past its own end.
PREAMBLE = ("Keep a Changelog", "История версии 0.1")
#: `## [Не выпущено]` has no version to release, so released sections are the
#: ones whose heading starts with a digit.
RELEASED = re.compile(r"^\d")

SAMPLE = """\
# Изменения

Преамбула, общая для файла.

## [Не выпущено]

## [1.2.0] — 2026-01-01

- Второе изменение.

## 1.1.0

- Первое изменение.
"""


@pytest.fixture
def sample(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "CHANGELOG.md"
    path.write_text(SAMPLE, encoding="utf-8")
    monkeypatch.setattr(release_notes, "CHANGELOG", path)


def released_versions() -> list[str]:
    return [
        match.group(1)
        for match in release_notes.SECTION.finditer(CHANGELOG)
        if RELEASED.match(match.group(1))
    ]


class TestTheRealChangelog:
    def test_there_is_a_released_version_to_slice(self) -> None:
        assert released_versions(), "в CHANGELOG.md нет ни одного выпущенного раздела"

    def test_no_section_reaches_into_the_preamble(self) -> None:
        for version in released_versions():
            notes = release_notes.notes_for(version)
            for phrase in PREAMBLE:
                assert phrase not in notes, (
                    f"заметки {version} захватили текст всего файла: «{phrase}»"
                )

    def test_every_released_section_carries_notes(self) -> None:
        for version in released_versions():
            assert release_notes.notes_for(version).strip()


@pytest.mark.usefixtures("sample")
class TestSlicing:
    def test_a_section_stops_at_the_next_heading(self) -> None:
        assert release_notes.notes_for("1.2.0") == "- Второе изменение."

    def test_the_last_section_stops_at_the_end_of_the_file(self) -> None:
        assert release_notes.notes_for("1.1.0") == "- Первое изменение."

    def test_a_heading_without_brackets_is_a_section_too(self) -> None:
        assert "1.1.0" in [
            match.group(1) for match in release_notes.SECTION.finditer(SAMPLE)
        ]

    def test_an_unknown_version_names_the_ones_there_are(self) -> None:
        with pytest.raises(SystemExit, match="1.2.0"):
            release_notes.notes_for("9.9.9")

    def test_a_section_without_notes_is_not_publishable(self) -> None:
        with pytest.raises(SystemExit, match="пуст"):
            release_notes.notes_for("Не")


class TestTheVersionGuard:
    def test_the_tag_may_carry_the_v(self) -> None:
        assert release_notes.check_version(f"v{__version__}") == __version__

    def test_a_tag_that_disagrees_with_the_package_stops_the_release(self) -> None:
        with pytest.raises(SystemExit, match="не совпадает"):
            release_notes.check_version("v0.0.0")
