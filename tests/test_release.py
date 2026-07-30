"""The release step: version numbers and the changelog rename.

What matters here is that the notes a release publishes are exactly the notes
that accumulated under «Не выпущено» — the rename must not move, swallow or
drop a line. So the check goes through `release_notes.notes_for`, the same
slicing the publishing workflow uses.

The git side (branch guards, commit, tag) is left to the tool itself: it is a
sequence of git calls with no logic of its own, and faking a repository to
test it would test the fake.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))

import release  # noqa: E402
import release_notes  # noqa: E402

SAMPLE = """\
# Изменения

Преамбула, общая для файла.

## [Не выпущено]

### Исправлено

- Что-то накопленное.

## [0.1.0] — 2026-01-01

- Первое изменение.
"""


class TestVersionNumbers:
    def test_a_development_version_precedes_its_release(self) -> None:
        assert release.parse("0.3.0.dev0") < release.parse("0.3.0")

    def test_versions_order_by_parts_not_by_text(self) -> None:
        assert release.parse("0.9.0") < release.parse("0.10.0")

    def test_a_number_of_no_known_shape_is_refused(self) -> None:
        with pytest.raises(SystemExit, match="не вида"):
            release.parse("0.3")

    def test_the_cycle_after_a_release_is_the_next_minor(self) -> None:
        assert release.next_cycle("0.2.0") == "0.3.0.dev0"

    def test_a_patch_cycle_is_asked_for_explicitly(self) -> None:
        assert release.next_cycle("0.2.0", patch=True) == "0.2.1.dev0"


class TestTheFloorForTheNextRelease:
    def test_a_released_tag_is_what_a_release_may_not_go_back_to(self) -> None:
        assert release.as_floor("v0.2.0") == "0.2.0"

    def test_an_early_prerelease_tag_is_not_a_floor(self) -> None:
        assert release.as_floor("v0.2.0a1") is None

    def test_a_patch_clears_the_floor_left_by_the_previous_release(self) -> None:
        floor = release.as_floor("v0.2.0")
        assert floor is not None
        assert release.parse("0.2.1") > release.parse(floor)

    def test_an_opened_cycle_does_not_decide_the_size_of_the_release(self) -> None:
        """The floor comes from a tag, so `0.3.0.dev0` in the working tree
        leaves a patch release available — it only labels the branch."""
        assert release.parse("0.2.1") < release.parse("0.3.0.dev0")


class TestTheVersionInThePackage:
    def test_the_declaration_is_found_and_rewritten(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        path = tmp_path / "__init__.py"
        path.write_text('"""Docstring."""\n\n__version__ = "0.2.0"\n', encoding="utf-8")
        monkeypatch.setattr(release, "INIT", path)

        release.write_version("0.3.0.dev0")

        assert release.read_version() == "0.3.0.dev0"
        assert path.read_text(encoding="utf-8").startswith('"""Docstring."""')

    def test_a_file_without_a_declaration_stops_the_release(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        path = tmp_path / "__init__.py"
        path.write_text("# ничего\n", encoding="utf-8")
        monkeypatch.setattr(release, "INIT", path)

        with pytest.raises(SystemExit, match="__version__"):
            release.read_version()


class TestTheChangelogRename:
    def test_the_accumulated_notes_become_the_release_notes(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        before = release.unreleased_notes(SAMPLE)
        renamed = release.release_changelog(SAMPLE, "0.2.0", "2026-02-02")

        path = tmp_path / "CHANGELOG.md"
        path.write_text(renamed, encoding="utf-8")
        monkeypatch.setattr(release_notes, "CHANGELOG", path)

        assert release_notes.notes_for("0.2.0") == before

    def test_an_empty_section_is_opened_for_the_next_release(self) -> None:
        renamed = release.release_changelog(SAMPLE, "0.2.0", "2026-02-02")
        assert release.unreleased_notes(renamed) == ""

    def test_the_preamble_stays_above_every_release(self) -> None:
        renamed = release.release_changelog(SAMPLE, "0.2.0", "2026-02-02")
        assert renamed.startswith("# Изменения\n\nПреамбула, общая для файла.")

    def test_earlier_releases_are_left_alone(self) -> None:
        renamed = release.release_changelog(SAMPLE, "0.2.0", "2026-02-02")
        assert "## [0.1.0] — 2026-01-01" in renamed

    def test_notes_are_read_up_to_the_next_heading(self) -> None:
        assert release.unreleased_notes(SAMPLE) == "### Исправлено\n\n- Что-то накопленное."

    def test_a_file_without_the_section_stops_the_release(self) -> None:
        with pytest.raises(SystemExit, match="Не выпущено"):
            release.unreleased_notes("# Изменения\n\n## [0.1.0]\n\n- Одно.\n")


class TestTheRealChangelog:
    def test_the_heading_the_tool_renames_is_there(self) -> None:
        text = (REPO / "CHANGELOG.md").read_text(encoding="utf-8")
        assert release.UNRELEASED in text, (
            "release.py переименовывает раздел, которого в CHANGELOG.md нет"
        )
