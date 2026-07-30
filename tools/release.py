#!/usr/bin/env python3
"""Cut a release, or open the next development cycle.

A release lives on `main` and nowhere else: everything on that branch is what
a teacher downloads from the site, so the branch only moves at a release. The
development version that follows belongs on `next`, where nobody downloads it
and the number never faces a teacher.

    python tools/release.py 0.3.0     # on main: version, changelog, tag
    python tools/release.py --next    # on next: open 0.4.0.dev0

Neither mode pushes: `git push --follow-tags` stays a deliberate act.
"""

from __future__ import annotations

import argparse
import datetime
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "tools"))

import release_notes  # noqa: E402

INIT = REPO / "src" / "physics_svg" / "__init__.py"
CHANGELOG = REPO / "CHANGELOG.md"

#: The heading a release renames. Everything under it is what gets published.
UNRELEASED = "## [Не выпущено]"

VERSION_LINE = re.compile(r'^__version__ = "([^"]+)"$', re.M)
#: Only stable numbers are published: no prereleases before 1.0 (docs/contribute.md).
RELEASE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")
DEV = re.compile(r"^(\d+)\.(\d+)\.(\d+)\.dev(\d+)$")


# --- version numbers ----------------------------------------------------


def parse(version: str) -> tuple[int, int, int, int, int]:
    """Sort key: a development version precedes the release it leads to."""
    if match := RELEASE.match(version):
        major, minor, patch = (int(part) for part in match.groups())
        return (major, minor, patch, 1, 0)
    if match := DEV.match(version):
        major, minor, patch, serial = (int(part) for part in match.groups())
        return (major, minor, patch, 0, serial)
    raise SystemExit(f"версия {version} не вида X.Y.Z или X.Y.Z.devN")


def next_cycle(version: str, patch: bool = False) -> str:
    """The development version that follows a release."""
    major, minor, level, _, _ = parse(version)
    if patch:
        return f"{major}.{minor}.{level + 1}.dev0"
    return f"{major}.{minor + 1}.0.dev0"


def as_floor(tag: str) -> str | None:
    """The version a tag forbids going back to, if it is one.

    Only a stable tag bounds the next release. An early prerelease is still in
    the history (`v0.2.0a1`), and it is not a number this tool compares to.
    """
    version = tag.lstrip("v")
    return version if RELEASE.match(version) else None


def read_version() -> str:
    match = VERSION_LINE.search(INIT.read_text(encoding="utf-8"))
    if not match:
        raise SystemExit(f"в {INIT.name} не найдено объявление __version__")
    return match.group(1)


def write_version(version: str) -> None:
    text = INIT.read_text(encoding="utf-8")
    updated, count = VERSION_LINE.subn(f'__version__ = "{version}"', text)
    if count != 1:
        raise SystemExit(f"в {INIT.name} объявлений __version__ не одно, а {count}")
    INIT.write_text(updated, encoding="utf-8")


# --- changelog ----------------------------------------------------------


def unreleased_notes(text: str) -> str:
    """The body of «Не выпущено» — exactly what this release would publish."""
    headings = list(release_notes.SECTION.finditer(text))
    for i, heading in enumerate(headings):
        if not heading.group(0).startswith(UNRELEASED):
            continue
        end = headings[i + 1].start() if i + 1 < len(headings) else len(text)
        return text[heading.end() : end].strip()
    raise SystemExit(f"в CHANGELOG.md нет раздела «{UNRELEASED[3:]}»")


def release_changelog(text: str, version: str, today: str) -> str:
    """Name the accumulated notes with a version, and open an empty section.

    The body is not moved: the old heading is what gets renamed, so the notes
    stay attached to the release they describe.
    """
    return text.replace(UNRELEASED, f"{UNRELEASED}\n\n## [{version}] — {today}", 1)


# --- git ----------------------------------------------------------------


def _git(*args: str) -> str:
    done = subprocess.run(
        ["git", *args], cwd=REPO, capture_output=True, text=True, encoding="utf-8"
    )
    if done.returncode:
        raise SystemExit(done.stderr.strip() or f"git {' '.join(args)}: код {done.returncode}")
    return done.stdout.strip()


