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
    <dl className="results-summary">
      <div className="summary-stat">
        <dt className="summary-stat-label">Overall Score</dt>
        <dd className={`summary-stat-value summary-stat-value--${tier}`}>
          {displayScore}
        </dd>
      </div>
      <div className="summary-stat">
        <dt className="summary-stat-label">Audits Completed</dt>
        <dd className="summary-stat-value">{results.length}</dd>
      </div>
      <div className="summary-stat">
        <dt className="summary-stat-label">Critical Findings</dt>
        <dd
          className={`summary-stat-value${
            criticalCount > 0 ? " summary-stat-value--poor" : ""
          }`}
        >
          {criticalCount}
        </dd>
      </div>
      <div className="summary-stat">
        <dt className="summary-stat-label">Recommendations</dt>
        <dd className="summary-stat-value">{recommendationsCount}</dd>
      </div>
    </dl>
  );
};

export default ResultsSummary;
