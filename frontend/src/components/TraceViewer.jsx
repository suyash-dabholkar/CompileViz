import { useEffect, useMemo, useState } from "react";
import QuizCard from "./QuizCard";
import Stepper from "./Stepper";
import useStepper from "../hooks/useStepper";

/**
 * The shared shell for any step trace: controls, the current step's
 * explanation, the optional quiz, and then whatever the tool wants to
 * draw for that step.
 *
 * The body is a render prop rather than a kind-to-component registry.
 * Each page has exactly one producer and one consumer of its step kinds,
 * so a `switch (step.kind)` inside one per-page component is the same
 * code with one fewer concept.
 *
 *   <TraceViewer trace={trace}>
 *     {({ step, index, steps, context }) => <RegexDirectSteps ... />}
 *   </TraceViewer>
 */
export default function TraceViewer({ trace, children }) {
  const steps = trace?.steps ?? [];
  const stepper = useStepper(steps.length);
  const [quizMode, setQuizMode] = useState(false);
  const [resolved, setResolved] = useState({});

  // A different trace means different questions; carrying answers over
  // would show a stale score and unlock steps nobody looked at.
  useEffect(() => setResolved({}), [trace]);

  const score = useMemo(() => {
    const outcomes = Object.values(resolved);
    return { attempted: outcomes.length, correct: outcomes.filter(Boolean).length };
  }, [resolved]);

  if (!steps.length) return null;

  const step = steps[stepper.index];
  const quiz = quizMode && step?.quiz ? step.quiz : null;
  // An unanswered question gates advancing, and hides the explanation -
  // otherwise the answer is sitting right underneath the question.
  const locked = Boolean(quiz) && resolved[stepper.index] === undefined;

  return (
    <div className="space-y-4">
      <Stepper
        stepper={stepper}
        labels={steps.map((s) => s.phase)}
        onNext={locked ? null : stepper.next}
        onJump={quizMode ? null : stepper.goTo}
        quizMode={quizMode}
        onQuizModeChange={setQuizMode}
        score={score}
      />

      {quiz && (
        <QuizCard
          key={step.i}
          quiz={quiz}
          onResolve={(correct) =>
            setResolved((current) => ({ ...current, [stepper.index]: correct }))
          }
          onAdvance={stepper.atEnd ? undefined : stepper.next}
        />
      )}

      <div className="border-l-2 border-signal bg-signal-light px-4 py-3">
        <p className="font-mono text-xs uppercase tracking-wide text-ink-faint">
          {step.phase} · step {step.i + 1}
        </p>
        {/* The title names the outcome ("q2 on 'a' goes to q1"), so it
            has to stay hidden alongside the explanation while a question
            is open, or the question answers itself. */}
        {locked ? (
          <p className="mt-1.5 text-sm italic text-ink-faint">
            Answer above to see what happens in this step.
          </p>
        ) : (
          <>
            <p className="mt-1 font-mono text-sm font-medium text-ink">{step.title}</p>
            <p className="mt-1.5 text-sm leading-relaxed text-ink-soft">{step.explain}</p>
          </>
        )}
      </div>

      {children({
        step,
        index: stepper.index,
        steps,
        context: trace.context ?? {},
        stepper,
        locked,
      })}

      {trace.truncated && (
        <p className="font-mono text-xs text-ink-faint">
          This trace was cut short at {steps.length} steps.
        </p>
      )}
    </div>
  );
}
