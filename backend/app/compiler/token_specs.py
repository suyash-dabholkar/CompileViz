"""
The toy language CompileViz compiles, and its lexical specification.

Language sketch (used consistently from here through code generation):

    int x;
    x = 2 + 3 * 4;
    if (x > 10) {
        x = x - 1;
    } else {
        x = x + 1;
    }
    while (x > 0) {
        x = x - 1;
    }

Types: int, float, bool, string. Statements: declarations, assignment,
if/else, while, return, and expression statements (including function
calls, once functions exist in a later milestone). Comments start with
// and run to end of line.

Every token type below is defined as a regex and handed to
direct_dfa.build_direct_dfa (Milestone 2), the same engine the regex
playground uses. That's deliberate: the lexer isn't a separate,
hand-rolled tokenizer, it's a direct, visible application of the
followpos DFA construction to a real problem.

TOKEN_SPECS order matters only as a tie-breaker: lexer.py always picks
the LONGEST match across every spec (maximal munch), and only when two
specs match the exact same length does the earlier one in this list
win. In practice that only matters for operators that share a prefix
(e.g. '=' and '=='), and even those resolve correctly by length alone,
since '==' is strictly longer than '=' whenever both are possible.

Regex syntax available (see regex_parser.py): literals, concatenation,
'|', '*', '+', '?', parentheses, and '[...]' character classes with
ranges. Characters that are also our regex metacharacters
( ) | * + ? [ ] \\ must be escaped with a backslash to appear literally.
"""

KEYWORDS = {
    "int",
    "float",
    "bool",
    "string",
    "if",
    "else",
    "while",
    "return",
    "def",
    "true",
    "false",
}

# A single quote character is code point 34. Splitting the printable
# ASCII range (32-126) around it, instead of trying to negate it,
# is how STRING's character class allows "everything except the closing
# quote" without needing a '[^...]' negated class, which regex_parser.py
# deliberately doesn't support (see its module docstring).
_PRINTABLE_EXCEPT_QUOTE = " -!#-~"

TOKEN_SPECS: list[tuple[str, str]] = [
    ("WHITESPACE", "[ \t\r\n]+"),
    ("COMMENT", "//[ -~]*"),
    ("FLOAT", "[0-9]+\\.[0-9]+"),
    ("INT", "[0-9]+"),
    ("STRING", f'"[{_PRINTABLE_EXCEPT_QUOTE}]*"'),
    ("IDENTIFIER", "[a-zA-Z_][a-zA-Z_0-9]*"),
    ("EQ", "=="),
    ("NE", "!="),
    ("LE", "<="),
    ("GE", ">="),
    ("AND", "&&"),
    ("OR", "\\|\\|"),
    ("ASSIGN", "="),
    ("LT", "<"),
    ("GT", ">"),
    ("PLUS", "\\+"),
    ("MINUS", "-"),
    ("STAR", "\\*"),
    ("SLASH", "/"),
    ("NOT", "!"),
    ("LPAREN", "\\("),
    ("RPAREN", "\\)"),
    ("LBRACE", "{"),
    ("RBRACE", "}"),
    ("SEMICOLON", ";"),
    ("COMMA", ","),
]

# Token types the lexer recognizes but never hands to the parser.
SKIP_TYPES = {"WHITESPACE", "COMMENT"}
