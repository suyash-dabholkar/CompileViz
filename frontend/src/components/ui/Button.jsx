const VARIANTS = {
  primary: "bg-signal text-ink hover:bg-signal-dark",
  secondary: "border border-ink text-ink hover:bg-ink hover:text-paper",
  ghost: "text-blueprint hover:text-blueprint-dark underline decoration-blueprint/30 hover:decoration-blueprint-dark underline-offset-4",
};

export function Button({ variant = "primary", className = "", children, ...props }) {
  return (
    <button
      className={`inline-flex items-center gap-2 px-4 py-2 text-sm font-medium transition-colors disabled:opacity-40 disabled:cursor-not-allowed ${VARIANTS[variant]} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}
