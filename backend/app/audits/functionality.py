"""
Functionality Audit Module â€” Phase 2
===================================
Checks real-world usability of a website by verifying that key interactive
and structural elements work correctly.

Checks performed:
1. Homepage loads successfully (HTTP status < 400, content present)
2. Navigation links detected
3. Contact form / contact page link detected
4. Internal link extraction and concurrent status validation (broken link / 404 detection)
"""

from __future__ import annotations

import os
import logging
import re
import time
import asyncio
from typing import Any, Tuple
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from app.schemas.audit import AuditResult, Finding

logger = logging.getLogger("audit_tool.functionality")

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
            "Invalid PLAYWRIGHT_GOTO_TIMEOUT_MS=%r â€” using default %s",
            raw,
            DEFAULT_GOTO_TIMEOUT_MS,
        )
        return DEFAULT_GOTO_TIMEOUT_MS


def _goto_wait_until() -> str:
    value = os.environ.get("PLAYWRIGHT_GOTO_WAIT_UNTIL", DEFAULT_GOTO_WAIT_UNTIL).strip().lower()
    allowed = {"domcontentloaded", "load", "networkidle", "commit"}
    if value not in allowed:
        logger.warning(
            "Invalid PLAYWRIGHT_GOTO_WAIT_UNTIL=%r â€” using %s",
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
    if "timeout" in msg_lower:
        return "Execution Timeout", error_msg
    if "javascript" in msg_lower or "script" in msg_lower:
        return "JavaScript Execution Failure", error_msg
    return "Functionality Audit Failed", error_msg


def _generate_error_result(url: str, error_msg: str, *, title: str = "Functionality Audit Failed") -> AuditResult:
    trimmed = error_msg[:ERROR_DESCRIPTION_LIMIT]
    if url:
        trimmed = f"URL: {url}\n{trimmed}"

    return AuditResult(
        audit_type="functionality",
        score=0.0,
        metrics={
            "homepage_url": url,
            "homepage_http_status": None,
            "homepage_body_length_chars": 0,
            "navigation_links_found": 0,
            "navigation_links": [],
            "contact_form_on_page": False,
            "contact_page_link": None,
            "internal_links_total_found": 0,
            "internal_links_checked": 0,
            "broken_links": [],
            "broken_links_count": 0,
        },
        findings=[
            Finding(
                id="func-audit-failed",
                title=title,
                description=trimmed,
                severity="critical",
                category="functionality",
            )
        ],
        recommendations=["Ensure the website is online, public, and the URL is correct."],
    )


async def run_functionality_audit(url: str) -> AuditResult:
    
    """
    Run the Functionality audit (Phase 2) using Playwright.
    
    Checks that the homepage loads successfully, detects navigation elements
    and links, detects contact forms, and checks internal links for 404s.
    """
    goto_timeout_ms = _goto_timeout_ms()
    goto_wait_until = _goto_wait_until()
    page_settle_ms = _page_settle_ms()

    logger.info(
        "Starting Functionality audit for %s (goto_timeout=%sms, wait_until=%s, settle=%sms)",
        url,
        goto_timeout_ms,
        goto_wait_until,
        page_settle_ms,
    )

    headless_env = os.environ.get("PLAYWRIGHT_HEADLESS", "True")
    headless = headless_env.lower() in ("true", "1", "yes")

    from playwright.async_api import async_playwright

    started_at = time.perf_counter()
    browser = None
    response = None

    try:
        async with async_playwright() as p:
            try:
                browser = await p.chromium.launch(headless=headless, channel="chromium")
            except Exception as exc:
                detail = f"Failed to launch Chromium browser: {exc}"
                logger.exception(detail)
                title, _ = _classify_playwright_error(detail)
                return _generate_error_result(url, detail, title=title)

            context = await browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
            )
            page = await context.new_page()

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
                    "Navigation completed in %.2fs â€” status=%s, final_url=%s",
                    nav_duration,
                    status,
                    final_url,
                )

                if page_settle_ms > 0:
                    await page.wait_for_timeout(page_settle_ms)
                # Screenshot capture
                screenshot_path = None
                screenshot_filename = None
                try:
                    safe_name = re.sub(r"[^a-zA-Z0-9]", "_", urlparse(url).netloc)
                    from datetime import datetime
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"{safe_name}_{timestamp}.png"
                    base_dir = os.path.dirname(os.path.abspath(__file__))
                    screenshots_dir = os.path.abspath(os.path.join(base_dir, "..", "..", "screenshots"))
                    os.makedirs(screenshots_dir, exist_ok=True)
                    screenshot_path = os.path.join(screenshots_dir, filename)
                    screenshot_filename = filename
                    await page.screenshot(path=screenshot_path, full_page=True)
                    logger.info("Screenshot saved: %s", screenshot_path)
                except Exception as ss_err:
                    logger.warning("Screenshot capture failed (non-fatal): %s", ss_err)
                    screenshot_path = None
                    screenshot_filename = None

                html = await page.content()

            except Exception as exc:
                detail = str(exc).strip() or repr(exc)
                title, _ = _classify_playwright_error(detail)
                duration = time.perf_counter() - started_at
                enriched = (
                    f"{detail}\n\n"
                    f"Failure category: {title}\n"
                    f"Navigation settings: wait_until={goto_wait_until}, timeout={goto_timeout_ms}ms\n"
                    f"Elapsed: {duration:.1f}s"
                )
                if response is not None:
                    enriched += f"\nHTTP status: {response.status}"
                enriched += f"\nFinal URL: {page.url}"

                logger.error("Functionality audit failed after %.2fs â€” %s: %s", duration, title, detail)
                return _generate_error_result(url, enriched, title=title)
            finally:
                if browser:
                    await browser.close()

        # Perform the actual logic checks on the retrieved HTML content
        return await _analyze_functionality(html, status, url, screenshot_filename)

    except Exception as exc:
        import traceback
        
        print("\n========== FUNCTIONALITY ERROR ==========")
        print(traceback.format_exc())
        print("=========================================\n")
        
        duration = time.perf_counter() - started_at
        detail = str(exc).strip() or repr(exc)
        title, _ = _classify_playwright_error(detail)
        enriched = f"{detail}\n\nElapsed: {duration:.1f}s"
        logger.exception("Error running functionality audit for %s after %.2fs", url, duration)
        return _generate_error_result(url, enriched, title=title)


