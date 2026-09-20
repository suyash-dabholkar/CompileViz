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
let themeDefined = false;

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

/**
 * A Monaco theme matching the app's blueprint palette instead of the
 * default "vs" theme's generic blue-and-black, so the editor reads as
 * part of the same designed surface as everything around it, not an
 * embedded third-party widget with its own look.
 */
export function registerToyTheme(monaco) {
  if (themeDefined) return;
  themeDefined = true;

  monaco.editor.defineTheme("compileviz", {
    base: "vs",
    inherit: true,
    rules: [
      { token: "keyword", foreground: "1D5FA8", fontStyle: "bold" },
      { token: "comment", foreground: "7C8AA3", fontStyle: "italic" },
      { token: "string", foreground: "0F9B8E" },
      { token: "number", foreground: "C6821F" },
      { token: "number.float", foreground: "C6821F" },
      { token: "identifier", foreground: "16213A" },
      { token: "delimiter", foreground: "3A4A66" },
      { token: "operator", foreground: "3A4A66" },
    ],
    colors: {
      "editor.background": "#FFFFFF",
      "editor.foreground": "#16213A",
      "editorLineNumber.foreground": "#B9C1D1",
      "editorLineNumber.activeForeground": "#1D5FA8",
      "editor.selectionBackground": "#E8F0FA",
      "editorCursor.foreground": "#E8A33D",
      "editorGutter.background": "#FFFFFF",
      "editorIndentGuide.background": "#EEF1F6",
    },
  });
}
