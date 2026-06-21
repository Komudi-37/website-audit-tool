import React from "react";
import type { AuditResult } from "../types";

interface Props {
  result: AuditResult;
}

interface SecurityMetrics {
  is_https?: boolean;
  http_redirects_to_https?: boolean | null;
  ssl_valid?: boolean;
  ssl_issuer?: string | null;
  ssl_expiry?: string | null;
  ssl_days_remaining?: number | null;
  ssl_protocol?: string | null;
  hsts_present?: boolean;
  hsts_max_age?: number | null;
  hsts_include_subdomains?: boolean;
  csp_present?: boolean;
  csp_value?: string | null;
  x_frame_options_present?: boolean;
  x_frame_options_value?: string | null;
  x_content_type_options_present?: boolean;
  referrer_policy_present?: boolean;
  referrer_policy_value?: string | null;
  permissions_policy_present?: boolean;
  permissions_policy_value?: string | null;
  total_headers_present?: number;
  total_headers_expected?: number;
  missing_headers?: string[];
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

const boolIcon = (val: boolean | null | undefined) => {
  if (val === true) return "✅";
  if (val === false) return "🛑";
  return "—";
};

const boolColor = (val: boolean | null | undefined) => {
  if (val === true) return "var(--green)";
  if (val === false) return "var(--red)";
  return "var(--text-muted)";
};

const SecurityCard: React.FC<Props> = ({ result }) => {
  const scoreColor = getScoreColor(result.score);
  const metrics = result.metrics as unknown as SecurityMetrics;

  return (
    <div className="performance-card security-card" style={{ marginTop: 24 }}>
      <div className="perf-header">
        <div className="perf-title-group">
          <span className="perf-icon">🔒</span>
          <h3>Security</h3>
        </div>
        <div className="perf-score-circle" style={{ borderColor: scoreColor, color: scoreColor }}>
          {result.score}
        </div>
      </div>

      <div className="perf-metrics-grid">
        <div className="metric-box">
          <span className="metric-label">HTTPS</span>
          <span className="metric-value" style={{ color: boolColor(metrics.is_https) }}>
            {metrics.is_https ? "Enabled ✅" : "Not Enabled 🛑"}
          </span>
        </div>
        <div className="metric-box">
          <span className="metric-label">HTTP → HTTPS Redirect</span>
          <span className="metric-value" style={{ color: boolColor(metrics.http_redirects_to_https) }}>
            {metrics.http_redirects_to_https === true ? "Active ✅" :
             metrics.http_redirects_to_https === false ? "Missing 🛑" : "—"}
          </span>
        </div>
        <div className="metric-box">
          <span className="metric-label">SSL/TLS Certificate</span>
          <span className="metric-value" style={{ color: boolColor(metrics.ssl_valid) }}>
            {metrics.ssl_valid ? `Valid ✅ (${metrics.ssl_days_remaining ?? "?"}d)` : `Invalid ${boolIcon(metrics.ssl_valid)}`}
          </span>
        </div>
        <div className="metric-box">
          <span className="metric-label">SSL Issuer</span>
          <span
            className="metric-value"
            title={metrics.ssl_issuer || "Unknown"}
          >
            {metrics.ssl_issuer
              ? metrics.ssl_issuer.length > 25
                ? metrics.ssl_issuer.substring(0, 25) + "..."
                : metrics.ssl_issuer
              : "—"}
          </span>
        </div>
        <div className="metric-box">
          <span className="metric-label">HSTS</span>
          <span className="metric-value" style={{ color: boolColor(metrics.hsts_present) }}>
            {metrics.hsts_present
              ? `Active ✅${metrics.hsts_max_age != null ? ` (${Math.floor(metrics.hsts_max_age / 86400)}d)` : ""}`
              : "Missing 🛑"}
          </span>
        </div>
        <div className="metric-box">
          <span className="metric-label">Content-Security-Policy</span>
          <span className="metric-value" style={{ color: boolColor(metrics.csp_present) }}>
            {metrics.csp_present ? "Present ✅" : "Missing 🛑"}
          </span>
        </div>
        <div className="metric-box">
          <span className="metric-label">X-Frame-Options</span>
          <span className="metric-value" style={{ color: boolColor(metrics.x_frame_options_present) }}>
            {metrics.x_frame_options_present
              ? `${metrics.x_frame_options_value ?? "Set"} ✅`
              : "Missing 🛑"}
          </span>
        </div>
        <div className="metric-box">
          <span className="metric-label">X-Content-Type-Options</span>
          <span className="metric-value" style={{ color: boolColor(metrics.x_content_type_options_present) }}>
            {metrics.x_content_type_options_present ? "nosniff ✅" : "Missing 🛑"}
          </span>
        </div>
        <div className="metric-box">
          <span className="metric-label">Referrer-Policy</span>
          <span
            className="metric-value"
            style={{ color: boolColor(metrics.referrer_policy_present) }}
            title={metrics.referrer_policy_value || ""}
          >
            {metrics.referrer_policy_present
              ? `${metrics.referrer_policy_value ?? "Set"} ✅`
              : "Missing ⚠️"}
          </span>
        </div>
        <div className="metric-box">
          <span className="metric-label">Permissions-Policy</span>
          <span className="metric-value" style={{ color: boolColor(metrics.permissions_policy_present) }}>
            {metrics.permissions_policy_present ? "Set ✅" : "Missing ⚠️"}
          </span>
        </div>
        <div className="metric-box">
          <span className="metric-label">Headers Present</span>
          <span
            className="metric-value"
            style={{
              color:
                (metrics.total_headers_present ?? 0) === (metrics.total_headers_expected ?? 6)
                  ? "var(--green)"
                  : (metrics.total_headers_present ?? 0) >= 4
                  ? "var(--amber)"
                  : "var(--red)",
            }}
          >
            {metrics.total_headers_present ?? 0} / {metrics.total_headers_expected ?? 6}
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

export default SecurityCard;