def _git_out(*args: str) -> str | None:
    """Output, or None if git refused — for questions that may legitimately
    have no answer: no such branch, no release yet."""
    done = subprocess.run(
        ["git", *args], cwd=REPO, capture_output=True, text=True, encoding="utf-8"
    )
    return done.stdout.strip() if done.returncode == 0 else None


def _git_ok(*args: str) -> bool:
    return _git_out(*args) is not None


def require_branch(name: str) -> None:
    current = _git("rev-parse", "--abbrev-ref", "HEAD")
    if current != name:
        raise SystemExit(f"этот шаг делается на ветке {name}, а сейчас {current}")


def require_clean() -> None:
    if _git("status", "--porcelain"):
        raise SystemExit("в рабочем дереве есть незакоммиченные изменения")


def last_release() -> str | None:
    """The newest version published on this line, or None before the first."""
    tag = _git_out("describe", "--tags", "--abbrev=0", "--match", "v*")
    return as_floor(tag) if tag else None


def require_merged(branch: str) -> None:
    """Release without the work, or a new cycle without the release — the two
    branches drifting apart is the only way this scheme breaks silently."""
    if not _git_ok("rev-parse", "--verify", "--quiet", f"refs/heads/{branch}"):
        raise SystemExit(f"ветки {branch} нет в этом клоне")
    if not _git_ok("merge-base", "--is-ancestor", branch, "HEAD"):
        raise SystemExit(f"ветка {branch} не влита в текущую — слей её перед этим шагом")


# --- modes --------------------------------------------------------------


def release(version: str, dry_run: bool) -> None:
    if not RELEASE.match(version):
        raise SystemExit(f"выпускается только номер вида X.Y.Z, а не {version}")
    require_branch("main")
    require_clean()
    require_merged("next")
    if _git("tag", "--list", f"v{version}"):
        raise SystemExit(f"тег v{version} уже существует")

    # Against the last tag, not against the number in the working tree: that
    # one is the development label carried over from `next`, and comparing to
    # it would let an opened cycle decide the size of the next release.
    current = read_version()
    previous = last_release()
    if previous and parse(version) <= parse(previous):
        raise SystemExit(f"версия {version} не старше выпущенной {previous}")

    text = CHANGELOG.read_text(encoding="utf-8")
    if not unreleased_notes(text):
        raise SystemExit(f"раздел «{UNRELEASED[3:]}» пуст — выпускать нечего")

    today = datetime.date.today().isoformat()
    if dry_run:
        print(f"{current} -> {version}, раздел CHANGELOG.md от {today}, тег v{version}")
        return

    write_version(version)
    CHANGELOG.write_text(release_changelog(text, version, today), encoding="utf-8")
    _git("commit", "-am", f"Версия {version}")
    # Annotated, because `git push --follow-tags` — the command below and the
    # one in docs/contribute.md — silently ignores lightweight tags.
    _git("tag", "-a", f"v{version}", "-m", f"Версия {version}")
    print(f"Готово: {version} закоммичена и помечена тегом v{version}")
    print("Дальше: git push --follow-tags, затем влить main в next и release.py --next")


def open_next(patch: bool, dry_run: bool) -> None:
    require_branch("next")
    require_clean()
    require_merged("main")

    current = read_version()
    if not RELEASE.match(current):
        raise SystemExit(f"версия {current} уже не выпуск — цикл открыт")
    following = next_cycle(current, patch)

    if dry_run:
        print(f"{current} -> {following}")
        return

    write_version(following)
    _git("commit", "-am", f"Открыт цикл {following}")
    print(f"Готово: {following}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("version", nargs="?", help="номер выпуска, например 0.3.0")
    parser.add_argument(
        "--next",
        dest="open_next",
        action="store_true",
        help="открыть следующий цикл разработки (делается на ветке next)",
    )
    parser.add_argument(
        "--patch", action="store_true", help="с --next: патчевый цикл вместо минорного"
    )
    parser.add_argument("--dry-run", action="store_true", help="показать правки, но не делать их")
    args = parser.parse_args()

    if args.open_next == bool(args.version):
        parser.error("нужен либо номер выпуска, либо --next")
    if args.patch and not args.open_next:
        parser.error("--patch работает только вместе с --next")

    if args.open_next:
        open_next(args.patch, args.dry_run)
    else:
        release(args.version, args.dry_run)


if __name__ == "__main__":
    main()
