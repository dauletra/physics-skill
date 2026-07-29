"""Validation problems and the paths that locate them.

Error text is the one part of the codebase written in Russian: it is read by
the teacher and by the model authoring the JSON, not by a contributor.

Paths use an ASCII arrow (`blocks[2] -> series[0] -> points`) on purpose —
`->` survives a cp1251 Windows console, `→` kills the whole message.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Path:
    """Location of a value inside the parsed document."""

    parts: tuple[str, ...] = ()

    def child(self, name: str) -> "Path":
        return Path(self.parts + (name,))

    def index(self, i: int) -> "Path":
        if not self.parts:
            return Path((f"[{i}]",))
        return Path(self.parts[:-1] + (f"{self.parts[-1]}[{i}]",))

    def __str__(self) -> str:
        return " -> ".join(self.parts)


@dataclass(frozen=True)
class Problem:
    path: Path
    message: str

    def __str__(self) -> str:
        location = str(self.path)
        return f"{location}: {self.message}" if location else self.message


class Invalid(ValueError):
    """Raised by a spec's `check()` when a cross-field invariant is broken.

    `field` narrows the reported path to one field, so the author is pointed
    at the value to change rather than at the whole block.
    """

    def __init__(self, message: str, field: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.field = field


class SchemaError(ValueError):
    """All problems found in one parse, reported together.

    Collecting everything matters: fixing a draft one error per run is the
    slowest possible loop for both the teacher and the model.
    """

    def __init__(self, problems: list[Problem]) -> None:
        self.problems = problems
        super().__init__(str(self))

    def __str__(self) -> str:
        return "\n".join(str(problem) for problem in self.problems)
