"""
The toy-language compiler pipeline. All six PRD phases are done as of
this milestone.

Milestone 7 (done): token_specs.py defines the toy language's tokens
    as regexes; lexer.py tokenizes source using the Milestone 2
    direct-method DFA engine, one DFA per token type, with maximal
    munch and error recovery.
Milestone 8 (done): ast_nodes.py defines the AST; parser.py is a
    recursive-descent parser over the lexer's tokens, with syntax
    error recovery.
Milestone 9 (done): symbol_table.py is a scoped symbol table;
    semantic_analyzer.py walks the AST, populating it and type
    checking every expression and statement.
Milestone 10 (done): tac.py defines the TAC instruction shape;
    tac_generator.py walks the AST and emits three-address code.
    Temps and labels are prefixed with '%' (%t1, %L1, ...) so they
    can never collide with a real variable name, see optimizer.py's
    docstring for the bug that fix closes.
Milestone 11 (done): optimizer.py runs constant folding/propagation,
    common subexpression elimination, and dead code elimination over
    the TAC, in that order, and keeps the TAC after every stage for a
    before/after view.
Milestone 12 (done): codegen.py lowers optimized TAC into stack-
    machine instructions (PUSH_CONST, LOAD, STORE, ADD, JMP, ...);
    interpreter.py actually executes that code (with a step cap
    against infinite loops), so the dashboard can show a program's
    real output, not just its generated assembly.
"""

from app.compiler.ast_nodes import (
    Assignment,
    BinaryOp,
    Block,
    Call,
    ExprStmt,
    Identifier,
    IfStmt,
    Literal,
    Program,
    ReturnStmt,
    UnaryOp,
    VarDecl,
    WhileStmt,
)
from app.compiler.codegen import CodeGenerator, Instr, generate_code
from app.compiler.interpreter import InterpreterResult, run_program
from app.compiler.lexer import LexError, LexResult, Token, tokenize
from app.compiler.optimizer import OptimizationResult, optimize
from app.compiler.parser import ParseError, ParseResult, Parser, parse
from app.compiler.semantic_analyzer import (
    BUILTIN_FUNCTIONS,
    SemanticAnalyzer,
    SemanticError,
    SemanticResult,
    analyze,
)
from app.compiler.symbol_table import Symbol, SymbolTable
from app.compiler.tac import TACInstr
from app.compiler.tac_generator import TACGenerator, generate_tac
from app.compiler.token_specs import KEYWORDS, TOKEN_SPECS

__all__ = [
    "KEYWORDS",
    "TOKEN_SPECS",
    "LexError",
    "LexResult",
    "Token",
    "tokenize",
    "Assignment",
    "BinaryOp",
    "Block",
    "Call",
    "ExprStmt",
    "Identifier",
    "IfStmt",
    "Literal",
    "Program",
    "ReturnStmt",
    "UnaryOp",
    "VarDecl",
    "WhileStmt",
    "Parser",
    "ParseError",
    "ParseResult",
    "parse",
    "BUILTIN_FUNCTIONS",
    "SemanticAnalyzer",
    "SemanticError",
    "SemanticResult",
    "analyze",
    "Symbol",
    "SymbolTable",
    "TACInstr",
    "TACGenerator",
    "generate_tac",
    "OptimizationResult",
    "optimize",
    "CodeGenerator",
    "Instr",
    "generate_code",
    "InterpreterResult",
    "run_program",
]
