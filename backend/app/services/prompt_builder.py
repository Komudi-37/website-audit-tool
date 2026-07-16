"""
Prompt Builder — constructs structured prompts for the AI audit analysis.

This module is intentionally side-effect free:
  - No HTTP calls.
  - No AI client imports.
  - No external dependencies beyond the standard library.

Usage:
    from app.services.prompt_builder import build_prompt
    prompt = build_prompt(audit_data)
"""

import json


def build_prompt(audit_data: dict) -> str:
    """
    Build a structured prompt string from a completed audit result.

    The prompt instructs the AI to act as a professional Website Audit
    Assistant and produce a structured JSON analysis based strictly on
    the provided audit data.  The AI must not invent data or reference
    anything outside the supplied JSON.

    Args:
        audit_data: The full audit response dict containing:
                    - url (str)
                    - overall_score (float)
                    - results (list of per-module AuditResult dicts)

    Returns:
        A complete prompt string ready to pass to AIClient.generate().

    Raises:
        ValueError: If audit_data is empty or not a dict.
    """
    if not audit_data or not isinstance(audit_data, dict):
        raise ValueError("audit_data must be a non-empty dictionary.")

    audit_json = json.dumps(audit_data, indent=2)

    prompt = f"""You are an expert Website Audit Assistant with deep knowledge of \
web performance, SEO, accessibility standards (WCAG), security best practices, \
and frontend functionality.

You have been given the results of an automated audit for the website: \
{audit_data.get("url", "unknown")}.

The overall audit score is: {audit_data.get("overall_score", 0):.1f} / 100.

Your task is to analyse the audit results provided below and produce a \
professional, actionable report.

STRICT RULES:
1. Base your analysis ONLY on the supplied audit data.
2. You may infer the severity, business impact, and priority of issues from the provided metrics and findings.
3. Do NOT fabricate website metrics, scan results, or issues that are not present in the audit data.
4. Generate professional findings and actionable recommendations using your reasoning based on the supplied audit results.
5. Use professional website audit language throughout.
6. Return ONLY valid JSON — no markdown, no code blocks, and no explanations outside the JSON object.
7. If a category's score is null (e.g., form_validation with no forms found on the page), state this as informational in that category's findings — do not treat it as a failure or missing data.
8. When selecting priority_fixes, always prioritize findings with severity='critical' over findings with severity='warning' or 'info', regardless of which category they come from. If multiple critical findings exist across categories, choose the ones with the most significant security, data-exposure, or user-blocking impact first (e.g., exposed passwords, broken checkout/contact forms, missing HTTPS) over cosmetic or SEO-only issues.
9. Aim to represent diverse categories in priority_fixes where possible — don't let one category dominate all slots if other categories have equally or more severe critical findings.

AUDIT DATA:
{audit_json}

You must return a single valid JSON object matching EXACTLY this schema:

{{
  "executive_summary": "<2-3 sentence overview of the website's overall audit \
health based strictly on the scores and findings above>",

  "overall_assessment": "<detailed paragraph assessing the website's strengths \
and weaknesses across all audited categories, referencing specific scores and \
findings from the data>",

  "business_impact": "<paragraph explaining how the identified issues — \
particularly critical and warning findings — could affect real users, search \
engine rankings, or business outcomes>",

  "priority_fixes": [
    "<specific actionable fix #1 drawn directly from the audit findings>",
    "<specific actionable fix #2 drawn directly from the audit findings>",
    "<specific actionable fix #3 drawn directly from the audit findings>",
    "<specific actionable fix #4 drawn directly from the audit findings>",
    "<specific actionable fix #5 drawn directly from the audit findings>"
  ],

  "categories": {{
    "seo": {{
      "findings": [
        "<finding drawn from the SEO audit results>"
      ],
      "recommendations": [
        "<recommendation drawn from the SEO audit recommendations>"
      ]
    }},
    "performance": {{
      "findings": [
        "<finding drawn from the Performance audit results>"
      ],
      "recommendations": [
        "<recommendation drawn from the Performance audit recommendations>"
      ]
    }},
    "accessibility": {{
      "findings": [
        "<finding drawn from the Accessibility audit results>"
      ],
      "recommendations": [
        "<recommendation drawn from the Accessibility audit recommendations>"
      ]
    }},
    "security": {{
      "findings": [
        "<finding drawn from the Security audit results>"
      ],
      "recommendations": [
        "<recommendation drawn from the Security audit recommendations>"
      ]
    }},
    "functionality": {{
      "findings": [
        "<finding drawn from the Functionality audit results>"
      ],
      "recommendations": [
        "<recommendation drawn from the Functionality audit recommendations>"
      ]
    }},
    "form_validation": {{
      "findings": [
        "<finding drawn from the Form Validation audit results>"
      ],
      "recommendations": [
        "<recommendation drawn from the Form Validation audit recommendations>"
      ]
    }}
  }}
}}

Remember: Return ONLY the JSON object. No text before or after it.
If any audit category has no findings or recommendations, return an empty array [] instead of null or omitting the field.

The JSON structure must always remain complete and valid.
"""

    return prompt.strip()