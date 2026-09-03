import { useCallback, useEffect, useState } from "react";
import { apiFetch } from "../lib/api.js";
import { useAuth } from "../lib/auth.jsx";
import { useToast, errorMessage } from "../lib/toast.jsx";
import { Badge, Card, EmptyState } from "../components/ui.jsx";
import { Spinner } from "../App.jsx";
import { formatDate } from "../lib/format.js";

export default function AdminApprovals() {
  const { token } = useAuth();
  const { push } = useToast();
  const [requests, setRequests] = useState(null);
  const [busy, setBusy] = useState({});

  const load = useCallback(async () => {
    try {
      const data = await apiFetch("/api/v1/admin/pending-requests", { token });
      setRequests(data);
    } catch (error) {
      push(errorMessage(error), "error");
      setRequests([]);
    }
  }, [token, push]);

  useEffect(() => {
    load();
  }, [load]);

  async function decide(request, decision) {
    const key = `${request.user_id}:${request.case_id}`;
    setBusy((prev) => ({ ...prev, [key]: true }));
    try {
      const res = await apiFetch("/api/v1/admin/decide-access", {
        method: "POST",
        token,
        body: { case_id: request.case_id, user_id: request.user_id, decision },
      });
      push(res.message || `Action recorded (${decision}).`, "success");
      await load();
    } catch (error) {
      push(errorMessage(error), "error");
    } finally {
      setBusy((prev) => ({ ...prev, [key]: false }));
    }
  }

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-100">Access approvals</h1>
        <p className="mt-1 text-sm text-slate-400">
          Review investigator requests for case-level access. Business of approving or rejecting requests.
        </p>
      </div>

      {requests === null ? (
        <div className="flex justify-center py-24">
          <Spinner size="lg" />
        </div>
      ) : requests.length === 0 ? (
        <EmptyState
          icon="✅"
          title="No pending access requests"
          description="When an investigator requests access to a case, the request appears here for review."
        />
      ) : (
        <div className="overflow-x-auto rounded-xl border border-slate-800">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-slate-800 bg-slate-900/70 text-xs uppercase tracking-wide text-slate-400">
                <th className="px-4 py-3 font-semibold">Investigator</th>
                <th className="px-4 py-3 font-semibold">Badge</th>
                <th className="px-4 py-3 font-semibold">Case</th>
                <th className="px-4 py-3 font-semibold">Requested</th>
                <th className="px-4 py-3 font-semibold text-right">Decision</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              {requests.map((r) => {
                const key = `${r.user_id}:${r.case_id}`;
                const isBusy = busy[key];
                return (
                  <tr key={key} className="bg-slate-950/40 hover:bg-slate-900/50">
                    <td className="px-4 py-3 font-medium text-slate-200">{r.username}</td>
                    <td className="px-4 py-3">
                      <span className="font-mono text-xs text-slate-400">{r.badge_number}</span>
                    </td>
                    <td className="px-4 py-3">
                      <span className="font-mono text-xs text-sky-400">{r.case_id}</span>
                    </td>
                    <td className="px-4 py-3 text-xs text-slate-400">{formatDate(r.created_at)}</td>
                    <td className="px-4 py-3">
                      <div className="flex items-center justify-end gap-2">
                        <Badge value={r.status} />
                        <button
                          disabled={isBusy}
                          onClick={() => decide(r, "APPROVE")}
                          className="rounded-lg bg-emerald-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-emerald-500 disabled:opacity-50"
                        >
                          {isBusy ? "…" : "Approve"}
                        </button>
                        <button
                          disabled={isBusy}
                          onClick={() => decide(r, "REJECT")}
                          className="rounded-lg border border-red-500/50 px-3 py-1.5 text-xs font-semibold text-red-300 hover:bg-red-950 disabled:opacity-50"
                        >
                          {isBusy ? "…" : "Reject"}
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      <Card className="p-4 text-xs text-slate-500">
        Every decision is written to the tamper-evident audit trail (action <code className="text-slate-400">CASE_ACCESS_DECIDED</code>) with the acting admin, target investigator, and decision.
      </Card>
    </div>
  );
}