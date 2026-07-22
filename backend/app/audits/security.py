"""Security audit engine — Phase 6.

Checks:
  1. HTTPS enforcement
  2. HTTP → HTTPS redirect
  3. SSL/TLS certificate validity
  4. Strict-Transport-Security (HSTS)
  5. Content-Security-Policy (CSP) — including weak directives
  6. X-Frame-Options
  7. X-Content-Type-Options
  8. Referrer-Policy
  9. Permissions-Policy
  10. Missing headers summary
"""

import logging
import time
from typing import List, Dict, Any, Tuple
from urllib.parse import urlparse

import requests

from app.schemas.audit import AuditResult, Finding
from app.core.config import settings

logger = logging.getLogger("audit_tool.security")

def _call_ssl_labs_api(hostname: str) -> Dict[str, Any]:
    """
    Query SSL Labs API for SSL/TLS information.
    """

    url = (
        f"{settings.SSL_LABS_BASE_URL}/analyze"
        f"?host={hostname}"
        f"&publish=off"
        f"&fromCache=on"
        f"&all=done"
    )

    for _ in range(6):

        response = requests.get(url, timeout=120)
        response.raise_for_status()

        data = response.json()

        status = data.get("status")
        if status in ("READY", "READY_WITH_WARNINGS"):
            return data
        if status =="ERROR":
            raise RuntimeError("SSL Labs scan failed.")
        
        time.sleep(5)

    raise RuntimeError(
        f"SSL Labs scan did not complete. Status={status}"
    )
    
def _call_mozilla_observatory(url: str) -> Dict[str, Any]:
    """
    Query Mozilla Observatory API.

    Returns an empty dict if the API is unavailable so the
    security audit can continue.
    """

    endpoint = (
        f"{settings.MOZILLA_OBSERVATORY_BASE_URL}/analyze"
    )

    try:
        response = requests.post(
            endpoint,
            json={
                "host": urlparse(url).hostname,
                "rescan": False,
                "hidden": True,
            },
            timeout=120,
        )

        response.raise_for_status()

        return response.json()

    except requests.RequestException as e:
        logger.warning(
            f"Mozilla Observatory unavailable: {e}"
        )
        return {}


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run_security_audit(url: str) -> AuditResult:
    """Run security audit against a given URL."""
    logger.info(f"Starting security audit for {url}")

    try:
        parsed = urlparse(url)
        hostname = parsed.hostname or ""

        # Fetch the page to get response headers
        response = requests.get(
            url,
            timeout=10,
            allow_redirects=True,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            },
        )
        headers = {k.lower(): v for k, v in response.headers.items()}
        observatory = _call_mozilla_observatory(url)

        # Run all checks
        score = 100
        all_findings: List[Finding] = []
        all_recommendations: List[str] = []
        metrics: Dict[str, Any] = {
             "mozilla_grade": observatory.get("grade"),
             "mozilla_score": observatory.get("score"),
        }
        grade = observatory.get("grade")
        score_from_api = observatory.get("score")
        if grade:
            if grade in("A+" , "A"):
                severity = "pass"
            elif grade == "B":
                severity= "info"
            else:
                severity = "warning"
            all_findings.append(
                 Finding(
            id="sec-mozilla-grade",
            title=f"Mozilla Observatory Grade: {grade}",
            description=f"Mozilla Observatory assigned this website a security grade of {grade}.",
            severity=severity,
            category="security",
        )
            )
                 
        checks = [
            _check_https(url, parsed),
            _check_http_redirect(parsed),
            _check_ssl_tls(hostname),
            _check_hsts(headers),
            _check_csp(headers),
            _check_x_frame_options(headers),
            _check_x_content_type_options(headers),
            _check_referrer_policy(headers),
            _check_permissions_policy(headers),
        ]

        for findings, penalty, recs, check_metrics in checks:
            all_findings.extend(findings)
            score -= penalty
            all_recommendations.extend(recs)
            metrics.update(check_metrics)

        # Missing headers summary (informational)
        missing_findings, _, missing_recs, missing_metrics = _check_missing_headers(metrics)
        all_findings.extend(missing_findings)
        all_recommendations.extend(missing_recs)
        metrics.update(missing_metrics)
        
        if isinstance(score_from_api, (int, float)):
            score = round((score + score_from_api) / 2)
        score = max(0, score)
        all_recommendations = list(dict.fromkeys(all_recommendations))

        return AuditResult(
            audit_type="security",
            score=score,
            metrics=metrics,
            findings=all_findings,
            recommendations=all_recommendations,
        )

    except requests.RequestException as e:
        logger.exception(f"Error fetching URL {url} for security audit")
        return _generate_error_result(url, f"Failed to fetch URL: {str(e)}")
    except Exception as e:
        logger.exception(f"Error running security audit for {url}")
        return _generate_error_result(url, str(e))


