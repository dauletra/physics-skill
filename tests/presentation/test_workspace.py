"""Loading a presentation draft folder: the invariants live on the folder.

The loader mirrors the document's on purpose, so the properties mirror too:
nothing is dropped silently, ids agree with file names, and every problem of
the draft is reported in one pass.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from physics_svg.presentation import WorkspaceError, load_workspace


def write_draft(folder: Path, manifest: dict, slides: dict[str, dict]) -> Path:
    folder.joinpath("presentation.json").write_text(
        json.dumps(manifest, ensure_ascii=False), encoding="utf-8"
    )
    slides_dir = folder / "slides"
    slides_dir.mkdir()
    for slide_id, raw in slides.items():
        slides_dir.joinpath(f"{slide_id}.json").write_text(
            json.dumps(raw, ensure_ascii=False), encoding="utf-8"
        )
    return folder


def test_a_draft_loads_into_models(tmp_path: Path) -> None:
    draft = write_draft(
        tmp_path,
        {"title": "Проба", "order": ["s1", "s2"]},
        {
            "s1": {"type": "title", "text": "Тема", "id": "s1"},
            "s2": {"type": "objectives", "items": ["читать график"], "id": "s2"},
        },
    )
    workspace = load_workspace(draft)
    assert workspace.presentation.title == "Проба"
    assert [model.type for model in workspace.slides] == ["title", "objectives"]
    # The author's JSON survives verbatim — it is what a future upload sends.
    assert workspace.raw_slides[0]["text"] == "Тема"


def test_without_order_the_files_come_sorted(tmp_path: Path) -> None:
    draft = write_draft(
        tmp_path,
        {"title": "Проба"},
        {
            "b": {"type": "title", "text": "Тема", "id": "b"},
            "a": {"type": "objectives", "items": ["цель"], "id": "a"},
        },
    )
    assert [model.type for model in load_workspace(draft).slides] == ["objectives", "title"]


def test_a_missing_manifest_is_the_whole_report(tmp_path: Path) -> None:
    with pytest.raises(WorkspaceError, match="presentation.json"):
        load_workspace(tmp_path)


def test_every_problem_is_reported_at_once(tmp_path: Path) -> None:
    # One pass: an unlisted file, a missing file, a wrong id and an invalid
    # slide are four problems of one draft, not four runs.
    draft = write_draft(
        tmp_path,
        {"title": "Проба", "order": ["s1", "s2", "s3"]},
        {
            "s1": {"type": "title", "text": "Тема", "id": "не-s1"},
            "s3": {"type": "objectives", "items": [], "id": "s3"},
            "s9": {"type": "title", "text": "Лишний", "id": "s9"},
        },
    )
    with pytest.raises(WorkspaceError) as caught:
        load_workspace(draft)
    report = str(caught.value)
    assert "s9" in report, "файл вне order должен быть назван, а не выброшен молча"
    assert "s2" in report, "недостающий файл слайда должен быть назван"
    assert "не-s1" in report, "расхождение id с именем файла должно быть названо"
    assert "items" in report, "невалидный слайд должен попасть в тот же отчёт"
