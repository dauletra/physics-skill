"""A draft folder as one file, and back.

The folder is the **working** shape: one file per block, one per slide, so
an edit touches one file and the model never rewrites a document to change a
sentence. One file is the **portable** shape: it travels through a session
boundary, ships as the worked example, and is what `document.html` has
carried embedded in it all along.

So this is not a new format. It is the shape `Workspace.source` already had,
given a name and a way back — before, the way back was prose in SKILL.md
telling the model to extract the JSON and lay twenty-two files out by hand.

This module is **above both genres**, and that is why it exists at all:
`document` and `presentation` know nothing of each other (CLAUDE.md), but a
lesson folder holds a sheet and a deck side by side, and something has to
pair a manifest with its items. Nothing here reaches into either genre
beyond its loader and its raw source.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from physics_svg.document import load_workspace as load_document
from physics_svg.presentation import load_workspace as load_presentation

#: Manifest name (without `.json`) and the key holding its items — which is
#: also the directory they are written to. Adding a genre is adding a row.
GENRES = (("document", "blocks"), ("presentation", "slides"))

#: The draft embedded in a finished page. Its payload escapes every `<` as
#: `<`, so nothing inside can close the tag early and a non-greedy match
#: cannot stop short.
_EMBEDDED = re.compile(
    r'<script type="application/json" id="document-source">(.*?)</script>', re.S
)

#: An id becomes a file name, so it may only hold what a file name may hold.
#: This is a safety check and not a style one: a packed draft can arrive from
#: a teacher's downloaded page, and `../` in an id would write outside the
#: folder that was asked for.
_ID = re.compile(r"^[A-Za-z0-9._-]+$")
_RESERVED = {".", ".."}


class DraftError(ValueError):
    """Problems with a packed draft, reported together — the same deal the
    folder loaders give: one pass fixes everything."""

    def __init__(self, problems: list[str]) -> None:
        self.problems = problems
        super().__init__("\n".join(problems))


def pack(folder: str | Path) -> dict[str, Any]:
    """The folder as one object, verbatim.

    Loaded through the real loaders rather than read as files: packing a
    draft that does not validate would produce an example nobody can build,
    and the error belongs to whoever is packing.
    """
    directory = Path(folder)
    packed: dict[str, Any] = {}
    if (directory / "document.json").exists():
        packed.update(load_document(directory).source)
    if (directory / "presentation.json").exists():
        packed.update(load_presentation(directory).source)
    if not packed:
        raise DraftError([f"в {directory} нет ни document.json, ни presentation.json"])
    return packed


def unpack(packed: Any, folder: str | Path) -> dict[str, int]:
    """Write the folder the loaders expect. Returns what was written.

    Everything is checked before anything is written: half a folder is worse
    than none, because it looks like a draft.
    """
    directory = Path(folder)
    problems = _problems(packed)
    if problems:
        raise DraftError(problems)
    if occupied := _occupied(directory):
        raise DraftError(
            [f"в {directory} уже есть черновик ({occupied}) — укажи другую папку"]
        )

    written: dict[str, int] = {}
    for manifest, items in GENRES:
        if manifest not in packed:
            continue
        directory.mkdir(parents=True, exist_ok=True)
        _write(directory / f"{manifest}.json", packed[manifest])
        target = directory / items
        target.mkdir(exist_ok=True)
        for raw in packed[items]:
            _write(target / f"{raw['id']}.json", raw)
        written[items] = len(packed[items])
    return written


def read(path: str | Path) -> Any:
    """A packed draft from a file — the JSON itself, or the one embedded in a
    finished page. A teacher brings back whichever they were given."""
    source = Path(path)
    if not source.exists():
        raise DraftError([f"не найден файл: {source}"])
    text = source.read_text(encoding="utf-8")
    if source.suffix.lower() in (".html", ".htm"):
        match = _EMBEDDED.search(text)
        if match is None:
            raise DraftError(
                [
                    f"в {source.name} нет встроенного черновика. Так собирается "
                    "раздаточный вариант (--handout): в нём черновика нет намеренно, "
                    "иначе ответы читались бы в исходном коде страницы. "
                    "Нужен обычный document.html"
                ]
            )
        text = match.group(1)
    try:
        return json.loads(text)
    except json.JSONDecodeError as error:
        raise DraftError([f"{source.name}: невалидный JSON — {error}"]) from None


def _problems(packed: Any) -> list[str]:
    if not isinstance(packed, dict):
        return ["черновик должен быть объектом JSON"]

    problems: list[str] = []
    known = {name for genre in GENRES for name in genre}
    if unknown := sorted(set(packed) - known):
        problems.append(
            f"неизвестные разделы: {', '.join(unknown)}; бывают {', '.join(sorted(known))}"
        )
    if not any(manifest in packed for manifest, _ in GENRES):
        problems.append(
            "в файле нет ни 'document', ни 'presentation' — это не черновик"
        )

    for manifest, items in GENRES:
        if manifest not in packed:
            if items in packed:
                problems.append(f"есть '{items}', но нет '{manifest}'")
            continue
        if not isinstance(packed[manifest], dict):
            problems.append(f"'{manifest}' должен быть объектом")
        if not isinstance(packed.get(items), list):
            problems.append(f"'{items}' должен быть списком")
            continue
        problems += _id_problems(packed[items], items)
    return problems


def _id_problems(raws: list[Any], items: str) -> list[str]:
    problems: list[str] = []
    seen: set[str] = set()
    for index, raw in enumerate(raws):
        where = f"{items}[{index}]"
        if not isinstance(raw, dict):
            problems.append(f"{where}: должен быть объектом")
            continue
        identifier = raw.get("id")
        if not isinstance(identifier, str) or not identifier:
            problems.append(f"{where}: нет 'id' — по нему называется файл")
        elif identifier in _RESERVED or not _ID.match(identifier):
            problems.append(
                f"{where}: id '{identifier}' не годится именем файла — "
                "буквы латиницы, цифры, дефис и подчёркивание"
            )
        elif identifier in seen:
            problems.append(f"{where}: id '{identifier}' уже встречался — файл был бы затёрт")
        else:
            seen.add(identifier)
    return problems


def _occupied(directory: Path) -> str | None:
    existing = [
        f"{manifest}.json"
        for manifest, _ in GENRES
        if (directory / f"{manifest}.json").exists()
    ]
    return ", ".join(existing) if existing else None


def _write(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
