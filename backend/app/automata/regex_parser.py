"""
Regex parsing for the direct-method (followpos / Aho-Ullman) DFA engine.

Supported syntax:
    a b        literal characters
    ab         concatenation (implicit, no operator needed)
    a|b        union / alternation
    a*         Kleene star (zero or more)
    a+         one or more, desugars to  a . a*
    a?         optional, desugars to  a | epsilon
    (a|b)c     grouping with parentheses
    [abc]      character class, desugars to  a|b|c
    [a-z]      character class range, desugars to  a|b|...|z
    \\c        escaped literal, treats the next character as itself
              (use this for '(', ')', '|', '*', '+', '?', '[', ']', '\\')

Not supported yet (kept out on purpose to keep the direct method
readable for the report): negated character classes ([^abc]) and the
'.' wildcard. Both can be added later as more desugaring rules without
touching the followpos algorithm itself.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


class RegexSyntaxError(ValueError):
    """Raised when the input regex cannot be parsed."""


# ---------------------------------------------------------------------------
# AST node types
# ---------------------------------------------------------------------------
# Every node type below is deliberately tiny: the followpos algorithm in
# direct_dfa.py only needs to tell these apart and recurse into children.


@dataclass
class Leaf:
    """A single input symbol at a specific position in the augmented regex.

    `position` is assigned later, once the whole tree (including the
    end-marker leaf) is built, by direct_dfa.assign_positions.
    """

    symbol: str
    position: Optional[int] = None


@dataclass
class Epsilon:
    """The empty-string leaf, used for `a?` and never assigned a position."""

    pass


@dataclass
class Concat:
    left: "Node"
    right: "Node"


@dataclass
class Union:
    left: "Node"
    right: "Node"


@dataclass
class Star:
    child: "Node"


Node = Leaf | Epsilon | Concat | Union | Star


def clone(node: Node) -> Node:
    """Deep-copy a subtree with fresh Leaf objects.

    Needed for `a+`, which desugars to `a . a*`: the two copies of `a`
    must be distinct Leaf instances so each gets its own position later.
    Reusing the same Leaf object in two places would mean the second
    position assignment silently overwrites the first.
    """
    if isinstance(node, Leaf):
        return Leaf(symbol=node.symbol)
    if isinstance(node, Epsilon):
        return Epsilon()
    if isinstance(node, Concat):
        return Concat(clone(node.left), clone(node.right))
    if isinstance(node, Union):
        return Union(clone(node.left), clone(node.right))
    if isinstance(node, Star):
        return Star(clone(node.child))
    raise TypeError(f"Unknown node type: {type(node)!r}")


def to_regex(node: Node) -> str:
    """Render a subtree back to regex source.

    Used by the teaching layer's explanations: once `a+` has been
    desugared to `a . a*` the original text is gone, so the step that
    reports the rewrite has to render both sides from the tree itself.
    """
    return _render(node, 0)


def _render(node: Node, min_prec: int) -> str:
    # Precedence: union 1, concatenation 2, star/atom 3. A child is
    # parenthesized only when its own precedence is below what the
    # surrounding context requires.
    if isinstance(node, Leaf):
        return f"\\{node.symbol}" if node.symbol in _SPECIAL else node.symbol
    if isinstance(node, Epsilon):
        return "ε"
    if isinstance(node, Union):
        text = f"{_render(node.left, 1)}|{_render(node.right, 1)}"
        return f"({text})" if min_prec > 1 else text
    if isinstance(node, Concat):
        text = f"{_render(node.left, 2)}{_render(node.right, 2)}"
        return f"({text})" if min_prec > 2 else text
    if isinstance(node, Star):
        return f"{_render(node.child, 3)}*"
    raise TypeError(f"Unknown node type: {type(node)!r}")


# ---------------------------------------------------------------------------
# Serialization for the teaching layer
#
# These live here, next to the node types, because both construction
# methods need them: the direct method annotates the tree with
# nullable/firstpos/lastpos, and Thompson's construction highlights the
# node whose fragment it is currently building.
# ---------------------------------------------------------------------------

def assign_node_ids(root: Node) -> dict[int, str]:
    """Give every node a stable pre-order id ("n1", "n2", ...).

    A side table keyed by id(node) rather than a new dataclass field:
    these nodes are @dataclass instances with a generated __eq__ that the
    tests compare directly, and clone() above would have to be taught to
    copy (or deliberately not copy) anything we added.
    """
    ids: dict[int, str] = {}

    def visit(node: Node) -> None:
        ids[id(node)] = f"n{len(ids) + 1}"
        if isinstance(node, (Concat, Union)):
            visit(node.left)
            visit(node.right)
        elif isinstance(node, Star):
            visit(node.child)

    visit(root)
    return ids


def tree_to_dict(
    node: Node,
    *,
    attrs: dict = None,
    followpos: dict = None,
    node_ids: dict = None,
    end_marker: str = None,
) -> dict:
    """Serialize a syntax tree, optionally annotated with the attributes
    the followpos algorithm computes.

    `attrs` maps id(node) -> (nullable, firstpos, lastpos); this module
    does not care who built it. With attrs=None every annotation field is
    null, which is what the plain "here is the parse tree" view wants, and
    what Thompson's construction uses.

    Child keys are the dataclass field names (left / right / child) so the
    frontend's generic AstTreeView labels them with no changes.
    """
    if node_ids is None:
        node_ids = assign_node_ids(node)

    nullable = first = last = None
    if attrs is not None and id(node) in attrs:
        nullable, first, last = attrs[id(node)]

    out: dict = {
        "id": node_ids.get(id(node)),
        "kind": type(node).__name__,
        "symbol": None,
        "position": None,
        "nullable": nullable,
        "firstpos": sorted(first) if first is not None else None,
        "lastpos": sorted(last) if last is not None else None,
        "followpos": None,
    }

    if isinstance(node, Leaf):
        # The real end marker is a Private Use Area character and must
        # never reach the UI as a glyph; the textbook writes it as '#'.
        if end_marker is not None and node.symbol == end_marker:
            out["symbol"] = "#"
            out["is_end_marker"] = True
        else:
            out["symbol"] = node.symbol
        out["position"] = node.position
        # followpos belongs to positions, not to nodes, so only a leaf
        # ever carries one.
        if followpos is not None and node.position in followpos:
            out["followpos"] = sorted(followpos[node.position])

    kwargs = dict(
        attrs=attrs, followpos=followpos, node_ids=node_ids, end_marker=end_marker
    )
    if isinstance(node, (Concat, Union)):
        out["left"] = tree_to_dict(node.left, **kwargs)
        out["right"] = tree_to_dict(node.right, **kwargs)
    elif isinstance(node, Star):
        out["child"] = tree_to_dict(node.child, **kwargs)

    return out


# ---------------------------------------------------------------------------
# Tokenizer
# ---------------------------------------------------------------------------

_SPECIAL = set("()|*+?[]\\")


def _tokenize(pattern: str) -> list[str]:
    """Split the pattern into a flat token list.

    Character classes are expanded here into a single 'CHARCLASS:<chars>'
    pseudo-token so the parser can treat `[abc]` the same way it treats
    a literal character, just with more than one symbol inside it.
    """
    tokens: list[str] = []
    i = 0
    n = len(pattern)
    while i < n:
        c = pattern[i]
        if c == "\\":
            if i + 1 >= n:
                raise RegexSyntaxError(
                    "Dangling escape character '\\' at end of pattern"
                )
            tokens.append(f"CHAR:{pattern[i + 1]}")
            i += 2
            continue
        if c == "[":
            end = pattern.find("]", i)
            if end == -1:
                raise RegexSyntaxError("Unterminated character class, missing ']'")
            chars = _expand_char_class(pattern[i + 1 : end])
            tokens.append(f"CHARCLASS:{chars}")
            i = end + 1
            continue
        if c in "()|*+?":
            tokens.append(c)
            i += 1
            continue
        tokens.append(f"CHAR:{c}")
        i += 1
    return tokens


def _expand_char_class(body: str) -> str:
    """Expand the inside of `[...]` (e.g. 'a-zA-Z0-9') into a string of
    every individual character it represents, with duplicates removed
    but order preserved (so error messages / tests stay predictable).
    """
    if body.startswith("^"):
        raise RegexSyntaxError(
            "Negated character classes ('[^...]') are not supported yet"
        )
    chars: list[str] = []
    seen: set[str] = set()
    i = 0
    n = len(body)
    while i < n:
        # a-z style range
        if i + 2 < n and body[i + 1] == "-" and body[i + 2] != "]":
            lo, hi = body[i], body[i + 2]
            if ord(lo) > ord(hi):
                raise RegexSyntaxError(f"Invalid character range '{lo}-{hi}'")
            for code in range(ord(lo), ord(hi) + 1):
                ch = chr(code)
                if ch not in seen:
                    seen.add(ch)
                    chars.append(ch)
            i += 3
            continue
        ch = body[i]
        if ch not in seen:
            seen.add(ch)
            chars.append(ch)
        i += 1
    if not chars:
        raise RegexSyntaxError("Empty character class '[]'")
    return "".join(chars)


# ---------------------------------------------------------------------------
# Recursive-descent parser
#
#   union   := concat ('|' concat)*
#   concat  := repeat+                     (one or more repeats)
#   repeat  := atom ('*' | '+' | '?')?
#   atom    := CHAR | CHARCLASS | '(' union ')'
# ---------------------------------------------------------------------------


class _Parser:
    def __init__(self, tokens: list[str], tracer=None):
        self.tokens = tokens
        self.pos = 0
        self.tracer = tracer

    def peek(self) -> Optional[str]:
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def advance(self) -> str:
        tok = self.tokens[self.pos]
        self.pos += 1
        return tok

    def parse(self) -> Node:
        if not self.tokens:
            raise RegexSyntaxError("Empty regex")
        node = self.parse_union()
        if self.pos != len(self.tokens):
            raise RegexSyntaxError(f"Unexpected token near position {self.pos}")
        return node

    def parse_union(self) -> Node:
        node = self.parse_concat()
        while self.peek() == "|":
            self.advance()
            rhs = self.parse_concat()
            node = Union(node, rhs)
        return node

    def parse_concat(self) -> Node:
        node = self.parse_repeat()
        while self.peek() is not None and self.peek() not in ("|", ")"):
            rhs = self.parse_repeat()
            node = Concat(node, rhs)
        return node

    def parse_repeat(self) -> Node:
        node = self.parse_atom()
        while self.peek() in ("*", "+", "?"):
            op = self.advance()
            if op == "*":
                node = Star(node)
            elif op == "+":
                before = to_regex(node)
                node = Concat(node, Star(clone(node)))
                self._desugar(f"{before}+", node, "one or more")
            elif op == "?":
                before = to_regex(node)
                node = Union(node, Epsilon())
                self._desugar(f"{before}?", node, "optional")
        return node

    def _desugar(self, before: str, node: Node, rule: str) -> None:
        """Report one rewrite. The followpos algorithm only knows about
        literals, concatenation, union and star, so `+`, `?` and
        character classes are rewritten into those during parsing. That
        rewrite is invisible in the final tree, which is exactly why
        "where did my + go?" is a real student question.
        """
        if not self.tracer:
            return
        after = to_regex(node)
        self.tracer.step(
            "regex.desugar",
            phase="parse",
            title=f"Rewrite {before}",
            explain=(
                f"The followpos algorithm only understands literals, "
                f"concatenation, union and star, so the {rule} operator is "
                f"rewritten before anything else happens: {before} becomes "
                f"{after}."
            ),
            result=after,
            before=before,
        )

    def parse_atom(self) -> Node:
        tok = self.peek()
        if tok is None:
            raise RegexSyntaxError("Unexpected end of pattern")
        if tok == "(":
            self.advance()
            node = self.parse_union()
            if self.peek() != ")":
                raise RegexSyntaxError("Missing closing ')'")
            self.advance()
            return node
        if tok.startswith("CHAR:"):
            self.advance()
            return Leaf(symbol=tok[len("CHAR:") :])
        if tok.startswith("CHARCLASS:"):
            self.advance()
            chars = tok[len("CHARCLASS:") :]
            node: Node = Leaf(symbol=chars[0])
            for ch in chars[1:]:
                node = Union(node, Leaf(symbol=ch))
            self._desugar(f"[{chars}]", node, "character class")
            return node
        raise RegexSyntaxError(f"Unexpected token '{tok}'")


def parse_regex(pattern: str, *, tracer=None) -> Node:
    """Parse a regex string into an AST (not yet augmented or positioned)."""
    tokens = _tokenize(pattern)
    return _Parser(tokens, tracer).parse()
