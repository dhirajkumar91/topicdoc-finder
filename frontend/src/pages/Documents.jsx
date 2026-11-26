import { useCallback, useEffect, useRef, useState } from "react";
import {
  getDocuments,
  startSingleProcessing,
  startBatchProcessing,
  getProcessingStatus,
} from "../services/documentService";
import {
  FileText,
  RefreshCw,
  Search,
  CheckCircle2,
  Clock,
  AlertCircle,
  LoaderCircle,
  Database,
  X,
  ExternalLink,
  Calendar,
  HardDrive,
  Layers,
  UserRound,
  Play,
  RotateCcw,
} from "lucide-react";

function Documents() {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedDocument, setSelectedDocument] = useState(null);
  const [processingStatus, setProcessingStatus] = useState(null);
  const [batchLimit, setBatchLimit] = useState(3);
  const [processingAction, setProcessingAction] = useState(false);
  const [processingDocumentId, setProcessingDocumentId] = useState(null);
  const [actionError, setActionError] = useState("");
  const [actionMessage, setActionMessage] = useState("");
  const wasProcessingRef = useRef(false);
  const pollingRef = useRef(false);
  const messageTimeoutRef = useRef(null);

  const showTemporaryMessage = useCallback((message) => {
    setActionMessage(message);

    if (messageTimeoutRef.current) {
      clearTimeout(messageTimeoutRef.current);
    }

    messageTimeoutRef.current = setTimeout(() => {
      setActionMessage("");
      messageTimeoutRef.current = null;
    }, 4000);
  }, []);

  const loadDocuments = useCallback(async (silent = false) => {
    try {
      // Do not set state before the first await. This keeps the initial
      // loading effect compatible with React's set-state-in-effect rule.
      const data = await getDocuments(100, 0);
      const updatedDocuments = data.documents || [];

      setDocuments(updatedDocuments);
      setSelectedDocument((currentDocument) => {
        if (!currentDocument) return currentDocument;

        return (
          updatedDocuments.find(
            (document) => document.document_id === currentDocument.document_id,
          ) || currentDocument
        );
      });

      if (!silent) setError("");
    } catch (err) {
      if (!silent) {
        setError(err.message || "Failed to load documents.");
      }
    } finally {
      if (!silent) setLoading(false);
    }
  }, []);

  // Initial fetch: update state only after the asynchronous request resolves.
  // Keeping this request inside the effect avoids synchronous setState-in-effect warnings.
  useEffect(() => {
    let cancelled = false;

    async function fetchInitialDocuments() {
      try {
        const data = await getDocuments(100, 0);

        if (cancelled) return;

        const updatedDocuments = data.documents || [];
        setDocuments(updatedDocuments);
        setError("");
      } catch (err) {
        if (!cancelled) {
          setError(err.message || "Failed to load documents.");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void fetchInitialDocuments();

    return () => {
      cancelled = true;
    };
  }, []);

  // Check processing status once on page load. Continue polling only while a
  // processing job is active; the recursive timeout avoids overlapping requests.
  const isProcessingActive = processingStatus?.is_running;

  useEffect(() => {
    // `undefined` means the initial status has not been checked yet.
    // When status is idle, do not start another request or interval.
    if (isProcessingActive === false) {
      return undefined;
    }

    let cancelled = false;
    let timeoutId = null;

    async function refreshProcessingStatus() {
      // A previous request may still be resolving during an effect transition.
      if (pollingRef.current) {
        if (!cancelled) {
          timeoutId = setTimeout(refreshProcessingStatus, 250);
        }
        return;
      }

      pollingRef.current = true;
      let shouldContinuePolling = false;

      try {
        const status = await getProcessingStatus();
        if (cancelled) return;

        setProcessingStatus(status);

        // Refresh the document table when stale documents are recovered.
        if (status.recovered_documents > 0) {
          showTemporaryMessage(
            `${status.recovered_documents} stale document(s) recovered and moved to pending.`,
          );
          await loadDocuments(true);
        }

        if (status.is_running) {
          wasProcessingRef.current = true;
          shouldContinuePolling = true;

          // Refresh document rows and statistics while processing is active.
          await loadDocuments(true);
        } else if (wasProcessingRef.current) {
          // The job has transitioned from running to finished.
          wasProcessingRef.current = false;
          await loadDocuments(true);

          const completed = status.completed || 0;
          const failed = status.failed || 0;
          showTemporaryMessage(
            failed === 0
              ? `Processing completed successfully (${completed} document${completed === 1 ? "" : "s"}).`
              : `Processing finished: ${completed} completed, ${failed} failed.`,
          );
        }
      } catch (err) {
        if (!cancelled) {
          console.error("Failed to fetch processing status:", err);
          // Retry after a short delay if the UI still believes processing is active.
          shouldContinuePolling = isProcessingActive === true;
        }
      } finally {
        pollingRef.current = false;
      }

      if (!cancelled && shouldContinuePolling) {
        timeoutId = setTimeout(refreshProcessingStatus, 2000);
      }
    }

    void refreshProcessingStatus();

    return () => {
      cancelled = true;
      if (timeoutId !== null) {
        clearTimeout(timeoutId);
      }
    };
  }, [isProcessingActive, loadDocuments, showTemporaryMessage]);

  // Clear the temporary-message timer only when the page unmounts.
  useEffect(() => {
    return () => {
      if (messageTimeoutRef.current) {
        clearTimeout(messageTimeoutRef.current);
      }
    };
  }, []);

  useEffect(() => {
    function handleEscape(event) {
      if (event.key === "Escape") {
        setSelectedDocument(null);
      }
    }

    window.addEventListener("keydown", handleEscape);

    return () => window.removeEventListener("keydown", handleEscape);
  }, []);

  async function handleSingleProcessing(document) {
    try {
      setProcessingDocumentId(document.document_id);
      setActionError("");
      setActionMessage("");

      const result = await startSingleProcessing(document.document_id);
      // The backend marks the job as running before returning this response.
      // Set the ref immediately so even very short jobs get a completion message.
      wasProcessingRef.current = true;
      setProcessingStatus((current) => ({
        ...(current || {}),
        is_running: true,
        mode: "single",
        total: 1,
        processed: 0,
        completed: 0,
        failed: 0,
      }));
      setActionMessage(result.message || "Document processing started.");
      await loadDocuments(true);
    } catch (err) {
      setActionError(err.message || "Unable to start document processing.");
    } finally {
      setProcessingDocumentId(null);
    }
  }

  async function handleBatchProcessing() {
    try {
      setProcessingAction(true);
      setActionError("");
      setActionMessage("");

      const result = await startBatchProcessing(batchLimit);

      if (result.total > 0) {
        wasProcessingRef.current = true;
        setProcessingStatus((current) => ({
          ...(current || {}),
          is_running: true,
          mode: "batch",
          total: result.total,
          processed: 0,
          completed: 0,
          failed: 0,
        }));
        setActionMessage(`Batch processing started for ${result.total} document(s).`);
      } else {
        showTemporaryMessage("No pending documents are available for processing.");
      }

      await loadDocuments(true);
    } catch (err) {
      setActionError(err.message || "Unable to start batch processing.");
    } finally {
      setProcessingAction(false);
    }
  }

  const filteredDocuments = documents.filter((document) => {
    const query = searchQuery.toLowerCase();

    return (
      (document.title || "").toLowerCase().includes(query) ||
      (document.original_filename || "").toLowerCase().includes(query) ||
      (document.source_name || "").toLowerCase().includes(query)
    );
  });

  const stats = {
    total: documents.length,
    completed: documents.filter(
      (document) => document.processing_status === "completed",
    ).length,
    pending: documents.filter(
      (document) => document.processing_status === "pending",
    ).length,
    failed: documents.filter(
      (document) => document.processing_status === "failed",
    ).length,
  };

  function formatFileSize(bytes) {
    if (!bytes) return "0 B";

    const units = ["B", "KB", "MB", "GB"];
    let size = bytes;
    let unitIndex = 0;

    while (size >= 1024 && unitIndex < units.length - 1) {
      size /= 1024;
      unitIndex++;
    }

    return `${size.toFixed(1)} ${units[unitIndex]}`;
  }

  function formatDate(date) {
    if (!date) return "—";

    return new Date(date).toLocaleDateString("en-IN", {
      day: "2-digit",
      month: "short",
      year: "numeric",
    });
  }

  function formatDateTime(date) {
    if (!date) return "—";

    return new Date(date).toLocaleString("en-IN", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  function getStatus(status) {
    const styles = {
      completed: "bg-emerald-50 text-emerald-700 ring-emerald-200",
      pending: "bg-amber-50 text-amber-700 ring-amber-200",
      processing: "bg-blue-50 text-blue-700 ring-blue-200",
      failed: "bg-red-50 text-red-700 ring-red-200",
    };

    const icons = {
      completed: CheckCircle2,
      pending: Clock,
      processing: LoaderCircle,
      failed: AlertCircle,
    };

    const Icon = icons[status] || Clock;

    return (
      <span
        className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ring-1 ring-inset ${
          styles[status] || styles.pending
        }`}
      >
        <Icon size={13} />
        {status}
      </span>
    );
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">
            Document Management
          </h1>

          <p className="mt-1 text-sm text-slate-500">
            Manage registered research papers and their processing status.
          </p>
        </div>

        <button
          onClick={() => {
            setLoading(true);
            void loadDocuments();
          }}
          disabled={loading}
          className="inline-flex items-center justify-center gap-2 rounded-lg border border-slate-200 bg-white px-4 py-2.5 text-sm font-medium text-slate-700 transition hover:bg-slate-50 disabled:opacity-50"
        >
          <RefreshCw size={16} className={loading ? "animate-spin" : ""} />
          Refresh
        </button>
      </div>

      {/* Statistics */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard
          title="Registered Documents"
          value={stats.total}
          icon={Database}
          iconColor="text-slate-600"
          iconBg="bg-slate-100"
        />

        <StatCard
          title="Indexed"
          value={stats.completed}
          icon={CheckCircle2}
          iconColor="text-emerald-600"
          iconBg="bg-emerald-50"
        />

        <StatCard
          title="Pending"
          value={stats.pending}
          icon={Clock}
          iconColor="text-amber-600"
          iconBg="bg-amber-50"
        />

        <StatCard
          title="Failed"
          value={stats.failed}
          icon={AlertCircle}
          iconColor="text-red-600"
          iconBg="bg-red-50"
        />
      </div>

      {/* Document Processing Controls */}
      <div className="space-y-4 rounded-xl border border-slate-200 bg-white p-5">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="font-semibold text-slate-900">Document Processing</h2>
            <p className="mt-1 text-sm text-slate-500">
              Process pending documents individually or in a limited batch.
            </p>
          </div>

          {processingStatus?.is_running && (
            <span className="inline-flex w-fit items-center gap-2 rounded-full bg-blue-50 px-3 py-1.5 text-xs font-medium text-blue-700">
              <LoaderCircle size={14} className="animate-spin" />
              Processing in progress
            </span>
          )}
        </div>

        <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
          <div>
            <label
              htmlFor="batch-size"
              className="mb-1.5 block text-xs font-medium text-slate-600"
            >
              Batch size
            </label>
            <select
              id="batch-size"
              value={batchLimit}
              onChange={(event) => setBatchLimit(Number(event.target.value))}
              disabled={processingStatus?.is_running || processingAction}
              className="rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm outline-none focus:border-blue-500 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {[1, 2, 3, 5].map((size) => (
                <option key={size} value={size}>
                  {size} document{size > 1 ? "s" : ""}
                </option>
              ))}
            </select>
          </div>

          <button
            type="button"
            onClick={handleBatchProcessing}
            disabled={
              processingStatus?.is_running || processingAction || stats.pending === 0
            }
            className="inline-flex items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {processingAction ? (
              <LoaderCircle size={16} className="animate-spin" />
            ) : (
              <Play size={16} />
            )}
            Process Pending Documents
          </button>
        </div>

        {actionMessage && (
          <div
            role="status"
            className="flex items-center gap-2 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2.5 text-sm text-emerald-700"
          >
            <CheckCircle2 size={16} className="shrink-0" />
            <span>{actionMessage}</span>
          </div>
        )}

        {actionError && (
          <p role="alert" className="text-sm text-red-600">
            {actionError}
          </p>
        )}

        {processingStatus?.is_running && (
          <div className="space-y-3 rounded-lg bg-blue-50 p-4">
            {/*
              progress_percent is calculated by the backend from actual
              pipeline stages and completed embedding attempts.
            */}
            <div className="flex justify-between gap-3 text-sm">
              <span className="font-medium text-blue-900">
                {processingStatus.mode === "batch"
                  ? "Overall batch progress"
                  : "Individual document progress"}
              </span>
              <span className="font-semibold tabular-nums text-blue-700">
                {Math.min(
                  100,
                  Math.max(0, Number(processingStatus.progress_percent) || 0),
                ).toFixed(1)}
                %
              </span>
            </div>

            <div
              className="h-2.5 overflow-hidden rounded-full bg-blue-100"
              role="progressbar"
              aria-label="Document processing progress"
              aria-valuemin={0}
              aria-valuemax={100}
              aria-valuenow={Math.min(
                100,
                Math.max(0, Number(processingStatus.progress_percent) || 0),
              )}
            >
              <div
                className="h-full rounded-full bg-blue-600 transition-[width] duration-500 ease-out"
                style={{
                  width: `${Math.min(
                    100,
                    Math.max(0, Number(processingStatus.progress_percent) || 0),
                  )}%`,
                }}
              />
            </div>

            <div className="flex flex-wrap gap-x-4 gap-y-2 text-xs text-slate-600">
              <span>Completed: {processingStatus.completed || 0}</span>
              <span>Failed: {processingStatus.failed || 0}</span>
              <span>
                Documents: {processingStatus.processed || 0}/
                {processingStatus.total || 0}
              </span>
              <span>
                Remaining: {Math.max(
                  0,
                  (processingStatus.total || 0) -
                    (processingStatus.processed || 0),
                )}
              </span>
            </div>

            {processingStatus.current_document && (
              <p className="break-words text-xs text-blue-800">
                Currently processing:{" "}
                <strong>{processingStatus.current_document.title}</strong>
              </p>
            )}

            {processingStatus.current_stage && (
              <div className="space-y-1 border-t border-blue-100 pt-3">
                <p className="text-sm font-semibold text-blue-900">
                  {processingStatus.current_stage}
                </p>
                {processingStatus.current_details && (
                  <p className="text-xs text-blue-700">
                    {processingStatus.current_details}
                  </p>
                )}
              </div>
            )}

            {(processingStatus.total_chunks || 0) > 0 && (
              <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-slate-600">
                <span>
                  Embedding attempts:{" "}
                  <strong>
                    {processingStatus.completed_chunks || 0}/
                    {processingStatus.total_chunks}
                  </strong>
                </span>
                <span>
                  Successful: {processingStatus.successful_chunks || 0}
                  {" · "}
                  Failed: {processingStatus.failed_chunks || 0}
                </span>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Documents Table */}
      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
        <div className="flex flex-col gap-3 border-b border-slate-200 p-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="font-semibold text-slate-900">Registered Papers</h2>

            <p className="mt-1 text-sm text-slate-500">
              {filteredDocuments.length} documents displayed
            </p>
          </div>

          <div className="relative w-full sm:max-w-xs">
            <Search
              size={16}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
            />

            <input
              type="text"
              placeholder="Search documents..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full rounded-lg border border-slate-200 py-2 pl-9 pr-3 text-sm outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
            />
          </div>
        </div>

        {loading ? (
          <div className="flex min-h-64 items-center justify-center">
            <div className="flex items-center gap-3 text-slate-500">
              <LoaderCircle size={20} className="animate-spin" />
              <span className="text-sm">Loading documents...</span>
            </div>
          </div>
        ) : error ? (
          <div className="flex min-h-64 flex-col items-center justify-center gap-3 px-6 text-center">
            <AlertCircle size={32} className="text-red-500" />
            <p className="text-sm text-red-600">{error}</p>

            <button
              onClick={loadDocuments}
              className="rounded-lg bg-slate-900 px-4 py-2 text-sm text-white hover:bg-slate-800"
            >
              Try again
            </button>
          </div>
        ) : filteredDocuments.length === 0 ? (
          <div className="flex min-h-64 flex-col items-center justify-center gap-3 px-6 text-center">
            <FileText size={36} className="text-slate-300" />

            <div>
              <p className="font-medium text-slate-700">No documents found</p>

              <p className="mt-1 text-sm text-slate-500">
                {searchQuery
                  ? "Try a different search term."
                  : "Registered research papers will appear here."}
              </p>
            </div>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[1050px] text-left">
              <thead className="bg-slate-50">
                <tr>
                  <th className="px-5 py-3 text-xs font-semibold uppercase tracking-wide text-slate-500">
                    Document
                  </th>

                  <th className="px-5 py-3 text-xs font-semibold uppercase tracking-wide text-slate-500">
                    Source
                  </th>

                  <th className="px-5 py-3 text-xs font-semibold uppercase tracking-wide text-slate-500">
                    Status
                  </th>

                  <th className="px-5 py-3 text-xs font-semibold uppercase tracking-wide text-slate-500">
                    Chunks
                  </th>

                  <th className="px-5 py-3 text-xs font-semibold uppercase tracking-wide text-slate-500">
                    File Size
                  </th>

                  <th className="px-5 py-3 text-xs font-semibold uppercase tracking-wide text-slate-500">
                    Registered
                  </th>
                  <th className="px-5 py-3 text-xs font-semibold uppercase tracking-wide text-slate-500">
                    Actions
                  </th>
                </tr>
              </thead>

              <tbody className="divide-y divide-slate-100">
                {filteredDocuments.map((document) => (
                  <tr
                    key={document.document_id}
                    onClick={() => setSelectedDocument(document)}
                    className="cursor-pointer transition hover:bg-blue-50/50"
                    title="Click to view document details"
                  >
                    <td className="px-5 py-4">
                      <div className="flex items-start gap-3">
                        <div className="mt-1 rounded-lg bg-blue-50 p-2 text-blue-600">
                          <FileText size={18} />
                        </div>

                        <div className="min-w-0">
                          <p className="max-w-md font-medium text-slate-800">
                            {document.title || document.original_filename}
                          </p>

                          <p className="mt-1 text-xs text-slate-500">
                            {document.original_filename}
                          </p>

                          {document.processing_status === "failed" &&
                            document.processing_error && (
                              <p className="mt-2 max-w-md text-xs text-red-600">
                                {document.processing_error}
                              </p>
                            )}
                        </div>
                      </div>
                    </td>

                    <td className="px-5 py-4">
                      <span className="rounded-md bg-slate-100 px-2 py-1 text-xs font-medium text-slate-700">
                        {document.source_name}
                      </span>
                    </td>

                    <td className="px-5 py-4">
                      {getStatus(document.processing_status)}
                    </td>

                    <td className="px-5 py-4 text-sm text-slate-700">
                      {document.chunk_count}
                    </td>

                    <td className="px-5 py-4 text-sm text-slate-700">
                      {formatFileSize(document.file_size)}
                    </td>

                    <td className="px-5 py-4 text-sm text-slate-500">
                      {formatDate(document.created_at)}
                    </td>
                    <td className="px-5 py-4">
                      {document.processing_status === "pending" && (
                        <button
                          type="button"
                          onClick={(event) => {
                            event.stopPropagation();
                            handleSingleProcessing(document);
                          }}
                          disabled={
                            processingStatus?.is_running ||
                            processingDocumentId === document.document_id
                          }
                          className="inline-flex items-center gap-1.5 rounded-lg bg-blue-50 px-3 py-2 text-xs font-medium text-blue-700 transition hover:bg-blue-100 disabled:cursor-not-allowed disabled:opacity-50"
                        >
                          {processingDocumentId === document.document_id ? (
                            <LoaderCircle size={14} className="animate-spin" />
                          ) : (
                            <Play size={14} />
                          )}
                          Process
                        </button>
                      )}

                      {document.processing_status === "failed" && (
                        <button
                          type="button"
                          onClick={(event) => {
                            event.stopPropagation();
                            handleSingleProcessing(document);
                          }}
                          disabled={
                            processingStatus?.is_running ||
                            processingDocumentId === document.document_id
                          }
                          className="inline-flex items-center gap-1.5 rounded-lg bg-red-50 px-3 py-2 text-xs font-medium text-red-700 transition hover:bg-red-100 disabled:cursor-not-allowed disabled:opacity-50"
                        >
                          {processingDocumentId === document.document_id ? (
                            <LoaderCircle size={14} className="animate-spin" />
                          ) : (
                            <RotateCcw size={14} />
                          )}
                          Retry
                        </button>
                      )}

                      {document.processing_status === "processing" && (
                        <span className="inline-flex items-center gap-1.5 text-xs text-blue-600">
                          <LoaderCircle size={14} className="animate-spin" />
                          Processing
                        </span>
                      )}

                      {document.processing_status === "completed" && (
                        <span className="text-xs text-emerald-600">Completed</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Document Details Modal */}
      {selectedDocument && (
        <DocumentDetailsModal
          document={selectedDocument}
          onClose={() => setSelectedDocument(null)}
          formatFileSize={formatFileSize}
          formatDate={formatDate}
          formatDateTime={formatDateTime}
          getStatus={getStatus}
        />
      )}
    </div>
  );
}

function DocumentDetailsModal({
  document,
  onClose,
  formatFileSize,
  formatDate,
  formatDateTime,
  getStatus,
}) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="max-h-[90vh] w-full max-w-3xl overflow-y-auto rounded-2xl bg-white shadow-2xl"
        onClick={(event) => event.stopPropagation()}
      >
        {/* Modal Header */}
        <div className="sticky top-0 z-10 flex items-start justify-between gap-4 border-b border-slate-200 bg-white px-6 py-5">
          <div className="flex items-start gap-3">
            <div className="rounded-xl bg-blue-50 p-3 text-blue-600">
              <FileText size={22} />
            </div>

            <div>
              <h2 className="text-lg font-semibold text-slate-900">
                Document Details
              </h2>

              <p className="mt-1 text-sm text-slate-500">
                Complete metadata and processing information
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="rounded-lg p-2 text-slate-500 transition hover:bg-slate-100 hover:text-slate-900"
            aria-label="Close modal"
          >
            <X size={20} />
          </button>
        </div>

        {/* Modal Content */}
        <div className="space-y-6 p-6">
          {/* Title */}
          <section>
            <label className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Title
            </label>

            <h3 className="mt-2 text-lg font-semibold leading-relaxed text-slate-900">
              {document.title || document.original_filename}
            </h3>
          </section>

          {/* Abstract */}
          <section>
            <SectionHeading title="Abstract" />

            <p className="mt-3 whitespace-pre-line text-sm leading-7 text-slate-600">
              {document.abstract || "No abstract available."}
            </p>
          </section>

          {/* Authors */}
          <section>
            <SectionHeading title="Authors" icon={UserRound} />

            <div className="mt-3">
              {document.authors?.length > 0 ? (
                <div className="flex flex-wrap gap-2">
                  {document.authors.map((author, index) => (
                    <span
                      key={index}
                      className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-1.5 text-sm text-slate-700"
                    >
                      {author}
                    </span>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-slate-500">Authors not available.</p>
              )}
            </div>
          </section>

          {/* Publication Metadata */}
          <section>
            <SectionHeading title="Publication Information" />

            <div className="mt-3 grid grid-cols-1 gap-4 sm:grid-cols-2">
              <DetailItem
                label="Publication Date"
                value={formatDate(document.published_date)}
                icon={Calendar}
              />

              <DetailItem label="Source" value={document.source_name || "—"} />

              <DetailItem
                label="External ID"
                value={document.external_id || "—"}
              />

              <DetailItem label="DOI" value={document.doi || "—"} />
            </div>
          </section>

          {/* Links */}
          <section>
            <SectionHeading title="External Resources" />

            <div className="mt-3 flex flex-wrap gap-3">
              {document.source_url && (
                <ExternalLinkButton
                  href={document.source_url}
                  label="Source Page"
                />
              )}

              {document.pdf_url && (
                <ExternalLinkButton
                  href={document.pdf_url}
                  label="PDF Source"
                />
              )}

              {document.doi && (
                <ExternalLinkButton
                  href={`https://doi.org/${document.doi}`}
                  label="Open DOI"
                />
              )}

              {!document.source_url && !document.pdf_url && !document.doi && (
                <p className="text-sm text-slate-500">
                  No external links available.
                </p>
              )}
            </div>
          </section>

          {/* File Information */}
          <section>
            <SectionHeading title="File Information" />

            <div className="mt-3 grid grid-cols-1 gap-4 sm:grid-cols-2">
              <DetailItem
                label="Original Filename"
                value={document.original_filename}
                icon={FileText}
              />

              <DetailItem
                label="File Size"
                value={formatFileSize(document.file_size)}
                icon={HardDrive}
              />

              <DetailItem label="Content Type" value="application/pdf" />

              <DetailItem label="File ID" value={document.document_id} />
            </div>
          </section>

          {/* Processing */}
          <section>
            <SectionHeading title="Processing Information" />

            <div className="mt-3 grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div className="rounded-xl border border-slate-200 p-4">
                <label className="text-xs font-medium text-slate-500">
                  Processing Status
                </label>

                <div className="mt-2">
                  {getStatus(document.processing_status)}
                </div>
              </div>

              <DetailItem
                label="Stored Chunks"
                value={document.chunk_count ?? 0}
                icon={Layers}
              />

              <DetailItem
                label="Processed At"
                value={formatDateTime(document.processed_at)}
              />

              <DetailItem
                label="Registered At"
                value={formatDateTime(document.created_at)}
              />

              <DetailItem
                label="Downloaded At"
                value={formatDateTime(document.downloaded_at)}
              />
            </div>

            {document.processing_error && (
              <div className="mt-4 rounded-xl border border-red-200 bg-red-50 p-4">
                <div className="flex items-center gap-2 text-sm font-semibold text-red-700">
                  <AlertCircle size={16} />
                  Processing Error
                </div>

                <p className="mt-2 whitespace-pre-wrap text-sm leading-relaxed text-red-600">
                  {document.processing_error}
                </p>
              </div>
            )}
          </section>
        </div>

        {/* Modal Footer */}
        <div className="sticky bottom-0 flex justify-end border-t border-slate-200 bg-white px-6 py-4">
          <button
            onClick={onClose}
            className="rounded-lg bg-slate-900 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-slate-800"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

function SectionHeading({ title, icon: Icon }) {
  return (
    <div className="flex items-center gap-2">
      {Icon && <Icon size={16} className="text-slate-500" />}

      <h4 className="text-sm font-semibold text-slate-800">{title}</h4>
    </div>
  );
}

function DetailItem({ label, value, icon: Icon }) {
  return (
    <div className="min-w-0 rounded-xl border border-slate-200 p-4">
      <label className="flex items-center gap-2 text-xs font-medium text-slate-500">
        {Icon && <Icon size={14} />}
        {label}
      </label>

      <p className="mt-2 break-words text-sm font-medium text-slate-800">
        {value || "—"}
      </p>
    </div>
  );
}

function ExternalLinkButton({ href, label }) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="inline-flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-sm font-medium text-blue-600 transition hover:border-blue-200 hover:bg-blue-50"
    >
      {label}
      <ExternalLink size={14} />
    </a>
  );
}

function StatCard({ title, value, icon: Icon, iconColor, iconBg }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5">
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium text-slate-500">{title}</p>

        <div className={`rounded-lg p-2 ${iconBg} ${iconColor}`}>
          <Icon size={20} />
        </div>
      </div>

      <p className="mt-4 text-2xl font-semibold text-slate-900">{value}</p>
    </div>
  );
}

export default Documents;
