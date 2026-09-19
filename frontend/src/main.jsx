import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App.jsx";
import "./index.css";
// Side-effect import: configures Monaco to load from the local bundle
// instead of a CDN. Must run before any Editor component mounts.
import "./editor/monacoSetup.js";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
