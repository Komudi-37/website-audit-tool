import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock, patch
from app.audits.functionality import run_functionality_audit
from app.schemas.audit import AuditResult


@pytest.mark.asyncio
async def test_run_functionality_audit_success():
    """Test successful homepage loading with nav links, contact form, and no internal links."""
    mock_response = AsyncMock()
    mock_response.status = 200

    mock_page = AsyncMock()
    mock_page.goto = AsyncMock(return_value=mock_response)
    mock_page.content = AsyncMock(
        return_value="""
        <html>
            <header>
                <nav>
                    <a href="/about">About Us</a>
                    <a href="/services">Our Services</a>
                </nav>
            </header>
            <main>
                <h1>Welcome to our test site homepage</h1>
                <p>This is a complete mock page designed to satisfy all checks of the website functionality audit. It contains enough text to exceed fifty characters easily.</p>
                <form id="contact-form">
                    <input type="text" name="name" placeholder="Your Name" />
                    <input type="email" name="email" placeholder="Your Email" />
                    <textarea name="message"></textarea>
                    <button type="submit">Submit</button>
                </form>
            </main>
        </html>
        """
    )
    mock_page.url = "https://example.com/"
    mock_page.wait_for_timeout = AsyncMock()

    mock_context = AsyncMock()
    mock_context.new_page = AsyncMock(return_value=mock_page)

    mock_browser = AsyncMock()
    mock_browser.new_context = AsyncMock(return_value=mock_context)
    mock_browser.close = AsyncMock()

    mock_chromium = AsyncMock()
    mock_chromium.launch = AsyncMock(return_value=mock_browser)

    mock_playwright = MagicMock()
    mock_playwright.chromium = mock_chromium

    # Mock HTTPX response to avoid real network calls for /about and /services
    mock_resp_success = MagicMock()
    mock_resp_success.status_code = 200
    mock_httpx_client = AsyncMock()
    mock_httpx_client.head = AsyncMock(return_value=mock_resp_success)

    with patch("playwright.async_api.async_playwright") as mock_ap, \
            patch("httpx.AsyncClient", return_value=mock_httpx_client):
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_playwright)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_ap.return_value = mock_context_manager

        result = await run_functionality_audit("https://example.com")

        assert isinstance(result, AuditResult)
        assert result.audit_type == "functionality"
        assert result.score == 100.0
        assert len(result.findings) == 4  # Homepage OK, Nav OK, Contact OK, Links OK

        # Verify findings IDs
        finding_ids = [f.id for f in result.findings]
        assert "func-homepage-ok" in finding_ids
        assert "func-nav-ok" in finding_ids
        assert "func-contact-form-ok" in finding_ids
        assert "func-links-ok" in finding_ids


@pytest.mark.asyncio
async def test_run_functionality_audit_links_working():
    """Test functionality audit when internal links exist and are all working."""
    mock_response = AsyncMock()
    mock_response.status = 200

    mock_page = AsyncMock()
    mock_page.goto = AsyncMock(return_value=mock_response)
    mock_page.content = AsyncMock(
        return_value="""
        <html>
            <header>
                <nav>
                    <a href="/about">About Us</a>
                </nav>
            </header>
            <main>
                <h1>Welcome to our test site homepage</h1>
                <p>This is a complete mock page designed to satisfy all checks of the website functionality audit. It contains enough text to exceed fifty characters easily.</p>
                <form id="contact-form">
                    <input type="email" name="email" />
                </form>
                <!-- Internal links to check -->
                <a href="/page1">Link 1</a>
                <a href="https://example.com/page2">Link 2</a>
                <!-- Fragment and mailto links to ignore -->
                <a href="#section">Ignore Fragment</a>
                <a href="mailto:test@example.com">Ignore Mailto</a>
                <a href="https://google.com/external">Ignore External</a>
            </main>
        </html>
        """
    )
    mock_page.url = "https://example.com/"
    mock_page.wait_for_timeout = AsyncMock()

    mock_context = AsyncMock()
    mock_context.new_page = AsyncMock(return_value=mock_page)

    mock_browser = AsyncMock()
    mock_browser.new_context = AsyncMock(return_value=mock_context)
    mock_browser.close = AsyncMock()

    mock_chromium = AsyncMock()
    mock_chromium.launch = AsyncMock(return_value=mock_browser)

    mock_playwright = MagicMock()
    mock_playwright.chromium = mock_chromium

    # Mock HTTPX response for working links
    mock_resp_success = MagicMock()
    mock_resp_success.status_code = 200
    mock_httpx_client = AsyncMock()
    mock_httpx_client.head = AsyncMock(return_value=mock_resp_success)

    with patch("playwright.async_api.async_playwright") as mock_ap, \
            patch("httpx.AsyncClient", return_value=mock_httpx_client):
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_playwright)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_ap.return_value = mock_context_manager

        result = await run_functionality_audit("https://example.com")

        assert isinstance(result, AuditResult)
        assert result.score == 100.0
        assert result.metrics["internal_links_total_found"] == 2
        assert result.metrics["internal_links_checked"] == 2
        assert result.metrics["broken_links_count"] == 0

        finding_ids = [f.id for f in result.findings]
        assert "func-links-ok" in finding_ids