# ---------------------------------------------------------------------------
# Check 1: HTTPS
# ---------------------------------------------------------------------------

def _check_https(url: str, parsed) -> Tuple[List[Finding], int, List[str], Dict[str, Any]]:
    findings: List[Finding] = []
    recommendations: List[str] = []
    penalty = 0
    is_https = parsed.scheme == "https"

    if is_https:
        findings.append(Finding(
            id="sec-https-ok",
            title="HTTPS Enabled",
            description="The site is served over HTTPS.",
            severity="pass",
            category="security",
        ))
    else:
        # Check if HTTPS version exists
        https_url = url.replace("http://", "https://", 1)
        try:
            requests.head(https_url, timeout=5, allow_redirects=False)
            # HTTPS exists but not used
            penalty = 15
            findings.append(Finding(
                id="sec-https-available",
                title="HTTPS Available but Not Used",
                description="The site is accessed over HTTP but an HTTPS version is available. The site should enforce HTTPS.",
                severity="critical",
                category="security",
            ))
            recommendations.append("Redirect all HTTP traffic to HTTPS.")
        except Exception:
            penalty = 20
            findings.append(Finding(
                id="sec-https-missing",
                title="HTTPS Not Available",
                description="The site does not appear to support HTTPS. All modern sites should use HTTPS to encrypt data in transit.",
                severity="critical",
                category="security",
            ))
            recommendations.append("Configure HTTPS with a valid SSL/TLS certificate (e.g., via Let's Encrypt).")

    return findings, penalty, recommendations, {"is_https": is_https}


# ---------------------------------------------------------------------------
# Check 2: HTTP → HTTPS redirect
# ---------------------------------------------------------------------------

def _check_http_redirect(parsed) -> Tuple[List[Finding], int, List[str], Dict[str, Any]]:
    """If the site has HTTPS, verify that the HTTP version redirects to HTTPS."""
    findings: List[Finding] = []
    recommendations: List[str] = []
    penalty = 0
    metrics: Dict[str, Any] = {"http_redirects_to_https": None}

    # Only meaningful if the canonical URL is HTTPS
    if parsed.scheme != "https":
        return findings, penalty, recommendations, metrics

    http_url = f"http://{parsed.hostname}" + (f":{parsed.port}" if parsed.port and parsed.port != 443 else "") + (parsed.path or "/")

    try:
        resp = requests.head(http_url, timeout=5, allow_redirects=True)
        final_url = resp.url
        if urlparse(final_url).scheme == "https":
            metrics["http_redirects_to_https"] = True
            findings.append(Finding(
                id="sec-http-redirect-ok",
                title="HTTP → HTTPS Redirect Active",
                description=f"HTTP requests are automatically redirected to HTTPS ({final_url}).",
                severity="pass",
                category="security",
            ))
        else:
            metrics["http_redirects_to_https"] = False
            penalty = 5
            findings.append(Finding(
                id="sec-http-redirect-missing",
                title="HTTP Does Not Redirect to HTTPS",
                description="The HTTP version of the site does not automatically redirect to HTTPS. Users accessing the site via HTTP will not be upgraded to a secure connection.",
                severity="warning",
                category="security",
            ))
            recommendations.append("Configure the web server to redirect all HTTP requests (port 80) to HTTPS (port 443).")
    except Exception:
        # Cannot reach HTTP endpoint — may be intentionally disabled; not penalized
        metrics["http_redirects_to_https"] = None
        findings.append(Finding(
            id="sec-http-redirect-skip",
            title="HTTP Redirect Check Skipped",
            description="Could not connect to the HTTP version of the site to verify redirect behavior.",
            severity="info",
            category="security",
        ))

    return findings, penalty, recommendations, metrics

