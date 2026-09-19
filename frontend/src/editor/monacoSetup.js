// @monaco-editor/react defaults to fetching Monaco's assets from a CDN
// (jsdelivr) at runtime. That's a real liability for a demo, it fails
// outright on a restricted campus network, an offline presentation, or
// any environment that blocks or intercepts that CDN (exactly what
// happened in testing here). Importing monaco-editor directly and
// handing that instance to the React wrapper's loader bundles
// everything into the app itself, so the editor needs no network
// access at all once the page has loaded.
//
// Importing from 'monaco-editor/esm/vs/editor/editor.api' rather than
// the package root is deliberate: the root import auto-registers every
// bundled language (C++, SQL, Swift, dozens more) neither this app nor
// the toy language needs, which bloated the build by several MB for
// nothing. This path gives just the core editor API; toyLanguage.js
// registers the one language actually used on top of it.
import * as monaco from "monaco-editor/esm/vs/editor/editor.api";
import editorWorker from "monaco-editor/esm/vs/editor/editor.worker?worker";
import { loader } from "@monaco-editor/react";

// Our toy language only needs basic tokenization (see toyLanguage.js),
// not a full language service, so the generic editor worker is the
// only one this needs, unlike the JSON/TS/CSS workers a general-
// purpose Monaco setup would also bundle.
self.MonacoEnvironment = {
  getWorker() {
    return new editorWorker();
  },
};

loader.config({ monaco });
