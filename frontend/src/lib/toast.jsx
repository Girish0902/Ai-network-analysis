import { createContext, useCallback, useContext, useState } from "react";

const ToastContext = createContext(null);

let toastCounter = 0;

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);

  const dismiss = useCallback((id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const push = useCallback(
    (message, type = "info") => {
      const id = ++toastCounter;
      setToasts((prev) => [...prev, { id, message, type }]);
      setTimeout(() => dismiss(id), 5000);
    },
    [dismiss]
  );

  return (
    <ToastContext.Provider value={{ push, dismiss }}>
      {children}
      <div className="fixed bottom-4 right-4 z-50 space-y-2 w-96 max-w-[calc(100vw-2rem)]">
        {toasts.map((t) => (
          <div
            key={t.id}
            className={`rounded-lg border px-4 py-3 text-sm shadow-lg backdrop-blur ${
              t.type === "error"
                ? "border-red-500/40 bg-red-950/90 text-red-100"
                : t.type === "success"
                ? "border-emerald-500/40 bg-emerald-950/90 text-emerald-100"
                : "border-slate-600/50 bg-slate-900/90 text-slate-100"
            }`}
          >
            <div className="flex items-start justify-between gap-2">
              <span className="whitespace-pre-wrap">{t.message}</span>
              <button
                onClick={() => dismiss(t.id)}
                className="text-slate-400 hover:text-slate-200 shrink-0"
                aria-label="Dismiss notification"
              >
                &times;
              </button>
            </div>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used within ToastProvider");
  return ctx;
}

export function errorMessage(error) {
  if (!error) return "Unknown error";
  if (error instanceof Error && error.message) return error.message;
  return String(error);
}