async def _analyze_functionality(html: str, http_status: int | str, url: str, screenshot_filename: str | None = None) -> AuditResult:
    findings: list[Finding] = []
    recommendations: list[str] = []
    metrics: dict[str, Any] = {}
    score = 100.0
    metrics["screenshot_path"] = screenshot_filename
    soup = BeautifulSoup(html, "html.parser")

    # 1. Homepage loads successfully check
    score, findings, recommendations, metrics = _check_homepage(
        url, html, http_status, score, findings, recommendations, metrics
    )

    # 2. Navigation Detection
    score, findings, recommendations, metrics = _check_navigation(
        soup, url, score, findings, recommendations, metrics
    )

    # 3. Contact Form Detection
    score, findings, recommendations, metrics = _check_contact_form(
        soup, url, score, findings, recommendations, metrics
    )

    # 4. Internal Link Validation
    score, findings, recommendations, metrics = await _check_internal_links(
        soup, url, score, findings, recommendations, metrics
    )

    return AuditResult(
        audit_type="functionality",
        score=round(max(0.0, min(100.0, score)), 1),
        metrics=metrics,
        findings=findings,
        recommendations=list(dict.fromkeys(recommendations)),
    )


def _check_homepage(
    url: str,
    html: str,
    http_status: int | str,
    score: float,
    findings: list[Finding],
    recommendations: list[str],
    metrics: dict[str, Any],
) -> tuple[float, list[Finding], list[str], dict[str, Any]]:
    metrics["homepage_url"] = url
    metrics["homepage_http_status"] = http_status

    if isinstance(http_status, int) and http_status >= 400:
        score -= 40
        findings.append(Finding(
            id="func-homepage-error",
            title=f"Homepage Returned HTTP {http_status}",
            description=f"The homepage at {url} returned HTTP {http_status}. This means the page does not exist or the server has an error.",
            severity="critical",
            category="functionality",
        ))
        recommendations.append(
            f"Investigate why the homepage returns HTTP {http_status} and restore it to a working state (HTTP 200)."
        )
    else:
        soup = BeautifulSoup(html, "html.parser")
        body_text = soup.get_text(strip=True)
        metrics["homepage_body_length_chars"] = len(body_text)

        if len(body_text) < 50:
            score -= 10
            findings.append(Finding(
                id="func-homepage-empty",
                title="Homepage Body Appears Empty",
                description=f"The homepage returned HTTP {http_status} but the visible text is only {len(body_text)} characters. The page may not be rendering correctly.",
                severity="warning",
                category="functionality",
            ))
            recommendations.append("Check that the homepage displays content correctly in a browser.")
        else:
            findings.append(Finding(
                id="func-homepage-ok",
                title="Homepage Loads Successfully",
                description=f"The homepage returned HTTP {http_status} and contains {len(body_text)} characters of visible text.",
                severity="pass",
                category="functionality",
            ))

    return score, findings, recommendations, metrics