def _check_ssl_tls(hostname: str):

    findings = []
    recommendations = []
    recommendations.append(
    "Run regular SSL Labs scans to monitor TLS configuration."
    )
    penalty = 0

    metrics = {
        "ssl_valid": False,
        "ssl_grade": None,
        "ssl_protocol": None,
        "ssl_expiry": None,
        "ssl_days_remaining": None,
    }

    if not hostname:
        return findings, penalty, recommendations, metrics

    try:

        report = _call_ssl_labs_api(hostname)

        endpoint = report["endpoints"][0]

        details = endpoint["details"]

        metrics["ssl_grade"] = endpoint.get("grade")
        grade = endpoint.get("grade")
        if grade in ("C", "D", "E", "F", "T", "M"):
            penalty += 15
            findings.append( Finding(
                id="sec-ssl-grade",
                title=f"Weak SSL Grade ({grade})",
                description=f"SSL Labs assigned a security grade of {grade}.",
                severity="warning",
                category="security",
            ))
            recommendations.append( "Improve TLS configuration to achieve at least an A grade.")
            
        protocols = details.get("protocols", [])

        metrics["ssl_protocol"] = [p.get("name") for p in protocols]

        cert = details.get("cert", {})

        metrics["ssl_expiry"] = cert.get("notAfter")

        metrics["ssl_days_remaining"] = cert.get("daysUntilExpiration")

        metrics["ssl_valid"] = endpoint.get("grade") not in (
            None,
            "T",
            "M",
        )

        days = cert.get("daysUntilExpiration")

        if days is None:

            findings.append(
                Finding(
                    id="sec-ssl-unknown",
                    title="SSL Information Unavailable",
                    description="SSL Labs did not return certificate expiry.",
                    severity="info",
                    category="security",
                )
            )

        elif days <= 0:

            penalty = 25

            findings.append(
                Finding(
                    id="sec-ssl-expired",
                    title="SSL Certificate Expired",
                    description="The SSL certificate has expired.",
                    severity="critical",
                    category="security",
                )
            )

            recommendations.append(
                "Renew the SSL certificate immediately."
            )

        elif days <= 30:

            penalty = 5

            findings.append(
                Finding(
                    id="sec-ssl-expiring",
                    title="SSL Certificate Expiring Soon",
                    description=f"Certificate expires in {days} days.",
                    severity="warning",
                    category="security",
                )
            )

            recommendations.append(
                "Renew the SSL certificate."
            )

        else:

            findings.append(
                Finding(
                    id="sec-ssl-valid",
                    title="SSL Certificate Valid",
                    description=f"Certificate valid for {days} more days.",
                    severity="pass",
                    category="security",
                )
            )

    except Exception as exc:

        penalty = 20

        findings.append(
            Finding(
                id="sec-ssl-error",
                title="SSL Scan Failed",
                description=str(exc),
                severity="warning",
                category="security",
            )
        )

    return findings, penalty, recommendations, metrics


# ---------------------------------------------------------------------------
# Check 4: HSTS
# ---------------------------------------------------------------------------

def _check_hsts(headers: Dict[str, str]) -> Tuple[List[Finding], int, List[str], Dict[str, Any]]:
    findings: List[Finding] = []
    recommendations: List[str] = []
    penalty = 0
    metrics: Dict[str, Any] = {
        "hsts_present": False,
        "hsts_max_age": None,
        "hsts_include_subdomains": False,
    }

    hsts_value = headers.get("strict-transport-security")
    if not hsts_value:
        penalty = 15
        metrics["hsts_present"] = False
        findings.append(Finding(
            id="sec-hsts-missing",
            title="HSTS Header Missing",
            description="The Strict-Transport-Security header is not set. This allows downgrade attacks from HTTPS to HTTP.",
            severity="critical",
            category="security",
        ))
        recommendations.append("Add the header: Strict-Transport-Security: max-age=31536000; includeSubDomains")
        return findings, penalty, recommendations, metrics

    metrics["hsts_present"] = True

    # Parse max-age
    max_age = None
    include_sub = False
    for part in hsts_value.split(";"):
        part = part.strip().lower()
        if part.startswith("max-age="):
            try:
                max_age = int(part.split("=", 1)[1])
            except ValueError:
                pass
        elif part == "includesubdomains":
            include_sub = True

    metrics["hsts_max_age"] = max_age
    metrics["hsts_include_subdomains"] = include_sub

    if max_age is not None and max_age < 31536000:
        penalty = 5
        findings.append(Finding(
            id="sec-hsts-weak",
            title="HSTS max-age Too Short",
            description=f"HSTS max-age is {max_age} seconds ({max_age // 86400} days). Recommended minimum is 31536000 (1 year).",
            severity="warning",
            category="security",
        ))
        recommendations.append("Increase the HSTS max-age to at least 31536000 seconds (1 year).")
    elif max_age is None:
        penalty = 10
        findings.append(Finding(
            id="sec-hsts-no-maxage",
            title="HSTS Missing max-age Directive",
            description=f"The HSTS header is present but missing a valid max-age directive: '{hsts_value}'.",
            severity="warning",
            category="security",
        ))
        recommendations.append("Include a max-age directive in the HSTS header.")
    else:
        findings.append(Finding(
            id="sec-hsts-ok",
            title="HSTS Header Configured",
            description=f"HSTS is active with max-age={max_age} ({max_age // 86400} days)"
                        f"{', includeSubDomains' if include_sub else ''}.",
            severity="pass",
            category="security",
        ))

    return findings, penalty, recommendations, metrics


