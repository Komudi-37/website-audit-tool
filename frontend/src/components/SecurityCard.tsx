import React from "react";
import type { AuditResult } from "../types";
import {
  AuditCardLayout,
  MetricCard,
  MetricsGrid,
  StatusBadge,
  truncate,
} from "./AuditCardShared";

interface Props {
  result: AuditResult;
}

interface SecurityMetrics {
  is_https?: boolean;
  http_redirects_to_https?: boolean | null;
  ssl_valid?: boolean;
  ssl_issuer?: string | null;
  ssl_days_remaining?: number | null;
  hsts_present?: boolean;
  hsts_max_age?: number | null;
  csp_present?: boolean;
  x_frame_options_present?: boolean;
  x_frame_options_value?: string | null;
  x_content_type_options_present?: boolean;
  referrer_policy_present?: boolean;
  referrer_policy_value?: string | null;
  permissions_policy_present?: boolean;
  total_headers_present?: number;
  total_headers_expected?: number;
}

function boolBadge(
  value: boolean | null | undefined,
  passLabel: string,
  failLabel: string
): React.ReactNode {
  if (value === true) return <StatusBadge variant="pass">{passLabel}</StatusBadge>;
  if (value === false) return <StatusBadge variant="fail">{failLabel}</StatusBadge>;
  return <StatusBadge variant="neutral">—</StatusBadge>;
}

const SecurityCard: React.FC<Props> = ({ result }) => {
  const metrics = result.metrics as unknown as SecurityMetrics;
  const headersPresent = metrics.total_headers_present ?? 0;
  const headersExpected = metrics.total_headers_expected ?? 6;
  const headersClass =
    headersPresent === headersExpected
      ? "metric-card-value--pass"
      : headersPresent >= 4
        ? "metric-card-value--warn"
        : "metric-card-value--fail";

  return (
    <AuditCardLayout
      title="Security"
      categoryTag="SEC"
      score={result.score}
      findings={result.findings}
      recommendations={result.recommendations}
      metrics={
        <MetricsGrid>
          <MetricCard
            label="HTTPS"
            value={boolBadge(metrics.is_https, "Enabled", "Not Enabled")}
          />
          <MetricCard
            label="HTTP → HTTPS Redirect"
            value={boolBadge(metrics.http_redirects_to_https, "Active", "Missing")}
          />
          <MetricCard
            label="SSL/TLS Certificate"
            value={
              metrics.ssl_valid ? (
                <StatusBadge variant="pass">
                  Valid ({metrics.ssl_days_remaining ?? "?"}d)
                </StatusBadge>
              ) : metrics.ssl_valid === false ? (
                <StatusBadge variant="fail">Invalid</StatusBadge>
              ) : (
                <StatusBadge variant="neutral">—</StatusBadge>
              )
            }
          />
          <MetricCard
            label="SSL Issuer"
            value={
              metrics.ssl_issuer ? truncate(metrics.ssl_issuer, 28) : "—"
            }
            title={metrics.ssl_issuer || undefined}
          />
          <MetricCard
            label="HSTS"
            value={
              metrics.hsts_present ? (
                <StatusBadge variant="pass">
                  Active
                  {metrics.hsts_max_age != null
                    ? ` (${Math.floor(metrics.hsts_max_age / 86400)}d)`
                    : ""}
                </StatusBadge>
              ) : (
                <StatusBadge variant="fail">Missing</StatusBadge>
              )
            }
          />
          <MetricCard
            label="Content-Security-Policy"
            value={boolBadge(metrics.csp_present, "Present", "Missing")}
          />
          <MetricCard
            label="X-Frame-Options"
            value={
              metrics.x_frame_options_present ? (
                <StatusBadge variant="pass">
                  {metrics.x_frame_options_value ?? "Set"}
                </StatusBadge>
              ) : (
                <StatusBadge variant="fail">Missing</StatusBadge>
              )
            }
          />
          <MetricCard
            label="X-Content-Type-Options"
            value={
              metrics.x_content_type_options_present ? (
                <StatusBadge variant="pass">nosniff</StatusBadge>
              ) : (
                <StatusBadge variant="fail">Missing</StatusBadge>
              )
            }
          />
          <MetricCard
            label="Referrer-Policy"
            value={
              metrics.referrer_policy_present ? (
                <StatusBadge variant="pass">
                  {metrics.referrer_policy_value ?? "Set"}
                </StatusBadge>
              ) : (
                <StatusBadge variant="warn">Missing</StatusBadge>
              )
            }
            title={metrics.referrer_policy_value || undefined}
          />
          <MetricCard
            label="Permissions-Policy"
            value={
              metrics.permissions_policy_present ? (
                <StatusBadge variant="pass">Set</StatusBadge>
              ) : (
                <StatusBadge variant="warn">Missing</StatusBadge>
              )
            }
          />
          <MetricCard
            label="Headers Present"
            value={
              <span className={headersClass}>
                {headersPresent} / {headersExpected}
              </span>
            }
          />
        </MetricsGrid>
      }
    />
  );
};

export default SecurityCard;
