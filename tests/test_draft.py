"""A draft folder as one file, and back — `physics_svg.draft`.

The pair has to be lossless, because it is the way work survives a session:
what the teacher brings back is a file, and what gets edited is a folder. A
round trip that dropped a field would lose an author's text silently, which
is why the first test compares the whole example rather than a sample.

The rest is refusals. Everything here can arrive from a page a teacher
downloaded weeks ago, so a packed draft is checked before a single file is
written — half a folder is worse than none, because it looks like a draft.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from physics_svg import draft
from physics_svg.document import load_workspace as load_document
from physics_svg.document.render import render_source
from physics_svg.presentation import load_workspace as load_presentation

REPO = Path(__file__).resolve().parent.parent
LESSON = REPO / "examples" / "kinematics-9th-grade"

SHEET = {
    "document": {"title": "Проба", "order": ["t"]},
    "blocks": [{"id": "t", "type": "text", "body": "Текст."}],
}


class TestRoundTrip:
    def test_the_worked_lesson_survives_intact(self, tmp_path: Path) -> None:
        """Both genres, every file, byte for byte after JSON parsing."""
        draft.unpack(draft.pack(LESSON), tmp_path / "lesson")
        for folder in ("blocks", "slides"):
            originals = sorted((LESSON / folder).glob("*.json"))
            assert originals
            for path in originals:
                restored = tmp_path / "lesson" / folder / path.name
                assert json.loads(restored.read_text(encoding="utf-8")) == json.loads(
                    path.read_text(encoding="utf-8")
                ), f"{folder}/{path.name} изменился в круговом обходе"
        for manifest in ("document.json", "presentation.json"):
            restored = tmp_path / "lesson" / manifest
            assert json.loads(restored.read_text(encoding="utf-8")) == json.loads(
                (LESSON / manifest).read_text(encoding="utf-8")
            )

    def test_the_restored_folder_loads(self, tmp_path: Path) -> None:
        """The point of the folder is that the loaders accept it."""
        draft.unpack(draft.pack(LESSON), tmp_path / "lesson")
        assert len(load_document(tmp_path / "lesson").blocks) > 1
        assert len(load_presentation(tmp_path / "lesson").slides) > 1

    def test_a_sheet_without_a_presentation_packs_alone(self, tmp_path: Path) -> None:
        """A lesson may be a sheet and nothing else — most are."""
        draft.unpack(SHEET, tmp_path / "sheet")
        assert not (tmp_path / "sheet" / "presentation.json").exists()
        assert draft.pack(tmp_path / "sheet") == SHEET


class TestReadingAPage:
    def test_it_reads_the_draft_embedded_in_a_document(self, tmp_path: Path) -> None:
        """Rule 3 of SKILL.md, mechanised: the finished page is the draft."""
        page = tmp_path / "document.html"
        page.write_text(f"<html><body>{render_source(SHEET)}</body></html>", encoding="utf-8")
        assert draft.read(page) == SHEET

    def test_a_handout_says_why_it_has_no_draft(self, tmp_path: Path) -> None:
        """The handout omits the draft deliberately — it would leak the
        answers through the page source. The message has to say so, or it
        reads as a broken file."""
        page = tmp_path / "document-handout.html"
        page.write_text("<html><body>без черновика</body></html>", encoding="utf-8")
        with pytest.raises(draft.DraftError, match="handout"):
            draft.read(page)

    def test_a_missing_file_is_not_a_traceback(self, tmp_path: Path) -> None:
        with pytest.raises(draft.DraftError, match="не найден файл"):
            draft.read(tmp_path / "нет.json")


class TestRefusals:
    def test_it_refuses_a_folder_that_already_holds_a_draft(self, tmp_path: Path) -> None:
        draft.unpack(SHEET, tmp_path / "sheet")
        with pytest.raises(draft.DraftError, match="уже есть черновик"):
            draft.unpack(SHEET, tmp_path / "sheet")

    def test_an_id_cannot_escape_the_folder(self, tmp_path: Path) -> None:
        """The packed draft may come from a page a teacher downloaded, so an
        id is a file name and is checked as one."""
        packed = {"document": {"order": ["x"]}, "blocks": [{"id": "../evil", "type": "text"}]}
        with pytest.raises(draft.DraftError, match="не годится именем файла"):
            draft.unpack(packed, tmp_path / "sheet")
        assert not (tmp_path.parent / "evil.json").exists()

    def test_two_blocks_with_one_id_would_overwrite(self, tmp_path: Path) -> None:
        packed = {
            "document": {"order": ["t"]},
            "blocks": [{"id": "t", "type": "text"}, {"id": "t", "type": "text"}],
        }
        with pytest.raises(draft.DraftError, match="уже встречался"):
            draft.unpack(packed, tmp_path / "sheet")

    def test_items_without_their_manifest_are_refused(self, tmp_path: Path) -> None:
        with pytest.raises(draft.DraftError, match="есть 'slides', но нет 'presentation'"):
            draft.unpack({**SHEET, "slides": []}, tmp_path / "sheet")

    def test_something_that_is_not_a_draft_says_so(self, tmp_path: Path) -> None:
        with pytest.raises(draft.DraftError, match="это не черновик"):
            draft.unpack({"заголовок": "нет"}, tmp_path / "sheet")

    def test_nothing_is_written_when_anything_is_wrong(self, tmp_path: Path) -> None:
        """Half a folder looks like a draft and is not one."""
        packed = {
            "document": {"order": ["a", "b"]},
            "blocks": [{"id": "a", "type": "text"}, {"id": "../b", "type": "text"}],
        }
        with pytest.raises(draft.DraftError):
            draft.unpack(packed, tmp_path / "sheet")
        assert not (tmp_path / "sheet").exists()

    def test_a_folder_without_a_manifest_cannot_be_packed(self, tmp_path: Path) -> None:
        (tmp_path / "empty").mkdir()
        with pytest.raises(draft.DraftError, match="нет ни document.json"):
            draft.pack(tmp_path / "empty")
