import React from "react";

interface Props {
  message: string;
  type: "loading" | "error" | "success";
}

const LIVE_MODE: Record<Props["type"], "polite" | "assertive"> = {
  loading: "polite",
  success: "polite",
  error: "assertive",
};

const StatusBanner: React.FC<Props> = ({ message, type }) => (
  <div
    className={`status-banner ${type}`}
    role="status"
    aria-live={LIVE_MODE[type]}
    aria-atomic="true"
  >
    <span className="status-indicator" aria-hidden="true" />
    <span>{message}</span>
  </div>
);

export default StatusBanner;
