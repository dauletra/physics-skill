"""The distributable bundle.

The bundle is what a teacher actually gets, and it is assembled rather than
committed — so these tests check the assembly, not a directory listing. The
end-to-end case is the important one: it unpacks nothing, installs nothing,
and runs the shipped entry point against the shipped example in a subprocess
with the repository off the path. If that passes, the thing works on a
machine that has never seen this project.
"""

from __future__ import annotations

import ast
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))

import build_skill  # noqa: E402
from physics_svg.cli import FORMATS  # noqa: E402
from physics_svg.document.questions import load_all as load_questions  # noqa: E402
from physics_svg.visuals import load_all as load_visuals  # noqa: E402


@pytest.fixture(scope="module")
def bundle(tmp_path_factory: pytest.TempPathFactory) -> Path:
    destination = tmp_path_factory.mktemp("bundle")
    return build_skill.build(destination / "skill", make_zip=False)


class TestContents:
    def test_the_entry_point_and_manifest_are_there(self, bundle: Path) -> None:
        assert (bundle / "SKILL.md").exists()
        assert (bundle / "scripts" / "render.py").exists()
        assert (bundle / "physics_svg" / "cli.py").exists()

    def test_all_four_references_are_generated(self, bundle: Path) -> None:
        names = {path.name for path in (bundle / "references").glob("*.md")}
        assert names == {"document.md", "questions.md", "symbols.md", "visuals.md"}

    def test_the_spec_library_ships(self, bundle: Path) -> None:
        for entry in load_visuals().values():
            shipped = list((bundle / "library" / entry.tag).glob("*.json"))
            assert len(shipped) == len(entry.specs), f"библиотека '{entry.tag}' неполная"

    def test_the_worked_example_ships(self, bundle: Path) -> None:
        assert (bundle / "examples" / "kinematics-9th-grade" / "document.json").exists()

    def test_the_schema_and_version_ship(self, bundle: Path) -> None:
        assert (bundle / "schema.json").exists()
        assert (bundle / "VERSION").read_text(encoding="utf-8").strip()

    def test_no_generated_junk(self, bundle: Path) -> None:
        junk = [
            path.relative_to(bundle).as_posix()
            for path in bundle.rglob("*")
            if "__pycache__" in path.parts or path.name.endswith(".pyc") or "output" in path.parts
        ]
        assert junk == []


class TestSkillMd:
    def test_every_placeholder_is_filled(self, bundle: Path) -> None:
        text = (bundle / "SKILL.md").read_text(encoding="utf-8")
        assert "{{" not in text

    def test_the_counts_match_the_registries(self, bundle: Path) -> None:
        text = (bundle / "SKILL.md").read_text(encoding="utf-8")
        assert f"все {len(load_questions())} видов" in text
        assert f"все {len(load_visuals())} типов" in text

    def test_it_promises_only_formats_the_cli_has(self, bundle: Path) -> None:
        """The command table is the model's whole knowledge of the surface.

        A format named here and unknown to the CLI is a run that fails in
        front of a teacher; a format the CLI has and the table omits is a file
        nobody is ever offered.
        """
        text = (bundle / "SKILL.md").read_text(encoding="utf-8")
        named = set(re.findall(r"--format (\w+)", text))
        assert named <= set(FORMATS), f"SKILL.md обещает форматы, которых нет: {named}"
        assert "docx" in named, "SKILL.md не рассказывает про Word — модель его не предложит"

    def test_it_promises_nothing_missing(self, bundle: Path) -> None:
        # `build` already fails on this; asserting here documents the rule.
        text = (bundle / "SKILL.md").read_text(encoding="utf-8")
        for mentioned in sorted(set(build_skill.MENTIONED_PATH.findall(text))):
            target = bundle / mentioned
            assert target.exists() or target.parent.exists(), mentioned


class TestReferencesFollowTheRegistries:
    def test_every_question_kind_is_documented(self, bundle: Path) -> None:
        text = (bundle / "references" / "questions.md").read_text(encoding="utf-8")
        for tag in load_questions():
            assert f"`{tag}`" in text, f"вид '{tag}' не попал в справочник"

    def test_every_illustration_is_documented(self, bundle: Path) -> None:
        text = (bundle / "references" / "visuals.md").read_text(encoding="utf-8")
        for tag in load_visuals():
            assert f"`{tag}`" in text, f"тип '{tag}' не попал в справочник"

    def test_the_index_in_document_md_lists_them_too(self, bundle: Path) -> None:
        text = (bundle / "references" / "document.md").read_text(encoding="utf-8")
        for tag in list(load_questions()) + list(load_visuals()):
            assert f"| `{tag}` |" in text

    def test_headings_stay_nested_under_one_title(self, bundle: Path) -> None:
        text = (bundle / "references" / "questions.md").read_text(encoding="utf-8")
        assert text.count("\n# ") == 0  # only the very first line is an H1
        assert text.startswith("# ")


