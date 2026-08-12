#!/usr/bin/env python3
"""Validate a .pptx against the schemas of ECMA-376.

Office says «в презентации обнаружена ошибка» and names nothing. This names
it: the part, the line and what the schema expected. It was written the day a
deck turned out to carry `xml:space` on `a:t` — legal on Word's `w:t`,
forbidden in DrawingML, and enough to make PowerPoint offer to repair every
lesson with a picture in it.

**Not a test, and cannot be one.** It needs `lxml` and a schema set that has
to be downloaded, while `tests/` must run offline with the standard library
alone. So it lives here and is named in `evals/pptx.md` as a step before a
lesson is shown. What the tests keep is the one rule this found; what this
keeps is the next one, not yet broken.

**Schemas are Strict, packages are Transitional.** ECMA publishes only the
Strict set, and Office writes Transitional. The two differ in namespaces and
in a handful of value forms, so the schemas are rewritten on the way into the
cache and the known differences are filtered out of the findings — each with
a line saying why. A filter that grows without such lines is how a validator
turns into noise.

**Which is also why Word is not covered here.** DrawingML and PresentationML
barely moved between the editions; WordprocessingML did — `w:ind w:left` is
`w:start` in Strict, a table width is `9638` there and `"9638dxa"` here, a
tab stop is `right` against `end`. Validating `document.xml` this way prints
three hundred differences and no mistakes, and a tool nobody believes checks
nothing. A sheet is proved by `evals/word.md` and by Word itself.

    python tools/ooxml_lint.py --fetch      # разово: схемы в .cache/
    python tools/ooxml_lint.py урок.pptx    # проверить колоду
"""

from __future__ import annotations

import argparse
import io
import re
import sys
import urllib.request
import zipfile
from pathlib import Path
from typing import Any, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
CACHE = REPO_ROOT / ".cache" / "ooxml-xsd"

#: ECMA-376 Part 1, 5th edition. Pinned: the schemas are a fixed document,
#: and a linter that changes its mind between runs is worse than none.
SCHEMA_URL = (
    "https://ecma-international.org/wp-content/uploads/"
    "ECMA-376-1_5th_edition_december_2016.zip"
)
#: The 94 KB worth of schemas inside the 43 MB of specification.
SCHEMA_MEMBER = "OfficeOpenXML-XMLSchema-Strict.zip"

#: The Strict schemas import the `xml:` namespace without saying where it is,
#: which no validator can resolve. Four attributes is all of it they use.
XML_XSD = """<?xml version="1.0" encoding="utf-8"?>
<xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema"
  targetNamespace="http://www.w3.org/XML/1998/namespace"
  xmlns:xml="http://www.w3.org/XML/1998/namespace">
  <xsd:attribute name="lang" type="xsd:string"/>
  <xsd:attribute name="space" type="xsd:NCName"/>
  <xsd:attribute name="base" type="xsd:anyURI"/>
  <xsd:attribute name="id" type="xsd:ID"/>
</xsd:schema>
"""

DML = "http://schemas.openxmlformats.org/drawingml/2006/main"
PML = "http://schemas.openxmlformats.org/presentationml/2006/main"
MATH = "http://schemas.openxmlformats.org/officeDocument/2006/math"
MCE = "http://schemas.openxmlformats.org/markup-compatibility/2006"

#: Which schema owns a part, by the namespace of its root element. What is
#: not here is either packaging rather than ECMA-376 Part 1 — content types,
#: relationships, core properties — or WordprocessingML, which the header
#: explains; either way the part is reported as unchecked rather than passed
#: over in silence.
SCHEMA_OF = {
    PML: "pml.xsd",
    DML: "dml-main.xsd",
}

#: Differences between Strict and Transitional, not mistakes. One line each
#: on why, because the day this list is longer than it is honest, the tool
#: has stopped saying anything.
KNOWN_STRICT_ONLY = (
    # Percentages: Transitional writes 145000, Strict writes "145%".
    "ST_TextSpacingPercentOrPercentString",
    "ST_Percentage",
)


def fetch(cache: Path) -> None:
    """Put the schemas into the cache, rewritten so they fit a real file.

    Three rewrites, none of them optional:

    1. Namespaces `purl.oclc.org/ooxml/X/Y` -> the Transitional ones Office
       actually writes.
    2. `default="off"` in `wml.xsd`: Strict's `ST_OnOff` is a boolean, so the
       schema does not even load as published.
    3. The `xml:` import gets a `schemaLocation`, or `xml:space` — which
       `w:t` and `m:t` legitimately carry — resolves to nothing.
    """
    cache.mkdir(parents=True, exist_ok=True)
    print(f"Скачивается {SCHEMA_URL} (~43 МБ, разово)…")
    with urllib.request.urlopen(SCHEMA_URL, timeout=180) as response:
        outer = zipfile.ZipFile(io.BytesIO(response.read()))
    inner = zipfile.ZipFile(io.BytesIO(outer.read(SCHEMA_MEMBER)))
    for name in inner.namelist():
        if not name.endswith(".xsd"):
            continue
        text = inner.read(name).decode("utf-8")
        text = re.sub(
            r"http://purl\.oclc\.org/ooxml/([A-Za-z]+)/([A-Za-z]+)",
            r"http://schemas.openxmlformats.org/\1/2006/\2",
            text,
        )
        text = text.replace('default="off"', 'default="false"')
        text = text.replace('default="on"', 'default="true"')
        text = text.replace(
            '<xsd:import namespace="http://www.w3.org/XML/1998/namespace"/>',
            '<xsd:import namespace="http://www.w3.org/XML/1998/namespace"'
            ' schemaLocation="xml.xsd"/>',
        )
        (cache / Path(name).name).write_text(text, encoding="utf-8")
    (cache / "xml.xsd").write_text(XML_XSD, encoding="utf-8")
    print(f"Готово: {cache}")


