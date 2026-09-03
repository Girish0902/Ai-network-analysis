import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { apiFetch } from "../lib/api.js";
import { useAuth, isAdmin } from "../lib/auth.jsx";
import { useToast, errorMessage } from "../lib/toast.jsx";
import { Badge, Button, Card, EmptyState, Input } from "../components/ui.jsx";
import { Spinner } from "../App.jsx";
import { formatDate } from "../lib/format.js";

function CreateCaseModal({ onClose, onCreate }) {
  const [form, setForm] = useState({ case_id: "", title: "", description: "" });
  const [errors, setErrors] = useState({});
  const [submitting, setSubmitting] = useState(false);

  function setField(key, value) {
    setForm((f) => ({ ...f, [key]: value }));
    setErrors((e) => ({ ...e, [key]: undefined }));
  }

  function validate() {
    const next = {};
    if (form.case_id.trim().length < 4 || !/^[A-Za-z0-9_.-]+$/.test(form.case_id.trim()))
      next.case_id = "Case ID must be 4+ characters (letters, digits, dot, dash or underscore).";
    if (form.title.trim().length < 3) next.title = "Provide a case title (3+ characters).";
    if (form.description.length > 2000) next.description = "Description must be under 2000 characters.";
    setErrors(next);
    return Object.keys(next).length === 0;
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!validate()) return;
    setSubmitting(true);
    try {
      await onCreate({
        case_id: form.case_id.trim(),
        title: form.title.trim(),
        description: form.description.trim() || null,
      });
      onClose();
    } catch (err) {
      setErrors((prev) => ({ ...prev, _server: errorMessage(err) }));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/60 p-4" onClick={onClose}>
      <div
        className="w-full max-w-lg rounded-xl border border-slate-700 bg-slate-900 p-6 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="text-lg font-bold text-slate-100">Create a new case</h2>
        <p className="mt-1 text-sm text-slate-400">
          The creator is automatically granted approved access to the case.
        </p>
        <form onSubmit={handleSubmit} className="mt-5 space-y-4">
          <Input
            label="Case ID"
            placeholder="CASE-2026-101"
            value={form.case_id}
            onChange={(e) => setField("case_id", e.target.value)}
            error={errors.case_id}
          />
          <Input
            label="Case title"
            placeholder="Financial Fraud Ring"
            value={form.title}
            onChange={(e) => setField("title", e.target.value)}
            error={errors.title}
          />
          <label className="block">
            <span className="mb-1.5 block text-sm font-medium text-slate-300">Description (optional)</span>
            <textarea
              rows={3}
              className={`w-full rounded-lg border bg-slate-950/60 px-3 py-2 text-sm text-slate-100 placeholder-slate-500 outline-none transition-colors focus:ring-2 ${
                errors.description
                  ? "border-red-500/60 focus:ring-red-400/40"
                  : "border-slate-700 focus:border-sky-500 focus:ring-sky-400/20"
              }`}
              placeholder="Brief context, entities of interest, or investigation notes&hellip;"
              value={form.description}
              onChange={(e) => setField("description", e.target.value)}
            />
            {errors.description && <span className="mt-1 block text-xs text-red-400">{errors.description}</span>}
          </label>
          {errors._server && (
            <p className="rounded-lg border border-red-500/40 bg-red-950/40 px-3 py-2 text-xs text-red-300">
              {errors._server}
            </p>
          )}
          <div className="flex justify-end gap-3 pt-2">
            <Button type="button" variant="secondary" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" disabled={submitting}>
              {submitting && <Spinner size="sm" />} Create case
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default function Dashboard() {
  const { user, token } = useAuth();
  const { push } = useToast();
  const navigate = useNavigate();
  const admin = isAdmin(user);

  const [cases, setCases] = useState(null);
  const [showCreate, setShowCreate] = useState(false);
  const [requestId, setRequestId] = useState("");
  const [requesting, setRequesting] = useState(false);

  const loadCases = useCallback(async () => {
    try {
      const data = await apiFetch("/api/v1/cases/my", { token });
      setCases(data);
    } catch (error) {
      push(errorMessage(error), "error");
      setCases([]);
    }
  }, [token, push]);

  useEffect(() => {
    loadCases();
  }, [loadCases]);

  async function handleCreate(payload) {
    const created = await apiFetch("/api/v1/cases/create", { method: "POST", body: payload, token });
    await loadCases();
    push(`Case ${created.case_id} created.`, "success");
    navigate(`/cases/${created.case_id}`);
  }

  async function handleRequestAccess(e) {
    e.preventDefault();
    const caseId = requestId.trim();
    if (caseId.length < 4) return;
    setRequesting(true);
    try {
      const res = await apiFetch(`/api/v1/cases/${encodeURIComponent(caseId)}/request-access`, {
        method: "POST",
        token,
      });
      push(res.detail || `Access request submitted for ${caseId}`, "success");
      setRequestId("");
      await loadCases();
    } catch (error) {
      push(errorMessage(error), "error");
    } finally {
      setRequesting(false);
    }
  }

  const openable = (c) => admin || c.access_status === "APPROVED";
  const filtered = cases || [];

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">
            Welcome back, {user?.username}
          </h1>
          <p className="mt-1 text-sm text-slate-400">
            {admin
              ? "Administrator view — all cases are accessible."
              : "Manage your assigned cases or request access to existing cases."}
          </p>
        </div>
        <Button onClick={() => setShowCreate(true)}>
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
          </svg>
          New case
        </Button>
      </div>

      {!admin && (
        <Card className="p-4">
          <form onSubmit={handleRequestAccess} className="flex flex-wrap items-end gap-3">
            <div className="flex-1 min-w-52">
              <Input
                label="Request access to a case"
                placeholder="Enter a case ID, e.g. CASE-2026-100"
                value={requestId}
                onChange={(e) => setRequestId(e.target.value)}
                hint="An admin will review and approve or reject the request."
              />
            </div>
            <Button type="submit" variant="secondary" disabled={requesting || requestId.trim().length < 4}>
              {requesting && <Spinner size="sm" />} Request access
            </Button>
          </form>
        </Card>
      )}

      <div>
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-400">
          {admin ? "All cases" : "Your cases"}
        </h2>
        {cases === null ? (
          <div className="flex justify-center py-16">
            <Spinner size="lg" />
          </div>
        ) : filtered.length === 0 ? (
          <EmptyState
            icon="🗂️"
            title="No cases yet"
            description={
              admin
                ? "No cases have been created in the platform yet."
                : "Create your first case, or request access to an existing case to get started."
            }
            action={
              <Button onClick={() => setShowCreate(true)}>Create a case</Button>
            }
          />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {filtered.map((c) => (
              <Card key={c.id} className="flex flex-col p-5">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="font-mono text-xs text-sky-400">{c.case_id}</p>
                    <h3 className="mt-1 text-base font-semibold text-slate-100">{c.title}</h3>
                  </div>
                  <Badge value={c.status} />
                </div>
                <p className="mt-2 text-sm text-slate-400 line-clamp-2 min-h-10">
                  {c.description || "No description provided."}
                </p>
                <div className="mt-4 flex flex-wrap items-center gap-2 text-xs text-slate-500">
                  {admin ? (
                    <Badge fallback="Admin access" />
                  ) : (
                    <Badge value={c.access_status} />
                  )}
                  <span>Created {formatDate(c.created_at)}</span>
                </div>
                <div className="mt-4 flex justify-end gap-2">
                  {openable(c) ? (
                    <Button size="sm" onClick={() => navigate(`/cases/${encodeURIComponent(c.case_id)}`)}>
                      Open workspace
                    </Button>
                  ) : (
                    <Button
                      size="sm"
                      variant="secondary"
                      disabled={c.access_status === "PENDING"}
                      onClick={async () => {
                        try {
                          const res = await apiFetch(
                            `/api/v1/cases/${encodeURIComponent(c.case_id)}/request-access`,
                            { method: "POST", token }
                          );
                          push(res.detail || "Access request submitted", "success");
                          await loadCases();
                        } catch (error) {
                          push(errorMessage(error), "error");
                        }
                      }}
                    >
                      {c.access_status === "PENDING" ? "Pending approval" : "Request access"}
                    </Button>
                  )}
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>

      {showCreate && (
        <CreateCaseModal
          onClose={() => setShowCreate(false)}
          onCreate={handleCreate}
        />
      )}
    </div>
  );
}