# ---------------------------------------------------------------------------
# Check 5: Content-Security-Policy
# ---------------------------------------------------------------------------

_UNSAFE_CSP_DIRECTIVES = {
    "'unsafe-inline'": {
        "label": "unsafe-inline",
        "desc": "Allows inline scripts/styles, which opens the door to XSS attacks.",
        "rec": "Remove 'unsafe-inline' from your CSP and use nonces or hashes for inline scripts.",
    },
    "'unsafe-eval'": {
        "label": "unsafe-eval",
        "desc": "Allows eval() and similar dynamic code execution, increasing XSS risk.",
        "rec": "Remove 'unsafe-eval' from your CSP and refactor code that relies on eval().",
    },
}


def _check_csp(headers: Dict[str, str]) -> Tuple[List[Finding], int, List[str], Dict[str, Any]]:
    findings: List[Finding] = []
    recommendations: List[str] = []
    penalty = 0
    metrics: Dict[str, Any] = {
        "csp_present": False,
        "csp_value": None,
    }

    csp_value = headers.get("content-security-policy")
    if not csp_value:
        penalty = 15
        findings.append(Finding(
            id="sec-csp-missing",
            title="Content-Security-Policy Header Missing",
            description="No CSP header is set. A Content-Security-Policy helps prevent XSS, clickjacking, and data injection attacks.",
            severity="critical",
            category="security",
        ))
        recommendations.append("Add a Content-Security-Policy header with strict directives.")
        return findings, penalty, recommendations, metrics

    metrics["csp_present"] = True
    metrics["csp_value"] = csp_value

    csp_lower = csp_value.lower()
    has_weakness = False

    # Check for unsafe-inline
    if "'unsafe-inline'" in csp_lower:
        has_weakness = True
        penalty += 5
        info = _UNSAFE_CSP_DIRECTIVES["'unsafe-inline'"]
        findings.append(Finding(
            id="sec-csp-unsafe-inline",
            title=f"CSP Contains '{info['label']}'",
            description=info["desc"],
            severity="warning",
            category="security",
        ))
        recommendations.append(info["rec"])

    # Check for unsafe-eval
    if "'unsafe-eval'" in csp_lower:
        has_weakness = True
        penalty += 5
        info = _UNSAFE_CSP_DIRECTIVES["'unsafe-eval'"]
        findings.append(Finding(
            id="sec-csp-unsafe-eval",
            title=f"CSP Contains '{info['label']}'",
            description=info["desc"],
            severity="warning",
            category="security",
        ))
        recommendations.append(info["rec"])

    # Check for wildcard sources — look for standalone * in directive values
    # e.g. "default-src *" or "script-src *" but not "*.example.com"
    directives = csp_value.split(";")
    has_wildcard = False
    for directive in directives:
        parts = directive.strip().split()
        if len(parts) >= 2:
            for source in parts[1:]:
                if source.strip() == "*":
                    has_wildcard = True
                    break
        if has_wildcard:
            break

    if has_wildcard:
        has_weakness = True
        penalty += 5
        findings.append(Finding(
            id="sec-csp-wildcard",
            title="CSP Contains Wildcard Source (*)",
            description="The CSP includes a wildcard (*) source, which effectively disables the protection for that directive by allowing content from any origin.",
            severity="warning",
            category="security",
        ))
        recommendations.append("Replace wildcard (*) sources in your CSP with specific, trusted domains.")

    if not has_weakness:
        findings.append(Finding(
            id="sec-csp-ok",
            title="Content-Security-Policy Configured",
            description=f"CSP header is present and does not contain known weak directives.",
            severity="pass",
            category="security",
        ))

    return findings, penalty, recommendations, metrics


