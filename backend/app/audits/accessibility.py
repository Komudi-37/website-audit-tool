"""Accessibility audit engine using Playwright and axe-core."""
import os
import logging
import datetime
import time
import asyncio
import math
from typing import List, Tuple
from app.schemas.audit import AuditResult, Finding

logger = logging.getLogger("audit_tool.accessibility")

DEFAULT_GOTO_TIMEOUT_MS = 45_000
DEFAULT_GOTO_WAIT_UNTIL = "domcontentloaded"
DEFAULT_PAGE_SETTLE_MS = 1_000
ERROR_DESCRIPTION_LIMIT = 800


def _goto_timeout_ms() -> int:
    raw = os.environ.get("PLAYWRIGHT_GOTO_TIMEOUT_MS", str(DEFAULT_GOTO_TIMEOUT_MS))
    try:
        return max(5_000, int(raw))
    except ValueError:
        logger.warning(
            "Invalid PLAYWRIGHT_GOTO_TIMEOUT_MS=%r — using default %s",
            raw,
            DEFAULT_GOTO_TIMEOUT_MS,
        )
        return DEFAULT_GOTO_TIMEOUT_MS


def _goto_wait_until() -> str:
    value = os.environ.get("PLAYWRIGHT_GOTO_WAIT_UNTIL", DEFAULT_GOTO_WAIT_UNTIL).strip().lower()
    allowed = {"domcontentloaded", "load", "networkidle", "commit"}
    if value not in allowed:
        logger.warning(
            "Invalid PLAYWRIGHT_GOTO_WAIT_UNTIL=%r — using %s",
            value,
            DEFAULT_GOTO_WAIT_UNTIL,
        )
        return DEFAULT_GOTO_WAIT_UNTIL
    return value


def _page_settle_ms() -> int:
    raw = os.environ.get("PLAYWRIGHT_PAGE_SETTLE_MS", str(DEFAULT_PAGE_SETTLE_MS))
    try:
        return max(0, int(raw))
    except ValueError:
        return DEFAULT_PAGE_SETTLE_MS


def _classify_playwright_error(error_msg: str) -> Tuple[str, str]:
    msg_lower = error_msg.lower()

    if "timeout" in msg_lower and ("page.goto" in msg_lower or "navigation" in msg_lower or "navigating" in msg_lower):
        return "Navigation Timeout", error_msg
    if "net::err_" in msg_lower or "ns_error_" in msg_lower:
        return "Navigation Failure", error_msg
    if "browser" in msg_lower and ("launch" in msg_lower or "closed" in msg_lower):
        return "Browser Launch Failure", error_msg
    if "cloudflare" in msg_lower or "captcha" in msg_lower or "access denied" in msg_lower or "bot" in msg_lower:
        return "Access Blocked", error_msg
    if "axe" in msg_lower or "accessibility" in msg_lower:
        return "Axe Scan Failure", error_msg
    if "timeout" in msg_lower:
        return "Execution Timeout", error_msg
    if "javascript" in msg_lower or "script" in msg_lower:
        return "JavaScript Execution Failure", error_msg
    return "Accessibility Audit Failed", error_msg


