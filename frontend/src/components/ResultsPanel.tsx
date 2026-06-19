import React from "react";
import type { AuditResponse, AuditResult } from "../types";
import PerformanceCard from "./PerformanceCard";

interface Props {
  data: unknown;
  url: string;
}

const ResultsPanel: React.FC<Props> = ({ data, url }) => {
  const response = data as Partial<AuditResponse>;
  const results = Array.isArray(response.results) ? response.results : [];
  
  const perfResult = results.find(r => r.audit_type === "performance") as AuditResult | undefined;
  
  const rawData = { ...response };
  if (perfResult && Array.isArray(rawData.results)) {
    rawData.results = rawData.results.filter(r => r.audit_type !== "performance");
  }

  const formatted = JSON.stringify(rawData, null, 2);

  return (
    <section className="results-section" aria-label="Audit results">
      <div className="results-header">
        <h2 className="results-title">Audit Results</h2>
        <span className="results-url">{url}</span>
      </div>

      {perfResult && (
        <PerformanceCard result={perfResult} />
      )}

      {rawData.results && rawData.results.length > 0 && (
        <div className="raw-response-card" style={{ marginTop: perfResult ? 24 : 0 }}>
          <div className="raw-response-header">
            <span>
              <span className="raw-dot" style={{ marginRight: 8 }} />
              API Response (Unimplemented Audits)
            </span>
            <span style={{ fontFamily: "'JetBrains Mono', monospace", color: "var(--text-muted)" }}>
              JSON
            </span>
          </div>
          <pre className="raw-response-body">{formatted}</pre>
        </div>
      )}
    </section>
  );
};

export default ResultsPanel;