@pytest.mark.asyncio
async def test_run_functionality_audit_links_broken():
    """Test functionality audit when some internal links return 404 or 500."""
    mock_response = AsyncMock()
    mock_response.status = 200

    mock_page = AsyncMock()
    mock_page.goto = AsyncMock(return_value=mock_response)
    mock_page.content = AsyncMock(
        return_value="""
        <html>
            <header>
                <nav>
                    <a href="/about">About Us</a>
                </nav>
            </header>
            <main>
                <h1>Welcome to our test site homepage</h1>
                <p>This is a complete mock page designed to satisfy all checks of the website functionality audit. It contains enough text to exceed fifty characters easily.</p>
                <form id="contact-form">
                    <input type="email" name="email" />
                </form>
                <a href="/page1">Broken 404</a>
                <a href="/page2">Broken 500</a>
                <a href="/page3">Working 200</a>
            </main>
        </html>
        """
    )
    mock_page.url = "https://example.com/"
    mock_page.wait_for_timeout = AsyncMock()

    mock_context = AsyncMock()
    mock_context.new_page = AsyncMock(return_value=mock_page)

    mock_browser = AsyncMock()
    mock_browser.new_context = AsyncMock(return_value=mock_context)
    mock_browser.close = AsyncMock()

    mock_chromium = AsyncMock()
    mock_chromium.launch = AsyncMock(return_value=mock_browser)

    mock_playwright = MagicMock()
    mock_playwright.chromium = mock_chromium

    # Mock HTTPX status-specific responses
    def mock_head_side_effect(url, **kwargs):
        resp = MagicMock()
        if "page1" in url:
            resp.status_code = 404
        elif "page2" in url:
            resp.status_code = 500
        else:
            resp.status_code = 200
        return resp

    mock_httpx_client = AsyncMock()
    mock_httpx_client.head = AsyncMock(side_effect=mock_head_side_effect)

    with patch("playwright.async_api.async_playwright") as mock_ap, \
            patch("httpx.AsyncClient", return_value=mock_httpx_client):
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_playwright)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_ap.return_value = mock_context_manager

        result = await run_functionality_audit("https://example.com")

        assert isinstance(result, AuditResult)
        # Score calculation: 100 - 2 broken links * 5 = 90.0
        assert result.score == 90.0
        assert result.metrics["internal_links_total_found"] == 3
        assert result.metrics["internal_links_checked"] == 3
        assert result.metrics["broken_links_count"] == 2

        finding_ids = [f.id for f in result.findings]
        assert "func-links-broken" in finding_ids


