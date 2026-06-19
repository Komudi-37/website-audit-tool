import logging
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any
from app.schemas.audit import AuditResult, Finding

logger = logging.getLogger("audit_tool.seo")

def run_seo_audit(url: str) -> AuditResult:
    """Run basic SEO audit against a given URL."""
    logger.info(f"Starting SEO audit for {url}")
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        return _analyze_seo(soup, url)

    except requests.RequestException as e:
        logger.exception(f"Error fetching URL {url} for SEO audit")
        return _generate_error_result(url, f"Failed to fetch URL: {str(e)}")
    except Exception as e:
        logger.exception(f"Error running SEO audit for {url}")
        return _generate_error_result(url, str(e))

def _analyze_seo(soup: BeautifulSoup, url: str) -> AuditResult:
    findings: List[Finding] = []
    recommendations: List[str] = []
    score = 100
    metrics: Dict[str, Any] = {}

    # 1. Check Title
    title_tag = soup.title
    if not title_tag or not title_tag.string:
        score -= 20
        findings.append(Finding(
            id="seo-title-missing",
            title="Missing Title Tag",
            description="The page is missing a <title> tag or it is empty.",
            severity="critical",
            category="seo"
        ))
        recommendations.append("Add a descriptive <title> tag to the document head.")
        metrics["title_length"] = 0
    else:
        title_text = title_tag.string.strip()
        metrics["title"] = title_text
        metrics["title_length"] = len(title_text)
        if len(title_text) < 10 or len(title_text) > 60:
            score -= 10
            findings.append(Finding(
                id="seo-title-length",
                title="Suboptimal Title Length",
                description=f"Title is {len(title_text)} characters long. Optimal length is between 10 and 60 characters.",
                severity="warning",
                category="seo"
            ))
            recommendations.append("Keep the title between 10 and 60 characters.")
        else:
            findings.append(Finding(
                id="seo-title-ok",
                title="Title Tag Present",
                description=f"Title is '{title_text}' ({len(title_text)} chars).",
                severity="pass",
                category="seo"
            ))

    # 2. Check Meta Description
    meta_desc = soup.find("meta", attrs={"name": "description"})
    if not meta_desc or not meta_desc.get("content"):
        score -= 20
        findings.append(Finding(
            id="seo-meta-desc-missing",
            title="Missing Meta Description",
            description="The page is missing a meta description.",
            severity="critical",
            category="seo"
        ))
        recommendations.append("Add a <meta name=\"description\" content=\"...\"> tag.")
        metrics["meta_description_length"] = 0
    else:
        desc_text = meta_desc.get("content").strip()
        metrics["meta_description"] = desc_text
        metrics["meta_description_length"] = len(desc_text)
        if len(desc_text) < 50 or len(desc_text) > 160:
            score -= 10
            findings.append(Finding(
                id="seo-meta-desc-length",
                title="Suboptimal Meta Description Length",
                description=f"Meta description is {len(desc_text)} characters long. Optimal length is between 50 and 160 characters.",
                severity="warning",
                category="seo"
            ))
            recommendations.append("Keep the meta description between 50 and 160 characters.")
        else:
            findings.append(Finding(
                id="seo-meta-desc-ok",
                title="Meta Description Present",
                description=f"Meta description is valid ({len(desc_text)} chars).",
                severity="pass",
                category="seo"
            ))

    # 3. Check H1
    h1_tags = soup.find_all("h1")
    metrics["h1_count"] = len(h1_tags)
    if len(h1_tags) == 0:
        score -= 15
        findings.append(Finding(
            id="seo-h1-missing",
            title="Missing H1 Tag",
            description="No <h1> tag found on the page.",
            severity="critical",
            category="seo"
        ))
        recommendations.append("Include exactly one <h1> tag summarizing the page content.")
    elif len(h1_tags) > 1:
        score -= 5
        findings.append(Finding(
            id="seo-h1-multiple",
            title="Multiple H1 Tags",
            description=f"Found {len(h1_tags)} <h1> tags.",
            severity="warning",
            category="seo"
        ))
        recommendations.append("Use only one <h1> tag per page.")
    else:
        findings.append(Finding(
            id="seo-h1-ok",
            title="Single H1 Tag Found",
            description="Page has exactly one <h1> tag.",
            severity="pass",
            category="seo"
        ))

    # 4. Check Image Alt Tags
    images = soup.find_all("img")
    images_without_alt = [img for img in images if not img.get("alt")]
    metrics["total_images"] = len(images)
    metrics["images_without_alt"] = len(images_without_alt)
    
    if len(images_without_alt) > 0:
        penalty = min(20, len(images_without_alt) * 2)
        score -= penalty
        findings.append(Finding(
            id="seo-img-alt-missing",
            title="Missing Image Alt Attributes",
            description=f"Found {len(images_without_alt)} out of {len(images)} images missing 'alt' attributes.",
            severity="warning" if len(images_without_alt) < len(images) else "critical",
            category="seo"
        ))
        recommendations.append("Add descriptive 'alt' attributes to all <img> tags.")
    elif len(images) > 0:
        findings.append(Finding(
            id="seo-img-alt-ok",
            title="Image Alt Attributes Present",
            description="All images have 'alt' attributes.",
            severity="pass",
            category="seo"
        ))

    score = max(0, score)
    
    # Deduplicate recommendations
    recommendations = list(dict.fromkeys(recommendations))

    return AuditResult(
        audit_type="seo",
        score=score,
        metrics=metrics,
        findings=findings,
        recommendations=recommendations
    )

def _generate_error_result(url: str, error_msg: str) -> AuditResult:
    return AuditResult(
        audit_type="seo",
        score=0,
        metrics={},
        findings=[
            Finding(
                id="seo-error",
                title="SEO Audit Failed",
                description=error_msg[:200],
                severity="critical",
                category="seo"
            )
        ],
        recommendations=["Ensure the URL is publicly accessible."]
    )
