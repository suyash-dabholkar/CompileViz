import { useId } from "react";

/**
 * A labeled dropdown of presets. Selecting one calls onSelect with
 * that preset's full object (not just the label), so the caller reads
 * whichever field it needs (pattern, grammar, source, ...).
 */
export default function PresetPicker({ label, presets, onSelect }) {
  const id = useId();

  return (
    <div>
      <label htmlFor={id} className="block text-xs font-medium text-ink-soft mb-1">
        {label}
      </label>
      <select
        id={id}
        defaultValue=""
        onChange={(e) => {
          const index = e.target.value;
          if (index === "") return;
          onSelect(presets[Number(index)]);
          e.target.value = ""; // reset so picking the same preset twice still fires onChange
        }}
        className="border border-ink/25 bg-white px-3 py-2 text-sm text-ink-soft focus:outline-none focus:border-blueprint"
      >
        <option value="" disabled>
          Load an example...
        </option>
        {presets.map((preset, i) => (
          <option key={i} value={i}>
            {preset.label}
          </option>
        ))}
      </select>
    </div>
  );
}
