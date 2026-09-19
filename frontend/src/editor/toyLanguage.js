// Registers the toy language with Monaco so the editor can syntax-highlight
// it, instead of falling back to plain text. This also gives Milestone 14
// (inline error highlighting) a real language id to attach diagnostic
// markers to, rather than bolting markers onto a generic plaintext buffer.

const KEYWORDS = [
  "int", "float", "bool", "string", "if", "else", "while",
  "return", "def", "true", "false",
];

const OPERATORS = [
  "==", "!=", "<=", ">=", "&&", "||", "=", "<", ">", "+", "-", "*", "/", "!",
];

let registered = false;

export function registerToyLanguage(monaco) {
  // Guard against re-registering on every editor mount (React StrictMode
  // double-invokes effects in dev, and this page can mount the editor
  // more than once across tab switches).
  if (registered) return;
  registered = true;

  monaco.languages.register({ id: "toylang" });

  monaco.languages.setLanguageConfiguration("toylang", {
    comments: { lineComment: "//" },
    brackets: [
      ["{", "}"],
      ["(", ")"],
    ],
    autoClosingPairs: [
      { open: "{", close: "}" },
      { open: "(", close: ")" },
      { open: '"', close: '"' },
    ],
  });

  monaco.languages.setMonarchTokensProvider("toylang", {
    keywords: KEYWORDS,
    operators: OPERATORS,
    symbols: /[=><!&|+\-*/]+/,

    tokenizer: {
      root: [
        [/\/\/.*$/, "comment"],
        [/"([^"\\]|\\.)*"/, "string"],
        [/\d+\.\d+/, "number.float"],
        [/\d+/, "number"],
        [
          /[a-zA-Z_]\w*/,
          { cases: { "@keywords": "keyword", "@default": "identifier" } },
        ],
        [/[{}()]/, "@brackets"],
        [/[;,]/, "delimiter"],
        [
          /@symbols/,
          { cases: { "@operators": "operator", "@default": "" } },
        ],
        [/\s+/, "white"],
      ],
    },
  });
}
