import React from "react";
import type { AuditResult } from "../types";
import { AuditCardLayout, MetricCard, MetricsGrid } from "./AuditCardShared";

interface Props {
  result: AuditResult;
}

const PerformanceCard: React.FC<Props> = ({ result }) => {
  const metrics = result.metrics;

  return (
    <AuditCardLayout
      title="Performance"
      categoryTag="PERF"
      score={result.score}
      findings={result.findings}
      recommendations={result.recommendations}
      metrics={
        <MetricsGrid>
          <MetricCard
            label="First Contentful Paint"
            value={String(metrics.fcp || "—")}
          />
          <MetricCard
            label="Largest Contentful Paint"
            value={String(metrics.lcp || "—")}
          />
          <MetricCard
            label="Cumulative Layout Shift"
            value={String(metrics.cls || "—")}
          />
          <MetricCard
            label="Time to Interactive"
            value={String(metrics.tti || "—")}
          />
          <MetricCard
            label="Speed Index"
            value={String(metrics.speed_index || "—")}
          />
          <MetricCard
            label="Total Blocking Time"
            value={String(metrics.total_blocking_time || "—")}
          />
        </MetricsGrid>
      }
    />
  );
};

export default PerformanceCard;
