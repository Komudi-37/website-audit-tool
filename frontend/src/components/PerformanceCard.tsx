import React from "react";
import type { AuditResult } from "../types";

interface Props {
  result: AuditResult;
}

const getScoreColor = (score: number) => {
  if (score >= 90) return "var(--green)";
  if (score >= 50) return "var(--amber)";
  return "var(--red)";
};

const getSeverityClass = (severity: string) => {
  switch (severity) {
    case "critical": return "severity-critical";
    case "warning": return "severity-warning";
    case "info": return "severity-info";
    case "pass": return "severity-pass";
    default: return "";
  }
};

const getSeverityIcon = (severity: string) => {
  switch (severity) {
    case "critical": return "🛑";
    case "warning": return "⚠️";
    case "info": return "ℹ️";
    case "pass": return "✅";
    default: return "•";
  }
};

const PerformanceCard: React.FC<Props> = ({ result }) => {
  const scoreColor = getScoreColor(result.score);
  
  return (
    <div className="performance-card">
      <div className="perf-header">
        <div className="perf-title-group">
          <span className="perf-icon">⚡</span>
          <h3>Performance</h3>
        </div>
        <div className="perf-score-circle" style={{ borderColor: scoreColor, color: scoreColor }}>
          {result.score}
        </div>
      </div>

      <div className="perf-metrics-grid">
        <div className="metric-box">
          <span className="metric-label">First Contentful Paint (FCP)</span>
          <span className="metric-value">{String(result.metrics.fcp || "—")}</span>
        </div>
        <div className="metric-box">
          <span className="metric-label">Largest Contentful Paint (LCP)</span>
          <span className="metric-value">{String(result.metrics.lcp || "—")}</span>
        </div>
        <div className="metric-box">
          <span className="metric-label">Cumulative Layout Shift (CLS)</span>
          <span className="metric-value">{String(result.metrics.cls || "—")}</span>
        </div>
        <div className="metric-box">
          <span className="metric-label">Time to Interactive (TTI)</span>
          <span className="metric-value">{String(result.metrics.tti || "—")}</span>
        </div>
        <div className="metric-box">
          <span className="metric-label">Speed Index</span>
          <span className="metric-value">{String(result.metrics.speed_index || "—")}</span>
        </div>
        <div className="metric-box">
          <span className="metric-label">Total Blocking Time</span>
          <span className="metric-value">{String(result.metrics.total_blocking_time || "—")}</span>
        </div>
      </div>

      {result.findings.length > 0 && (
        <div className="perf-findings">
          <h4>Findings</h4>
          <ul className="finding-list">
            {result.findings.map((f, i) => (
              <li key={i} className={`finding-item ${getSeverityClass(f.severity)}`}>
                <span className="finding-icon">{getSeverityIcon(f.severity)}</span>
                <div>
                  <span className="finding-title">{f.title}</span>
                  <span className="finding-desc">{f.description}</span>
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}

      {result.recommendations.length > 0 && (
        <div className="perf-recommendations">
          <h4>Recommendations</h4>
          <ul className="rec-list">
            {result.recommendations.map((rec, i) => (
              <li key={i}>
                <span className="rec-bullet">💡</span> {rec}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};

export default PerformanceCard;