async def run_accessibility_audit(url: str) -> AuditResult:
    """Run Accessibility audit using Playwright and axe-core."""
    goto_timeout_ms = _goto_timeout_ms()
    goto_wait_until = _goto_wait_until()
    page_settle_ms = _page_settle_ms()

    logger.info(
        "Starting Accessibility audit for %s (goto_timeout=%sms, wait_until=%s, settle=%sms)",
        url,
        goto_timeout_ms,
        goto_wait_until,
        page_settle_ms,
    )

    base_dir = os.path.dirname(os.path.abspath(__file__))
    screenshots_dir = os.path.abspath(os.path.join(base_dir, "..", "..", "screenshots"))
    os.makedirs(screenshots_dir, exist_ok=True)

    from app.core.playwright_manager import get_browser
    from axe_playwright_python.async_playwright import Axe

    started_at = time.perf_counter()
    response = None

    try:
        browser, context, page = await get_browser()
        page.set_default_navigation_timeout(goto_timeout_ms)
        page.set_default_timeout(goto_timeout_ms)

        try:
            nav_started = time.perf_counter()
            response = await page.goto(
                url,
                wait_until=goto_wait_until,
                timeout=goto_timeout_ms,
            )
            nav_duration = time.perf_counter() - nav_started
            status = response.status if response else "unknown"
            final_url = page.url
            logger.info(
                "Navigation completed in %.2fs — status=%s, final_url=%s",
                nav_duration,
                status,
                final_url,
            )

            if page_settle_ms > 0:
                await page.wait_for_timeout(page_settle_ms)

            axe_started = time.perf_counter()
            axe = Axe()
            axe_results = await axe.run(page)
            axe_duration = time.perf_counter() - axe_started
            logger.info("Axe scan completed in %.2fs", axe_duration)

            parsed_result = _parse_axe_report(axe_results.response, url)

        except Exception as exc:
            detail = str(exc).strip() or repr(exc)
            title, _ = _classify_playwright_error(detail)
            duration = time.perf_counter() - started_at

            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_filename = f"a11y_error_{timestamp}.png"
            screenshot_path = os.path.join(screenshots_dir, screenshot_filename)
            try:
                if not page.is_closed():
                    await page.screenshot(path=screenshot_path)
                    logger.error("Saved failure screenshot to %s", screenshot_path)
            except Exception as screenshot_err:
                logger.warning("Could not take screenshot on failure: %s", screenshot_err)

            enriched = (
                f"{detail}\n\n"
                f"Failure category: {title}\n"
                f"Navigation settings: wait_until={goto_wait_until}, timeout={goto_timeout_ms}ms\n"
                f"Elapsed: {duration:.1f}s"
            )
            if response is not None:
                enriched += f"\nHTTP status: {response.status}"
            enriched += f"\nFinal URL: {page.url}"

            logger.error("Accessibility audit failed after %.2fs — %s: %s", duration, title, detail)
            return _generate_error_result(url, enriched, title=title)
        finally:
            try:
                if not page.is_closed():
                    await page.close()
            except Exception:
                pass
            try:
                await context.close()
            except Exception:
                pass
            # Note: browser itself is a shared/reused instance (see playwright_manager.py) —
            # do NOT close it here, only close_browser() at app shutdown should do that.

        total_duration = time.perf_counter() - started_at
        logger.info("Accessibility audit succeeded for %s in %.2fs", url, total_duration)
        return parsed_result

    except Exception as exc:
        duration = time.perf_counter() - started_at
        detail = str(exc).strip() or repr(exc)
        title, _ = _classify_playwright_error(detail)
        enriched = f"{detail}\n\nElapsed: {duration:.1f}s"
        logger.exception("Error running accessibility audit for %s after %.2fs", url, duration)
        return _generate_error_result(url, enriched, title=title)


def _categorize_violation(rule_id: str) -> str:
    rule_id = rule_id.lower()

    if rule_id in ("image-alt", "image-redundant-alt", "input-image-alt", "area-alt"):
        return "alt_text"

    if rule_id in ("label", "label-title-only", "form-field-multiple-labels", "aria-label", "select-name", "input-button-name"):
        return "form_labels"

    if rule_id.startswith("aria-") or "aria" in rule_id:
        return "aria_attributes"

    if "contrast" in rule_id or rule_id == "color-contrast":
        return "color_contrast"

    if rule_id in ("heading-order", "page-has-heading-one", "p-as-heading") or "heading" in rule_id:
        return "heading_hierarchy"

    if rule_id in ("bypass", "focusable-content", "tabindex", "accesskeys", "scrollable-region-focusable", "keyboard-navigation", "focus-visible", "duplicate-id-active"):
        return "keyboard_accessibility"

    return "keyboard_accessibility"


