import React from "react";

interface Props {
  data: unknown;
  url: string;
}

const ResultsPanel: React.FC<Props> = ({ data, url }) => {
  const formatted = JSON.stringify(data, null, 2);

  return (
    <section className="results-section" aria-label="Audit results">
      <div className="results-header">
        <h2 className="results-title">Audit Results</h2>
        <span className="results-url">{url}</span>
      </div>

      <div className="raw-response-card">
        <div className="raw-response-header">
          <span>
            <span className="raw-dot" style={{ marginRight: 8 }} />
            API Response
          </span>
          <span style={{ fontFamily: "'JetBrains Mono', monospace", color: "var(--text-muted)" }}>
            JSON
          </span>
        </div>
        <pre className="raw-response-body">{formatted}</pre>
      </div>
    </section>
  );
};

export default ResultsPanel;
