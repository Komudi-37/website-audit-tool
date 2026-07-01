// API service — all backend communication goes through here
import type { AuditRequest, AuditResponse, AuditHistoryItem } from "../types";

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
  console.log("PDF payload results count:", (payload as any)?.results?.length);
  console.log("PDF payload first result findings count:", (payload as any)?.results?.[0]?.findings?.length);
  const res = await fetch(`${BASE_URL}/export/pdf`, {
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

export async function getAuditHistory(limit = 20): Promise<AuditHistoryItem[]> {
  const res = await fetch(`${BASE_URL}/audit/history?limit=${limit}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error((err as { detail?: string }).detail ?? "Failed to fetch audit history");
  }
  return res.json();
}

export async function getAuditHistoryDetail(id: number): Promise<AuditResponse> {
  const res = await fetch(`${BASE_URL}/audit/history/${id}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error((err as { detail?: string }).detail ?? "Failed to fetch audit detail");
  }
  return res.json();
}