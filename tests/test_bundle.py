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
import io
import json
import os
import re
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))

import build_skill  # noqa: E402
from physics_svg import draft  # noqa: E402
from physics_svg.cli import FORMATS  # noqa: E402
from physics_svg.document import load_workspace as load_document_draft  # noqa: E402
from physics_svg.document.questions import load_all as load_questions  # noqa: E402
from physics_svg.presentation import load_workspace as load_presentation_draft  # noqa: E402
from physics_svg.presentation import parse_slide  # noqa: E402
from physics_svg.presentation.slides import load_all as load_slides  # noqa: E402
from physics_svg.visuals import load_all as load_visuals  # noqa: E402


@pytest.fixture(scope="module")
def bundle(tmp_path_factory: pytest.TempPathFactory) -> Path:
    destination = tmp_path_factory.mktemp("bundle")
    return build_skill.build(destination / "skill", make_zip=False)


class TestContents:
    def test_the_entry_point_and_manifest_are_there(self, bundle: Path) -> None:
        assert (bundle / "SKILL.md").exists()
        assert (bundle / "scripts" / "render.py").exists()
        assert (bundle / "physics_svg" / "__init__.py").exists()
        assert (bundle / "physics_svg" / "cli.py").exists()

    def test_the_package_ships_modules_only(self, bundle: Path) -> None:
        """The package travels as code and nothing else.

        The `specs/*.json`, `templates/*.json`, `doc.md` and `card.md` that
        sit beside the modules are already in `library/` and `references/`,
        and nothing reads them at run time — the properties that open them
        belong to the build, the suite and the site. Shipping them again was
        116 of the 329 files that got the bundle refused (FILE_LIMIT).
        """
        extra = [
            path.relative_to(bundle).as_posix()
            for path in (bundle / "physics_svg").rglob("*")
            if path.is_file() and path.suffix != ".py"
        ]
        assert extra == [], f"в пакет попали не-модули: {extra[:5]}"

    def test_every_reference_is_generated(self, bundle: Path) -> None:
        names = {path.name for path in (bundle / "references").glob("*.md")}
        assert names == {
            "document.md",
            "presentation.md",
            "questions.md",
            "slides.md",
            "symbols.md",
            "visuals.md",
        }

    def test_the_spec_library_ships(self, bundle: Path) -> None:
        for entry in load_visuals().values():
            shipped = list((bundle / "library" / entry.tag).glob("*.json"))
            assert len(shipped) == len(entry.specs), f"библиотека '{entry.tag}' неполная"

    def test_slide_templates_ship_unwrapped(self, bundle: Path) -> None:
        """What the model copies must be a slide, not an envelope.

        The name and the "when" are the catalogue's business; a file landing
        in `slides/` with them still inside would not validate.
        """
        for entry in load_slides().values():
            for template in entry.templates:
                path = bundle / "library" / "slides" / entry.tag / f"{template.slug}.json"
                assert path.exists(), f"шаблон '{entry.tag}/{template.slug}' не доехал"
                shipped = json.loads(path.read_text(encoding="utf-8"))
                assert shipped == template.slide
                assert parse_slide(shipped, template.slug) is not None

    def test_the_worked_example_ships_packed(self, bundle: Path, tmp_path: Path) -> None:
        """One file, and `unpack` gives back the folder it came from.

        Thirty-five files bought one example in a bundle whose files are
        counted. Packed they buy the same example for one — but only if the
        way back works, so this checks the round trip rather than the file.
        """
        packed = bundle / "examples" / "kinematics-9th-grade.json"
        assert packed.exists()
        draft.unpack(draft.read(packed), tmp_path / "lesson")
        workspace = load_document_draft(tmp_path / "lesson")
        assert workspace.document.title
        assert len(workspace.blocks) > 1
        # One lesson, two drafts side by side — the example teaches the shape
        # of a lesson as much as the content.
        lesson = load_presentation_draft(tmp_path / "lesson")
        assert len(lesson.slides) > 1

    def test_the_version_ships(self, bundle: Path) -> None:
        assert (bundle / "VERSION").read_text(encoding="utf-8").strip()

    def test_the_json_schema_does_not_ship(self, bundle: Path) -> None:
        """Nothing pointed at it, so it was weight in the archive and a
        wrong turn for a model listing the folder. `render.py schema` still
        prints it, from the same models, on demand."""
        assert not (bundle / "schema.json").exists()

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
        # Not «все N типов»: with four of them that reads as a grammar slip,
        # and the count is what has to stay true, not the case ending.
        assert f"типы иллюстраций ({len(load_visuals())})" in text
        assert f"все {len(load_slides())} видов слайдов" in text

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


