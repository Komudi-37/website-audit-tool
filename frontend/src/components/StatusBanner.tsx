import React from "react";

interface Props {
  message: string;
  type: "loading" | "error" | "success";
}

const StatusBanner: React.FC<Props> = ({ message, type }) => (
  <div className={`status-banner ${type}`} role="status" aria-live="polite">
    <span className="status-indicator" aria-hidden="true" />
    <span>{message}</span>
  </div>
);

export default StatusBanner;
