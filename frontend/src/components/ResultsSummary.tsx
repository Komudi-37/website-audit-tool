import React from "react";
import type { AuditResult } from "../types";
import { getScoreTier } from "./AuditCardShared";

interface Props {
  overallScore: number;
  results: AuditResult[];
}

const ResultsSummary: React.FC<Props> = ({ overallScore, results }) => {
  const tier = getScoreTier(overallScore);
  const displayScore = Number.isInteger(overallScore)
    ? overallScore
    : Math.round(overallScore * 10) / 10;

  const criticalCount = results.reduce(
    (total, result) =>
      total + result.findings.filter((finding) => finding.severity === "critical").length,
    0
  );

  const recommendationsCount = results.reduce(
    (total, result) => total + result.recommendations.length,
    0
  );

  return (
    <div className="results-summary" aria-label="Audit summary">
      <div className="summary-stat">
        <span className="summary-stat-label">Overall Score</span>
        <span className={`summary-stat-value summary-stat-value--${tier}`}>
          {displayScore}
        </span>
      </div>
      <div className="summary-stat">
        <span className="summary-stat-label">Audits Completed</span>
        <span className="summary-stat-value">{results.length}</span>
      </div>
      <div className="summary-stat">
        <span className="summary-stat-label">Critical Findings</span>
        <span
          className={`summary-stat-value${
            criticalCount > 0 ? " summary-stat-value--poor" : ""
          }`}
        >
          {criticalCount}
        </span>
      </div>
      <div className="summary-stat">
        <span className="summary-stat-label">Recommendations</span>
        <span className="summary-stat-value">{recommendationsCount}</span>
      </div>
    </div>
  );
};

export default ResultsSummary;
