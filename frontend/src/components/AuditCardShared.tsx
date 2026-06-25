import React from "react";
import type { Finding } from "../types";

export type ScoreTier = "good" | "warning" | "poor";
export type StatusVariant = "pass" | "fail" | "warn" | "neutral";

export function getScoreTier(score: number): ScoreTier {
  if (score >= 90) return "good";
  if (score >= 70) return "warning";
  return "poor";
}

function getSeverityLabel(severity: Finding["severity"] | string): string {
  switch (severity) {
    case "critical":
      return "Critical";
    case "warning":
      return "Warning";
    case "info":
      return "Info";
    case "pass":
      return "Pass";
    default:
      return severity;
  }
}

export function SeverityBadge({ severity }: { severity: Finding["severity"] | string }) {
  return (
    <span className={`severity-badge severity-badge--${severity}`}>
      {getSeverityLabel(severity)}
    </span>
  );
}

export function StatusBadge({
  variant,
  children,
}: {
  variant: StatusVariant;
  children: React.ReactNode;
}) {
  return <span className={`status-badge status-badge--${variant}`}>{children}</span>;
}

export function MetricCard({
  label,
  value,
  title,
}: {
  label: string;
  value: React.ReactNode;
  title?: string;
}) {
  return (
    <div className="metric-card">
      <span className="metric-card-label">{label}</span>
      <span className="metric-card-value" title={title}>
        {value}
      </span>
    </div>
  );
}

export const AUDIT_ERROR_FINDING_IDS = new Set([
  "perf-error",
  "a11y-audit-failed",
  "func-audit-failed",
]);

export function AuditErrorBanner({ finding }: { finding: Finding }) {
  return (
    <div className="audit-error-banner" role="alert">
      <p className="audit-error-banner-title">{finding.title}</p>
      <pre className="audit-error-banner-message">{finding.description}</pre>
    </div>
  );
}

export function MetricsGrid({ children }: { children: React.ReactNode }) {
  return <div className="audit-metrics-grid">{children}</div>;
}

interface AuditCardLayoutProps {
  title: string;
  categoryTag: string;
  score: number;
  metrics: React.ReactNode;
  findings: Finding[];
  recommendations: string[];
  className?: string;
  preserveFindingWhitespace?: boolean;
}

export function AuditCardLayout({
  title,
  categoryTag,
  score,
  metrics,
  findings,
  recommendations,
  className = "",
  preserveFindingWhitespace = false,
}: AuditCardLayoutProps) {
  const tier = getScoreTier(score);
  const displayScore = Number.isInteger(score) ? score : Math.round(score * 10) / 10;
  const errorFinding = findings.find((f) => AUDIT_ERROR_FINDING_IDS.has(f.id));
  const operationalFindings = errorFinding
    ? findings.filter((f) => !AUDIT_ERROR_FINDING_IDS.has(f.id))
    : findings;

  return (
    <article className={`audit-card ${className}`.trim()}>
      <header className="audit-card-header">
        <div className="audit-card-title-group">
          <span className="audit-category-tag">{categoryTag}</span>
          <h3 className="audit-card-title">{title}</h3>
        </div>
        <div className="audit-score-display">
          <span className={`audit-score-value audit-score-value--${tier}`}>
            {displayScore}
          </span>
          <span className="audit-score-label">Score</span>
        </div>
      </header>

      {errorFinding && <AuditErrorBanner finding={errorFinding} />}

      <section className="audit-section" aria-labelledby={`${categoryTag}-metrics`}>
        <h4 className="audit-section-title" id={`${categoryTag}-metrics`}>
          Metrics
        </h4>
        {metrics}
      </section>

      {operationalFindings.length > 0 && (
        <section className="audit-section" aria-labelledby={`${categoryTag}-findings`}>
          <h4 className="audit-section-title" id={`${categoryTag}-findings`}>
            Findings
            <span className="audit-section-count">{operationalFindings.length}</span>
          </h4>
          <ul className="audit-findings-list">
            {operationalFindings.map((f, i) => (
              <li key={f.id || i} className="audit-finding-item">
                <div className="audit-finding-header">
                  <SeverityBadge severity={f.severity} />
                  <span className="audit-finding-title">{f.title}</span>
                </div>
                {preserveFindingWhitespace ? (
                  <pre className="audit-finding-desc audit-finding-desc--pre">{f.description}</pre>
                ) : (
                  <p className="audit-finding-desc">{f.description}</p>
                )}
              </li>
            ))}
          </ul>
        </section>
      )}

      {recommendations.length > 0 && (
        <section className="audit-section" aria-labelledby={`${categoryTag}-recs`}>
          <h4 className="audit-section-title" id={`${categoryTag}-recs`}>
            Recommendations
            <span className="audit-section-count">{recommendations.length}</span>
          </h4>
          <ol className="audit-recommendations-list">
            {recommendations.map((rec, i) => (
              <li key={i} className="audit-recommendation-item">
                {rec}
              </li>
            ))}
          </ol>
        </section>
      )}
    </article>
  );
}

export function metricValueClass(count: number, warnThreshold = 0): string {
  if (count > warnThreshold) return "metric-card-value--fail";
  return "metric-card-value--pass";
}

export function truncate(value: string, max: number): string {
  return value.length > max ? `${value.substring(0, max)}…` : value;
}
