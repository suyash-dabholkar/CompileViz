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
      <label htmlFor={id} className="block text-xs font-medium text-slate-600 mb-1">
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
        className="rounded-md border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
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
