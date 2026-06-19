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
    icon: "⚡",
    description: "Page speed, Core Web Vitals",
  },
  {
    id: "seo",
    label: "SEO",
    icon: "🔍",
    description: "Meta tags, headings, indexability",
  },
  {
    id: "accessibility",
    label: "Accessibility",
    icon: "♿",
    description: "ARIA, contrast, keyboard nav",
  },
  {
    id: "security",
    label: "Security",
    icon: "🔒",
    description: "SSL, headers, CSP, HSTS",
  },
  {
    id: "functionality",
    label: "Functionality",
    icon: "⚙️",
    description: "Navigation, links, forms",
  },
];
