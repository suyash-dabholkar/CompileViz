// Milestone 15: a built-in library so a professor or evaluator can
// explore every tool instantly during a live demo without typing
// anything, and so you always have a known-good (or known-broken, on
// purpose) example on hand.

export const REGEX_PRESETS = [
  {
    label: "(a|b)*abb — textbook example",
    pattern: "(a|b)*abb",
  },
  {
    label: "Identifier: [a-zA-Z][a-zA-Z0-9]*",
    pattern: "[a-zA-Z][a-zA-Z0-9]*",
  },
  {
    label: "Integer: [0-9]+",
    pattern: "[0-9]+",
  },
  {
    label: "Float: [0-9]+\\.[0-9]+",
    pattern: "[0-9]+\\.[0-9]+",
  },
  {
    label: "a(b|c)*d",
    pattern: "a(b|c)*d",
  },
  {
    label: "Optional character: colou?r",
    pattern: "colou?r",
  },
];

export const GRAMMAR_PRESETS = [
  {
    label: "Classic expression grammar (LL(1))",
    grammar: "E -> T E'\nE' -> + T E' | eps\nT -> F T'\nT' -> * F T' | eps\nF -> ( E ) | id",
  },
  {
    label: "Ambiguous grammar (FIRST/FIRST conflict)",
    grammar: "S -> A | B\nA -> a\nB -> a",
  },
  {
    label: "Dangling-else grammar (not LL(1))",
    grammar: "Stmt -> if Cond then Stmt Else | other\nElse -> else Stmt | eps",
  },
  {
    label: "Simple comma-separated list",
    grammar: "List -> id ListTail\nListTail -> , id ListTail | eps",
  },
];

export const PROGRAM_PRESETS = [
  {
    label: "Valid: if/else + while + print",
    category: "valid",
    source: `int x;
x = 2 + 3 * 4;
if (x > 10) {
    x = x - 1;
} else {
    x = x + 1;
}
// a comment
while (x > 0) {
    x = x - 1;
}
print(x);`,
  },
  {
    label: "Valid: constant folding demo",
    category: "valid",
    source: `int x = 2 + 3 * 4;
print(x);`,
  },
  {
    label: "Valid: countdown loop",
    category: "valid",
    source: `int x = 5;
while (x > 0) {
    print(x);
    x = x - 1;
}`,
  },
  {
    label: "Error: invalid character (lexical)",
    category: "lexical-error",
    source: `int x = 5;
@ y = 10;`,
  },
  {
    label: "Error: missing semicolon (syntax)",
    category: "syntax-error",
    source: `int x = 5
x = x + 1;`,
  },
  {
    label: "Error: undeclared variable (semantic)",
    category: "semantic-error",
    source: `y = 10;
print(y);`,
  },
  {
    label: "Error: type mismatch (semantic)",
    category: "semantic-error",
    source: `int x = "hello";`,
  },
];
