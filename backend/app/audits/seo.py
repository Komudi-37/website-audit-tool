import logging
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any
from urllib.parse import urljoin, urlparse
from app.schemas.audit import AuditResult, Finding

logger = logging.getLogger("audit_tool.seo")

def run_seo_audit(url: str) -> AuditResult:
    """Run basic SEO audit against a given URL."""
    logger.info(f"Starting SEO audit for {url}")
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        return _analyze_seo(soup, url, dict(response.headers))

    except requests.RequestException as e:
        logger.exception(f"Error fetching URL {url} for SEO audit")
        return _generate_error_result(url, f"Failed to fetch URL: {str(e)}")
    except Exception as e:
        logger.exception(f"Error running SEO audit for {url}")
        return _generate_error_result(url, str(e))

def _analyze_seo(soup: BeautifulSoup, url: str, headers: Dict[str, str] = None) -> AuditResult:
    findings: List[Finding] = []
    recommendations: List[str] = []
    score = 100
    metrics: Dict[str, Any] = {}
    
    if headers is None:
        headers = {}

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
    else:
        findings.append(Finding(
            id="seo-img-alt-ok",
            title="Image Alt Attributes Present",
            description="All images have 'alt' attributes." if len(images) > 0 else "No images found on the page.",
            severity="pass",
            category="seo"
        ))

    # 5. Check Canonical Tag
    canonical_tags = soup.find_all("link", attrs={"rel": "canonical"})
    metrics["canonical_url"] = None
    if not canonical_tags:
        score -= 10
        findings.append(Finding(
            id="seo-canonical-missing",
            title="Missing Canonical Tag",
            description="No canonical link tag was found. This can lead to duplicate content issues.",
            severity="warning",
            category="seo"
        ))
        recommendations.append("Add a <link rel=\"canonical\" href=\"...\"> tag to the page head.")
    elif len(canonical_tags) > 1:
        score -= 5
        findings.append(Finding(
            id="seo-canonical-multiple",
            title="Multiple Canonical Tags Found",
            description=f"Found {len(canonical_tags)} canonical link tags. There should be only one canonical tag per page.",
            severity="warning",
            category="seo"
        ))
        recommendations.append("Ensure there is only one canonical link tag per page.")
    else:
        canonical_href = canonical_tags[0].get("href")
        if not canonical_href:
            score -= 10
            findings.append(Finding(
                id="seo-canonical-empty",
                title="Empty Canonical Tag",
                description="A canonical link tag was found but the href attribute is empty.",
                severity="warning",
                category="seo"
            ))
            recommendations.append("Specify a valid absolute URL in the canonical tag's href attribute.")
        else:
            canonical_href_str = canonical_href.strip()
            metrics["canonical_url"] = canonical_href_str
            findings.append(Finding(
                id="seo-canonical-ok",
                title="Canonical Tag Present",
                description=f"Canonical URL is set to '{canonical_href_str}'.",
                severity="pass",
                category="seo"
            ))

    # 6. Check Robots.txt
    robots_url = urljoin(url, "/robots.txt")
    metrics["robots_txt_url"] = robots_url
    metrics["robots_txt_exists"] = False
    try:
        r = requests.get(robots_url, timeout=5)
        if r.status_code == 200:
            metrics["robots_txt_exists"] = True
            findings.append(Finding(
                id="seo-robots-ok",
                title="robots.txt Found",
                description=f"A robots.txt file was found at {robots_url}.",
                severity="pass",
                category="seo"
            ))
        else:
            score -= 10
            findings.append(Finding(
                id="seo-robots-missing",
                title="Missing robots.txt",
                description=f"robots.txt file was not found at {robots_url} (HTTP Status: {r.status_code}).",
                severity="warning",
                category="seo"
            ))
            recommendations.append("Create a robots.txt file at the root of your site to control search engine crawling.")
    except Exception as e:
        score -= 10
        findings.append(Finding(
            id="seo-robots-missing",
            title="Missing robots.txt",
            description=f"Could not retrieve robots.txt at {robots_url}: {str(e)}",
            severity="warning",
            category="seo"
        ))
        recommendations.append("Create a robots.txt file at the root of your site to control search engine crawling.")

    # 7. Check Sitemap.xml
    sitemap_url = urljoin(url, "/sitemap.xml")
    metrics["sitemap_url"] = sitemap_url
    metrics["sitemap_exists"] = False
    try:
        r = requests.get(sitemap_url, timeout=5)
        if r.status_code == 200:
            metrics["sitemap_exists"] = True
            findings.append(Finding(
                id="seo-sitemap-ok",
                title="sitemap.xml Found",
                description=f"A sitemap.xml file was found at {sitemap_url}.",
                severity="pass",
                category="seo"
            ))
        else:
            score -= 10
            findings.append(Finding(
                id="seo-sitemap-missing",
                title="Missing sitemap.xml",
                description=f"sitemap.xml file was not found at {sitemap_url} (HTTP Status: {r.status_code}).",
                severity="warning",
                category="seo"
            ))
            recommendations.append("Create a sitemap.xml file and place it at the root of your site to help search engines index your pages.")
    except Exception as e:
        score -= 10
        findings.append(Finding(
            id="seo-sitemap-missing",
            title="Missing sitemap.xml",
            description=f"Could not retrieve sitemap.xml at {sitemap_url}: {str(e)}",
            severity="warning",
            category="seo"
        ))
        recommendations.append("Create a sitemap.xml file and place it at the root of your site to help search engines index your pages.")

    # 8. Check Indexability
    indexable = True
    noindex_reasons = []
    
    meta_robots = soup.find("meta", attrs={"name": "robots"})
    if meta_robots:
        content = meta_robots.get("content", "").lower()
        if "noindex" in content:
            indexable = False
            noindex_reasons.append("meta robots tag contains noindex")
            
    meta_googlebot = soup.find("meta", attrs={"name": "googlebot"})
    if meta_googlebot:
        content_g = meta_googlebot.get("content", "").lower()
        if "noindex" in content_g:
            indexable = False
            noindex_reasons.append("meta googlebot tag contains noindex")

    if headers:
        x_robots = None
        for k, v in headers.items():
            if k.lower() == "x-robots-tag":
                x_robots = v
                break
        if x_robots:
            if "noindex" in x_robots.lower():
                indexable = False
                noindex_reasons.append(f"X-Robots-Tag header contains noindex: '{x_robots}'")

    metrics["indexable"] = indexable
    metrics["noindex_reasons"] = noindex_reasons

    if not indexable:
        score -= 20
        findings.append(Finding(
            id="seo-noindex",
            title="Page is Non-Indexable",
            description="The page is excluded from search engine indexing because of a noindex directive: " + ", ".join(noindex_reasons),
            severity="warning",
            category="seo"
        ))
        recommendations.append("Remove the 'noindex' directive from meta tags or response headers if you want search engines to index this page.")
    else:
        findings.append(Finding(
            id="seo-indexable-ok",
            title="Page is Indexable",
            description="No noindex directives found in meta tags or response headers.",
            severity="pass",
            category="seo"
        ))

    # 9. Broken Link Detection
    parsed_base = urlparse(url)
    links = soup.find_all("a", href=True)
    unique_internal_urls = []
    seen_urls = set()
    
    for l in links:
        href = l.get("href").strip()
        if not href:
            continue
        
        href_lower = href.lower()
        if href_lower.startswith(("mailto:", "tel:", "javascript:", "#")):
            continue
            
        absolute_url = urljoin(url, href)
        parsed_link = urlparse(absolute_url)
        
        if parsed_link.scheme in ("http", "https"):
            if parsed_link.netloc == parsed_base.netloc:
                normalized_url = parsed_link._replace(fragment="").geturl()
                if normalized_url not in seen_urls:
                    seen_urls.add(normalized_url)
                    unique_internal_urls.append(normalized_url)

    total_internal_found = len(unique_internal_urls)
    links_to_test = unique_internal_urls[:20]
    broken_links = []

    for test_url in links_to_test:
        try:
            r = requests.head(test_url, timeout=3, allow_redirects=True)
            if r.status_code >= 400:
                r = requests.get(test_url, timeout=3, allow_redirects=True)
            
            if r.status_code >= 400:
                broken_links.append({"url": test_url, "status": r.status_code})
        except Exception as e:
            broken_links.append({"url": test_url, "status": "Error", "reason": str(e)})

    metrics["total_internal_links_found"] = total_internal_found
    metrics["links_checked"] = len(links_to_test)
    metrics["broken_links"] = broken_links
    metrics["broken_links_count"] = len(broken_links)

    if broken_links:
        penalty = min(25, len(broken_links) * 5)
        score -= penalty
        broken_desc = "\n".join([f"- {item['url']} (Status: {item['status']})" for item in broken_links])
        findings.append(Finding(
            id="seo-links-broken",
            title="Broken Links Detected",
            description=f"Found {len(broken_links)} broken internal links out of {len(links_to_test)} checked:\n{broken_desc}",
            severity="warning" if len(broken_links) < len(links_to_test) else "critical",
            category="seo"
        ))
        recommendations.append("Fix or remove all broken internal links pointing to non-existent pages.")
    else:
        findings.append(Finding(
            id="seo-links-ok",
            title="Internal Links Verified",
            description=f"Checked {len(links_to_test)} internal links; all returned successful status codes." if len(links_to_test) > 0 else "No internal links found to verify.",
            severity="pass",
            category="seo"
        ))

    score = max(0, score)
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
