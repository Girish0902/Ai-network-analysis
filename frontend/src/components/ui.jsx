export function Button({ className = "", variant = "primary", size = "md", ...props }) {
  const base =
    "inline-flex items-center justify-center gap-2 rounded-lg font-semibold transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-sky-400 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer";
  const variants = {
    primary:
      "bg-sky-600 text-white hover:bg-sky-500 shadow-sm",
    secondary:
      "border border-slate-700 bg-slate-800/60 text-slate-200 hover:bg-slate-700",
    danger:
      "bg-red-600/90 text-white hover:bg-red-500",
    success:
      "bg-emerald-600 text-white hover:bg-emerald-500",
    ghost:
      "text-slate-300 hover:bg-slate-800",
  };
  const sizes = {
    sm: "px-2.5 py-1.5 text-xs",
    md: "px-4 py-2 text-sm",
    lg: "px-5 py-2.5 text-base",
  };
  return (
    <button className={`${base} ${variants[variant]} ${sizes[size]} ${className}`} {...props} />
  );
}

export function Input({ className = "", label, hint, error, ...props }) {
  return (
    <label className="block">
      {label && (
        <span className="mb-1.5 block text-sm font-medium text-slate-300">{label}</span>
      )}
      <input
        className={`w-full rounded-lg border bg-slate-950/60 px-3 py-2 text-sm text-slate-100 placeholder-slate-500 outline-none transition-colors focus:ring-2 ${
          error
            ? "border-red-500/60 focus:ring-red-400/40"
            : "border-slate-700 focus:border-sky-500 focus:ring-sky-400/20"
        } ${className}`}
        {...props}
      />
      {error && <span className="mt-1 block text-xs text-red-400">{error}</span>}
      {hint && !error && <span className="mt-1 block text-xs text-slate-500">{hint}</span>}
    </label>
  );
}

const badgeStyles = {
  OPEN: "bg-emerald-500/10 text-emerald-300 ring-emerald-500/30",
  CLOSED: "bg-slate-500/10 text-slate-300 ring-slate-500/30",
  APPROVED: "bg-emerald-500/10 text-emerald-300 ring-emerald-500/30",
  PENDING: "bg-amber-500/10 text-amber-300 ring-amber-500/30",
  REJECTED: "bg-red-500/10 text-red-300 ring-red-500/30",
  COMPLETED: "bg-emerald-500/10 text-emerald-300 ring-emerald-500/30",
  OCR_PENDING: "bg-amber-500/10 text-amber-300 ring-amber-500/30",
  FAILED: "bg-red-500/10 text-red-300 ring-red-500/30",
  QUARANTINED: "bg-red-500/10 text-red-300 ring-red-500/30",
};

export function Badge({ value, fallback, className = "" }) {
  const text = value ?? fallback;
  if (!text) return null;
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-[11px] font-semibold ring-1 ring-inset ${badgeStyles[String(text).toUpperCase()] || "bg-slate-500/10 text-slate-300 ring-slate-500/30"} ${className}`}
    >
      {text}
    </span>
  );
}

export function Card({ className = "", children }) {
  return (
    <div className={`rounded-xl border border-slate-800 bg-slate-900/50 shadow-sm ${className}`}>
      {children}
    </div>
  );
}

export function EmptyState({ icon, title, description, action }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 rounded-xl border border-dashed border-slate-700 px-6 py-12 text-center">
      {icon && <div className="text-3xl">{icon}</div>}
      <p className="text-sm font-medium text-slate-300">{title}</p>
      {description && <p className="max-w-md text-xs text-slate-500">{description}</p>}
      {action && <div className="mt-2">{action}</div>}
    </div>
  );
}