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
  canonical_url?: string | null;
  robots_txt_exists?: boolean;
  robots_txt_url?: string;
  sitemap_exists?: boolean;
  sitemap_url?: string;
  indexable?: boolean;
  noindex_reasons?: string[];
  total_internal_links_found?: number;
  links_checked?: number;
  broken_links_count?: number;
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
            {metrics.title ? (metrics.title.length > 20 ? metrics.title.substring(0, 20) + "..." : metrics.title) : "—"}
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
        <div className="metric-box">
          <span className="metric-label">Indexable</span>
          <span className="metric-value" style={{ color: metrics.indexable === false ? "var(--red)" : "var(--green)" }}>
            {metrics.indexable === false ? "No 🛑" : "Yes ✅"}
          </span>
        </div>
        <div className="metric-box">
          <span className="metric-label">Canonical URL</span>
          <span className="metric-value" title={metrics.canonical_url || "Missing"}>
            {metrics.canonical_url ? (metrics.canonical_url.length > 20 ? metrics.canonical_url.substring(0, 20) + "..." : metrics.canonical_url) : "Missing"}
          </span>
        </div>
        <div className="metric-box">
          <span className="metric-label">robots.txt</span>
          <span className="metric-value" style={{ color: metrics.robots_txt_exists ? "var(--green)" : "var(--amber)" }}>
            {metrics.robots_txt_exists ? "Found ✅" : "Missing ⚠️"}
          </span>
        </div>
        <div className="metric-box">
          <span className="metric-label">sitemap.xml</span>
          <span className="metric-value" style={{ color: metrics.sitemap_exists ? "var(--green)" : "var(--amber)" }}>
            {metrics.sitemap_exists ? "Found ✅" : "Missing ⚠️"}
          </span>
        </div>
        <div className="metric-box">
          <span className="metric-label">Broken Links</span>
          <span className="metric-value" style={{ color: (metrics.broken_links_count ?? 0) > 0 ? "var(--red)" : "var(--green)" }}>
            {metrics.broken_links_count ?? 0} / {metrics.links_checked ?? 0}
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
