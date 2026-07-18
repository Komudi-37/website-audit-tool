"""
AI Analyzer — orchestrates prompt building, AI generation, and response parsing.

This module is the single internal entry point for AI-powered audit analysis.
It wires together prompt_builder and ai_client, then validates and returns
the structured analysis as a Python dictionary.

Usage:
    from app.services.ai_analyzer import analyze_audit
    analysis = await analyze_audit(audit_data)
"""

import json
import logging
from typing import Any

from app.services.prompt_builder import build_prompt
from app.services.ai_client import ai_client

logger = logging.getLogger("audit_tool.ai_analyzer")

# Keys that must be present in every valid AI response
REQUIRED_KEYS: frozenset[str] = frozenset({
    "executive_summary",
    "overall_assessment",
    "business_impact",
    "priority_fixes",
    "categories",
})



async def analyze_audit(audit_data: dict[str, Any]) -> dict[str, Any]:
    """
    Run an AI-powered analysis on a completed audit result.

    Orchestrates the full pipeline:
      1. Validates the input audit data.
      2. Builds a structured prompt via prompt_builder.
      3. Sends the prompt to OpenRouter via ai_client.
      4. Strips markdown fences if the model wraps the JSON.
      5. Parses the JSON response.
      6. Validates all required top-level keys are present.
      7. Returns the parsed analysis dictionary.

    Args:
        audit_data: The full audit response dictionary containing at minimum:
                    - url (str)
                    - overall_score (float)
                    - results (list)

    Returns:
        A validated dictionary matching the AI response schema:
        {
            "executive_summary": str,
            "overall_assessment": str,
            "business_impact": str,
            "priority_fixes": list[str],
            "categories": {
                "seo": {"findings": [...], "recommendations": [...]},
                "performance": {"findings": [...], "recommendations": [...]},
                "accessibility": {"findings": [...], "recommendations": [...]},
                "security": {"findings": [...], "recommendations": [...]},
                "functionality": {"findings": [...], "recommendations": [...]}
            }
        }

    Raises:
        ValueError: If audit_data is invalid or the AI returns unparseable JSON.
        RuntimeError: If the AI service call fails or required keys are missing.
    """
    if not audit_data or not isinstance(audit_data, dict):
        raise ValueError("audit_data must be a non-empty dictionary.")

    url = audit_data.get("url", "unknown")
    overall_score = audit_data.get("overall_score", 0)

    logger.info(
        "Starting AI analysis — url=%s, overall_score=%.1f",
        url,
        overall_score,
    )

    # ── Step 1: Build prompt ─────────────────────────────────────────
    try:
        prompt = build_prompt(audit_data)
    except ValueError as exc:
        logger.error("Prompt building failed: %s", exc)
        raise ValueError(f"Failed to build AI prompt: {exc}") from exc

    logger.debug("Prompt built successfully (chars=%d)", len(prompt))

    # ── Step 2: Call AI ──────────────────────────────────────────────
    try:
        raw_response = await ai_client.generate(prompt)
    except RuntimeError as exc:
        logger.error("AI generation failed for url=%s: %s", url, exc)
        raise RuntimeError(f"AI analysis failed: {exc}") from exc

    logger.debug(
        "Raw AI response received (chars=%d)",
        len(raw_response),
    )

    # ── Step 3: Strip markdown fences if present ─────────────────────
    # Some models wrap JSON in ```json ... ``` even when instructed not to.
    cleaned = raw_response.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        # Remove the opening fence (```json or ```)
        lines = lines[1:] if lines[0].startswith("```") else lines
        # Remove the closing fence
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()

    # ── Step 4: Parse JSON ───────────────────────────────────────────
    try:
        analysis: dict[str, Any] = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        logger.error(
            "Failed to parse AI response as JSON for url=%s. "
            "Response (first 500 chars): %s",
            url,
            cleaned[:500],
        )
        raise ValueError(
            f"AI returned a response that could not be parsed as JSON: {exc}"
        ) from exc

    if not isinstance(analysis, dict):
        raise ValueError(
            f"AI returned valid JSON but expected an object, "
            f"got {type(analysis).__name__}."
        )

    # ── Step 5: Validate required keys ──────────────────────────────
    missing_keys = REQUIRED_KEYS - analysis.keys()
    
    if missing_keys:
        logger.error(
            "AI response missing required keys for url=%s: %s",
            url,
            missing_keys,
        )
        raise RuntimeError(
            f"AI response is missing required fields: {sorted(missing_keys)}. "
            "The model may have returned an incomplete response."
        )

    logger.info(
        "AI analysis completed successfully — url=%s, "
        "priority_fixes=%d, categories=%d",
        url,
        len(analysis.get("priority_fixes", [])),
        len(analysis.get("categories", {})),
    )
    
    
    required_categories={
        "seo",
        "performance",
        "accessibility",
        "security",
        "functionality",
        "form_validation"
    }
    categories = analysis.get("categories", {})
    if not isinstance(categories, dict):
        raise RuntimeError("'categories' must be a JSON object.")
    
    missing_categories = required_categories - categories.keys()
    if missing_categories:
        raise RuntimeError(
            f"AI response is missing category sections: {sorted(missing_categories)}"
    )
        
    
    priority_fixes = analysis.get("priority_fixes")
    if not isinstance(priority_fixes, list):
        raise RuntimeError(
        "'priority_fixes' must be a list."
    )
        
    # Validate each category structure
    for category_name in required_categories:
        category = categories[category_name]
        
        if not isinstance(category, dict):
             raise RuntimeError(
            f"{category_name} must be a JSON object."
        )
        if "findings" not in category:
             raise RuntimeError(
            f"{category_name} is missing 'findings'."
        )
        if "recommendations" not in category:
             raise RuntimeError(
            f"{category_name} is missing 'recommendations'."
        )
        if not isinstance(category["findings"], list):
            raise RuntimeError(
            f"{category_name}.findings must be a list."
        )
        if not isinstance(category["recommendations"], list):
            raise RuntimeError(
            f"{category_name}.recommendations must be a list."
        )

    return analysis