def _parse_axe_report(data: dict, url: str) -> AuditResult:
    violations = data.get("violations", [])
    passes = data.get("passes", [])

    score = 100
    findings: List[Finding] = []
    recommendations: List[str] = []

    metrics = {
        "missing_alt_text_count": 0,
        "missing_form_labels_count": 0,
        "missing_aria_attributes_count": 0,
        "color_contrast_issues_count": 0,
        "heading_hierarchy_issues_count": 0,
        "keyboard_accessibility_issues_count": 0,
        "total_violations": 0,
        "rules_passed": len(passes),
    }

    cat_violation_counts = {
        "alt_text": 0,
        "form_labels": 0,
        "aria_attributes": 0,
        "color_contrast": 0,
        "heading_hierarchy": 0,
        "keyboard_accessibility": 0,
    }

    for v in violations:
        rule_id = v.get("id", "")
        impact = v.get("impact", "minor")
        description = v.get("description", "")
        help_text = v.get("help", "")
        nodes = v.get("nodes", [])
        node_count = len(nodes)

        impact_weights = {"critical": 7, "serious": 4, "moderate": 2, "minor": 1}
        base_weight = impact_weights.get(impact, 1)
        
        # Scale by affected elements using sqrt to avoid linear explosion,
        # but ensure even single-node violations still count meaningfully
        node_multiplier = 1 + math.sqrt(max(0, node_count - 1)) * 0.5
        deduction = min(base_weight * node_multiplier, 12)  # cap per-violation-type deduction at 12
        
        score -= deduction

        cat = _categorize_violation(rule_id)
        cat_violation_counts[cat] += 1

        metric_key = f"{cat}_issues_count" if cat in ("color_contrast", "heading_hierarchy", "keyboard_accessibility") else f"missing_{cat}_count"
        metrics[metric_key] += node_count
        metrics["total_violations"] += node_count

        if impact in ("critical", "serious"):
            severity = "critical"
        elif impact == "moderate":
            severity = "warning"
        else:
            severity = "info"

        failing_targets = []
        for node in nodes[:3]:
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
            category="accessibility",
        ))

        recommendations.append(f"Fix {help_text.lower()} issues: {description}")

    # Apply overall safety cap: total deduction capped at 80 (score never below 20)
    score = max(20, score)

    friendly_names = {
        "alt_text": "Image Alt Text",
        "form_labels": "Form Labels",
        "aria_attributes": "ARIA Attributes",
        "color_contrast": "Color Contrast",
        "heading_hierarchy": "Heading Hierarchy",
        "keyboard_accessibility": "Keyboard Accessibility",
    }
    for cat, count in cat_violation_counts.items():
        if count == 0:
            findings.append(Finding(
                id=f"a11y-{cat.replace('_', '-')}-ok",
                title=f"{friendly_names[cat]} Check Passed",
                description=f"No violations detected for {friendly_names[cat].lower()}.",
                severity="pass",
                category="accessibility",
            ))

    recommendations = list(dict.fromkeys(recommendations))
    if not recommendations and score == 100:
        recommendations.append("No accessibility issues found! Keep up the good work.")

    return AuditResult(
        audit_type="accessibility",
        score=score,
        metrics=metrics,
        findings=findings,
        recommendations=recommendations,
    )


def _generate_error_result(url: str, error_msg: str, *, title: str = "Accessibility Audit Failed") -> AuditResult:
    trimmed = error_msg[:ERROR_DESCRIPTION_LIMIT]
    if url:
        trimmed = f"URL: {url}\n{trimmed}"

    return AuditResult(
        audit_type="accessibility",
        score=0.0,
        metrics={"total_violations": 0},
        findings=[
            Finding(
                id="a11y-audit-failed",
                title=title,
                description=trimmed,
                severity="critical",
                category="accessibility",
            )
        ],
        recommendations=["Ensure the website is accessible and Playwright is properly configured."],
    )