def etree() -> Any:
    """`lxml`, or the reason it is not here.

    Imported on use rather than at the top: the tool is worth running from a
    checkout that has never installed anything, and a traceback is a worse
    way to say «поставь lxml» than a sentence.
    """
    try:
        from lxml import etree as module
    except ModuleNotFoundError:
        raise SystemExit("нужен lxml: python -m pip install lxml") from None
    return module


def schema(cache: Path, name: str, loaded: dict[str, Any]) -> Any:
    if name not in loaded:
        loaded[name] = etree().XMLSchema(etree().parse(str(cache / name)))
    return loaded[name]


def resolve_alternate_content(tree: Any) -> None:
    """Markup compatibility, decided the way the strictest reader decides it.

    `mc:AlternateContent` offers a choice to a reader that understands some
    extension and a fallback to one that does not. The schema knows nothing
    of either, so the fallback is spliced in and the choice dropped — which
    also means the formulas inside it leave this pass and are validated
    separately against the maths schema.
    """
    for alternate in list(tree.iter(f"{{{MCE}}}AlternateContent")):
        parent = alternate.getparent()
        if parent is None:
            continue
        position = list(parent).index(alternate)
        fallback = alternate.find(f"{{{MCE}}}Fallback")
        parent.remove(alternate)
        if fallback is not None:
            for offset, child in enumerate(list(fallback)):
                parent.insert(position + offset, child)


def findings_of(validator: Any, part: str) -> list[str]:
    return [
        f"{part}:{error.line}: {error.message}"
        for error in validator.error_log
        if not any(known in error.message for known in KNOWN_STRICT_ONLY)
    ]


def check(data: bytes, cache: Path) -> tuple[list[str], list[str]]:
    """(findings, parts nobody checked)."""
    loaded: dict[str, Any] = {}
    findings: list[str] = []
    unchecked: list[str] = []
    with zipfile.ZipFile(io.BytesIO(data)) as package:
        for part in sorted(package.namelist()):
            if not part.endswith(".xml"):
                unchecked.append(part)
                continue
            tree = etree().parse(io.BytesIO(package.read(part)))
            namespace = tree.getroot().tag.partition("}")[0].lstrip("{")
            name = SCHEMA_OF.get(namespace)
            if name is None:
                unchecked.append(part)
                continue
            # Maths first: the body pass resolves `mc:AlternateContent` by
            # dropping the branch the formulas live in.
            findings += _validate_maths(tree, schema(cache, "shared-math.xsd", loaded), part)
            findings += _validate_body(tree, schema(cache, name, loaded), part)
    return findings, unchecked


def _validate_body(tree: Any, validator: Any, part: str) -> list[str]:
    resolve_alternate_content(tree)
    if validator.validate(tree):
        return []
    return findings_of(validator, part)


def _validate_maths(tree: Any, validator: Any, part: str) -> list[str]:
    """The pass the body pass cannot make.

    A formula reaches a slide inside the branch of `mc:AlternateContent` that
    the body pass throws away, and `pml.xsd` would not know what to do with
    it anyway. So each `m:oMath` is lifted out and checked on its own, which
    is exactly how a reader that understands the extension sees it.
    """
    findings: list[str] = []
    for maths in tree.getroot().iter(f"{{{MATH}}}oMath"):
        fragment = etree().fromstring(etree().tostring(maths))
        if not validator.validate(fragment):
            findings += findings_of(validator, part)
    return findings


def _listed(unchecked: list[str]) -> str:
    """The unchecked parts, said in a line.

    Thirty relationship files printed one by one bury the one name that
    matters, and a report nobody reads to the end is a report that hides
    things. They are collapsed; anything else is named.
    """
    rels = [part for part in unchecked if part.endswith(".rels")]
    named = [part for part in unchecked if not part.endswith(".rels")]
    if rels:
        named.append(f"{len(rels)} файлов .rels")
    return ", ".join(named)


def main(argv: Optional[list[str]] = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("packages", nargs="*", help="файлы .pptx")
    parser.add_argument("--fetch", action="store_true", help="скачать схемы в .cache/ и выйти")
    parser.add_argument("--schemas", default=str(CACHE), help="папка со схемами")
    parser.add_argument("--quiet", action="store_true", help="не перечислять непроверенные части")
    args = parser.parse_args(argv)

    cache = Path(args.schemas)
    if args.fetch:
        fetch(cache)
        return 0
    if not args.packages:
        parser.error("нечего проверять")
    if not (cache / "pml.xsd").exists():
        raise SystemExit(
            f"нет схем в {cache}; разово: python tools/ooxml_lint.py --fetch"
        )

    total = 0
    for name in args.packages:
        path = Path(name)
        if not path.exists():
            raise SystemExit(f"не найдено: {path}")
        findings, unchecked = check(path.read_bytes(), cache)
        total += len(findings)
        print(f"== {path}")
        for line in findings:
            print(f"   {line}")
        if not findings:
            print("   схеме соответствует")
        if unchecked and not args.quiet:
            print(f"   не проверялись: {_listed(unchecked)}")
    return 1 if total else 0


if __name__ == "__main__":
    raise SystemExit(main())
