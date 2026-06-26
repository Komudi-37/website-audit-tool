import React, { useState } from "react";
import type { AuditResult } from "../types";
import { AuditCardLayout, MetricCard, MetricsGrid } from "./AuditCardShared";

interface Props {
  result: AuditResult;
}

type DeviceTab = "mobile" | "desktop";

const PerformanceCard: React.FC<Props> = ({ result }) => {
  const metrics = result.metrics as Record<string, string | number | null>;
  const [tab, setTab] = useState<DeviceTab>("mobile");

  const hasMobile  = metrics.mobile_score  !== undefined;
  const hasDesktop = metrics.desktop_score !== undefined;
  const hasBoth    = hasMobile && hasDesktop;

  const p = hasBoth ? `${tab}_` : "";

  const get = (key: string): string => {
    const val = metrics[`${p}${key}`] ?? metrics[key] ?? "—";
    return String(val || "—");
  };

  const mobileScore  = typeof metrics.mobile_score  === "number" ? metrics.mobile_score  : null;
  const desktopScore = typeof metrics.desktop_score === "number" ? metrics.desktop_score : null;

  const scoreLabel = hasBoth
   ? `Mobile: ${mobileScore ?? "N/A"} · Desktop: ${desktopScore ?? "N/A"}`
    : undefined;

  return (
    <AuditCardLayout
      title="Performance"
      categoryTag="PERF"
      score={result.score}
      findings={result.findings}
      recommendations={result.recommendations}
      preserveFindingWhitespace
      scoreLabel={scoreLabel}
      metrics={
        <>
          {hasBoth && (
            <div className="perf-tabs" role="tablist" aria-label="Device preset">
              {(["mobile", "desktop"] as DeviceTab[]).map((t) => (
                <button
                  key={t}
                  role="tab"
                  aria-selected={tab === t}
                  className={`perf-tab${tab === t ? " perf-tab--active" : ""}`}
                  onClick={() => setTab(t)}
                >
                  {t === "mobile" ? "📱 Mobile" : "🖥 Desktop"}
                  {t === "mobile"  && mobileScore  !== null && (
                    <span className="perf-tab-score">{mobileScore}</span>
                  )}
                  {t === "desktop" && desktopScore !== null && (
                    <span className="perf-tab-score">{desktopScore}</span>
                  )}
                </button>
              ))}
            </div>
          )}
          <MetricsGrid>
            <MetricCard label="First Contentful Paint" value={get("fcp")} />
            <MetricCard label="Largest Contentful Paint" value={get("lcp")} />
            <MetricCard label="Cumulative Layout Shift"  value={get("cls")} />
            <MetricCard label="Time to Interactive"      value={get("tti")} />
            <MetricCard label="Speed Index"              value={get("speed_index")} />
            <MetricCard label="Total Blocking Time"      value={get("total_blocking_time")} />
          </MetricsGrid>
        </>
      }
    />
  );
};

export default PerformanceCard;