# ---------------------------------------------------------------------------
# Check 6: X-Frame-Options
# ---------------------------------------------------------------------------

def _check_x_frame_options(headers: Dict[str, str]) -> Tuple[List[Finding], int, List[str], Dict[str, Any]]:
    findings: List[Finding] = []
    recommendations: List[str] = []
    penalty = 0
    value = headers.get("x-frame-options")
    metrics: Dict[str, Any] = {
        "x_frame_options_present": value is not None,
        "x_frame_options_value": value,
    }

    if not value:
        penalty = 10
        findings.append(Finding(
            id="sec-xfo-missing",
            title="X-Frame-Options Header Missing",
            description="The X-Frame-Options header is not set. This leaves the site vulnerable to clickjacking attacks.",
            severity="warning",
            category="security",
        ))
        recommendations.append("Add the header: X-Frame-Options: DENY (or SAMEORIGIN if framing is needed).")
    elif value.upper() in ("DENY", "SAMEORIGIN"):
        findings.append(Finding(
            id="sec-xfo-ok",
            title="X-Frame-Options Header Set",
            description=f"X-Frame-Options is set to '{value.upper()}', protecting against clickjacking.",
            severity="pass",
            category="security",
        ))
    else:
        penalty = 5
        findings.append(Finding(
            id="sec-xfo-weak",
            title="X-Frame-Options Has Unusual Value",
            description=f"X-Frame-Options is set to '{value}'. Expected values are DENY or SAMEORIGIN.",
            severity="warning",
            category="security",
        ))
        recommendations.append("Set X-Frame-Options to DENY or SAMEORIGIN.")

    return findings, penalty, recommendations, metrics


# ---------------------------------------------------------------------------
# Check 7: X-Content-Type-Options
# ---------------------------------------------------------------------------

def _check_x_content_type_options(headers: Dict[str, str]) -> Tuple[List[Finding], int, List[str], Dict[str, Any]]:
    findings: List[Finding] = []
    recommendations: List[str] = []
    penalty = 0
    value = headers.get("x-content-type-options")
    metrics: Dict[str, Any] = {
        "x_content_type_options_present": value is not None,
    }

    if not value:
        penalty = 10
        findings.append(Finding(
            id="sec-xcto-missing",
            title="X-Content-Type-Options Header Missing",
            description="The X-Content-Type-Options header is not set. Without it, browsers may MIME-sniff responses, potentially leading to XSS.",
            severity="warning",
            category="security",
        ))
        recommendations.append("Add the header: X-Content-Type-Options: nosniff")
    elif value.lower() == "nosniff":
        findings.append(Finding(
            id="sec-xcto-ok",
            title="X-Content-Type-Options Set",
            description="X-Content-Type-Options is set to 'nosniff', preventing MIME-type sniffing.",
            severity="pass",
            category="security",
        ))
    else:
        penalty = 5
        findings.append(Finding(
            id="sec-xcto-weak",
            title="X-Content-Type-Options Has Unexpected Value",
            description=f"X-Content-Type-Options is set to '{value}'. Expected value is 'nosniff'.",
            severity="warning",
            category="security",
        ))
        recommendations.append("Set X-Content-Type-Options to 'nosniff'.")

    return findings, penalty, recommendations, metrics


# ---------------------------------------------------------------------------
# Check 8: Referrer-Policy
# ---------------------------------------------------------------------------

_SAFE_REFERRER_POLICIES = {
    "no-referrer",
    "no-referrer-when-downgrade",
    "origin",
    "origin-when-cross-origin",
    "same-origin",
    "strict-origin",
    "strict-origin-when-cross-origin",
}


