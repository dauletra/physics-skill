"""A subset of LaTeX -> OMML, the maths of a Word document.

The only place `m:` elements are written, exactly as `wml.py` is the only
place `w:` elements are. If an `f'<m:f>'` appears anywhere else, a constructor
is missing here.

Two steps, on purpose. `parse` turns LaTeX into a small tree; `omml` prints
that tree. The split is what makes the subset checkable: what is supported is
a property of the tree, tests are written against it, and nobody has to read
XML to see whether `x_0^2` came out right.

**The subset is closed.** Fractions, roots, powers, indices, brackets,
upright text, Greek letters and the comparison operators — the things a
physics sheet actually holds, and nothing else. A formula outside it is not
guessed at: `convert` returns the reason instead, the Word backend prints the
formula as the author typed it, and the build says so out loud. A converter
that quietly mangles a formula is worse than one that admits it cannot.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional, Union

from physics_svg.document.emit.docx.wml import el, escape

#: Word has one maths font, and a formula written in anything else stops
#: looking like a formula.
MATH_FONT = "Cambria Math"

#: Thin space: `\,` and its relatives. Wider ones are not worth telling apart
#: on a school worksheet.
_THIN_SPACE = " "


# --- the tree -----------------------------------------------------------


@dataclass(frozen=True)
class Sym:
    """A stretch of characters. Italic by default — that is how a variable
    looks; `upright` is `\\text{…}`, where the author means words or units."""

    text: str
    upright: bool = False


@dataclass(frozen=True)
class Row:
    """Things one after another."""

    items: tuple["Node", ...]


@dataclass(frozen=True)
class Frac:
    num: "Node"
    den: "Node"


@dataclass(frozen=True)
class Rad:
    """A root. `degree` is `\\sqrt[3]{…}`; without it the sign has no index."""

    radicand: "Node"
    degree: Optional["Node"] = None


@dataclass(frozen=True)
class Scripts:
    """A base with a power, an index, or both."""

    base: "Node"
    sup: Optional["Node"] = None
    sub: Optional["Node"] = None


@dataclass(frozen=True)
class Delim:
    """Brackets that grow with what is inside them — the reason `m:d` exists
    and plain characters are not enough."""

    inner: "Node"
    left: str = "("
    right: str = ")"


Node = Union[Sym, Row, Frac, Rad, Scripts, Delim]


class Unknown(ValueError):
    """Something outside the subset, named so the build can say what."""


# --- what a command means ------------------------------------------------

_GREEK = {
    "alpha": "α", "beta": "β", "gamma": "γ", "delta": "δ", "epsilon": "ε",
    "varepsilon": "ε", "zeta": "ζ", "eta": "η", "theta": "θ", "iota": "ι",
    "kappa": "κ", "lambda": "λ", "mu": "μ", "nu": "ν", "xi": "ξ", "pi": "π",
    "rho": "ρ", "sigma": "σ", "tau": "τ", "upsilon": "υ", "phi": "φ",
    "varphi": "φ", "chi": "χ", "psi": "ψ", "omega": "ω",
    "Gamma": "Γ", "Delta": "Δ", "Theta": "Θ", "Lambda": "Λ", "Xi": "Ξ",
    "Pi": "Π", "Sigma": "Σ", "Upsilon": "Υ", "Phi": "Φ", "Psi": "Ψ",
    "Omega": "Ω",
}

_OPERATORS = {
    "cdot": "·", "times": "×", "div": "÷", "pm": "±", "mp": "∓",
    "approx": "≈", "neq": "≠", "ne": "≠", "equiv": "≡", "sim": "∼",
    "leq": "≤", "le": "≤", "geq": "≥", "ge": "≥", "ll": "≪", "gg": "≫",
    "to": "→", "rightarrow": "→", "leftarrow": "←", "Rightarrow": "⇒",
    "infty": "∞", "propto": "∝", "perp": "⊥", "parallel": "∥",
    "circ": "∘", "prime": "′", "ldots": "…", "dots": "…", "angle": "∠",
}

#: `\{`, `\%`, `\ ` and the rest: a character the author had to escape.
_ESCAPED = set("{}$&#%_ ")

_SYMBOLS = {**_GREEK, **_OPERATORS}

#: Brackets that may grow. The closing one is looked up by the opening one,
#: so an unmatched bracket stays an ordinary character instead of eating the
#: rest of the formula.
_BRACKETS = {"(": ")", "[": "]"}

#: One token: a command, an escaped character, a piece of syntax, a run of
#: spaces (which maths ignores), or a single character.
_TOKEN = re.compile(r"\\[A-Za-z]+|\\.|[{}^_\[\]()]|\s+|.", re.S)


# --- LaTeX -> tree -------------------------------------------------------


def parse(latex: str) -> Node:
    """The formula as a tree. Raises `Unknown` for anything outside the
    subset, naming what it was."""
    parser = _Parser(_TOKEN.findall(latex))
    node = parser.row(())
    parser.skip()
    if parser.peek() is not None:
        raise Unknown(f"лишняя скобка '{parser.peek()}'")
    return node


class _Parser:
    def __init__(self, tokens: list[str]) -> None:
        self.tokens = tokens
        self.at = 0

    def peek(self) -> Optional[str]:
        return self.tokens[self.at] if self.at < len(self.tokens) else None

    def take(self) -> str:
        token = self.tokens[self.at]
        self.at += 1
        return token

    def skip(self) -> None:
        """Maths ignores the spaces an author typed — `\\,` is how a space is
        asked for on purpose. Inside `\\text{…}` they are kept, which is why
        this is called by the parser and not by the tokeniser."""
        while self.at < len(self.tokens) and self.tokens[self.at].isspace():
            self.at += 1

    def row(self, stop: tuple[str, ...]) -> Node:
        """Items until one of `stop` (left unconsumed) or the end."""
        items: list[Node] = []
        while True:
            self.skip()
            token = self.peek()
            if token is None or token in stop:
                break
            if token == "}":
                # A group is structure: an unbalanced brace means the formula
                # was not understood, and guessing where it ends would print
                # something the author did not write. Round brackets are not
                # structure — an odd one is just a character, as in «(0; 5]».
                raise Unknown("лишняя скобка '}'")
            items.append(self._scripted())
        return items[0] if len(items) == 1 else Row(tuple(items))

    def _scripted(self) -> Node:
        """An atom with whatever `^` and `_` follow it."""
        base = self._atom()
        sup: Optional[Node] = None
        sub: Optional[Node] = None
        self.skip()
        while self.peek() in ("^", "_"):
            mark = self.take()
            self.skip()
            if self.peek() is None:
                raise Unknown(f"после '{mark}' ничего нет")
            value = self._atom()
            self.skip()
            if mark == "^":
                sup = value
            else:
                sub = value
        if sup is None and sub is None:
            return base
        return Scripts(base, sup, sub)

    def _atom(self) -> Node:
        self.skip()
        token = self.take()
        if token == "{":
            inner = self.row(("}",))
            self._expect("}")
            return inner
        if token in _BRACKETS and self._closes(token) is not None:
            inner = self.row((_BRACKETS[token],))
            self._expect(_BRACKETS[token])
            return Delim(inner, token, _BRACKETS[token])
        if token.startswith("\\"):
            return self._command(token[1:])
        return Sym(token)

    def _command(self, name: str) -> Node:
        if name == "frac":
            return Frac(self._argument("\\frac"), self._argument("\\frac"))
        if name == "sqrt":
            degree = None
            self.skip()
            if self.peek() == "[":
                self.take()
                degree = self.row(("]",))
                self._expect("]")
            return Rad(self._argument("\\sqrt"), degree)
        if name in ("text", "mathrm", "operatorname"):
            return Sym(self._verbatim(name), upright=True)
        if name in ("left", "right"):
            return self._grown(name)
        if name in _SYMBOLS:
            return Sym(_SYMBOLS[name])
        if name in (",", ";", ":", "!", " ", "quad", "qquad"):
            return Sym(_THIN_SPACE, upright=True)
        if name in _ESCAPED:
            return Sym(name)
        raise Unknown(f"неизвестная команда '\\{name}'")

    def _grown(self, name: str) -> Node:
        """`\\left( … \\right)`: the same delimiter, said the long way."""
        if name == "right":
            raise Unknown("'\\right' без '\\left'")
        opening = self.take() if self.peek() is not None else ""
        if opening not in _BRACKETS:
            raise Unknown(f"после '\\left' ожидается скобка, а не '{opening}'")
        inner = self.row(("\\right",))
        self._expect("\\right")
        closing = self.take() if self.peek() is not None else ""
        if closing != _BRACKETS[opening]:
            raise Unknown(f"'\\left{opening}' закрыт '{closing}'")
        return Delim(inner, opening, closing)

    def _argument(self, command: str) -> Node:
        """One argument: a group, or the single token that follows — `\\frac12`
        is a half in TeX, and an author who writes it means one."""
        self.skip()
        if self.peek() is None:
            raise Unknown(f"у '{command}' не хватает аргумента")
        return self._atom()

    def _verbatim(self, command: str) -> str:
        """The contents of `\\text{…}` as typed: spaces and all, no maths."""
        if self.peek() != "{":
            raise Unknown(f"после '\\{command}' ожидается '{{'")
        self.take()
        depth = 1
        collected: list[str] = []
        while True:
            token = self.peek()
            if token is None:
                raise Unknown(f"'\\{command}' не закрыт")
            self.take()
            if token == "{":
                depth += 1
            elif token == "}":
                depth -= 1
                if depth == 0:
                    break
            collected.append(token)
        return "".join(collected)

    def _expect(self, token: str) -> None:
        self.skip()
        if self.peek() != token:
            raise Unknown(f"ожидается '{token}'")
        self.take()

    def _closes(self, opening: str) -> Optional[int]:
        """Where the bracket opened at the cursor is closed, or `None`.

        Checked before a bracket becomes `m:d`, so `(0; 5]` keeps its
        characters instead of making the whole formula untranslatable.
        """
        closing = _BRACKETS[opening]
        depth = 0
        for index in range(self.at, len(self.tokens)):
            token = self.tokens[index]
            if token == opening:
                depth += 1
            elif token == closing:
                if depth == 0:
                    return index
                depth -= 1
        return None


# --- tree -> OMML --------------------------------------------------------


def omml(node: Node) -> str:
    if isinstance(node, Row):
        return "".join(omml(item) for item in _merged(node.items))
    if isinstance(node, Sym):
        return _run(node.text, node.upright)
    if isinstance(node, Frac):
        return el("m:f", children=_part("m:num", node.num) + _part("m:den", node.den))
    if isinstance(node, Rad):
        # `m:deg` is required even when empty — an empty one plus `m:degHide`
        # is how a plain square root is written.
        properties = "" if node.degree is not None else el(
            "m:radPr", children=el("m:degHide", {"m:val": "1"})
        )
        degree = _part("m:deg", node.degree) if node.degree is not None else el("m:deg")
        return el("m:rad", children=properties + degree + _part("m:e", node.radicand))
    if isinstance(node, Scripts):
        return _scripts(node)
    if isinstance(node, Delim):
        properties = ""
        if (node.left, node.right) != ("(", ")"):
            properties = el(
                "m:dPr",
                children=el("m:begChr", {"m:val": node.left})
                + el("m:endChr", {"m:val": node.right}),
            )
        return el("m:d", children=properties + _part("m:e", node.inner))
    raise Unknown(f"узел '{type(node).__name__}' не печатается")


def _scripts(node: Scripts) -> str:
    base = _part("m:e", node.base)
    if node.sup is not None and node.sub is not None:
        return el("m:sSubSup", children=base + _part("m:sub", node.sub) + _part("m:sup", node.sup))
    if node.sup is not None:
        return el("m:sSup", children=base + _part("m:sup", node.sup))
    return el("m:sSub", children=base + _part("m:sub", node.sub))


def _part(tag: str, node: Optional[Node]) -> str:
    return el(tag, children=omml(node) if node is not None else "")


def _run(text: str, upright: bool) -> str:
    """One run of a formula.

    Upright text keeps the document's own font: units and words inside a
    formula should read like the sentence around them, not like a variable.
    """
    if not text:
        return ""
    properties = el("m:rPr", children=el("m:nor")) if upright else ""
    fonts = (
        ""
        if upright
        else el(
            "w:rPr",
            children=el("w:rFonts", {"w:ascii": MATH_FONT, "w:hAnsi": MATH_FONT}),
        )
    )
    return el(
        "m:r",
        children=properties + fonts + el("m:t", {"xml:space": "preserve"}, escape(text)),
    )


def _merged(items: tuple[Node, ...]) -> list[Node]:
    """Neighbouring characters of the same kind become one run.

    Not cosmetics: `document.xml` is read in diffs, and one run per letter
    makes a two-symbol formula unreadable.
    """
    merged: list[Node] = []
    for item in items:
        if isinstance(item, Row) and not item.items:
            continue  # a space the author typed
        previous = merged[-1] if merged else None
        if (
            isinstance(item, Sym)
            and isinstance(previous, Sym)
            and previous.upright == item.upright
        ):
            merged[-1] = Sym(previous.text + item.text, item.upright)
        else:
            merged.append(item)
    return merged


# --- what the backend calls ---------------------------------------------


def convert(latex: str, *, display: bool = False) -> tuple[Optional[str], str]:
    """The formula as OMML, or `None` and the reason it was left alone.

    Never raises: a formula outside the subset is a fact about the sheet, not
    a reason to refuse building it. The caller prints the original text and
    reports the reason.
    """
    if not latex.strip():
        return None, "формула пустая"
    try:
        tree = parse(latex)
        body = omml(tree)
    except Unknown as error:
        return None, str(error)
    if not body:
        return None, "формула пустая"
    formula = el("m:oMath", children=body)
    return (el("m:oMathPara", children=formula) if display else formula), ""
