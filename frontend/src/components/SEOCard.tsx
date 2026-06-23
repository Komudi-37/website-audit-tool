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

interface SEOMetrics {
  title?: string;
  title_length?: number;
  h1_count?: number;
  total_images?: number;
  images_without_alt?: number;
  canonical_url?: string | null;
  robots_txt_exists?: boolean;
  sitemap_exists?: boolean;
  indexable?: boolean;
  links_checked?: number;
  broken_links_count?: number;
}

const SEOCard: React.FC<Props> = ({ result }) => {
  const metrics = result.metrics as unknown as SEOMetrics;
  const brokenLinks = metrics.broken_links_count ?? 0;

  return (
    <AuditCardLayout
      title="SEO"
      categoryTag="SEO"
      score={result.score}
      findings={result.findings}
      recommendations={result.recommendations}
      metrics={
        <MetricsGrid>
          <MetricCard
            label="Title Tag"
            value={metrics.title ? truncate(metrics.title, 28) : "—"}
            title={metrics.title}
          />
          <MetricCard
            label="Title Length"
            value={metrics.title_length != null ? `${metrics.title_length} chars` : "—"}
          />
          <MetricCard
            label="H1 Tags"
            value={metrics.h1_count ?? "—"}
          />
          <MetricCard
            label="Images without Alt"
            value={`${metrics.images_without_alt ?? 0} / ${metrics.total_images ?? 0}`}
          />
          <MetricCard
            label="Indexable"
            value={
              metrics.indexable === false ? (
                <StatusBadge variant="fail">No</StatusBadge>
              ) : (
                <StatusBadge variant="pass">Yes</StatusBadge>
              )
            }
          />
          <MetricCard
            label="Canonical URL"
            value={
              metrics.canonical_url ? (
                truncate(metrics.canonical_url, 28)
              ) : (
                <StatusBadge variant="warn">Missing</StatusBadge>
              )
            }
            title={metrics.canonical_url || undefined}
          />
          <MetricCard
            label="robots.txt"
            value={
              metrics.robots_txt_exists ? (
                <StatusBadge variant="pass">Found</StatusBadge>
              ) : (
                <StatusBadge variant="warn">Missing</StatusBadge>
              )
            }
          />
          <MetricCard
            label="sitemap.xml"
            value={
              metrics.sitemap_exists ? (
                <StatusBadge variant="pass">Found</StatusBadge>
              ) : (
                <StatusBadge variant="warn">Missing</StatusBadge>
              )
            }
          />
          <MetricCard
            label="Broken Links"
            value={
              <span className={brokenLinks > 0 ? "metric-card-value--fail" : "metric-card-value--pass"}>
                {brokenLinks} / {metrics.links_checked ?? 0}
              </span>
            }
          />
        </MetricsGrid>
      }
    />
  );
};

export default SEOCard;
