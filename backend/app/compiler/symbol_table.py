"""
A scoped symbol table: a stack of scopes, each a name -> Symbol map,
supporting the block scoping the toy language's if/while/bare blocks
need (a variable declared inside a block is invisible outside it, and
may shadow an outer variable of the same name).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Symbol:
    name: str
    type: str  # "int" | "float" | "bool" | "string"
    line: int
    column: int
    scope_depth: int

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "type": self.type,
            "line": self.line,
            "column": self.column,
            "scope_depth": self.scope_depth,
        }


class SymbolTable:
    def __init__(self) -> None:
        self._scopes: list[dict[str, Symbol]] = [{}]  # index 0 is the global scope
        self.all_declared: list[Symbol] = []  # every symbol ever declared, for display

    @property
    def depth(self) -> int:
        return len(self._scopes) - 1

    def push_scope(self) -> None:
        self._scopes.append({})

    def pop_scope(self) -> None:
        self._scopes.pop()

    def declare(self, name: str, type_: str, line: int, column: int) -> bool:
        """Declares `name` in the CURRENT (innermost) scope only.
        Returns False (and declares nothing) if `name` is already
        declared in this exact scope, that's a redeclaration error for
        the caller to report. Shadowing an OUTER scope's variable of
        the same name is allowed, so this never looks at outer scopes.
        """
        current = self._scopes[-1]
        if name in current:
            return False
        symbol = Symbol(name, type_, line, column, self.depth)
        current[name] = symbol
        self.all_declared.append(symbol)
        return True

    def lookup(self, name: str) -> Symbol | None:
        """Searches from the innermost scope outward, so an inner
        declaration correctly shadows an outer one of the same name.
        """
        for scope in reversed(self._scopes):
            if name in scope:
                return scope[name]
        return None
