import React from "react";
import type { AuditResponse, AuditResult } from "../types";
import PerformanceCard from "./PerformanceCard";
import SEOCard from "./SEOCard";
import AccessibilityCard from "./AccessibilityCard";
import SecurityCard from "./SecurityCard";
import FunctionalityCard from "./FunctionalityCard";
import ResultsSummary from "./ResultsSummary";
import { downloadPDF } from "../services/api";

interface Props {
  data: unknown;
  url: string;
}

const ResultsPanel: React.FC<Props> = ({ data, url }) => {
  const response = data as Partial<AuditResponse>;
  const results = Array.isArray(response.results) ? response.results : [];
  const [copied, setCopied] = React.useState(false);

  const handleCopyUrl = async () => {
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error("Failed to copy URL:", err);
    }
  };

  const perfResult = results.find((r) => r.audit_type === "performance") as
    | AuditResult
    | undefined;
  const seoResult = results.find((r) => r.audit_type === "seo") as AuditResult | undefined;
  const accessibilityResult = results.find((r) => r.audit_type === "accessibility") as
    | AuditResult
    | undefined;
  const securityResult = results.find((r) => r.audit_type === "security") as
    | AuditResult
    | undefined;
  const functionalityResult = results.find((r) => r.audit_type === "functionality") as
    | AuditResult
    | undefined;

  const renderedResults = [
    perfResult,
    seoResult,
    accessibilityResult,
    securityResult,
    functionalityResult,
  ].filter(Boolean) as AuditResult[];

  const hasRenderedCards = renderedResults.length > 0;
  const overallScore = response.overall_score ?? 0;

  return (
    <section className="results-section" aria-label="Audit results">
      <header className="results-header">
        <div className="results-header-text">
          <h2 className="results-title">Audit Results</h2>
          <p className="results-subtitle">Report generated for the submitted URL</p>
        </div>
        <div className="results-url-wrapper">
          <code className="results-url" title={url}>
            {url}
          </code>
          <button
            className="btn-copy"
            onClick={handleCopyUrl}
            aria-label="Copy URL"
            title="Copy URL"
          >
            {copied ? "Copied!" : "Copy"}
          </button>
        </div>
      </header>
      {hasRenderedCards && (
        <div style={{ display: "flex", justifyContent: "flex-end", margin: "1rem 0" }}>
          <button
            className="btn-primary"
            onClick={async () => {
              try {
                await downloadPDF(response);
              } catch (err) {
                alert("PDF generation failed. Please try again.");
              }
            }}
          >
            Download PDF Report
          </button>
        </div>
      )}

      {hasRenderedCards && (
        <ResultsSummary overallScore={overallScore} results={renderedResults} />
      )}

      {hasRenderedCards && (
        <div className="audit-results-list">
          {perfResult && <PerformanceCard result={perfResult} />}
          {seoResult && <SEOCard result={seoResult} />}
          {accessibilityResult && <AccessibilityCard result={accessibilityResult} />}
          {securityResult && <SecurityCard result={securityResult} />}
          {functionalityResult && <FunctionalityCard result={functionalityResult} />}
        </div>
      )}
    </section>
  );
};

export default ResultsPanel;