#: What the model is allowed to read, in characters. Not tokens: a tokeniser
#: is a dependency and the bundle has none — for Russian prose the two move
#: together closely enough (roughly two characters to a token).
#:
#: SKILL.md is the strict one: it is read **whole, on every trigger**,
#: including the triggers that turn out to be a miss. A reference is read
#: when its genre comes up, so it may be larger — but only until it stops
#: being read selectively.
SKILL_BUDGET = 15_000
REFERENCE_BUDGET = 21_000


class TestContextBudget:
    """The bundle's real cost is what the model reads, and it grows quietly.

    Every other test here asks whether something is *present*: the kind is
    documented, the template ships, the path resolves. Nothing asked what it
    weighs, and the answer drifted — a workflow for one genre sat in SKILL.md
    where the other genre paid for it, and twenty-eight templates were
    printed in full inside the reference that also names their files.

    A number that fails is not a verdict that the text is bad. It is the
    moment to decide where the new text belongs: in the entry point, in a
    reference the genre reads, or in `library/` where nothing pays for it
    until it is opened.
    """

    def test_the_entry_point_stays_readable_in_one_go(self, bundle: Path) -> None:
        text = (bundle / "SKILL.md").read_text(encoding="utf-8")
        assert len(text) <= SKILL_BUDGET, (
            f"SKILL.md — {len(text)} символов при бюджете {SKILL_BUDGET}: "
            "он читается целиком на каждое срабатывание, в том числе ложное. "
            "Унеси добавленное в references/ того жанра, которому оно нужно"
        )

    def test_the_bundle_fits_through_the_uploader(self, bundle: Path) -> None:
        """The other budget here is context; this one is installation.

        claude.ai counts files, not bytes, and refuses past FILE_LIMIT. The
        bundle went over quietly — it built, it passed, and the refusal came
        from the uploader — so the number belongs where the other budgets
        are. `build` fails on it too; asserting here documents the rule.
        """
        files = [path for path in bundle.rglob("*") if path.is_file()]
        assert len(files) <= build_skill.FILE_LIMIT, (
            f"в бандле {len(files)} файлов при лимите {build_skill.FILE_LIMIT}: "
            "claude.ai такой архив не примет. Ищи, что уехало вторым экземпляром"
        )

    def test_no_reference_outgrows_a_selective_read(self, bundle: Path) -> None:
        for path in sorted((bundle / "references").glob("*.md")):
            size = len(path.read_text(encoding="utf-8"))
            assert size <= REFERENCE_BUDGET, (
                f"references/{path.name} — {size} символов при бюджете "
                f"{REFERENCE_BUDGET}: справочник такого размера читают целиком "
                "ради одного вида. Разрежь по видам или унеси примеры в library/"
            )


class TestReferencesFollowTheRegistries:
    def test_every_question_kind_is_documented(self, bundle: Path) -> None:
        text = (bundle / "references" / "questions.md").read_text(encoding="utf-8")
        for tag in load_questions():
            assert f"`{tag}`" in text, f"вид '{tag}' не попал в справочник"

    def test_every_illustration_is_documented(self, bundle: Path) -> None:
        text = (bundle / "references" / "visuals.md").read_text(encoding="utf-8")
        for tag in load_visuals():
            assert f"`{tag}`" in text, f"тип '{tag}' не попал в справочник"

    def test_every_slide_kind_is_documented(self, bundle: Path) -> None:
        text = (bundle / "references" / "slides.md").read_text(encoding="utf-8")
        for tag in load_slides():
            assert f"`{tag}`" in text, f"вид слайда '{tag}' не попал в справочник"

    def test_every_template_reaches_the_catalogue_and_the_fragment(self, bundle: Path) -> None:
        catalogue = (bundle / "references" / "presentation.md").read_text(encoding="utf-8")
        fragments = (bundle / "references" / "slides.md").read_text(encoding="utf-8")
        for entry in load_slides().values():
            for template in entry.templates:
                path = f"library/slides/{entry.tag}/{template.slug}.json"
                assert path in catalogue, f"шаблона '{path}' нет в каталоге"
                assert template.when in catalogue
                # And in the kind's own fragment, placed by the prose or
                # appended — a template invisible to the reference is a
                # template nobody takes.
                assert path in fragments, f"шаблона '{path}' нет в справочнике видов"

    def test_the_index_in_document_md_lists_them_too(self, bundle: Path) -> None:
        text = (bundle / "references" / "document.md").read_text(encoding="utf-8")
        for tag in list(load_questions()) + list(load_visuals()):
            assert f"| `{tag}` |" in text

    def test_headings_stay_nested_under_one_title(self, bundle: Path) -> None:
        text = (bundle / "references" / "questions.md").read_text(encoding="utf-8")
        assert text.count("\n# ") == 0  # only the very first line is an H1
        assert text.startswith("# ")

    def test_nothing_shipped_talks_about_the_player(self, bundle: Path) -> None:
        """The player was withdrawn (docs/pptx.md, phase P6) and the deck took
        its place. What the model reads has to say so.

        A reference that still describes the player teaches the model to
        promise a teacher behaviour PowerPoint does not have — clicking a
        plate to open one answer out of turn, an Esc list of stages, a title
        screen assembled from the manifest. The word survived the removal
        once, in eleven places; a grep is cheaper than finding out again from
        a lesson.
        """
        for path in [bundle / "SKILL.md", *sorted((bundle / "references").glob("*.md"))]:
            text = path.read_text(encoding="utf-8")
            stale = [line for line in text.splitlines() if "плеер" in line.lower()]
            assert not stale, (
                f"{path.name}: справочник описывает снятый плеер — "
                f"{len(stale)} строк, первая: {stale[0].strip()[:80]}"
            )


