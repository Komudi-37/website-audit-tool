import React from "react";
import type { AuditResult } from "../types";
import {
  AuditCardLayout,
  MetricCard,
  MetricsGrid,
  metricValueClass,
} from "./AuditCardShared";

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

const AccessibilityCard: React.FC<Props> = ({ result }) => {
  const metrics = result.metrics as unknown as AccessibilityMetrics;

  const countMetric = (label: string, count: number | undefined) => (
    <MetricCard
      label={label}
      value={
        <span className={metricValueClass(count ?? 0)}>
          {count ?? 0}
        </span>
      }
    />
  );

  return (
    <AuditCardLayout
      title="Accessibility"
      categoryTag="A11Y"
      score={result.score}
      findings={result.findings}
      recommendations={result.recommendations}
      preserveFindingWhitespace
      metrics={
        <MetricsGrid>
          {countMetric("Missing Alt Text", metrics.missing_alt_text_count)}
          {countMetric("Missing Form Labels", metrics.missing_form_labels_count)}
          {countMetric("Missing ARIA Attributes", metrics.missing_aria_attributes_count)}
          {countMetric("Color Contrast Issues", metrics.color_contrast_issues_count)}
          {countMetric("Heading Hierarchy Issues", metrics.heading_hierarchy_issues_count)}
          {countMetric("Keyboard Access Issues", metrics.keyboard_accessibility_issues_count)}
          {countMetric("Total Violations", metrics.total_violations)}
          <MetricCard
            label="Axe Rules Passed"
            value={
              <span className="metric-card-value--pass">
                {metrics.rules_passed ?? 0}
              </span>
            }
          />
        </MetricsGrid>
      }
    />
  );
};

export default AccessibilityCard;
