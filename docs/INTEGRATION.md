# CompileViz sidebar shell - integration (5 min)

Copy into frontend/src/ keeping paths:
  src/App.jsx                           (REPLACES your App.jsx - back up the old one)
  src/shell.css                         (new)
  src/polish.css                        (new or replace)
  src/components/ui/Sidebar.jsx         (new)
  src/components/ui/WakeUpBanner.jsx    (new or replace)
  src/components/ui/PipelineStrip.jsx   (optional, see earlier steps 3 and 4)

Then in src/main.jsx, after the index.css import add:
  import "./polish.css";
  import "./shell.css";

That's all. Pages are untouched. Run `npm run dev`.
If your friend changed App.jsx (new tabs/pages), add them to the TABS array in the new App.jsx
(id, label, icon: regex|grammar|minimizer|compiler, Component).
