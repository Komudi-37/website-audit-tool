import React from "react";
import type { AuditResult } from "../types";
import { AuditCardLayout, MetricCard, MetricsGrid } from "./AuditCardShared";

interface Props {
  result: AuditResult;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

/** Returns a CSS colour string based on a 0-100 score. */
function scoreColour(score: number): string {
  if (score >= 90) return "var(--green)";
  if (score >= 50) return "var(--amber)";
  return "var(--red)";
}

/**
 * Attempts to compute a human-readable delta between two metric display values.
 * Returns null when values are equal or cannot be parsed numerically.
 */
function deltaLabel(desktopVal: string, mobileVal: string): string | null {
  if (!desktopVal || !mobileVal || desktopVal === "—" || mobileVal === "—") return null;
  const parse = (v: string) => parseFloat(v.replace(/[^0-9.]/g, ""));
  const d = parse(desktopVal);
  const m = parse(mobileVal);
  if (isNaN(d) || isNaN(m) || d === m) return null;
  const diff = m - d; // positive → mobile is slower / worse
  const unit = desktopVal.replace(/[\d.\s]/g, "").trim();
  const sign = diff > 0 ? "+" : "";
  return `Δ ${sign}${diff.toFixed(1)}${unit}`;
}

// ── Component ─────────────────────────────────────────────────────────────────

const PerformanceCard: React.FC<Props> = ({ result }) => {
  const metrics = result.metrics as Record<string, unknown>;
  const hasDualMode =
    typeof metrics.desktop_score !== "undefined" &&
    typeof metrics.mobile_score !== "undefined";

  // ── Fallback: original single-column layout ───────────────────────────────
  if (!hasDualMode) {
    return (
      <AuditCardLayout
        title="Performance"
        categoryTag="PERF"
        score={result.score}
        findings={result.findings}
        recommendations={result.recommendations}
        preserveFindingWhitespace
        metrics={
          <MetricsGrid>
            <MetricCard label="First Contentful Paint"    value={String(metrics.fcp                 || "—")} />
            <MetricCard label="Largest Contentful Paint"  value={String(metrics.lcp                 || "—")} />
            <MetricCard label="Cumulative Layout Shift"   value={String(metrics.cls                 || "—")} />
            <MetricCard label="Time to Interactive"       value={String(metrics.tti                 || "—")} />
            <MetricCard label="Speed Index"               value={String(metrics.speed_index         || "—")} />
            <MetricCard label="Total Blocking Time"       value={String(metrics.total_blocking_time  || "—")} />
          </MetricsGrid>
        }
      />
    );
  }

  // ── Dual-mode layout ──────────────────────────────────────────────────────
  const desktopScore = Number(metrics.desktop_score);
  const mobileScore  = Number(metrics.mobile_score);
  const gap          = Number(metrics.performance_gap ?? (desktopScore - mobileScore));

  const metricPairs = [
    { label: "First Contentful Paint",   dk: "desktop_fcp",                  mk: "mobile_fcp"                 },
    { label: "Largest Contentful Paint", dk: "desktop_lcp",                  mk: "mobile_lcp"                 },
    { label: "Cumulative Layout Shift",  dk: "desktop_cls",                  mk: "mobile_cls"                 },
    { label: "Time to Interactive",      dk: "desktop_tti",                  mk: "mobile_tti"                 },
    { label: "Speed Index",              dk: "desktop_speed_index",          mk: "mobile_speed_index"         },
    { label: "Total Blocking Time",      dk: "desktop_total_blocking_time",  mk: "mobile_total_blocking_time" },
  ] as const;

  const dualMetrics = (
    <div className="perf-dual-metrics">
      {/* ── Score Badges ── */}
      <div className="perf-score-badges">
        <div className="perf-score-badge">
          <span className="perf-badge-icon" aria-hidden="true">🖥</span>
          <span className="perf-badge-label">Desktop</span>
          <span className="perf-badge-score" style={{ color: scoreColour(desktopScore) }}>
            {desktopScore}
          </span>
        </div>

        <div
          className={`perf-gap-chip ${gap > 15 ? "perf-gap-chip--warn" : "perf-gap-chip--ok"}`}
          title="Desktop score minus Mobile score"
        >
          <span className="perf-gap-label">Gap</span>
          <strong className="perf-gap-value">{gap > 0 ? `+${gap}` : gap} pts</strong>
        </div>

        <div className="perf-score-badge">
          <span className="perf-badge-icon" aria-hidden="true">📱</span>
          <span className="perf-badge-label">Mobile</span>
          <span className="perf-badge-score" style={{ color: scoreColour(mobileScore) }}>
            {mobileScore}
          </span>
        </div>
      </div>

      {/* ── Metric Table ── */}
      <div className="perf-metric-table" role="table" aria-label="Desktop vs Mobile metrics">
        <div className="perf-metric-header" role="row">
          <span className="perf-metric-name" role="columnheader">Metric</span>
          <span className="perf-col-label"   role="columnheader">🖥 Desktop</span>
          <span className="perf-col-label perf-col-delta" role="columnheader">Δ Mobile</span>
          <span className="perf-col-label"   role="columnheader">📱 Mobile</span>
        </div>

        {metricPairs.map(({ label, dk, mk }) => {
          const dv    = String(metrics[dk] || "—");
          const mv    = String(metrics[mk] || "—");
          const delta = deltaLabel(dv, mv);
          const isWorse = delta !== null && delta.startsWith("Δ +");
          return (
            <div className="perf-metric-row" key={label} role="row">
              <span className="perf-metric-name"  role="cell">{label}</span>
              <span className="perf-metric-value" role="cell">{dv}</span>
              <span
                className={`perf-delta-chip ${
                  delta === null ? "" : isWorse ? "perf-delta--worse" : "perf-delta--better"
                }`}
                role="cell"
                title={isWorse ? "Mobile is slower" : delta ? "Mobile is faster" : ""}
              >
                {delta ?? "—"}
              </span>
              <span className="perf-metric-value" role="cell">{mv}</span>
            </div>
          );
        })}
      </div>
    </div>
  );

  return (
    <AuditCardLayout
      title="Performance"
      categoryTag="PERF"
      score={result.score}
      findings={result.findings}
      recommendations={result.recommendations}
      preserveFindingWhitespace
      metrics={dualMetrics}
    />
  );
};

export default PerformanceCard;

