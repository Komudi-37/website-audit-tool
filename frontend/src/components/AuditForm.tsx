import React from "react";
import type { AuditCategory } from "../types";
import { AUDIT_CATEGORIES } from "../services/constants";

interface Props {
  url: string;
  onUrlChange: (v: string) => void;
  selected: AuditCategory[];
  onToggle: (c: AuditCategory) => void;
  onSubmit: () => void;
  loading: boolean;
}

const AuditForm: React.FC<Props> = ({
  url,
  onUrlChange,
  selected,
  onToggle,
  onSubmit,
  loading,
}) => {
  const handleKey = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !loading) onSubmit();
  };

  const getCategoryTitle = (catId: string): string => {
    switch (catId) {
      case "performance":
        return "Analyze page speed, Core Web Vitals, LCP, FCP, CLS";
      case "seo":
        return "Check meta tags, headings, canonical URLs, robots.txt, sitemap";
      case "accessibility":
        return "Scan for ARIA issues, color contrast, keyboard navigation";
      case "security":
        return "Inspect HTTPS, security headers, CSP, HSTS, X-Frame-Options";
      case "functionality":
        return "Test navigation links, contact forms, internal link health";
      case "form_validation":
        return "Check password field types, form labels, required inputs";
      default:
        return "";
    }
  };

  return (
    <div className="audit-form-card" aria-busy={loading}>
      <section className="audit-primary" aria-labelledby="audit-primary-title">
        <div className="audit-primary-header">
          <h2 id="audit-primary-title" className="audit-primary-title">
            Start an audit
          </h2>
          <p className="audit-primary-desc">
            Enter a URL to generate a structured report across selected categories.
          </p>
        </div>

        <div className="input-group">
          <div className="url-input-wrapper">
            <label htmlFor="url-input" className="url-input-label">
              Website URL
            </label>
            <div className="url-input-field">
              <span className="url-input-icon" aria-hidden="true" />
              <input
                id="url-input"
                type="url"
                className="url-input"
                placeholder="https://example.com"
                value={url}
                onChange={(e) => onUrlChange(e.target.value)}
                onKeyDown={handleKey}
                disabled={loading}
                autoComplete="url"
                spellCheck={false}
              />
            </div>
          </div>
          <button
            id="run-audit-btn"
            type="button"
            className="btn-run"
            onClick={onSubmit}
            disabled={loading || !url.trim()}
            aria-disabled={loading || !url.trim()}
            aria-busy={loading}
            title="Start a full website audit across selected categories"
          >
            {loading ? (
              <>
                <span className="spinner" aria-hidden="true" />
                <span>Auditing…</span>
                <span className="visually-hidden">Audit in progress</span>
              </>
            ) : (
              <>Run Audit</>
            )}
          </button>
        </div>
      </section>

      <section className="audit-categories" aria-labelledby="audit-categories-label">
        <div className="section-header">
          <p id="audit-categories-label" className="section-label">
            Audit categories
          </p>
          <span className="section-meta">
            {selected.length} of {AUDIT_CATEGORIES.length} selected
          </span>
        </div>
        <div className="categories-grid" role="group" aria-label="Select audit categories">
          {AUDIT_CATEGORIES.map((cat) => {
            const isSelected = selected.includes(cat.id);
            return (
              <label
                key={cat.id}
                htmlFor={`cat-${cat.id}`}
                className={`category-chip${isSelected ? " selected" : ""}`}
                title={getCategoryTitle(cat.id)}
              >
                <input
                  id={`cat-${cat.id}`}
                  type="checkbox"
                  checked={isSelected}
                  onChange={() => onToggle(cat.id)}
                  disabled={loading}
                />
                <span className="chip-check" aria-hidden="true">
                  {isSelected && (
                    <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                      <path
                        d="M2.5 6L5 8.5L9.5 3.5"
                        stroke="currentColor"
                        strokeWidth="1.5"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      />
                    </svg>
                  )}
                </span>
                <span className="chip-icon">{cat.icon}</span>
                <span className="chip-info">
                  <span className="chip-label">{cat.label}</span>
                  <span className="chip-desc">{cat.description}</span>
                </span>
              </label>
            );
          })}
        </div>
      </section>
    </div>
  );
};

export default AuditForm;
