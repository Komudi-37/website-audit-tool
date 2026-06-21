import React from "react";
import type { AuditResponse, AuditResult } from "../types";
import PerformanceCard from "./PerformanceCard";
import SEOCard from "./SEOCard";
import AccessibilityCard from "./AccessibilityCard";
import SecurityCard from "./SecurityCard";

interface Props {
  data: unknown;
  url: string;
}

const ResultsPanel: React.FC<Props> = ({ data, url }) => {
  const response = data as Partial<AuditResponse>;
  const results = Array.isArray(response.results) ? response.results : [];
  
  const perfResult = results.find(r => r.audit_type === "performance") as AuditResult | undefined;
  const seoResult = results.find(r => r.audit_type === "seo") as AuditResult | undefined;
  const accessibilityResult = results.find(r => r.audit_type === "accessibility") as AuditResult | undefined;
  const securityResult = results.find(r => r.audit_type === "security") as AuditResult | undefined;
  
  const rawData = { ...response };
  if (Array.isArray(rawData.results)) {
    rawData.results = rawData.results.filter(
      r => r.audit_type !== "performance" && 
           r.audit_type !== "seo" && 
           r.audit_type !== "accessibility" &&
           r.audit_type !== "security"
    );
  }

  const formatted = JSON.stringify(rawData, null, 2);
  const hasRenderedCards = !!(perfResult || seoResult || accessibilityResult || securityResult);

  return (
    <section className="results-section" aria-label="Audit results">
      <div className="results-header">
        <h2 className="results-title">Audit Results</h2>
        <span className="results-url">{url}</span>
      </div>

      {perfResult && (
        <PerformanceCard result={perfResult} />
      )}

      {seoResult && (
        <SEOCard result={seoResult} />
      )}

      {accessibilityResult && (
        <AccessibilityCard result={accessibilityResult} />
      )}

      {securityResult && (
        <SecurityCard result={securityResult} />
      )}

      {rawData.results && rawData.results.length > 0 && (
        <div className="raw-response-card" style={{ marginTop: hasRenderedCards ? 24 : 0 }}>
          <div className="raw-response-header">
            <span>
              <span className="raw-dot" style={{ marginRight: 8 }} />
              API Response (Unimplemented Audits)
            </span>
            <span style={{ fontFamily: "'JetBrains Mono', monospace", color: "var(--text-muted)" }}>
              JSON
            </span>
          </div>
          <pre className="raw-response-body">{formatted}</pre>
        </div>
      )}
    </section>
  );
};

export default ResultsPanel;

