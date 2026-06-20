"""Accessibility audit engine using Playwright and axe-core."""
import os
import logging
import datetime
from typing import List, Dict, Any
from app.schemas.audit import AuditResult, Finding

logger = logging.getLogger("audit_tool.accessibility")

async def run_accessibility_audit(url: str) -> AuditResult:
    """Run Accessibility audit using Playwright and axe-core."""
    logger.info(f"Starting Accessibility audit for {url}")
    
    # Environment override for headless mode (headless by default)
    headless_env = os.environ.get("PLAYWRIGHT_HEADLESS", "True")
    headless = headless_env.lower() in ("true", "1", "yes")
    
    # Ensure screenshots directory exists at the root of the backend folder
    base_dir = os.path.dirname(os.path.abspath(__file__))
    screenshots_dir = os.path.abspath(os.path.join(base_dir, "..", "..", "screenshots"))
    os.makedirs(screenshots_dir, exist_ok=True)
    
    from playwright.async_api import async_playwright
    from axe_playwright_python.async_playwright import Axe
    
    browser = None
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=headless)
            context = await browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            
            try:
                await page.goto(url, wait_until="load", timeout=30000)
                # Let the page stabilize
                await page.wait_for_timeout(1000)
                
                # Execute Axe scan using the dependency-managed engine
                axe = Axe()
                axe_results = await axe.run(page)
                
            except Exception as e:
                # Capture screenshot on navigation/runtime failure
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                screenshot_filename = f"a11y_error_{timestamp}.png"
                screenshot_path = os.path.join(screenshots_dir, screenshot_filename)
                try:
                    await page.screenshot(path=screenshot_path)
                    logger.error(f"Saved failure screenshot to {screenshot_path}")
                except Exception as screenshot_err:
                    logger.warning(f"Could not take screenshot on navigation failure: {screenshot_err}")
                raise e
            finally:
                await browser.close()
                
        # Parse the Axe results
        return _parse_axe_report(axe_results.response, url)
        
    except Exception as e:
        logger.exception(f"Error running accessibility audit for {url}")
        return _generate_error_result(url, str(e))

def _categorize_violation(rule_id: str) -> str:
    rule_id = rule_id.lower()
    
    # 1. Missing alt text
    if rule_id in ("image-alt", "image-redundant-alt", "input-image-alt", "area-alt"):
        return "alt_text"
        
    # 2. Missing form labels
    if rule_id in ("label", "label-title-only", "form-field-multiple-labels", "aria-label", "select-name", "input-button-name"):
        return "form_labels"
        
    # 3. Missing ARIA attributes
    if rule_id.startswith("aria-") or "aria" in rule_id:
        return "aria_attributes"
        
    # 4. Color contrast issues
    if "contrast" in rule_id or rule_id == "color-contrast":
        return "color_contrast"
        
    # 5. Heading hierarchy issues
    if rule_id in ("heading-order", "page-has-heading-one", "p-as-heading") or "heading" in rule_id:
        return "heading_hierarchy"
        
    # 6. Keyboard accessibility issues
    if rule_id in ("bypass", "focusable-content", "tabindex", "accesskeys", "scrollable-region-focusable", "keyboard-navigation", "focus-visible", "duplicate-id-active"):
        return "keyboard_accessibility"
        
    return "keyboard_accessibility"

