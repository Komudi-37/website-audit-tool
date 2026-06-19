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

  return (
    <div className="audit-card">
      {/* URL Input */}
      <div className="input-group">
        <div className="url-input-wrapper">
          <span className="url-input-icon">🌐</span>
          <input
            id="url-input"
            type="url"
            className="url-input"
            placeholder="https://example.com"
            value={url}
            onChange={(e) => onUrlChange(e.target.value)}
            onKeyDown={handleKey}
            disabled={loading}
            autoComplete="off"
            spellCheck={false}
          />
        </div>
        <button
          id="run-audit-btn"
          className="btn-run"
          onClick={onSubmit}
          disabled={loading || !url.trim()}
        >
          {loading ? (
            <>
              <span className="spinner" />
              Auditing…
            </>
          ) : (
            <>▶ Run Audit</>
          )}
        </button>
      </div>

      {/* Category Selection */}
      <p className="section-label">Audit Categories</p>
      <div className="categories-grid" role="group" aria-label="Select audit categories">
        {AUDIT_CATEGORIES.map((cat) => {
          const isSelected = selected.includes(cat.id);
          return (
            <label
              key={cat.id}
              htmlFor={`cat-${cat.id}`}
              className={`category-chip${isSelected ? " selected" : ""}`}
            >
              <input
                id={`cat-${cat.id}`}
                type="checkbox"
                checked={isSelected}
                onChange={() => onToggle(cat.id)}
                disabled={loading}
              />
              <span className="chip-icon">{cat.icon}</span>
              <span className="chip-info">
                <span className="chip-label">{cat.label}</span>
                <span className="chip-desc">{cat.description}</span>
              </span>
            </label>
          );
        })}
      </div>
    </div>
  );
};

export default AuditForm;
