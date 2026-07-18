import type { AuditCategory } from "../types";

interface CategoryOption {
  id: AuditCategory;
  label: string;
  icon: string;
  description: string;
}

export const AUDIT_CATEGORIES: CategoryOption[] = [
  {
    id: "performance",
    label: "Performance",
    icon: "PERF",
    description: "Page speed, Core Web Vitals",
  },
  {
    id: "seo",
    label: "SEO",
    icon: "SEO",
    description: "Meta tags, headings, indexability",
  },
  {
    id: "accessibility",
    label: "Accessibility",
    icon: "A11Y",
    description: "ARIA, contrast, keyboard nav",
  },
  {
    id: "security",
    label: "Security",
    icon: "SEC",
    description: "SSL, headers, CSP, HSTS",
  },
  {
    id: "functionality",
    label: "Functionality",
    icon: "FUNC",
    description: "Navigation, links, forms",
  },
  {
    id: "form_validation",
    label: "Form Validation",
    icon: "FORM",
    description: "Password fields, labels, required inputs",
  },
];
