// API service — all backend communication goes through here
import type { AuditRequest, AuditResponse } from "../types";

const BASE_URL = import.meta.env.VITE_API_URL ?? "";

export async function checkHealth(): Promise<{ status: string }> {
  const res = await fetch(`${BASE_URL}/health`);
  if (!res.ok) throw new Error("Backend unreachable");
  return res.json();
}

export async function runAudit(payload: AuditRequest): Promise<AuditResponse> {
  const res = await fetch(`${BASE_URL}/audit`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error((err as { detail?: string }).detail ?? "Audit request failed");
  }
  return res.json();
}
export async function downloadPDF(payload: object): Promise<void> {
  const res = await fetch("/export/pdf", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    throw new Error("PDF generation failed");
  }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "audit-report.pdf";
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}