def _check_referrer_policy(headers: Dict[str, str]) -> Tuple[List[Finding], int, List[str], Dict[str, Any]]:
    findings: List[Finding] = []
    recommendations: List[str] = []
    penalty = 0
    value = headers.get("referrer-policy")
    metrics: Dict[str, Any] = {
        "referrer_policy_present": value is not None,
        "referrer_policy_value": value,
    }

    if not value:
        penalty = 5
        findings.append(Finding(
            id="sec-referrer-missing",
            title="Referrer-Policy Header Missing",
            description="The Referrer-Policy header is not set. This may leak sensitive URL information to third-party sites.",
            severity="warning",
            category="security",
        ))
        recommendations.append("Add the header: Referrer-Policy: strict-origin-when-cross-origin")
    elif value.lower().strip() in _SAFE_REFERRER_POLICIES:
        findings.append(Finding(
            id="sec-referrer-ok",
            title="Referrer-Policy Header Set",
            description=f"Referrer-Policy is set to '{value}'.",
            severity="pass",
            category="security",
        ))
    elif value.lower().strip() == "unsafe-url":
        penalty = 5
        findings.append(Finding(
            id="sec-referrer-unsafe",
            title="Referrer-Policy Set to 'unsafe-url'",
            description="The Referrer-Policy is set to 'unsafe-url', which sends the full URL as referrer to all origins including insecure ones.",
            severity="warning",
            category="security",
        ))
        recommendations.append("Change Referrer-Policy to 'strict-origin-when-cross-origin' or 'no-referrer'.")
    else:
        findings.append(Finding(
            id="sec-referrer-ok",
            title="Referrer-Policy Header Set",
            description=f"Referrer-Policy is set to '{value}'.",
            severity="pass",
            category="security",
        ))

    return findings, penalty, recommendations, metrics


# ---------------------------------------------------------------------------
# Check 9: Permissions-Policy
# ---------------------------------------------------------------------------

def _check_permissions_policy(headers: Dict[str, str]) -> Tuple[List[Finding], int, List[str], Dict[str, Any]]:
    findings: List[Finding] = []
    recommendations: List[str] = []
    penalty = 0
    value = headers.get("permissions-policy")
    metrics: Dict[str, Any] = {
        "permissions_policy_present": value is not None,
        "permissions_policy_value": value,
    }

    if not value:
        penalty = 5
        findings.append(Finding(
            id="sec-permpolicy-missing",
            title="Permissions-Policy Header Missing",
            description="The Permissions-Policy header is not set. This header restricts access to browser features like camera, microphone, and geolocation.",
            severity="warning",
            category="security",
        ))
        recommendations.append("Add a Permissions-Policy header to restrict browser feature access (e.g., camera=(), microphone=(), geolocation=()).")
    else:
        findings.append(Finding(
            id="sec-permpolicy-ok",
            title="Permissions-Policy Header Set",
            description=f"Permissions-Policy is configured: {value[:100]}{'...' if len(value) > 100 else ''}.",
            severity="pass",
            category="security",
        ))

    return findings, penalty, recommendations, metrics


# ---------------------------------------------------------------------------
# Check 10: Missing headers summary (informational)
# ---------------------------------------------------------------------------

_HEADER_CHECKS = [
    ("hsts_present", "Strict-Transport-Security"),
    ("csp_present", "Content-Security-Policy"),
    ("x_frame_options_present", "X-Frame-Options"),
    ("x_content_type_options_present", "X-Content-Type-Options"),
    ("referrer_policy_present", "Referrer-Policy"),
    ("permissions_policy_present", "Permissions-Policy"),
]


def _check_missing_headers(metrics: Dict[str, Any]) -> Tuple[List[Finding], int, List[str], Dict[str, Any]]:
    missing: List[str] = []
    for key, header_name in _HEADER_CHECKS:
        if not metrics.get(key, False):
            missing.append(header_name)

    total_expected = len(_HEADER_CHECKS)
    total_present = total_expected - len(missing)

    summary_metrics = {
        "total_headers_present": total_present,
        "total_headers_expected": total_expected,
        "missing_headers": missing,
    }

    findings: List[Finding] = []
    if missing:
        findings.append(Finding(
            id="sec-headers-summary",
            title=f"{len(missing)} Security Header(s) Missing",
            description=f"Missing headers: {', '.join(missing)}. "
                        f"{total_present}/{total_expected} recommended security headers are present.",
            severity="info",
            category="security",
        ))

    return findings, 0, [], summary_metrics


# ---------------------------------------------------------------------------
# Error fallback
# ---------------------------------------------------------------------------

def _generate_error_result(url: str, error_msg: str) -> AuditResult:
    return AuditResult(
        audit_type="security",
        score=0,
        metrics={},
        findings=[
            Finding(
                id="sec-error",
                title="Security Audit Failed",
                description=f"The security scanner encountered an error: {error_msg[:300]}",
                severity="critical",
                category="security",
            )
        ],
        recommendations=["Ensure the URL is publicly accessible and try again."],
    )
