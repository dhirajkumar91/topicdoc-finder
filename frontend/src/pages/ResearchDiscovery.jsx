
import { useState } from "react";
import {
  Search,
  Loader2,
  ExternalLink,
  FileText,
  CalendarDays,
  Users,
  Globe,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import {
  discoverResearch,
  downloadSelectedPapers,
  uploadManualPdf,
} from "../services/discoveryService";

export default function ResearchDiscovery() {
  const [query, setQuery] = useState("");
  const [papers, setPapers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [downloadLoading, setDownloadLoading] = useState(false);
  const [error, setError] = useState("");
  const [downloadError, setDownloadError] = useState("");
  const [downloadSummary, setDownloadSummary] = useState(null);
  const [searched, setSearched] = useState(false);
  const [expandedAbstracts, setExpandedAbstracts] = useState({});
  const [maxResults, setMaxResults] = useState(5);
  const [selectedPapers, setSelectedPapers] = useState([]);
  const [manualUploadLoading, setManualUploadLoading] = useState({});
  const [manualUploadResults, setManualUploadResults] = useState({});

  const handleManualUpload = async (file, paper, index) => {
    if (!file) return;

    if (file.type !== "application/pdf" && !file.name.toLowerCase().endsWith(".pdf")) {
      setManualUploadResults((prev) => ({
        ...prev,
        [index]: { status: "failed", message: "Please select a PDF file." },
      }));
      return;
    }

    setManualUploadLoading((prev) => ({ ...prev, [index]: true }));
    setManualUploadResults((prev) => ({ ...prev, [index]: null }));

    try {
      const result = await uploadManualPdf(file, paper);
      setManualUploadResults((prev) => ({
        ...prev,
        [index]: {
          status: result.status || "saved",
          message: result.message || "PDF uploaded and registered successfully.",
          filename: result.filename,
          document_id: result.document_id,
        },
      }));
    } catch (err) {
      setManualUploadResults((prev) => ({
        ...prev,
        [index]: { status: "failed", message: err.message || "Manual PDF upload failed." },
      }));
    } finally {
      setManualUploadLoading((prev) => ({ ...prev, [index]: false }));
    }
  };

  const handleSearch = async (e) => {
    e.preventDefault();

    if (!query.trim()) return;

    setLoading(true);
    setError("");
    setPapers([]);
    setSearched(true);
    setExpandedAbstracts({});
    setSelectedPapers([]);
    setManualUploadLoading({});
    setManualUploadResults({});
    setDownloadError("");
    setDownloadSummary(null);

    try {
      const data = await discoverResearch(query.trim(), maxResults);
      setPapers(data.results || []);
    } catch (err) {
      setError(err.message || "Research discovery failed.");
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadSelected = async () => {
    if (selectedPapers.length === 0 || downloadLoading) return;

    const selectedDocuments = selectedPapers.map(
      (index) => papers[index]
    );

    setDownloadLoading(true);
    setDownloadError("");
    setDownloadSummary(null);

    try {
      const data = await downloadSelectedPapers(selectedDocuments);

      setDownloadSummary(data);
    } catch (err) {
      setDownloadError(
        err.message || "Failed to download selected papers."
      );
    } finally {
      setDownloadLoading(false);
    }
  };

  const toggleAbstract = (index) => {
    setExpandedAbstracts((prev) => ({
      ...prev,
      [index]: !prev[index],
    }));
  };

  const togglePaperSelection = (index) => {
    setSelectedPapers((prev) =>
      prev.includes(index)
        ? prev.filter((selectedIndex) => selectedIndex !== index)
        : [...prev, index]
    );
  };

  const toggleSelectAll = () => {
    if (selectedPapers.length === papers.length) {
      setSelectedPapers([]);
    } else {
      setSelectedPapers(papers.map((_, index) => index));
    }
  };

  const getSourceNames = (paper) => {
    if (Array.isArray(paper.sources)) {
      return paper.sources;
    }

    if (paper.source_name) {
      return [paper.source_name];
    }

    return [];
  };

  return (
    <div className="max-w-6xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-2 text-indigo-600 text-sm font-medium mb-3">
          <Globe size={17} />
          Admin Research Discovery
        </div>

        <h1 className="text-3xl font-bold tracking-tight text-slate-900">
          Research Discovery
        </h1>

        <p className="mt-2 text-slate-500 max-w-2xl">
          Discover academic papers from external research sources. Find
          relevant publications to add to your knowledge base.
        </p>
      </div>

      {/* Search */}
      <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm mb-8">
        <form onSubmit={handleSearch}>
          <label className="block text-sm font-medium text-slate-700 mb-3">
            Research topic
          </label>

          <div className="flex flex-col sm:flex-row gap-3">
            <div className="flex items-center gap-3 border border-slate-200 rounded-xl px-4 flex-1 focus-within:ring-2 focus-within:ring-indigo-100 focus-within:border-indigo-400">
              <Search size={19} className="text-slate-400 shrink-0" />

              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="e.g. machine learning in healthcare"
                className="w-full py-3 outline-none text-sm bg-transparent"
              />
            </div>

            <button
              type="submit"
              disabled={loading || !query.trim()}
              className="px-5 py-3 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white rounded-xl font-medium text-sm flex items-center justify-center gap-2 transition"
            >
              {loading ? (
                <Loader2 size={17} className="animate-spin" />
              ) : (
                <Search size={17} />
              )}
              Discover Papers
            </button>
          </div>

          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mt-4">
            <p className="text-xs text-slate-400">
              Searches the external academic sources configured in your
              backend.
            </p>

            <div className="flex items-center gap-2">
              <label className="text-xs text-slate-500">
                Results per source
              </label>

              <select
                value={maxResults}
                onChange={(e) => setMaxResults(Number(e.target.value))}
                className="border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-700 bg-white outline-none focus:ring-2 focus:ring-indigo-100"
              >
                <option value={3}>3</option>
                <option value={5}>5</option>
                <option value={10}>10</option>
                <option value={15}>15</option>
                <option value={20}>20</option>
              </select>
            </div>
          </div>
        </form>
      </div>

      {/* Search Error */}
      {error && (
        <div className="mb-6 p-4 border border-red-200 bg-red-50 rounded-xl text-sm text-red-600">
          {error}
        </div>
      )}

      {/* Download Error */}
      {downloadError && (
        <div className="mb-6 p-4 border border-red-200 bg-red-50 rounded-xl text-sm text-red-600">
          {downloadError}
        </div>
      )}

      {/* Download Summary */}
      {downloadSummary && (
        <div className="mb-6 p-5 border border-slate-200 bg-white rounded-xl shadow-sm">
          <h3 className="font-semibold text-slate-800 mb-3">
            Download Summary
          </h3>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div>
              <p className="text-xs text-slate-500">
                Requested
              </p>
              <p className="text-xl font-semibold text-slate-800">
                {downloadSummary.total_requested}
              </p>
            </div>

            <div>
              <p className="text-xs text-slate-500">
                Registered
              </p>
              <p className="text-xl font-semibold text-green-600">
                {downloadSummary.downloaded}
              </p>
            </div>

            <div>
              <p className="text-xs text-slate-500">
                Duplicates
              </p>
              <p className="text-xl font-semibold text-amber-600">
                {downloadSummary.duplicates}
              </p>
            </div>

            <div>
              <p className="text-xs text-slate-500">
                Failed
              </p>
              <p className="text-xl font-semibold text-red-600">
                {downloadSummary.failed}
              </p>
            </div>
          </div>

          {/* Individual Results */}
          {downloadSummary.results?.length > 0 && (
            <div className="mt-5 pt-4 border-t border-slate-100 space-y-3">
              {downloadSummary.results.map((result, index) => (
                <div
                  key={index}
                  className="flex flex-col sm:flex-row sm:items-start justify-between gap-2 text-sm"
                >
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-slate-700">
                      {result.title || "Untitled paper"}
                    </p>

                    {result.message && (
                      <p className="text-xs text-red-500 mt-1">
                        {result.message}
                      </p>
                    )}

                    {result.filename && (
                      <p className="text-xs text-slate-400 mt-1">
                        {result.filename}
                      </p>
                    )}
                  </div>

                  <span
                    className={`text-xs font-medium px-2.5 py-1 rounded-full shrink-0 ${
                      result.status === "saved"
                        ? "bg-green-50 text-green-700"
                        : result.status === "duplicate"
                        ? "bg-amber-50 text-amber-700"
                        : "bg-red-50 text-red-700"
                    }`}
                  >
                    {result.status === "saved"
                      ? "Registered"
                      : result.status === "duplicate"
                      ? "Duplicate"
                      : "Failed"}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="py-20 flex flex-col items-center justify-center text-slate-500">
          <Loader2 size={36} className="animate-spin text-indigo-600 mb-4" />

          <p className="font-medium text-slate-700">
            Searching academic sources...
          </p>

          <p className="text-sm mt-2">
            This may take a few moments.
          </p>
        </div>
      )}

      {/* Results */}
      {!loading && papers.length > 0 && (
        <div>
          {/* Results Header */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-5">
            <div>
              <h2 className="text-lg font-semibold text-slate-800">
                Discovery Results
              </h2>

              <p className="text-sm text-slate-500 mt-1">
                {papers.length} papers discovered
              </p>
            </div>

            {/* Selection Controls */}
            <div className="flex flex-wrap items-center justify-between sm:justify-end gap-3">
              <span className="text-sm font-medium text-indigo-600">
                {selectedPapers.length} selected
              </span>

              <button
                type="button"
                onClick={toggleSelectAll}
                disabled={downloadLoading}
                className="text-sm font-medium text-indigo-600 hover:text-indigo-800 transition disabled:opacity-50"
              >
                {selectedPapers.length === papers.length
                  ? "Deselect All"
                  : "Select All"}
              </button>

              <button
                type="button"
                onClick={handleDownloadSelected}
                disabled={selectedPapers.length === 0 || downloadLoading}
                className="inline-flex items-center gap-2 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-300 disabled:text-slate-500 disabled:cursor-not-allowed text-white rounded-xl text-sm font-medium transition"
              >
                {downloadLoading ? (
                  <Loader2 size={16} className="animate-spin" />
                ) : (
                  <FileText size={16} />
                )}

                {downloadLoading
                  ? "Downloading..."
                  : `Download Selected (${selectedPapers.length})`}
              </button>
            </div>
          </div>

          <div className="space-y-4">
            {papers.map((paper, index) => {
              const sources = getSourceNames(paper);
              const abstractExpanded = expandedAbstracts[index];
              const isSelected = selectedPapers.includes(index);

              return (
                <article
                  key={`${paper.external_id || paper.doi || paper.title}-${index}`}
                  className={`bg-white rounded-2xl p-6 shadow-sm transition ${
                    isSelected
                      ? "border-2 border-indigo-400"
                      : "border border-slate-200"
                  }`}
                >
                  {/* Paper Title and Selection */}
                  <div className="flex items-start gap-4">
                    {/* Checkbox */}
                    <div className="pt-1">
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => togglePaperSelection(index)}
                        disabled={downloadLoading}
                        className="h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500 cursor-pointer disabled:cursor-not-allowed"
                        aria-label={`Select ${paper.title || "paper"}`}
                      />
                    </div>

                    {/* Paper Icon */}
                    <div className="h-11 w-11 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center shrink-0">
                      <FileText size={21} />
                    </div>

                    <div className="flex-1 min-w-0">
                      <h3 className="text-lg font-semibold text-slate-900 leading-snug">
                        {paper.title || "Untitled paper"}
                      </h3>

                      {/* Metadata */}
                      <div className="flex flex-wrap gap-x-5 gap-y-2 mt-3 text-xs text-slate-500">
                        {paper.published_date && (
                          <span className="flex items-center gap-1.5">
                            <CalendarDays size={14} />
                            {paper.published_date}
                          </span>
                        )}

                        {paper.authors?.length > 0 && (
                          <span className="flex items-center gap-1.5">
                            <Users size={14} />
                            {paper.authors.slice(0, 3).join(", ")}
                            {paper.authors.length > 3 &&
                              ` +${paper.authors.length - 3}`}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Sources */}
                  {sources.length > 0 && (
                    <div className="flex flex-wrap gap-2 mt-4">
                      {sources.map((source, sourceIndex) => (
                        <span
                          key={sourceIndex}
                          className="text-xs font-medium text-indigo-700 bg-indigo-50 px-2.5 py-1 rounded-full"
                        >
                          {source}
                        </span>
                      ))}
                    </div>
                  )}

                  {/* Abstract */}
                  {paper.abstract && (
                    <div className="mt-5">
                      <p
                        className={`text-sm text-slate-600 leading-7 whitespace-pre-wrap ${
                          abstractExpanded ? "" : "line-clamp-4"
                        }`}
                      >
                        {paper.abstract}
                      </p>

                      {paper.abstract.length > 300 && (
                        <button
                          onClick={() => toggleAbstract(index)}
                          className="mt-2 text-sm font-medium text-indigo-600 hover:text-indigo-800 flex items-center gap-1"
                        >
                          {abstractExpanded ? (
                            <>
                              Show less <ChevronUp size={16} />
                            </>
                          ) : (
                            <>
                              Read more <ChevronDown size={16} />
                            </>
                          )}
                        </button>
                      )}
                    </div>
                  )}

                  {/* DOI */}
                  {paper.doi && (
                    <p className="mt-4 text-xs text-slate-400 break-all">
                      DOI: {paper.doi}
                    </p>
                  )}

                  {/* Actions */}
                  <div className="flex flex-wrap items-center gap-3 mt-5 pt-5 border-t border-slate-100">
                    {paper.source_url && (
                      <a
                        href={paper.source_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-2 px-4 py-2 border border-slate-200 rounded-lg text-sm font-medium text-slate-700 hover:bg-slate-50 transition"
                      >
                        <ExternalLink size={16} />
                        View Source
                      </a>
                    )}

                    {paper.pdf_url && (
                      <a
                        href={paper.pdf_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-50 text-indigo-700 rounded-lg text-sm font-medium hover:bg-indigo-100 transition"
                      >
                        <FileText size={16} />
                        PDF Link
                      </a>
                    )}
                    <label className={`inline-flex items-center gap-2 px-4 py-2 border border-slate-200 rounded-lg text-sm font-medium cursor-pointer hover:bg-slate-50 transition ${manualUploadLoading[index] ? "opacity-60 cursor-not-allowed" : "text-slate-700"}`}>
                      {manualUploadLoading[index] ? (
                        <Loader2 size={16} className="animate-spin" />
                      ) : (
                        <FileText size={16} />
                      )}
                      {manualUploadLoading[index] ? "Uploading PDF..." : "Upload Manual PDF"}
                      <input
                        type="file"
                        accept="application/pdf,.pdf"
                        className="hidden"
                        disabled={manualUploadLoading[index]}
                        onChange={(e) => {
                          const file = e.target.files?.[0];
                          if (file) handleManualUpload(file, paper, index);
                          e.target.value = "";
                        }}
                      />
                    </label>
                  </div>

                  {manualUploadResults[index] && (
                    <div className={`mt-3 p-3 rounded-lg text-sm ${
                      manualUploadResults[index].status === "failed"
                        ? "bg-red-50 text-red-700 border border-red-200"
                        : "bg-green-50 text-green-700 border border-green-200"
                    }`}>
                      <p>{manualUploadResults[index].message}</p>
                      {manualUploadResults[index].filename && (
                        <p className="text-xs mt-1 opacity-80">
                          {manualUploadResults[index].filename}
                        </p>
                      )}
                    </div>
                  )}
                </article>
              );
            })}
          </div>
        </div>
      )}

      {/* No Results */}
      {!loading && searched && papers.length === 0 && !error && (
        <div className="bg-white border border-slate-200 border-dashed rounded-2xl p-12 text-center">
          <div className="h-14 w-14 bg-slate-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
            <Search size={24} className="text-slate-400" />
          </div>

          <h3 className="text-lg font-semibold text-slate-800">
            No papers found
          </h3>

          <p className="text-sm text-slate-500 mt-2">
            Try a different topic or broader search query.
          </p>
        </div>
      )}

      {/* Initial State */}
      {!loading && !searched && (
        <div className="bg-white border border-slate-200 border-dashed rounded-2xl p-12 text-center">
          <div className="h-14 w-14 bg-indigo-50 rounded-2xl flex items-center justify-center mx-auto mb-4">
            <Globe size={24} className="text-indigo-600" />
          </div>

          <h3 className="text-lg font-semibold text-slate-800">
            Discover research papers
          </h3>

          <p className="text-sm text-slate-500 mt-2 max-w-md mx-auto">
            Search across external academic platforms and discover relevant
            research to add to your knowledge base.
          </p>
        </div>
      )}
    </div>
  );
}