@pytest.mark.asyncio
async def test_run_functionality_audit_links_exceptions():
    """Test functionality audit when link checking raises Timeout or connection errors."""
    mock_response = AsyncMock()
    mock_response.status = 200

    mock_page = AsyncMock()
    mock_page.goto = AsyncMock(return_value=mock_response)
    mock_page.content = AsyncMock(
        return_value="""
        <html>
            <header>
                <nav>
                    <a href="/about">About Us</a>
                </nav>
            </header>
            <main>
                <h1>Welcome to our test site homepage</h1>
                <p>This is a complete mock page designed to satisfy all checks of the website functionality audit. It contains enough text to exceed fifty characters easily.</p>
                <form id="contact-form">
                    <input type="email" name="email" />
                </form>
                <a href="/timeout-page">Timeout Link</a>
                <a href="/conn-error-page">Connection Error Link</a>
            </main>
        </html>
        """
    )
    mock_page.url = "https://example.com/"
    mock_page.wait_for_timeout = AsyncMock()

    mock_context = AsyncMock()
    mock_context.new_page = AsyncMock(return_value=mock_page)

    mock_browser = AsyncMock()
    mock_browser.new_context = AsyncMock(return_value=mock_context)
    mock_browser.close = AsyncMock()

    mock_chromium = AsyncMock()
    mock_chromium.launch = AsyncMock(return_value=mock_browser)

    mock_playwright = MagicMock()
    mock_playwright.chromium = mock_chromium

    # Mock HTTPX exceptions
    def mock_head_side_effect(url, **kwargs):
        if "timeout" in url:
            raise httpx.TimeoutException("Timeout occurred", request=MagicMock())
        elif "conn-error" in url:
            raise httpx.ConnectError("Connection refused", request=MagicMock())
        else:
            resp = MagicMock()
            resp.status_code = 200
            return resp

    mock_httpx_client = AsyncMock()
    mock_httpx_client.head = AsyncMock(side_effect=mock_head_side_effect)

    with patch("playwright.async_api.async_playwright") as mock_ap, \
            patch("httpx.AsyncClient", return_value=mock_httpx_client):
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_playwright)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_ap.return_value = mock_context_manager

        result = await run_functionality_audit("https://example.com")

        print("DEBUG BROKEN LINKS:", result.metrics["broken_links"])

        assert isinstance(result, AuditResult)
        # Score calculation: 100 - 2 * 5 = 90.0 (about is 200, timeout is broken, conn-error is broken)
        assert result.score == 90.0
        assert result.metrics["broken_links_count"] == 2

        broken_statuses = [b["status"] for b in result.metrics["broken_links"]]
        assert "timeout" in broken_statuses
        assert "connection_error" in broken_statuses


@pytest.mark.asyncio
async def test_run_functionality_audit_excessive_broken_links():
    """Test functionality audit broken link cap penalty (-25)."""
    mock_response = AsyncMock()
    mock_response.status = 200

    mock_page = AsyncMock()
    mock_page.goto = AsyncMock(return_value=mock_response)

    # 6 broken links
    links_html = "".join(f'<a href="/broken{i}">Link {i}</a>' for i in range(1, 7))
    mock_page.content = AsyncMock(
        return_value=f"""
        <html>
            <header>
                <nav>
                    <a href="/about">About Us</a>
                </nav>
            </header>
            <main>
                <h1>Welcome to our test site homepage</h1>
                <p>This is a complete mock page designed to satisfy all checks of the website functionality audit. It contains enough text to exceed fifty characters easily.</p>
                <form id="contact-form">
                    <input type="email" name="email" />
                </form>
                {links_html}
            </main>
        </html>
        """
    )
    mock_page.url = "https://example.com/"
    mock_page.wait_for_timeout = AsyncMock()

    mock_context = MagicMock()
    mock_context.new_page = AsyncMock(return_value=mock_page)

    mock_browser = AsyncMock()
    mock_browser.new_context = AsyncMock(return_value=mock_context)
    mock_browser.close = AsyncMock()

    mock_chromium = AsyncMock()
    mock_chromium.launch = AsyncMock(return_value=mock_browser)

    mock_playwright = MagicMock()
    mock_playwright.chromium = mock_chromium

    # Mock HTTPX response to return 404 for all broken links, but 200 for other page links like /about
    def mock_head_side_effect(url, **kwargs):
        resp = MagicMock()
        if "broken" in url:
            resp.status_code = 404
        else:
            resp.status_code = 200
        return resp

    mock_httpx_client = AsyncMock()
    mock_httpx_client.head = AsyncMock(side_effect=mock_head_side_effect)

    with patch("playwright.async_api.async_playwright") as mock_ap, \
            patch("httpx.AsyncClient", return_value=mock_httpx_client):
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_playwright)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_ap.return_value = mock_context_manager

        result = await run_functionality_audit("https://example.com")

        assert isinstance(result, AuditResult)
        # Score calculation: 100 - min(25, 6 * 5) = 75.0
        assert result.score == 75.0
        assert result.metrics["broken_links_count"] == 6
        assert len(result.findings) == 4

        finding_ids = [f.id for f in result.findings]
        assert "func-links-broken" in finding_ids

        # Verify severity is critical since >= 5 broken links
        broken_finding = next(f for f in result.findings if f.id == "func-links-broken")
        assert broken_finding.severity == "critical"
