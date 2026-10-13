import { useCallback, useEffect, useMemo, useState } from "react";

/**
 * Index state for anything that walks a list of steps: prev/next, jump,
 * and autoplay.
 *
 * Deliberately knows nothing about traces, quizzes or rendering, so the
 * same hook drives the regex playground now and the compiler pipeline
 * later. The keyboard shortcuts live in Stepper.jsx rather than here,
 * so that a caller which needs to gate advancing (quiz mode) can wrap
 * `next` once and have both the button and the arrow key respect it.
 */
export default function useStepper(total, { fps: initialFps = 1.5 } = {}) {
  // Read once: this is an OS-level preference, not something that
  // changes while a student is halfway through a trace.
  const reducedMotion = useMemo(
    () => window.matchMedia?.("(prefers-reduced-motion: reduce)").matches === true,
    [],
  );

  const [index, setIndex] = useState(0);
  const [playing, setPlaying] = useState(false);
  // Slower default when motion is reduced: the preference is about not
  // being made to watch things move quickly, so the control stays and
  // the pace changes.
  const [fps, setFps] = useState(reducedMotion ? 0.8 : initialFps);

  const lastIndex = Math.max(0, total - 1);
  const atStart = index <= 0;
  const atEnd = index >= lastIndex;

  // A new trace (different pattern) restarts from the beginning rather
  // than leaving the index pointing into the middle of something else.
  useEffect(() => {
    setIndex(0);
    setPlaying(false);
  }, [total]);

  const goTo = useCallback(
    (n) => setIndex(Math.min(Math.max(0, n), Math.max(0, total - 1))),
    [total],
  );
  const next = useCallback(() => setIndex((i) => Math.min(lastIndex, i + 1)), [lastIndex]);
  const prev = useCallback(() => setIndex((i) => Math.max(0, i - 1)), []);
  const first = useCallback(() => setIndex(0), []);
  const last = useCallback(() => setIndex(lastIndex), [lastIndex]);
  const togglePlay = useCallback(() => setPlaying((p) => !p), []);

  useEffect(() => {
    if (!playing) return undefined;
    const id = setInterval(next, 1000 / fps);
    return () => clearInterval(id);
  }, [playing, fps, next]);

  // Stop at the end instead of sitting on the last step with the pause
  // button still showing.
  useEffect(() => {
    if (playing && atEnd) setPlaying(false);
  }, [playing, atEnd]);

  return {
    index,
    total,
    atStart,
    atEnd,
    playing,
    fps,
    reducedMotion,
    goTo,
    next,
    prev,
    first,
    last,
    togglePlay,
    setFps,
    setPlaying,
  };
}