def _check_navigation(
    soup: BeautifulSoup,
    base_url: str,
    score: float,
    findings: list[Finding],
    recommendations: list[str],
    metrics: dict[str, Any],
) -> tuple[float, list[Finding], list[str], dict[str, Any]]:
    nav_containers = (
        soup.find_all("nav")
        + soup.find_all(attrs={"role": "navigation"})
        + soup.find_all("header")
        + [
            tag for tag in soup.find_all(True)
            if any(
                "nav" in cls.lower() or "menu" in cls.lower()
                for cls in (tag.get("class") or [])
            )
        ]
    )

    nav_links: list[dict[str, str]] = []
    seen_hrefs: set[str] = set()

    for container in nav_containers:
        for a_tag in container.find_all("a", href=True):
            href = a_tag["href"].strip()
            if href.startswith(("#", "mailto:", "tel:", "javascript:")) or href.lower().startswith("javascript:"):
                continue
            absolute = urljoin(base_url, href)
            if absolute not in seen_hrefs:
                seen_hrefs.add(absolute)
                nav_links.append({
                    "text": a_tag.get_text(strip=True)[:60],
                    "href": absolute,
                })

    metrics["navigation_links_found"] = len(nav_links)
    metrics["navigation_links"] = nav_links[:20]

    if not nav_containers:
        score -= 15
        findings.append(Finding(
            id="func-nav-missing",
            title="No Navigation Element Detected",
            description="No <nav> tag, role='navigation', or element with a nav/menu class was found on the page.",
            severity="warning",
            category="functionality",
        ))
        recommendations.append("Add a <nav> element containing links to the site's main sections.")

    elif not nav_links:
        score -= 10
        findings.append(Finding(
            id="func-nav-no-links",
            title="Navigation Found but Contains No Links",
            description="A navigation container was found but contained no <a> links.",
            severity="warning",
            category="functionality",
        ))
        recommendations.append("Add links inside your navigation element (Home, About, Contact, etc.).")

    else:
        sample = ", ".join(lnk["text"] for lnk in nav_links[:3] if lnk["text"]) or "n/a"
        findings.append(Finding(
            id="func-nav-ok",
            title="Navigation Links Detected",
            description=f"Found {len(nav_links)} navigation link(s). Examples: {sample}",
            severity="pass",
            category="functionality",
        ))

    return score, findings, recommendations, metrics


def _check_contact_form(
    soup: BeautifulSoup,
    base_url: str,
    score: float,
    findings: list[Finding],
    recommendations: list[str],
    metrics: dict[str, Any],
) -> tuple[float, list[Finding], list[str], dict[str, Any]]:
    CONTACT_FIELD_RE = re.compile(
        r"email|message|contact|name|phone|subject|enquiry|inquiry",
        re.IGNORECASE,
    )

    contact_form_found = False
    for form in soup.find_all("form"):
        for field in form.find_all(["input", "textarea", "select"]):
            if field.get("type", "").lower() == "email":
                contact_form_found = True
                break
            for attr in ("name", "id", "placeholder", "aria-label"):
                if CONTACT_FIELD_RE.search(field.get(attr, "")):
                    contact_form_found = True
                    break
            if contact_form_found:
                break
        if contact_form_found:
            break

    metrics["contact_form_on_page"] = contact_form_found

    if contact_form_found:
        findings.append(Finding(
            id="func-contact-form-ok",
            title="Contact Form Detected",
            description="A contact form with email or message fields was found on this page.",
            severity="pass",
            category="functionality",
        ))
        metrics["contact_page_link"] = None
    else:
        CONTACT_LINK_RE = re.compile(
            r"contact|get.in.touch|reach.us|enquir|support|help",
            re.IGNORECASE,
        )

        contact_link: str | None = None
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"].strip()
            text = a_tag.get_text(strip=True)
            if CONTACT_LINK_RE.search(href) or CONTACT_LINK_RE.search(text):
                contact_link = urljoin(base_url, href)
                break

        metrics["contact_page_link"] = contact_link

        if contact_link:
            findings.append(Finding(
                id="func-contact-link-found",
                title="Contact Page Link Found",
                description=f"No contact form was found on this page, but a link to a contact page was detected: {contact_link}",
                severity="info",
                category="functionality",
            ))
        else:
            score -= 5
            findings.append(Finding(
                id="func-contact-missing",
                title="No Contact Form or Contact Link Found",
                description="Neither a contact form nor a link to a contact page was detected. Users may have difficulty reaching the site owner.",
                severity="warning",
                category="functionality",
            ))
            recommendations.append("Add a contact form or a clearly labelled link to a contact page.")

    return score, findings, recommendations, metrics


