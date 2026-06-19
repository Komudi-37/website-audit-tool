// Shared TypeScript types for the audit tool

export type AuditCategory =
  | "performance"
  | "seo"
  | "accessibility"
  | "security"
  | "functionality";

export interface AuditRequest {
  url: string;
  categories?: AuditCategory[];
}

export interface Finding {
  id: string;
  title: string;
  description: string;
  severity: "critical" | "warning" | "info" | "pass";
  category: AuditCategory;
}

export interface AuditResult {
  audit_type: AuditCategory;
  score: number;           // 0–100
  metrics: Record<string, unknown>;
  findings: Finding[];
  recommendations: string[];
}

export interface AuditResponse {
  url: string;
  timestamp: string;
  results: AuditResult[];
  overall_score: number;
}

export type AuditStatus = "idle" | "loading" | "success" | "error";
