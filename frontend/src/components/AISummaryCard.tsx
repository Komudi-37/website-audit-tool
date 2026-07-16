import React from "react";

export interface AISummaryCardProps {
  executiveSummary: string;
  overallAssessment: string;
  businessImpact: string;
  priorityFixes: string[];
}

const AISummaryCard: React.FC<AISummaryCardProps> = ({
  executiveSummary,
  overallAssessment,
  businessImpact,
  priorityFixes,
}) => {
  const hasExecutiveSummary = executiveSummary.trim().length > 0;
  const hasOverallAssessment = overallAssessment.trim().length > 0;
  const hasBusinessImpact = businessImpact.trim().length > 0;
  const filteredPriorityFixes = priorityFixes.filter((fix) => fix.trim().length > 0);
  const hasPriorityFixes = filteredPriorityFixes.length > 0;

  const hasAnyContent =
    hasExecutiveSummary || hasOverallAssessment || hasBusinessImpact || hasPriorityFixes;

  if (!hasAnyContent) {
    return null;
  }

  return (
    <article className="audit-card">
      <header className="audit-card-header">
        <div className="audit-card-title-group">
          <span className="audit-category-tag">AI</span>
          <h3 className="audit-card-title">🤖 AI Executive Summary</h3>
        </div>
      </header>

      {hasExecutiveSummary && (
        <section className="audit-section" aria-labelledby="ai-executive-summary">
          <h4 className="audit-section-title" id="ai-executive-summary">
            Executive Summary
          </h4>
          <p className="audit-finding-desc">{executiveSummary}</p>
        </section>
      )}

      {hasOverallAssessment && (
        <section className="audit-section" aria-labelledby="ai-overall-assessment">
          <h4 className="audit-section-title" id="ai-overall-assessment">
            Overall Assessment
          </h4>
          <p className="audit-finding-desc">{overallAssessment}</p>
        </section>
      )}

      {hasBusinessImpact && (
        <section className="audit-section" aria-labelledby="ai-business-impact">
          <h4 className="audit-section-title" id="ai-business-impact">
            Business Impact
          </h4>
          <p className="audit-finding-desc">{businessImpact}</p>
        </section>
      )}

      {hasPriorityFixes && (
        <section className="audit-section" aria-labelledby="ai-priority-fixes">
          <h4 className="audit-section-title" id="ai-priority-fixes">
            Priority Fixes
            <span className="audit-section-count">{filteredPriorityFixes.length}</span>
          </h4>
          <ul className="audit-recommendations-list">
            {filteredPriorityFixes.map((fix, i) => (
              <li key={`${i}-${fix.slice(0, 40)}`} className="audit-recommendation-item">
                {fix}
              </li>
            ))}
          </ul>
        </section>
      )}
    </article>
  );
};

export default AISummaryCard;