class TestZeroDependencies:
    """The bundle must import nothing but the standard library.

    This is the promise that lets the skill run offline, in any sandbox, with
    no install step — and it is the kind of promise that breaks quietly, by
    someone adding a convenient import.
    """

    def test_the_shipped_package_imports_only_stdlib(self, bundle: Path) -> None:
        foreign = set()
        modules = sorted((bundle / "physics_svg").rglob("*.py"))
        # Without this the check passes on an empty folder — it would have
        # nothing to walk and no way to say so.
        assert modules, "в пакете нет модулей: проверять было нечего"
        for path in modules:
            module = path.relative_to(bundle).as_posix()
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=module)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    names = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom):
                    names = [node.module or ""] if node.level == 0 else []
                else:
                    continue
                for imported in names:
                    root = imported.split(".")[0]
                    if root and root != "physics_svg" and root not in sys.stdlib_module_names:
                        foreign.add(f"{Path(module).name}: {imported}")
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

    def _unpack_the_example(
        self, bundle: Path, clean_env: dict[str, str], tmp_path: Path
    ) -> Path:
        """The shipped example, in the folder shape, through the shipped
        command — the first thing a teacher's session does with it."""
        lesson = tmp_path / "lesson"
        result = subprocess.run(
            [
                sys.executable,
                str(bundle / "scripts" / "render.py"),
                "unpack",
                str(bundle / "examples" / "kinematics-9th-grade.json"),
                str(lesson),
            ],
            capture_output=True, text=True, encoding="utf-8", env=clean_env, cwd=tmp_path,
        )
        assert result.returncode == 0, result.stderr
        return lesson

    def test_it_unpacks_and_builds_the_shipped_example(
        self, bundle: Path, clean_env: dict[str, str], tmp_path: Path
    ) -> None:
        lesson = self._unpack_the_example(bundle, clean_env, tmp_path)
        result = subprocess.run(
            [
                sys.executable,
                str(bundle / "scripts" / "render.py"),
                "build",
                str(lesson),
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

    def test_it_builds_the_shipped_lesson_presentation(
        self, bundle: Path, clean_env: dict[str, str], tmp_path: Path
    ) -> None:
        """The third artefact, end to end: a deck that opens, built by the
        packaged copy with nothing but the standard library — the picture
        drawn offline as native shapes, the formulas as OMML inside the
        file."""
        lesson = self._unpack_the_example(bundle, clean_env, tmp_path)
        result = subprocess.run(
            [
                sys.executable,
                str(bundle / "scripts" / "render.py"),
                "present",
                str(lesson),
                "-o",
                str(tmp_path / "out"),
            ],
            capture_output=True, text=True, encoding="utf-8", env=clean_env, cwd=tmp_path,
        )
        assert result.returncode == 0, result.stderr
        deck = (tmp_path / "out" / "presentation.pptx").read_bytes()
        assert deck[:2] == b"PK"
        with zipfile.ZipFile(io.BytesIO(deck)) as package:
            names = package.namelist()
            slides = [name for name in names if name.startswith("ppt/slides/slide")]
            assert len(slides) > 1, "урок собрался в один слайд"
            body = "".join(package.read(name).decode("utf-8") for name in slides)
        assert "a:custGeom" in body, "иллюстрация не дошла до слайда фигурами"
        assert "<m:oMath" in body, "формула не дошла до слайда как формула"

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
