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

interface FunctionalityMetrics {
  homepage_url?: string;
  homepage_http_status?: number | string | null;
  homepage_body_length_chars?: number;
  navigation_links_found?: number;
  navigation_links?: Array<{ text: string; href: string }>;
  contact_form_on_page?: boolean;
  contact_page_link?: string | null;
  internal_links_total_found?: number;
  internal_links_checked?: number;
  broken_links_count?: number;
}

function homepageStatusBadge(status: number | string | null | undefined): React.ReactNode {
  if (status == null) {
    return <StatusBadge variant="neutral">—</StatusBadge>;
  }
  if (typeof status === "number") {
    if (status >= 400) {
      return <StatusBadge variant="fail">HTTP {status}</StatusBadge>;
    }
    return <StatusBadge variant="pass">HTTP {status}</StatusBadge>;
  }
  return <StatusBadge variant="neutral">{String(status)}</StatusBadge>;
}

function contactDetectionBadge(metrics: FunctionalityMetrics): React.ReactNode {
  if (metrics.contact_form_on_page) {
    return <StatusBadge variant="pass">Form on Page</StatusBadge>;
  }
  if (metrics.contact_page_link) {
    return <StatusBadge variant="pass">Link Found</StatusBadge>;
  }
  return <StatusBadge variant="warn">Not Found</StatusBadge>;
}

const FunctionalityCard: React.FC<Props> = ({ result }) => {
  const metrics = result.metrics as unknown as FunctionalityMetrics;
  const brokenLinks = metrics.broken_links_count ?? 0;
  const linksChecked = metrics.internal_links_checked ?? 0;
  const linksTotal = metrics.internal_links_total_found ?? 0;
  const navLinksFound = metrics.navigation_links_found ?? 0;

  return (
    <>
    <AuditCardLayout
      title="Functionality"
      categoryTag="FUNC"
      score={result.score}
      findings={result.findings}
      recommendations={result.recommendations}
      preserveFindingWhitespace
      metrics={
        <MetricsGrid>
          {/* all your existing MetricCard lines stay exactly as they are */}
          <MetricCard
            label="Homepage Status"
            value={homepageStatusBadge(metrics.homepage_http_status)}
          />
          <MetricCard
            label="Navigation Links Found"
            value={
              <span className={navLinksFound > 0 ? "metric-card-value--pass" : "metric-card-value--warn"}>
                {navLinksFound}
              </span>
            }
          />
          <MetricCard
            label="Contact Form"
            value={contactDetectionBadge(metrics)}
            title={metrics.contact_page_link || undefined}
          />
          <MetricCard
            label="Internal Links Checked"
            value={`${linksChecked} / ${linksTotal}`}
          />
          <MetricCard
            label="Broken Links"
            value={
              <span className={brokenLinks > 0 ? "metric-card-value--fail" : "metric-card-value--pass"}>
                {brokenLinks}
              </span>
            }
          />
          {metrics.contact_page_link && !metrics.contact_form_on_page && (
            <MetricCard
              label="Contact Page"
              value={truncate(metrics.contact_page_link, 28)}
              title={metrics.contact_page_link}
            />
          )}
        </MetricsGrid>
      }
    />
    {(result.metrics as Record<string,unknown>).screenshot_path &&(
      <div className="screenshot-section">
      <p className="screenshot-label">Website Preview</p>
      <img
      src={`/screenshots/${String((result.metrics as Record<string, unknown>).screenshot_path).split(/[\\/]/).pop()}`}
      alt="Website screenshot"
      className="screenshot-image"
      />
      </div>
    )}
  </>
  );
};

export default FunctionalityCard;
