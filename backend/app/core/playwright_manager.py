"""
Playwright browser manager for consistent browser initialization across all audits.

This module centralizes Playwright bootstrap to handle subprocess issues
that occur in both Windows (Python 3.14) and Linux (Render) environments.
"""
import logging
import traceback
import asyncio
from typing import Optional, Tuple
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

logger = logging.getLogger("audit_tool.playwright_manager")

# Global browser instance for reuse across audits
_browser: Optional[Browser] = None
_playwright_context = None


async def get_browser() -> Tuple[Browser, BrowserContext, Page]:
    """
    Get or create a browser instance with context and page.
    
    Returns:
        Tuple of (browser, context, page)
        
    Raises:
        RuntimeError: If browser launch fails after retry
    """
    global _browser, _playwright_context
    
    max_retries = 1
    
    for attempt in range(max_retries + 1):
        try:
            if _browser is None or _browser.is_connected() is False:
                logger.info(f"Launching browser (attempt {attempt + 1}/{max_retries + 1})")
                
                # Use headless mode from environment
                import os
                headless_env = os.environ.get("PLAYWRIGHT_HEADLESS", "True")
                headless = headless_env.lower() in ("true", "1", "yes")
                
                loop = asyncio.get_running_loop()
                logger.info("DIAG [1/6] Running loop: %s", type(loop).__name__)
                logger.info("DIAG [2/6] Policy: %s", type(asyncio.get_event_loop_policy()).__name__)

                # --- Step 3: Create async_playwright() object ---
                logger.info("DIAG [3/6] Calling async_playwright()...")
                try:
                    _playwright_context = async_playwright()
                    logger.info("DIAG [3/6] async_playwright() returned: %s", type(_playwright_context).__name__)
                except Exception:
                    logger.error("DIAG [3/6] FAILED at async_playwright()\n%s", traceback.format_exc())
                    raise

                # --- Step 4: Enter context (__aenter__) ---
                logger.info("DIAG [4/6] Calling __aenter__()...")
                try:
                    p = await _playwright_context.__aenter__()
                    logger.info("DIAG [4/6] __aenter__() returned: %s", type(p).__name__)
                except Exception:
                    logger.error("DIAG [4/6] FAILED at __aenter__()\n%s", traceback.format_exc())
                    raise

                # --- Step 5: Launch Chromium ---
                # Only use hardcoded path if explicitly set via env var (Render).
                # Locally, let Playwright use its own installed browser.
                chromium_path = os.environ.get("PLAYWRIGHT_CHROMIUM_PATH")
                launch_kwargs = {
                    "headless": headless,
                    "args": [
                        "--no-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-gpu",
                    ],
                }
                if chromium_path:
                    launch_kwargs["executable_path"] = chromium_path

                logger.info(
                    "DIAG [5/6] Calling p.chromium.launch(headless=%s, executable_path=%s)...",
                    headless, chromium_path or "<default>",
                )
                try:
                    _browser = await p.chromium.launch(**launch_kwargs)
                    logger.info("DIAG [5/6] chromium.launch() returned: %s", type(_browser).__name__)
                except Exception:
                    logger.error("DIAG [5/6] FAILED at chromium.launch()\n%s", traceback.format_exc())
                    raise

                logger.info("DIAG [6/6] Browser launched successfully")
            
            # --- Create context ---
            logger.info("DIAG creating browser context...")
            try:
                context = await _browser.new_context(
                    viewport={"width": 1280, "height": 800},
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    ),
                )
                logger.info("DIAG browser context created")
            except Exception:
                logger.error("DIAG FAILED at browser.new_context()\n%s", traceback.format_exc())
                raise

            # --- Create page ---
            logger.info("DIAG creating page...")
            try:
                page = await context.new_page()
                logger.info("DIAG page created")
            except Exception:
                logger.error("DIAG FAILED at context.new_page()\n%s", traceback.format_exc())
                raise
            
            return _browser, context, page
            
        except Exception as exc:
            logger.error(
                "Browser launch failed (attempt %d/%d): %s\n%s",
                attempt + 1,
                max_retries + 1,
                exc,
                traceback.format_exc(),
            )
            if attempt == max_retries:
                await close_browser()
                raise
            await asyncio.sleep(1)


async def close_browser():
    """Safely close the global browser instance."""
    global _browser, _playwright_context
    
    try:
        if _browser:
            await _browser.close()
            _browser = None
            logger.info("Browser closed")
    except Exception as exc:
        logger.warning(f"Error closing browser: {exc}")
    
    try:
        if _playwright_context:
            await _playwright_context.__aexit__(None, None, None)
            _playwright_context = None
    except Exception as exc:
        logger.warning(f"Error closing playwright context: {exc}")

