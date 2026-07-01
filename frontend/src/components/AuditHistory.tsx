import React, { useEffect, useState, useRef } from "react";
import { getAuditHistory, getAuditHistoryDetail } from "../services/api";
import type { AuditHistoryItem, AuditResponse } from "../types";
import { getScoreTier } from "./AuditCardShared";

interface AuditHistoryProps {
  onSelect: (data: AuditResponse) => void;
  refreshKey?: number;
}

const HistorySkeleton: React.FC = () => (
  <div className="history-wrapper" aria-hidden="true">
    <div className="history-stack-wrapper">
      {Array.from({ length: 3 }, (_, i) => (
        <div
          key={i}
          className="history-stack-card"
          style={{
            transform: `translateY(${-i * 8}px) rotate(${i === 1 ? -1.5 : i === 2 ? 2 : 0}deg)`,
            zIndex: 3 - i,
          }}
        >
          <div className="skeleton-line" style={{ width: "60%", height: "16px" }} />
          <div className="skeleton-line" style={{ width: "40px", height: "16px" }} />
        </div>
      ))}
    </div>
  </div>
);

const AuditHistory: React.FC<AuditHistoryProps> = ({ onSelect, refreshKey }) => {
  const [history, setHistory] = useState<AuditHistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>("");
  const [isExpanded, setIsExpanded] = useState(false);
  const [loadingId, setLoadingId] = useState<number | null>(null);
  const [visibleItems, setVisibleItems] = useState<boolean[]>([]);
  const rafRef = useRef<number | undefined>(undefined);

  useEffect(() => {
    const fetchHistory = async () => {
      setLoading(true);
      setError("");
      try {
        const data = await getAuditHistory(20);
        setHistory(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load audit history");
      } finally {
        setLoading(false);
      }
    };

    fetchHistory();
  }, [refreshKey]);

  useEffect(() => {
    if (isExpanded && history.length > 0) {
      setVisibleItems(new Array(history.length).fill(false));
      rafRef.current = requestAnimationFrame(() => {
        rafRef.current = requestAnimationFrame(() => {
          setVisibleItems(new Array(history.length).fill(true));
        });
      });
    }
    return () => {
      if (rafRef.current) {
        cancelAnimationFrame(rafRef.current);
      }
    };
  }, [isExpanded, history.length]);

  const handleItemClick = async (id: number) => {
    setLoadingId(id);
    try {
      const data = await getAuditHistoryDetail(id);
      onSelect(data);
    } catch (err) {
      console.error("Failed to load audit detail:", err);
    } finally {
      setLoadingId(null);
    }
  };

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return "Just now";
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
  };

  const getScoreTierClass = (score: number) => {
    const tier = getScoreTier(score);
    return `history-item-score--${tier}`;
  };

  const handleStackClick = () => {
    setIsExpanded(true);
  };

  const handleCollapse = () => {
    setIsExpanded(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent, action: () => void) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      action();
    }
  };

  if (loading) {
    return <HistorySkeleton />;
  }

  if (error) {
    return (
      <div className="empty-state">
        <p className="empty-title">Error loading history</p>
        <p className="empty-desc">{error}</p>
      </div>
    );
  }

  if (history.length === 0) {
    return (
      <div className="empty-state">
        <div className="empty-icon" aria-hidden="true" />
        <p className="empty-title">No audits yet</p>
        <p className="empty-desc">
          Run your first audit above.
        </p>
      </div>
    );
  }

  const recentItems = history.slice(0, 3);
  const mostRecent = history[0];

  if (!isExpanded) {
    return (
      <div className="history-wrapper">
        <div
          className="history-stack-wrapper"
          onClick={handleStackClick}
          onKeyDown={(e) => handleKeyDown(e, handleStackClick)}
          role="button"
          tabIndex={0}
          aria-label={`View ${history.length} recent audits`}
        >
          {recentItems.map((item, index) => (
          <div
            key={item.id}
            className={`history-stack-card history-stack-card--${index}`}
          >
            {index === 0 && (
              <>
                <div className="history-item-url" title={mostRecent.url}>
                  {mostRecent.url}
                </div>
                <span className={`history-item-score ${getScoreTierClass(mostRecent.overall_score)}`}>
                  {Math.round(mostRecent.overall_score)}
                </span>
              </>
            )}
          </div>
        ))}
        </div>
        <div className="history-stack-hint">
          <span>{history.length}</span> recent audits — click to view
        </div>
      </div>
    );
  }

  return (
    <div className="history-wrapper">
      <div className="history-header">
        <h3 className="history-title">Recent Audits</h3>
        <button
          className="btn-copy"
          onClick={handleCollapse}
          onKeyDown={(e) => handleKeyDown(e, handleCollapse)}
          aria-label="Collapse audit history"
        >
          ✕
        </button>
      </div>
      <div className="history-fan">
        {history.map((item, index) => (
          <div
            key={item.id}
            className={`history-fan-item ${visibleItems[index] ? "visible" : ""}`}
            style={{ transitionDelay: `${index * 50}ms` }}
            onClick={() => handleItemClick(item.id)}
            onKeyDown={(e) => handleKeyDown(e, () => handleItemClick(item.id))}
            role="button"
            tabIndex={0}
            aria-label={`View audit for ${item.url}`}
          >
            <div className="history-item-url" title={item.url}>
              {item.url}
            </div>
            <div className="history-item-meta">
              {loadingId === item.id ? (
                <div className="history-item-spinner" aria-hidden="true" />
              ) : (
                <span
                  className={`history-item-score ${getScoreTierClass(item.overall_score)}`}
                >
                  {Math.round(item.overall_score)}
                </span>
              )}
              <span className="history-item-categories" title={item.categories}>
                {item.categories}
              </span>
              <span className="history-item-time">
                {formatTimestamp(item.timestamp)}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default AuditHistory;
