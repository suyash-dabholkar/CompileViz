/**
 * Two panel treatments, used deliberately rather than uniformly:
 *
 * - "primary" (default): a title-block header bar (ink background,
 *   paper-colored text) over a bordered white surface with a small
 *   offset shadow, like a page pulled off a drafting table. Reserved
 *   for the content that IS the point of a page: a diagram, the AST,
 *   the TAC listing, the code editor.
 * - "quiet": a thin hairline border, no header bar, no shadow.
 *   For secondary/supporting content: data tables, stat strips,
 *   inline notices. Keeping these deliberately undecorated is what
 *   lets the primary panels actually read as more important, instead
 *   of every piece of content competing at the same visual volume.
 */
export function Panel({ title, subtitle, variant = "primary", className = "", children }) {
  if (variant === "quiet") {
    return (
      <div className={`border border-graph bg-white/70 ${className}`}>
        {title && (
          <div className="border-b border-graph px-4 py-2.5">
            <h3 className="text-sm font-medium text-ink-soft">{title}</h3>
            {subtitle && <p className="text-xs text-ink-faint mt-0.5">{subtitle}</p>}
          </div>
        )}
        <div className="p-4">{children}</div>
      </div>
    );
  }

  return (
    <div className={`border border-ink/20 bg-white shadow-[4px_4px_0_0_rgba(22,33,58,0.10)] ${className}`}>
      {title && (
        <div className="flex items-baseline justify-between gap-3 bg-ink px-4 py-2.5">
          <h3 className="font-mono text-sm text-paper">{title}</h3>
          {subtitle && <span className="font-mono text-xs text-paper/60">{subtitle}</span>}
        </div>
      )}
      <div className="p-4">{children}</div>
    </div>
  );
}
