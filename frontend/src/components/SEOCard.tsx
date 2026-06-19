import React from "react";
import type { AuditResult } from "../types";

interface Props {
  result: AuditResult;
}

interface SEOMetrics {
  title?: string;
  title_length?: number;
  h1_count?: number;
  total_images?: number;
  images_without_alt?: number;
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

const SEOCard: React.FC<Props> = ({ result }) => {
  const scoreColor = getScoreColor(result.score);
  const metrics = result.metrics as unknown as SEOMetrics;
  
  return (
    <div className="performance-card seo-card" style={{ marginTop: 24 }}>
      <div className="perf-header">
        <div className="perf-title-group">
          <span className="perf-icon">🔍</span>
          <h3>SEO</h3>
        </div>
        <div className="perf-score-circle" style={{ borderColor: scoreColor, color: scoreColor }}>
          {result.score}
        </div>
      </div>

      <div className="perf-metrics-grid">
        <div className="metric-box">
          <span className="metric-label">Title Tag</span>
          <span className="metric-value" title={metrics.title}>
            {metrics.title ? (metrics.title.length > 30 ? metrics.title.substring(0, 30) + "..." : metrics.title) : "—"}
          </span>
        </div>
        <div className="metric-box">
          <span className="metric-label">Title Length</span>
          <span className="metric-value">{metrics.title_length ?? "—"} chars</span>
        </div>
        <div className="metric-box">
          <span className="metric-label">H1 Tags</span>
          <span className="metric-value">{metrics.h1_count ?? "—"}</span>
        </div>
        <div className="metric-box">
          <span className="metric-label">Images without Alt</span>
          <span className="metric-value">
            {metrics.images_without_alt ?? 0} / {metrics.total_images ?? 0}
          </span>
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

export default SEOCard;
