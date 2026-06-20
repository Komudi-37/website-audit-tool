import React from "react";
import type { AuditResult } from "../types";

interface Props {
  result: AuditResult;
}

interface AccessibilityMetrics {
  missing_alt_text_count?: number;
  missing_form_labels_count?: number;
  missing_aria_attributes_count?: number;
  color_contrast_issues_count?: number;
  heading_hierarchy_issues_count?: number;
  keyboard_accessibility_issues_count?: number;
  total_violations?: number;
  rules_passed?: number;
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

const AccessibilityCard: React.FC<Props> = ({ result }) => {
  const scoreColor = getScoreColor(result.score);
  const metrics = result.metrics as unknown as AccessibilityMetrics;

  return (
    <div className="performance-card accessibility-card" style={{ marginTop: 24 }}>
      <div className="perf-header">
        <div className="perf-title-group">
          <span className="perf-icon">♿</span>
          <h3>Accessibility</h3>
        </div>
        <div className="perf-score-circle" style={{ borderColor: scoreColor, color: scoreColor }}>
          {result.score}
        </div>
      </div>

      <div className="perf-metrics-grid">
        <div className="metric-box">
          <span className="metric-label">Missing Alt Text</span>
          <span className="metric-value" style={{ color: (metrics.missing_alt_text_count ?? 0) > 0 ? "var(--red)" : "var(--green)" }}>
            {metrics.missing_alt_text_count ?? 0}
          </span>
        </div>
        <div className="metric-box">
          <span className="metric-label">Missing Form Labels</span>
          <span className="metric-value" style={{ color: (metrics.missing_form_labels_count ?? 0) > 0 ? "var(--red)" : "var(--green)" }}>
            {metrics.missing_form_labels_count ?? 0}
          </span>
        </div>
        <div className="metric-box">
          <span className="metric-label">Missing ARIA Attributes</span>
          <span className="metric-value" style={{ color: (metrics.missing_aria_attributes_count ?? 0) > 0 ? "var(--red)" : "var(--green)" }}>
            {metrics.missing_aria_attributes_count ?? 0}
          </span>
        </div>
        <div className="metric-box">
          <span className="metric-label">Color Contrast Issues</span>
          <span className="metric-value" style={{ color: (metrics.color_contrast_issues_count ?? 0) > 0 ? "var(--red)" : "var(--green)" }}>
            {metrics.color_contrast_issues_count ?? 0}
          </span>
        </div>
        <div className="metric-box">
          <span className="metric-label">Heading Hierarchy Issues</span>
          <span className="metric-value" style={{ color: (metrics.heading_hierarchy_issues_count ?? 0) > 0 ? "var(--red)" : "var(--green)" }}>
            {metrics.heading_hierarchy_issues_count ?? 0}
          </span>
        </div>
        <div className="metric-box">
          <span className="metric-label">Keyboard Access Issues</span>
          <span className="metric-value" style={{ color: (metrics.keyboard_accessibility_issues_count ?? 0) > 0 ? "var(--red)" : "var(--green)" }}>
            {metrics.keyboard_accessibility_issues_count ?? 0}
          </span>
        </div>
        <div className="metric-box">
          <span className="metric-label">Total Violations</span>
          <span className="metric-value" style={{ color: (metrics.total_violations ?? 0) > 0 ? "var(--red)" : "var(--green)" }}>
            {metrics.total_violations ?? 0}
          </span>
        </div>
        <div className="metric-box">
          <span className="metric-label">Axe Rules Passed</span>
          <span className="metric-value" style={{ color: "var(--green)" }}>
            {metrics.rules_passed ?? 0}
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
                  <pre className="finding-desc" style={{ whiteSpace: "pre-wrap", fontFamily: "inherit", margin: "4px 0 0 0" }}>
                    {f.description}
                  </pre>
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

export default AccessibilityCard;