class TestZeroDependencies:
    """The bundle must import nothing but the standard library.

    This is the promise that lets the skill run offline, in any sandbox, with
    no install step — and it is the kind of promise that breaks quietly, by
    someone adding a convenient import.
    """

    def test_the_shipped_package_imports_only_stdlib(self, bundle: Path) -> None:
        foreign = set()
        for path in (bundle / "physics_svg").rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    names = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom):
                    names = [node.module or ""] if node.level == 0 else []
                else:
                    continue
                for name in names:
                    root = name.split(".")[0]
                    if root and root != "physics_svg" and root not in sys.stdlib_module_names:
                        foreign.add(f"{path.name}: {name}")
        assert foreign == set(), f"в бандл просочились сторонние импорты: {sorted(foreign)}"


class TestEndToEnd:
    """Run the bundle the way a teacher's sandbox will."""

    @pytest.fixture(scope="class")
    def clean_env(self) -> dict[str, str]:
        environment = dict(os.environ)
        # Nothing from the repository may be reachable: the bundle has to
        # carry everything it needs.
        environment.pop("PYTHONPATH", None)
        return environment

    def test_it_builds_the_shipped_example(
        self, bundle: Path, clean_env: dict[str, str], tmp_path: Path
    ) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(bundle / "scripts" / "render.py"),
                "build",
                str(bundle / "examples" / "kinematics-9th-grade"),
                "-o",
                str(tmp_path / "out"),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=clean_env,
            cwd=tmp_path,
        )
        assert result.returncode == 0, result.stderr
        html = (tmp_path / "out" / "document.html").read_text(encoding="utf-8")
        assert '<div class="answers-section">' in html
        assert 'id="document-source"' in html

    def test_it_builds_a_word_document(
        self, bundle: Path, clean_env: dict[str, str], tmp_path: Path
    ) -> None:
        """The Word backend ships and runs with nothing installed — the whole
        promise of the bundle applied to a format that usually needs a
        library."""
        draft = tmp_path / "draft"
        (draft / "blocks").mkdir(parents=True)
        (draft / "document.json").write_text(
            '{"title": "Проба", "order": ["t"]}', encoding="utf-8"
        )
        (draft / "blocks" / "t.json").write_text(
            '{"id": "t", "type": "task", "blocks": ['
            '{"type": "text", "body": "Условие."}, {"type": "open", "answer": "42"}]}',
            encoding="utf-8",
        )
        result = subprocess.run(
            [
                sys.executable,
                str(bundle / "scripts" / "render.py"),
                "build",
                str(draft),
                "--format",
                "docx",
                "-o",
                str(tmp_path / "out"),
            ],
            capture_output=True, text=True, encoding="utf-8", env=clean_env, cwd=tmp_path,
        )
        assert result.returncode == 0, result.stderr
        data = (tmp_path / "out" / "document.docx").read_bytes()
        assert data[:2] == b"PK"

    def test_it_draws_a_library_spec(
        self, bundle: Path, clean_env: dict[str, str], tmp_path: Path
    ) -> None:
        spec = next((bundle / "library" / "instrument").glob("*.json"))
        output = tmp_path / "picture.svg"
        result = subprocess.run(
            [sys.executable, str(bundle / "scripts" / "render.py"),
             "visual", str(spec), "-o", str(output)],
            capture_output=True, text=True, encoding="utf-8", env=clean_env, cwd=tmp_path,
        )
        assert result.returncode == 0, result.stderr
        svg = output.read_text(encoding="utf-8")
        assert svg.startswith("<svg") and 'fill="#fff"' in svg

    def test_a_preview_refuses_a_format_it_cannot_make(
        self, bundle: Path, clean_env: dict[str, str], tmp_path: Path
    ) -> None:
        """`--block` builds an HTML preview and nothing else. Writing HTML for
        someone who asked for Word would look like success and be the wrong
        file — so the combination is refused, as `--handout --block` is."""
        draft = tmp_path / "draft"
        (draft / "blocks").mkdir(parents=True)
        (draft / "document.json").write_text('{"order": ["t"]}', encoding="utf-8")
        (draft / "blocks" / "t.json").write_text(
            '{"id": "t", "type": "text", "body": "Текст."}', encoding="utf-8"
        )
        result = subprocess.run(
            [
                sys.executable,
                str(bundle / "scripts" / "render.py"),
                "build", str(draft), "--block", "t", "--format", "docx",
            ],
            capture_output=True, text=True, encoding="utf-8", env=clean_env, cwd=tmp_path,
        )
        assert result.returncode == 2
        assert "--format" in result.stderr
        assert not list(draft.glob("*.preview.html"))

    def test_a_broken_draft_reports_problems_without_a_traceback(
        self, bundle: Path, clean_env: dict[str, str], tmp_path: Path
    ) -> None:
        draft = tmp_path / "draft"
        (draft / "blocks").mkdir(parents=True)
        (draft / "document.json").write_text('{"order": ["a"]}', encoding="utf-8")
        (draft / "blocks" / "a.json").write_text(
            '{"type": "task", "id": "a", "blocks": [{"type": "open"}]}', encoding="utf-8"
        )
        result = subprocess.run(
            [sys.executable, str(bundle / "scripts" / "render.py"), "build", str(draft)],
            capture_output=True, text=True, encoding="utf-8", env=clean_env, cwd=tmp_path,
        )
        assert result.returncode == 1
        assert "Traceback" not in result.stderr
        assert "нет условия" in result.stderr
