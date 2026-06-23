import React, { useState } from "react";
import AuditForm from "../components/AuditForm";
import StatusBanner from "../components/StatusBanner";
import ResultsPanel from "../components/ResultsPanel";
import { runAudit } from "../services/api";
import type { AuditCategory, AuditStatus } from "../types";
import { AUDIT_CATEGORIES } from "../services/constants";

const ResultsLoadingSkeleton: React.FC = () => (
  <div className="results-skeleton" aria-hidden="true">
    <div className="results-skeleton-header">
      <div className="skeleton-line skeleton-line--title" />
      <div className="skeleton-line skeleton-line--subtitle" />
      <div className="skeleton-line skeleton-line--url" />
    </div>
    <div className="results-skeleton-summary">
      {Array.from({ length: 4 }, (_, i) => (
        <div key={i} className="skeleton-stat" />
      ))}
    </div>
    {Array.from({ length: 3 }, (_, i) => (
      <div key={i} className="skeleton-card">
        <div className="skeleton-line skeleton-line--card-title" />
        <div className="skeleton-metrics">
          {Array.from({ length: 4 }, (_, j) => (
            <div key={j} className="skeleton-metric" />
          ))}
        </div>
      </div>
    ))}
  </div>
);

const Home: React.FC = () => {
  const [url, setUrl] = useState("");
  const [selected, setSelected] = useState<AuditCategory[]>(
    AUDIT_CATEGORIES.map((c) => c.id)
  );
  const [status, setStatus] = useState<AuditStatus>("idle");
  const [result, setResult] = useState<unknown>(null);
  const [error, setError] = useState<string>("");

  const isLoading = status === "loading";

  const toggleCategory = (cat: AuditCategory) => {
    setSelected((prev) =>
      prev.includes(cat) ? prev.filter((c) => c !== cat) : [...prev, cat]
    );
  };

  const handleSubmit = async () => {
    const trimmed = url.trim();
    if (!trimmed) return;

    try {
      new URL(trimmed);
    } catch {
      setError("Please enter a valid URL including http:// or https://");
      setStatus("error");
      return;
    }

    setStatus("loading");
    setError("");
    setResult(null);

    try {
      const data = await runAudit({ url: trimmed, categories: selected });
      setResult(data);
      setStatus("success");
    } catch (err) {
      setError(err instanceof Error ? err.message : "An unexpected error occurred");
      setStatus("error");
    }
  };

  const liveMessage = isLoading
    ? "Running audit. Results will appear when complete."
    : status === "success"
      ? "Audit complete. Results are available below."
      : "";

  return (
    <>
      <div className="visually-hidden" aria-live="polite" aria-atomic="true">
        {liveMessage}
      </div>

      <AuditForm
        url={url}
        onUrlChange={setUrl}
        selected={selected}
        onToggle={toggleCategory}
        onSubmit={handleSubmit}
        loading={isLoading}
      />

      {isLoading && (
        <StatusBanner
          type="loading"
          message="Running audit. This may take up to a minute."
        />
      )}
      {status === "error" && (
        <StatusBanner type="error" message={error} />
      )}
      {status === "success" && (
        <StatusBanner type="success" message="Audit complete." />
      )}

      <section
        className="results-area"
        aria-label="Results area"
        aria-busy={isLoading}
      >
        {result ? (
          <ResultsPanel data={result} url={url} />
        ) : isLoading ? (
          <ResultsLoadingSkeleton />
        ) : (
          <div className="empty-state">
            <div className="empty-icon" aria-hidden="true" />
            <p className="empty-title">No audit run yet</p>
            <p className="empty-desc">
              Enter a URL above, select your audit categories, and click{" "}
              <strong>Run Audit</strong>.
            </p>
          </div>
        )}
      </section>
    </>
  );
};

export default Home;
