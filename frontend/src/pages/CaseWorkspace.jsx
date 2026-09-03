import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { apiFetch } from "../lib/api.js";
import { useAuth, isAdmin } from "../lib/auth.jsx";
import { useToast, errorMessage } from "../lib/toast.jsx";
import { Badge, Button, Card, EmptyState } from "../components/ui.jsx";
import { Spinner } from "../App.jsx";
import { formatBytes, formatDate, accessLabel } from "../lib/format.js";

function AccessDeniedPanel({ caseId, requestPending, onRequest }) {
  const [submitting, setSubmitting] = useState(false);
  return (
    <EmptyState
      icon="🔒"
      title="You do not have access to this case"
      description={
        requestPending
          ? "Your access request is pending administrator review. You will be able to open the workspace once it is approved."
          : "Request access to this case. An administrator will review and approve or reject the request."
      }
      action={
        !requestPending ? (
          <Button
            disabled={submitting}
            onClick={async () => {
              setSubmitting(true);
              try {
                await onRequest();
              } finally {
                setSubmitting(false);
              }
            }}
          >
            {submitting && <Spinner size="sm" />} Request access to {caseId}
          </Button>
        ) : undefined
      }
    />
  );
}

function ProcessResultModal({ job, onClose }) {
  const payload = job.evidence_payload || {};
  const blocks = Array.isArray(payload.blocks) ? payload.blocks : [];
  const index = payload.detection_index || {};
  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/60 p-4" onClick={onClose}>
      <div
        className="flex max-h-[90vh] w-full max-w-3xl flex-col rounded-xl border border-slate-700 bg-slate-900 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-slate-800 px-6 py-4">
          <div>
            <h2 className="text-lg font-bold text-slate-100">Processing result</h2>
            <p className="text-xs text-slate-400">
              Job #{job.id} &middot; {job.route || "—"} &middot; {job.extraction_method || "—"}
            </p>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg px-2 py-1 text-slate-400 hover:bg-slate-800 hover:text-slate-200"
            aria-label="Close"
          >
            &times;
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-6 py-5 space-y-5">
          <div className="flex flex-wrap gap-2">
            <Badge value={job.status} />
            <span className="rounded-full bg-slate-800 px-2.5 py-0.5 text-[11px] text-slate-300">
              Route: {job.route || "—"}
            </span>
            <span className="rounded-full bg-slate-800 px-2.5 py-0.5 text-[11px] text-slate-300">
              Method: {job.extraction_method || "—"}
            </span>
            {job.error && (
              <span className="rounded-full bg-red-500/10 px-2.5 py-0.5 text-[11px] text-red-300 ring-1 ring-inset ring-red-500/30">
                {job.error}
              </span>
            )}
          </div>

          {Object.keys(index).length > 0 && (
            <Card className="p-4">
              <h3 className="mb-2 text-sm font-semibold text-slate-300">Detection index</h3>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
                <Stat label="Total pages" value={index.total_pages} />
                <Stat label="Native pages" value={index.native_digital_pages} />
                <Stat label="Scanned pages" value={index.scanned_pages} />
                <Stat label="Blocks" value={index.total_blocks} />
              </div>
              {(job.ocr_pending_pages || []).length > 0 && (
                <p className="mt-3 text-xs text-amber-300">
                  OCR pending for page(s): {(job.ocr_pending_pages || []).join(", ")} — visual processing
                  is queued for the Phase 1.3/1.4 OCR pipeline.
                </p>
              )}
            </Card>
          )}

          {blocks.length === 0 ? (
            <EmptyState
              icon="📄"
              title="No extraction blocks"
              description="This document produced no text blocks (e.g. a scanned page awaiting OCR), or processing returned an empty result."
            />
          ) : (
            <div className="space-y-3">
              <h3 className="text-sm font-semibold text-slate-300">
                Extracted blocks ({blocks.length})
              </h3>
              {blocks.map((block) => (
                <Card key={block.block_id} className="p-4">
                  <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
                    <span className="font-mono text-slate-400">{block.block_id}</span>
                    <span>Page {block.page_number}</span>
                    <span>Conf {Math.round((block.confidence || 0) * 100)}%</span>
                    {block.detected_language && <span>{block.detected_language}</span>}
                    <span className="font-mono">bbox [{block.bbox?.join(", ")}]</span>
                  </div>
                  {block.text ? (
                    <p className="mt-2 whitespace-pre-wrap text-sm text-slate-300">{block.text}</p>
                  ) : (
                    <p className="mt-2 text-xs italic text-slate-500">No text — tabular/other content.</p>
                  )}
                  {Array.isArray(block.structured_tables) && block.structured_tables.length > 0 && (
                    <div className="mt-3 overflow-x-auto rounded-lg border border-slate-800">
                      <table className="w-full text-left text-xs">
                        <tbody>
                          {block.structured_tables.map((row, ri) => (
                            <tr key={ri} className={ri === 0 ? "bg-slate-800/60" : "bg-slate-900/40"}>
                              {Array.isArray(row) ? (
                                row.map((cell, ci) => (
                                  <td key={ci} className="border-r border-slate-800 px-3 py-1.5 text-slate-300">
                                    {cell != null ? String(cell) : ""}
                                  </td>
                                ))
                              ) : (
                                <td className="px-3 py-1.5 text-slate-400">{String(row)}</td>
                              )}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </Card>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function Stat({ label, value }) {
  return (
    <div className="rounded-lg bg-slate-800/50 px-3 py-2">
      <p className="text-[11px] uppercase tracking-wide text-slate-500">{label}</p>
      <p className="text-lg font-bold text-slate-100">{value ?? "—"}</p>
    </div>
  );
}

export default function CaseWorkspace() {
  const { caseId } = useParams();
  const { user, token } = useAuth();
  const { push } = useToast();
  const admin = isAdmin(user);

  const [workspace, setWorkspace] = useState(null);
  const [accessState, setAccessState] = useState("loading"); // loading | denied | ok
  const [pending, setPending] = useState(false);
  const [documents, setDocuments] = useState(null);
  const [processing, setProcessing] = useState({});
  const [viewing, setViewing] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef(null);

  const accessible = accessState === "ok";

  const loadDocuments = useCallback(async () => {
    try {
      const data = await apiFetch(`/api/v1/cases/${encodeURIComponent(caseId)}/evidence`, { token });
      setDocuments(data);
    } catch (error) {
      push(errorMessage(error), "error");
      setDocuments([]);
    }
  }, [caseId, token, push]);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setAccessState("loading");
      try {
        const data = await apiFetch(`/api/v1/cases/${encodeURIComponent(caseId)}/workspace`, { token });
        if (!cancelled) {
          setWorkspace(data);
          setAccessState("ok");
          setPending(false);
        }
      } catch (error) {
        if (!cancelled) {
          setPending(error.status === 409 && String(error.message || "").includes("pending"));
          setAccessState("denied");
        }
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [caseId, token]);

  useEffect(() => {
    if (accessible) loadDocuments();
  }, [accessible, loadDocuments]);

  async function handleRequest() {
    try {
      const res = await apiFetch(`/api/v1/cases/${encodeURIComponent(caseId)}/request-access`, {
        method: "POST",
        token,
      });
      push(res.detail || "Access request submitted.", "success");
      setPending(res.status === "PENDING");
    } catch (error) {
      push(errorMessage(error), "error");
    }
  }

  async function handleUpload(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      const res = await apiFetch(`/api/v1/cases/${encodeURIComponent(caseId)}/evidence/upload`, {
        method: "POST",
        body: fd,
        isFormData: true,
        token,
      });
      push(`Uploaded ${res.filename} (${res.sha256.slice(0, 12)}…).`, "success");
      if (fileInputRef.current) fileInputRef.current.value = "";
      await loadDocuments();
    } catch (error) {
      push(errorMessage(error), "error");
    } finally {
      setUploading(false);
    }
  }

  async function handleProcess(document) {
    setProcessing((prev) => ({ ...prev, [document.id]: true }));
    try {
      const job = await apiFetch(
        `/api/v1/cases/${encodeURIComponent(caseId)}/evidence/${document.id}/process`,
        { method: "POST", token }
      );
      push(`Processing finished with status ${job.status}.`, job.status === "FAILED" ? "error" : "success");
      setViewing(job);
      await loadDocuments();
    } catch (error) {
      push(errorMessage(error), "error");
    } finally {
      setProcessing((prev) => ({ ...prev, [document.id]: false }));
    }
  }

  async function handleDownload(document) {
    try {
      const res = await apiFetch(
        `/api/v1/cases/${encodeURIComponent(caseId)}/evidence/${document.id}/download-url`,
        { token }
      );
      window.open(res.url, "_blank", "noopener,noreferrer");
      return;
    } catch {
      // fall through: local storage backend streams bytes through the authenticated API
    }
    try {
      const response = await apiFetch(
        `/api/v1/cases/${encodeURIComponent(caseId)}/evidence/${document.id}/stream`,
        { token }
      );
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = document.original_filename;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      setTimeout(() => URL.revokeObjectURL(url), 10_000);
    } catch (error) {
      push(errorMessage(error), "error");
    }
  }

  if (accessState === "loading") {
    return (
      <div className="flex justify-center py-24">
        <Spinner size="lg" />
      </div>
    );
  }

  if (!accessible) {
    return (
      <div className="mx-auto max-w-3xl">
        <Breadcrumbs caseId={caseId} />
        <AccessDeniedPanel caseId={caseId} requestPending={pending} onRequest={handleRequest} />
      </div>
    );
  }

  const caseData = workspace?.case;

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <Breadcrumbs caseId={caseId} />

      <Card className="p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <p className="font-mono text-sm text-sky-400">{caseData.case_id}</p>
              <Badge value={caseData.status} />
              {!admin && (
                <Badge value={workspace.access_status} />
              )}
            </div>
            <h1 className="mt-2 text-2xl font-bold text-slate-100">{caseData.title}</h1>
            <p className="mt-2 text-sm text-slate-400">{caseData.description || "No description provided."}</p>
          </div>
          <div className="text-right text-xs text-slate-500">
            <p>Your role: <span className="text-slate-300">{user?.role}</span></p>
            <p>Created: {formatDate(caseData.created_at)}</p>
            <p>{workspace.message}</p>
          </div>
        </div>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <Card className="lg:col-span-2 flex flex-col">
          <div className="border-b border-slate-800 px-5 py-4">
            <h2 className="text-base font-semibold text-slate-100">Evidence documents</h2>
            <p className="text-xs text-slate-500">
              Uploaded files are hashed with SHA-256, MIME-validated, scanned, and stored immutably.
            </p>
          </div>

          <div
            className={`flex-1 p-5 ${dragOver ? "bg-sky-500/5" : ""}`}
            onDragOver={(e) => {
              e.preventDefault();
              setDragOver(true);
            }}
            onDragLeave={() => setDragOver(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDragOver(false);
              if (e.dataTransfer.files?.[0]) {
                const dt = new DataTransfer();
                dt.items.add(e.dataTransfer.files[0]);
                if (fileInputRef.current) fileInputRef.current.files = dt.files;
                handleUpload({ target: { files: dt.files } });
              }
            }}
          >
            <div
              onClick={() => fileInputRef.current?.click()}
              className="cursor-pointer rounded-xl border border-dashed border-slate-600 bg-slate-950/40 px-6 py-8 text-center transition-colors hover:border-sky-500/60"
            >
              <input
                ref={fileInputRef}
                type="file"
                className="hidden"
                onChange={handleUpload}
                disabled={uploading}
              />
              <div className="text-3xl">{uploading ? "⏳" : "📤"}</div>
              <p className="mt-2 text-sm font-medium text-slate-200">
                {uploading ? "Uploading evidence…" : "Click or drop evidence to upload"}
              </p>
              <p className="mt-1 text-xs text-slate-500">
                PDF, scanned images, CSV, XLS, XLSX &mdash; validated and fingerprinted automatically.
              </p>
            </div>

            <div className="mt-5">
              {documents === null ? (
                <div className="flex justify-center py-10">
                  <Spinner />
                </div>
              ) : documents.length === 0 ? (
                <EmptyState
                  icon="🗄️"
                  title="No evidence yet"
                  description="Upload a document to begin building the case record. Processing extracts blocks, tables, and bounding boxes."
                />
              ) : (
                <ul className="divide-y divide-slate-800 rounded-xl border border-slate-800">
                  {documents.map((doc) => (
                    <li key={doc.id} className="flex flex-wrap items-center gap-3 px-4 py-3">
                      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-slate-800 text-lg">
                        {doc.is_quarantined ? "🔴" : doc.mime_type.includes("pdf") ? "📕" : "📄"}
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-sm font-medium text-slate-200">{doc.original_filename}</p>
                        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-slate-500">
                          <span>{formatBytes(doc.file_size_bytes)}</span>
                          <span className="font-mono">{doc.sha256_hash.slice(0, 12)}…</span>
                          <span>{formatDate(doc.created_at)}</span>
                        </div>
                        {doc.processing_error && (
                          <p className="mt-1 text-xs text-red-400">{doc.processing_error}</p>
                        )}
                      </div>
                      <div className="flex items-center gap-2">
                        {doc.processing_status ? (
                          <Badge value={doc.processing_status} />
                        ) : (
                          <span className="text-[11px] text-slate-500">Not processed</span>
                        )}
                        {doc.is_quarantined && <Badge value="QUARANTINED" />}
                        <Button size="sm" variant="secondary" onClick={() => handleDownload(doc)}>
                          Download
                        </Button>
                        <Button
                          size="sm"
                          disabled={processing[doc.id] || doc.is_quarantined}
                          onClick={() => handleProcess(doc)}
                        >
                          {processing[doc.id] && <Spinner size="sm" />}
                          Process
                        </Button>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        </Card>

        <Card className="h-fit">
          <div className="border-b border-slate-800 px-5 py-4">
            <h2 className="text-base font-semibold text-slate-100">Case summary</h2>
          </div>
          <div className="space-y-4 px-5 py-4 text-sm">
            <Stat label="Access context" value={admin ? "Admin bypass" : accessLabel(workspace.access_status)} />
            <Stat label="Documents uploaded" value={documents?.length ?? "—"} />
            <div className="rounded-lg bg-slate-800/40 px-3 py-2 text-xs text-slate-400">
              <p className="mb-1 font-medium text-slate-300">Next steps</p>
              <ul className="list-disc space-y-1 pl-4">
                <li>Upload evidence to the case record.</li>
                <li>Process a document to extract blocks &amp; provenance.</li>
                <li>Graph exploration, AI assistant and reporting arrive with the Phase 2&ndash;4 modules.</li>
              </ul>
            </div>
          </div>
        </Card>
      </div>

      {viewing && <ProcessResultModal job={viewing} onClose={() => setViewing(null)} />}
    </div>
  );
}

function Breadcrumbs({ caseId }) {
  return (
    <nav className="text-xs text-slate-500">
      <Link to="/" className="hover:text-sky-400">Dashboard</Link>
      <span className="mx-2">/</span>
      <span className="text-slate-300">{caseId}</span>
    </nav>
  );
}