import { useEffect, useState } from "react";
import { Button } from "./ui/Button";

/**
 * One "predict the next step" question, derived entirely from the step's
 * own `data.result` on the backend (see app/trace.py).
 *
 * Three kinds cover everything:
 *  - "set"    pick from a known finite universe (positions, states,
 *             terminals). This is most of them, which is why no
 *             distractor generation is needed anywhere.
 *  - "number" a single value.
 *  - "choice" one of a handful of given options.
 *
 * Expected to be mounted with key={step.i} so moving to another step
 * gives a fresh, unanswered card without a reset effect.
 */
export default function QuizCard({ quiz, onResolve, onAdvance }) {
  const [picked, setPicked] = useState(quiz.kind === "set" ? [] : "");
  const [status, setStatus] = useState("open");
  // The score reports the first attempt, so guessing until it goes green
  // does not read back as having known the answer.
  const [missed, setMissed] = useState(false);

  const settled = status === "correct" || status === "revealed";

  // A correct answer moves on by itself, so a run of questions feels
  // like progress rather than a form to submit repeatedly.
  useEffect(() => {
    if (status !== "correct" || !onAdvance) return undefined;
    const id = setTimeout(onAdvance, 600);
    return () => clearTimeout(id);
  }, [status, onAdvance]);

  function resolve(correct) {
    setStatus(correct ? "correct" : "wrong");
    if (correct) onResolve(!missed);
    else setMissed(true);
  }

  function check(value = picked) {
    if (quiz.kind === "set") {
      const want = [...quiz.answer].sort((a, b) => a - b).join(",");
      const got = [...value].sort((a, b) => a - b).join(",");
      resolve(want === got);
    } else if (quiz.kind === "number") {
      resolve(value !== "" && Number(value) === quiz.answer);
    } else {
      resolve(value === quiz.answer);
    }
  }

  function reveal() {
    setStatus("revealed");
    onResolve(false);
  }

  const tone = {
    open: "border-ink/20 bg-white",
    wrong: "border-red-300 bg-red-50",
    correct: "border-circuit bg-circuit-light",
    revealed: "border-signal bg-signal-light",
  }[status];

  return (
    <div className={`border ${tone}`}>
      <div className="flex items-baseline justify-between gap-3 border-b border-current/10 px-4 py-2">
        <p className="text-sm font-medium text-ink">{quiz.question}</p>
        <span className="shrink-0 font-mono text-[11px] uppercase tracking-wide text-ink-faint">
          {status === "correct"
            ? "correct"
            : status === "wrong"
              ? "not quite"
              : status === "revealed"
                ? "answer shown"
                : "your turn"}
        </span>
      </div>

      <div className="space-y-3 p-4">
        {quiz.kind === "set" && (
          <div className="flex flex-wrap gap-1.5">
            {(quiz.universe ?? []).map((item) => {
              const on = picked.includes(item);
              const isAnswer = settled && quiz.answer.includes(item);
              return (
                <button
                  key={item}
                  type="button"
                  disabled={settled}
                  onClick={() =>
                    setPicked((current) =>
                      current.includes(item)
                        ? current.filter((x) => x !== item)
                        : [...current, item],
                    )
                  }
                  className={`border px-2.5 py-1 font-mono text-sm disabled:cursor-default ${
                    isAnswer
                      ? "border-circuit bg-circuit text-white"
                      : on
                        ? "border-blueprint bg-blueprint-light text-blueprint"
                        : "border-graph bg-white text-ink-soft hover:border-ink-faint"
                  }`}
                >
                  {item}
                </button>
              );
            })}
            {!quiz.universe?.length && (
              <p className="font-mono text-xs text-ink-faint">no options available</p>
            )}
          </div>
        )}

        {quiz.kind === "number" && (
          <input
            type="number"
            value={settled ? quiz.answer : picked}
            disabled={settled}
            onChange={(e) => setPicked(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && check()}
            className="w-28 border border-ink/25 bg-white px-3 py-2 font-mono text-sm focus:border-blueprint focus:outline-none disabled:bg-paper"
          />
        )}

        {quiz.kind === "choice" && (
          <div className="flex flex-wrap gap-1.5">
            {(quiz.choices ?? []).map((choice) => {
              const isAnswer = settled && choice === quiz.answer;
              const chosenWrong = status === "wrong" && choice === picked;
              return (
                <button
                  key={choice}
                  type="button"
                  disabled={settled}
                  onClick={() => {
                    setPicked(choice);
                    check(choice);
                  }}
                  className={`border px-3 py-1.5 font-mono text-sm disabled:cursor-default ${
                    isAnswer
                      ? "border-circuit bg-circuit text-white"
                      : chosenWrong
                        ? "border-red-400 bg-red-100 text-red-700"
                        : "border-graph bg-white text-ink-soft hover:border-ink-faint"
                  }`}
                >
                  {choice}
                </button>
              );
            })}
          </div>
        )}

        <div className="flex items-center gap-2">
          {!settled && quiz.kind !== "choice" && (
            <Button type="button" onClick={() => check()}>
              Check
            </Button>
          )}
          {!settled && (
            <Button type="button" variant="ghost" onClick={reveal}>
              Show me
            </Button>
          )}
          {status === "wrong" && (
            <p className="font-mono text-xs text-red-700">
              Try again, or reveal the answer to move on.
            </p>
          )}
          {settled && (
            <p className="font-mono text-xs text-ink-soft">
              Read the explanation below, then continue.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
