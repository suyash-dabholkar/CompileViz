import { useEffect } from "react";

/**
 * The control bar for a step trace: a phase ribbon, transport buttons, a
 * scrubber and the speed control.
 *
 * Square, hairline-bordered and mono-labelled to match the rest of the
 * blueprint system. `signal` amber is the current step, `blueprint` the
 * steps already walked, `ink-faint` what is still ahead.
 *
 * Keyboard handling lives here rather than in useStepper so that a
 * caller which gates advancing (quiz mode passes onNext={null}) gets the
 * arrow key disabled for free, instead of the key quietly bypassing the
 * gate the button respects.
 */

/** Collapse a per-step phase list into contiguous labelled runs. */
function phaseRuns(labels) {
  const runs = [];
  labels.forEach((label, i) => {
    const current = runs[runs.length - 1];
    if (current && current.label === label) current.end = i;
    else runs.push({ label, start: i, end: i });
  });
  return runs;
}

const SPEEDS = [0.8, 1.5, 3, 6];

export default function Stepper({
  stepper,
  labels = [],
  onNext,
  onJump,
  quizMode = false,
  onQuizModeChange,
  score,
}) {
  const { index, total, atStart, atEnd, playing, fps, reducedMotion } = stepper;
  const advance = onNext === undefined ? stepper.next : onNext;
  const jump = onJump === undefined ? stepper.goTo : onJump;
  const motion = reducedMotion ? "" : "transition-colors";

  useEffect(() => {
    function onKey(event) {
      if (event.metaKey || event.ctrlKey || event.altKey) return;

      // Only step aside for a control that would consume the key itself.
      // Bailing on every INPUT is too broad: it would mean that clicking
      // the quiz checkbox leaves focus on an input and silently kills
      // arrow-key navigation until the student clicks somewhere else.
      const target = event.target;
      const tag = target?.tagName;
      const type = (target?.type || "").toLowerCase();
      const isToggle = tag === "INPUT" && (type === "checkbox" || type === "radio");
      const typesText =
        tag === "TEXTAREA" ||
        tag === "SELECT" ||
        target?.isContentEditable ||
        (tag === "INPUT" && !isToggle); // text, number, and the range scrubber
      if (typesText) return;
      // Space activates a focused button or checkbox; let it.
      if (event.key === " " && (isToggle || tag === "BUTTON")) return;

      switch (event.key) {
        case "ArrowRight":
          if (advance) advance();
          break;
        case "ArrowLeft":
          stepper.prev();
          break;
        case "Home":
          if (jump) jump(0);
          break;
        case "End":
          if (jump) jump(total - 1);
          break;
        case " ":
          if (advance) stepper.togglePlay();
          break;
        default:
          return;
      }
      event.preventDefault();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [advance, jump, stepper, total]);

  if (!total) return null;
  const runs = phaseRuns(labels);

  return (
    <div className="border border-ink/20 bg-white">
      {runs.length > 1 && (
        <div className="flex border-b border-graph" role="group" aria-label="Phases">
          {runs.map((run) => {
            const length = run.end - run.start + 1;
            const active = index >= run.start && index <= run.end;
            const done = index > run.end;
            return (
              <button
                key={`${run.label}-${run.start}`}
                type="button"
                onClick={jump ? () => jump(run.start) : undefined}
                disabled={!jump}
                title={`${run.label} — ${length} step${length === 1 ? "" : "s"}`}
                style={{ flexGrow: length }}
                className={`min-w-0 truncate border-r border-graph px-2 py-1.5 font-mono text-[11px] uppercase tracking-wide last:border-r-0 disabled:cursor-default ${motion} ${
                  active
                    ? "bg-signal-light text-ink"
                    : done
                      ? "bg-blueprint-light text-blueprint"
                      : "text-ink-faint hover:bg-paper"
                }`}
              >
                {run.label}
              </button>
            );
          })}
        </div>
      )}

      <div className="flex flex-wrap items-center gap-3 px-3 py-2">
        <div className="flex items-center">
          <StepButton onClick={jump ? () => jump(0) : undefined} disabled={atStart || !jump} label="First step">
            |&lt;
          </StepButton>
          <StepButton onClick={stepper.prev} disabled={atStart} label="Previous step">
            &lt;
          </StepButton>
          <StepButton
            onClick={advance ? stepper.togglePlay : undefined}
            disabled={(atEnd && !playing) || !advance}
            label={playing ? "Pause" : "Play"}
            wide
          >
            {playing ? "Pause" : "Play"}
          </StepButton>
          <StepButton onClick={advance} disabled={atEnd || !advance} label="Next step">
            &gt;
          </StepButton>
          <StepButton onClick={jump ? () => jump(total - 1) : undefined} disabled={atEnd || !jump} label="Last step">
            &gt;|
          </StepButton>
        </div>

        <span className="font-mono text-xs text-ink-soft tabular-nums">
          {String(index + 1).padStart(String(total).length, "0")} / {total}
        </span>

        <input
          type="range"
          min={0}
          max={total - 1}
          value={index}
          disabled={!jump}
          onChange={(e) => jump && jump(Number(e.target.value))}
          aria-label="Step"
          className="h-1 min-w-[8rem] flex-1 cursor-pointer appearance-none bg-graph accent-signal disabled:cursor-not-allowed disabled:opacity-40"
        />

        <label className="flex items-center gap-1.5 font-mono text-[11px] text-ink-faint">
          <span className="sr-only">Playback speed</span>
          <select
            value={fps}
            onChange={(e) => stepper.setFps(Number(e.target.value))}
            className="border border-graph bg-white px-1 py-0.5 font-mono text-[11px] text-ink-soft"
          >
            {SPEEDS.map((speed) => (
              <option key={speed} value={speed}>
                {speed}x
              </option>
            ))}
          </select>
        </label>

        {onQuizModeChange && (
          <label className="flex cursor-pointer items-center gap-1.5 border border-graph px-2 py-1 font-mono text-[11px] text-ink-soft">
            <input
              type="checkbox"
              checked={quizMode}
              onChange={(e) => onQuizModeChange(e.target.checked)}
              className="accent-signal"
            />
            Quiz me
            {quizMode && score && score.attempted > 0 && (
              <span className="text-circuit">
                {score.correct}/{score.attempted}
              </span>
            )}
          </label>
        )}
      </div>
    </div>
  );
}

function StepButton({ onClick, disabled, label, children, wide = false }) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      aria-label={label}
      title={label}
      className={`border border-graph bg-white font-mono text-xs text-ink hover:bg-paper disabled:opacity-30 disabled:hover:bg-white ${
        wide ? "px-2.5" : "px-2"
      } -ml-px py-1 first:ml-0`}
    >
      {children}
    </button>
  );
}
