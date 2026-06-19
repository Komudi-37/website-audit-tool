import React, { useState } from "react";
import AuditForm from "../components/AuditForm";
import StatusBanner from "../components/StatusBanner";
import ResultsPanel from "../components/ResultsPanel";
import { runAudit } from "../services/api";
import type { AuditCategory, AuditStatus } from "../types";
import { AUDIT_CATEGORIES } from "../services/constants";

const Home: React.FC = () => {
  const [url, setUrl] = useState("");
  const [selected, setSelected] = useState<AuditCategory[]>(
    AUDIT_CATEGORIES.map((c) => c.id)
  );
  const [status, setStatus] = useState<AuditStatus>("idle");
  const [result, setResult] = useState<unknown>(null);
  const [error, setError] = useState<string>("");

  const toggleCategory = (cat: AuditCategory) => {
    setSelected((prev) =>
      prev.includes(cat) ? prev.filter((c) => c !== cat) : [...prev, cat]
    );
  };

  const handleSubmit = async () => {
    const trimmed = url.trim();
    if (!trimmed) return;

    // Basic URL validation
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

  return (
    <>
      <AuditForm
        url={url}
        onUrlChange={setUrl}
        selected={selected}
        onToggle={toggleCategory}
        onSubmit={handleSubmit}
        loading={status === "loading"}
      />

      {status === "loading" && (
        <StatusBanner type="loading" message="Connecting to audit engine…" />
      )}
      {status === "error" && (
        <StatusBanner type="error" message={error} />
      )}
      {status === "success" && (
        <StatusBanner type="success" message="Audit completed successfully!" />
      )}

      <section aria-label="Results area">
        {result ? (
          <ResultsPanel data={result} url={url} />
        ) : status !== "loading" ? (
          <div className="empty-state">
            <div className="empty-icon">🔎</div>
            <p className="empty-title">No audit run yet</p>
            <p className="empty-desc">
              Enter a URL above, select your audit categories, and click{" "}
              <strong>Run Audit</strong>.
            </p>
          </div>
        ) : null}
      </section>
    </>
  );
};

export default Home;