async def _check_internal_links(
    soup: BeautifulSoup,
    base_url: str,
    score: float,
    findings: list[Finding],
    recommendations: list[str],
    metrics: dict[str, Any],
) -> tuple[float, list[Finding], list[str], dict[str, Any]]:
    parsed_base = urlparse(base_url)
    base_domain = parsed_base.netloc.lower()
    base_url_normalized = parsed_base._replace(fragment="").geturl().rstrip("/")

    internal_urls: list[str] = []
    seen: set[str] = set()

    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"].strip()
        if href.startswith(("#", "mailto:", "tel:", "javascript:")) or href.lower().startswith("javascript:"):
            continue

        absolute = urljoin(base_url, href)
        parsed = urlparse(absolute)

        if parsed.scheme.lower() not in ("http", "https"):
            continue
        if parsed.netloc.lower() != base_domain:
            continue

        normalized = parsed._replace(fragment="").geturl()
        # Skip base URL itself
        if normalized.rstrip("/") == base_url_normalized:
            continue

        if normalized not in seen:
            seen.add(normalized)
            internal_urls.append(normalized)

    total_found = len(internal_urls)
    urls_to_check = internal_urls[:25]

    metrics["internal_links_total_found"] = total_found
    metrics["internal_links_checked"] = len(urls_to_check)

    broken_links: list[dict[str, Any]] = []

    if urls_to_check:
        async with httpx.AsyncClient() as client:
            tasks = [_check_url(client, u) for u in urls_to_check]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for r in results:
                if isinstance(r, dict):
                    broken_links.append(r)
                elif isinstance(r, Exception):
                    logger.warning("Link checking task raised an exception: %s", r)

    metrics["broken_links"] = broken_links
    metrics["broken_links_count"] = len(broken_links)

    if total_found == 0:
        findings.append(Finding(
            id="func-links-none",
            title="No Internal Links Found",
            description="No internal links were found on this page.",
            severity="info",
            category="functionality",
        ))
    elif broken_links:
        penalty = min(25, len(broken_links) * 5)
        score -= penalty

        broken_summary = "; ".join(
            f"{b['url']} ({b['status']})" for b in broken_links[:5]
        )
        if len(broken_links) > 5:
            broken_summary += f" â€¦ and {len(broken_links) - 5} more"

        findings.append(Finding(
            id="func-links-broken",
            title=f"Broken Internal Links Detected ({len(broken_links)} found)",
            description=(
                f"Checked {len(urls_to_check)} of {total_found} internal links; "
                f"{len(broken_links)} returned error status codes or failed to resolve. "
                f"Examples: {broken_summary}"
            ),
            severity="critical" if len(broken_links) >= 5 else "warning",
            category="functionality",
        ))
        recommendations.append("Remove broken internal links or fix the URLs causing 4xx/5xx responses.")
        recommendations.append("Fix 404 pages referenced in site navigation.")
    else:
        findings.append(Finding(
            id="func-links-ok",
            title="All Checked Internal Links Are Working",
            description=(
                f"Checked {len(urls_to_check)} of {total_found} internal link(s); "
                "all returned successful HTTP status codes (< 400)."
            ),
            severity="pass",
            category="functionality",
        ))

    return score, findings, recommendations, metrics


async def _check_url(client: httpx.AsyncClient, url: str) -> dict[str, Any] | None:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }
    try:
        # Use HEAD request as it is faster
        resp = await client.head(url, headers=headers, timeout=6.0, follow_redirects=True)
        # Fallback to GET for servers that block/fail on HEAD (returning 400 or 405)
        if resp.status_code in (400, 405):
            resp = await client.get(url, headers=headers, timeout=6.0, follow_redirects=True)

        if resp.status_code >= 400:
            return {"url": url, "status": f"HTTP {resp.status_code}"}
        return None
    except httpx.TimeoutException:
        return {"url": url, "status": "timeout"}
    except httpx.ConnectError:
        return {"url": url, "status": "connection_error"}
    except httpx.HTTPStatusError as exc:
        return {"url": url, "status": f"HTTP {exc.response.status_code}"}
    except httpx.RequestError as exc:
        return {"url": url, "status": "request_error", "detail": str(exc)[:80]}
    except Exception as exc:
        return {"url": url, "status": "error", "detail": str(exc)[:80]}
