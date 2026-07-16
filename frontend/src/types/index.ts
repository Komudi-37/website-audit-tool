// Shared TypeScript types for the audit tool

export type AuditCategory =
  | "performance"
  | "seo"
  | "accessibility"
  | "security"
  | "functionality"
  | "form_validation";

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
  score: number | null;      // 0–100, or null if not applicable
  metrics: Record<string, unknown>;
  findings: Finding[];
  recommendations: string[];
}

export interface AuditResponse {
  url: string;
  timestamp: string;
  results: AuditResult[];
  overall_score: number;
  executive_summary: string;
  overall_assessment: string;
  business_impact: string;
  priority_fixes: string[];
}

export interface AuditHistoryItem {
  id: number;
  url: string;
  timestamp: string;
  overall_score: number;
  categories: string;
}

export type AuditStatus = "idle" | "loading" | "success" | "error";
