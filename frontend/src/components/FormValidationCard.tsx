import React from "react";
import type { AuditResult } from "../types";
import {
  AuditCardLayout,
  MetricCard,
  MetricsGrid,
  StatusBadge,
} from "./AuditCardShared";

interface Props {
  result: AuditResult;
}

interface FormValidationMetrics {
  total_forms_found?: number;
  total_fields_found?: number;
  password_fields_using_text_type?: number;
  missing_labels_count?: number;
  required_fields_count?: number;
  disabled_fields_count?: number;
  readonly_fields_count?: number;
  file_upload_fields_count?: number;
}

const FormValidationCard: React.FC<Props> = ({ result }) => {
  const metrics = result.metrics as unknown as FormValidationMetrics;
  const score = result.score;

  // Handle null score case (no forms found)
  if (score === null) {
    return (
      <AuditCardLayout
        title="Form Validation"
        categoryTag="FORM"
        score={null}
        findings={result.findings}
        recommendations={result.recommendations}
        metrics={null}
      />
    );
  }

  const passwordTextTypeCount = metrics.password_fields_using_text_type ?? 0;
  const missingLabelsCount = metrics.missing_labels_count ?? 0;
  const requiredFieldsCount = metrics.required_fields_count ?? 0;
  const fileUploadCount = metrics.file_upload_fields_count ?? 0;
  const disabledCount = metrics.disabled_fields_count ?? 0;
  const readonlyCount = metrics.readonly_fields_count ?? 0;

  return (
    <AuditCardLayout
      title="Form Validation"
      categoryTag="FORM"
      score={score}
      findings={result.findings}
      recommendations={result.recommendations}
      metrics={
        <MetricsGrid>
          <MetricCard
            label="Total Forms"
            value={metrics.total_forms_found ?? 0}
          />
          <MetricCard
            label="Total Fields"
            value={metrics.total_fields_found ?? 0}
          />
          <MetricCard
            label="Password Fields Using Text Type"
            value={
              passwordTextTypeCount > 0 ? (
                <StatusBadge variant="fail">{passwordTextTypeCount}</StatusBadge>
              ) : (
                <StatusBadge variant="pass">0</StatusBadge>
              )
            }
          />
          <MetricCard
            label="Missing Labels"
            value={
              missingLabelsCount > 0 ? (
                <StatusBadge variant="warn">{missingLabelsCount}</StatusBadge>
              ) : (
                <StatusBadge variant="pass">0</StatusBadge>
              )
            }
          />
          <MetricCard
            label="Required Fields"
            value={requiredFieldsCount}
          />
          <MetricCard
            label="File Upload Fields"
            value={fileUploadCount}
          />
          <MetricCard
            label="Disabled Fields"
            value={disabledCount}
          />
          <MetricCard
            label="Readonly Fields"
            value={readonlyCount}
          />
        </MetricsGrid>
      }
    />
  );
};

export default FormValidationCard;
