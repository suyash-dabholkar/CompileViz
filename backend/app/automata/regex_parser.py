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
                raise RegexSyntaxError("Dangling escape character '\\' at end of pattern")
            tokens.append(f"CHAR:{pattern[i + 1]}")
            i += 2
            continue
        if c == "[":
            end = pattern.find("]", i)
            if end == -1:
                raise RegexSyntaxError("Unterminated character class, missing ']'")
            chars = _expand_char_class(pattern[i + 1:end])
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
    def __init__(self, tokens: list[str]):
        self.tokens = tokens
        self.pos = 0

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
                node = Concat(node, Star(clone(node)))
            elif op == "?":
                node = Union(node, Epsilon())
        return node

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
            return Leaf(symbol=tok[len("CHAR:"):])
        if tok.startswith("CHARCLASS:"):
            self.advance()
            chars = tok[len("CHARCLASS:"):]
            node: Node = Leaf(symbol=chars[0])
            for ch in chars[1:]:
                node = Union(node, Leaf(symbol=ch))
            return node
        raise RegexSyntaxError(f"Unexpected token '{tok}'")


def parse_regex(pattern: str) -> Node:
    """Parse a regex string into an AST (not yet augmented or positioned)."""
    tokens = _tokenize(pattern)
    return _Parser(tokens).parse()