def _parse_axe_report(data: dict, url: str) -> AuditResult:
    violations = data.get("violations", [])
    passes = data.get("passes", [])
    
    score = 100
    findings: List[Finding] = []
    recommendations: List[str] = []
    
    # Initialize counts for the 6 primary categories
    metrics = {
        "missing_alt_text_count": 0,
        "missing_form_labels_count": 0,
        "missing_aria_attributes_count": 0,
        "color_contrast_issues_count": 0,
        "heading_hierarchy_issues_count": 0,
        "keyboard_accessibility_issues_count": 0,
        "total_violations": 0,
        "rules_passed": len(passes)
    }
    
    # Track which categories had violations for pass findings
    cat_violation_counts = {
        "alt_text": 0,
        "form_labels": 0,
        "aria_attributes": 0,
        "color_contrast": 0,
        "heading_hierarchy": 0,
        "keyboard_accessibility": 0
    }
    
    for v in violations:
        rule_id = v.get("id", "")
        impact = v.get("impact", "minor")
        description = v.get("description", "")
        help_text = v.get("help", "")
        nodes = v.get("nodes", [])
        node_count = len(nodes)
        
        # Apply simplified score penalties:
        # Critical: -10, Serious: -5, Moderate: -3, Minor: -1
        if impact == "critical":
            score -= 10
        elif impact == "serious":
            score -= 5
        elif impact == "moderate":
            score -= 3
        else: # minor
            score -= 1
            
        # Determine category
        cat = _categorize_violation(rule_id)
        cat_violation_counts[cat] += 1
        
        # Update metrics
        metric_key = f"{cat}_issues_count" if cat in ("color_contrast", "heading_hierarchy", "keyboard_accessibility") else f"missing_{cat}_count"
        metrics[metric_key] += node_count
        metrics["total_violations"] += node_count
        
        # Map severity to Pydantic Finding severity
        if impact in ("critical", "serious"):
            severity = "critical"
        elif impact == "moderate":
            severity = "warning"
        else:
            severity = "info"
            
        # Build description with failing targets details
        failing_targets = []
        for node in nodes[:3]: # limit to 3 targets to keep response size reasonable
            target_selector = ", ".join(node.get("target", []))
            html_snippet = node.get("html", "")
            failure_msg = node.get("failureSummary", "")
            failing_targets.append(
                f"- Selector: `{target_selector}`\n  HTML: `{html_snippet}`\n  Issue: {failure_msg}"
            )
            
        desc_bullets = "\n".join(failing_targets)
        nodes_suffix = f"\n\nFailing elements (showing {len(failing_targets)} of {node_count}):\n{desc_bullets}" if nodes else ""
        finding_desc = f"{description}{nodes_suffix}"
        
        findings.append(Finding(
            id=f"a11y-{rule_id}",
            title=help_text,
            description=finding_desc,
            severity=severity,
            category="accessibility"
        ))
        
        # Add recommendation
        recommendations.append(f"Fix {help_text.lower()} issues: {description}")
        
    # Cap score at 0
    score = max(0, score)
    
    # Add pass findings for completely green categories
    friendly_names = {
        "alt_text": "Image Alt Text",
        "form_labels": "Form Labels",
        "aria_attributes": "ARIA Attributes",
        "color_contrast": "Color Contrast",
        "heading_hierarchy": "Heading Hierarchy",
        "keyboard_accessibility": "Keyboard Accessibility"
    }
    for cat, count in cat_violation_counts.items():
        if count == 0:
            findings.append(Finding(
                id=f"a11y-{cat.replace('_', '-')}-ok",
                title=f"{friendly_names[cat]} Check Passed",
                description=f"No violations detected for {friendly_names[cat].lower()}.",
                severity="pass",
                category="accessibility"
            ))
            
    recommendations = list(dict.fromkeys(recommendations))
    if not recommendations and score == 100:
        recommendations.append("No accessibility issues found! Keep up the good work.")
        
    return AuditResult(
        audit_type="accessibility",
        score=score,
        metrics=metrics,
        findings=findings,
        recommendations=recommendations
    )

def _generate_error_result(url: str, error_msg: str) -> AuditResult:
    return AuditResult(
        audit_type="accessibility",
        score=0.0,
        metrics={"total_violations": 0},
        findings=[
            Finding(
                id="a11y-audit-failed",
                title="Accessibility Audit Failed",
                description=f"The Playwright accessibility scanner encountered an error: {error_msg[:300]}",
                severity="critical",
                category="accessibility"
            )
        ],
        recommendations=["Ensure the website is accessible and Playwright is properly configured."]
    )
