import React from "react";
import type { AuditResponse, AuditResult } from "../types";
import PerformanceCard from "./PerformanceCard";
import SEOCard from "./SEOCard";
import AccessibilityCard from "./AccessibilityCard";
import SecurityCard from "./SecurityCard";
import ResultsSummary from "./ResultsSummary";

interface Props {
  data: unknown;
  url: string;
}

const RENDERED_TYPES = new Set(["performance", "seo", "accessibility", "security"]);

const ResultsPanel: React.FC<Props> = ({ data, url }) => {
  const response = data as Partial<AuditResponse>;
  const results = Array.isArray(response.results) ? response.results : [];

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

  const renderedResults = [perfResult, seoResult, accessibilityResult, securityResult].filter(
    Boolean
  ) as AuditResult[];

  const rawData = { ...response };
  if (Array.isArray(rawData.results)) {
    rawData.results = rawData.results.filter((r) => !RENDERED_TYPES.has(r.audit_type));
  }

  const formatted = JSON.stringify(rawData, null, 2);
  const hasRenderedCards = renderedResults.length > 0;
  const overallScore = response.overall_score ?? 0;

  return (
    <section className="results-section" aria-label="Audit results">
      <header className="results-header">
        <div className="results-header-text">
          <h2 className="results-title">Audit Results</h2>
          <p className="results-subtitle">Report generated for the submitted URL</p>
        </div>
        <code className="results-url" title={url}>
          {url}
        </code>
      </header>

      {hasRenderedCards && (
        <ResultsSummary overallScore={overallScore} results={renderedResults} />
      )}

      {hasRenderedCards && (
        <div className="audit-results-list">
          {perfResult && <PerformanceCard result={perfResult} />}
          {seoResult && <SEOCard result={seoResult} />}
          {accessibilityResult && <AccessibilityCard result={accessibilityResult} />}
          {securityResult && <SecurityCard result={securityResult} />}
        </div>
      )}

      {rawData.results && rawData.results.length > 0 && (
        <div className={`raw-response-card${hasRenderedCards ? " raw-response-card--spaced" : ""}`}>
          <div className="raw-response-header">
            <span>API Response (Unimplemented Audits)</span>
            <span className="raw-response-format">JSON</span>
          </div>
          <pre className="raw-response-body">{formatted}</pre>
        </div>
      )}
    </section>
  );
};

export default ResultsPanel;
