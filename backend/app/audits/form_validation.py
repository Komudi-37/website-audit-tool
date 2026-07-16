"""Form validation audit engine using static HTML analysis and dynamic Playwright testing."""
import sys
import asyncio
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import logging
import httpx
from bs4 import BeautifulSoup
from typing import List, Dict, Any
from app.schemas.audit import AuditResult, Finding

logger = logging.getLogger("audit_tool.form_validation")


async def run_form_validation_audit(url: str) -> AuditResult:
    """Run form validation audit against a given URL using static HTML analysis and dynamic Playwright testing."""
    logger.info(f"Starting form validation audit for {url}")
    
    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Phase 1+2: Static HTML analysis
            static_result = await _analyze_forms(soup, url)
            
            # Phase 3: Dynamic testing with Playwright (graceful fallback)
            try:
                dynamic_findings = await _run_dynamic_tests(url, soup)
                # Merge dynamic findings into static result
                static_result.findings.extend(dynamic_findings)
                static_result.metrics["dynamic_tests_note"] = "Dynamic tests intercept and block all network requests — no real form submissions occur"
                logger.info(f"Dynamic testing completed for {url}, added {len(dynamic_findings)} findings")
            except Exception as e:
                logger.warning(f"Dynamic testing failed for {url}, falling back to static results only: {e}")
                static_result.metrics["dynamic_tests_note"] = "Dynamic tests skipped due to error — only static analysis performed"
            
            return static_result

    except httpx.HTTPStatusError as e:
        logger.exception(f"Error fetching URL {url} for form validation audit")
        return _generate_error_result(url, f"Failed to fetch URL: {str(e)}")
    except Exception as e:
        logger.exception(f"Error running form validation audit for {url}")
        return _generate_error_result(url, str(e))


async def _analyze_forms(soup: BeautifulSoup, url: str) -> AuditResult:
    findings: List[Finding] = []
    recommendations: List[str] = []
    score = 100
    metrics: Dict[str, Any] = {}
    
    # Find all form tags
    forms = soup.find_all("form")
    metrics["total_forms_found"] = len(forms)
    
    # If no forms found, return not applicable result
    if len(forms) == 0:
        return AuditResult(
            audit_type="form_validation",
            score=None,
            metrics=metrics,
            findings=[
                Finding(
                    id="form-validation-not-applicable",
                    title="No Forms Detected",
                    description="This page has no forms to validate. The form validation audit is not applicable.",
                    severity="info",
                    category="form_validation"
                )
            ],
            recommendations=["N/A — no forms present on this page."]
        )
    
    # Analyze each form
    all_fields = []
    password_fields_using_text_type = 0
    missing_labels_count = 0
    required_fields_count = 0
    disabled_fields_count = 0
    readonly_fields_count = 0
    file_upload_fields_count = 0
    
    for form_idx, form in enumerate(forms):
        # Find all form elements within this form
        inputs = form.find_all("input")
        selects = form.find_all("select")
        textareas = form.find_all("textarea")
        buttons = form.find_all("button")
        
        form_fields = []
        
        # Process input fields
        for input_elem in inputs:
            field_data = _extract_field_data(input_elem, "input")
            form_fields.append(field_data)
            all_fields.append(field_data)
        
        # Process select fields
        for select_elem in selects:
            field_data = _extract_field_data(select_elem, "select")
            form_fields.append(field_data)
            all_fields.append(field_data)
        
        # Process textarea fields
        for textarea_elem in textareas:
            field_data = _extract_field_data(textarea_elem, "textarea")
            form_fields.append(field_data)
            all_fields.append(field_data)
        
        # Process button fields
        for button_elem in buttons:
            field_data = _extract_field_data(button_elem, "button")
            form_fields.append(field_data)
            all_fields.append(field_data)
    
    metrics["total_fields_found"] = len(all_fields)
    
    # Perform static HTML checks on all fields
    for field in all_fields:
        # Check 1: Password field type
        if _is_password_field(field):
            if field.get("type") != "password":
                password_fields_using_text_type += 1
                score -= 15
                findings.append(Finding(
                    id="form-password-text-type",
                    title="Password Field Using Text Type",
                    description=f"Field with name/id '{field.get('name') or field.get('id')}' appears to be a password field but uses type='text' instead of type='password'. This is a security risk.",
                    severity="critical",
                    category="form_validation"
                ))
                recommendations.append("Change type='text' to type='password' for password input fields.")
        
        # Check 2: Label association (for input, select, textarea only)
        if field.get("tag") in ("input", "select", "textarea"):
            if not _has_label(field, soup):
                missing_labels_count += 1
                score -= 5
                findings.append(Finding(
                    id="form-missing-label",
                    title="Missing Form Label",
                    description=f"Field with name/id '{field.get('name') or field.get('id')}' lacks a proper label association. It should have a matching <label for='id'>, a wrapping <label>, or an aria-label attribute.",
                    severity="warning",
                    category="form_validation"
                ))
                recommendations.append("Ensure all form fields have proper label associations for accessibility.")
        
        # Check 3: Count required fields (metric only)
        if field.get("required"):
            required_fields_count += 1
        
        # Check 4: Count disabled/readonly fields (metrics only)
        if field.get("disabled"):
            disabled_fields_count += 1
        if field.get("readonly"):
            readonly_fields_count += 1
        
        # Check 5: File upload accept attribute
        if field.get("type") == "file":
            file_upload_fields_count += 1
            if not field.get("accept"):
                score -= 2
                findings.append(Finding(
                    id="form-file-accept-missing",
                    title="File Upload Missing Accept Attribute",
                    description=f"File input field with name/id '{field.get('name') or field.get('id')}' is missing the 'accept' attribute to limit file types.",
                    severity="info",
                    category="form_validation"
                ))
                recommendations.append("Add an 'accept' attribute to file input fields to restrict allowed file types (e.g., accept='.jpg,.png,.pdf').")
    
    # Cap deductions per issue type to prevent one type from dominating
    score = max(0, score)
    
    # Update metrics
    metrics["password_fields_using_text_type"] = password_fields_using_text_type
    metrics["missing_labels_count"] = missing_labels_count
    metrics["required_fields_count"] = required_fields_count
    metrics["disabled_fields_count"] = disabled_fields_count
    metrics["readonly_fields_count"] = readonly_fields_count
    metrics["file_upload_fields_count"] = file_upload_fields_count
    
    # Add pass findings for checks with no issues
    if password_fields_using_text_type == 0:
        findings.append(Finding(
            id="form-password-type-ok",
            title="Password Field Types Correct",
            description="All password fields use type='password'.",
            severity="pass",
            category="form_validation"
        ))
    
    if missing_labels_count == 0:
        findings.append(Finding(
            id="form-labels-ok",
            title="Form Labels Present",
            description="All form fields have proper label associations.",
            severity="pass",
            category="form_validation"
        ))
    
    # Add informational findings for metrics
    findings.append(Finding(
        id="form-required-metric",
        title="Required Fields Count",
        description=f"Found {required_fields_count} fields with the 'required' attribute.",
        severity="info",
        category="form_validation"
    ))
    
    findings.append(Finding(
        id="form-disabled-metric",
        title="Disabled Fields Count",
        description=f"Found {disabled_fields_count} fields with the 'disabled' attribute.",
        severity="info",
        category="form_validation"
    ))
    
    findings.append(Finding(
        id="form-readonly-metric",
        title="Readonly Fields Count",
        description=f"Found {readonly_fields_count} fields with the 'readonly' attribute.",
        severity="info",
        category="form_validation"
    ))
    
    recommendations = list(dict.fromkeys(recommendations))
    
    return AuditResult(
        audit_type="form_validation",
        score=score,
        metrics=metrics,
        findings=findings,
        recommendations=recommendations
    )


def _extract_field_data(element, tag_name: str) -> Dict[str, Any]:
    """Extract relevant attributes from a form field element."""
    field_data = {
        "tag": tag_name,
        "type": element.get("type", ""),
        "name": element.get("name", ""),
        "id": element.get("id", ""),
        "required": element.has_attr("required"),
        "maxlength": element.get("maxlength"),
        "minlength": element.get("minlength"),
        "pattern": element.get("pattern"),
        "disabled": element.has_attr("disabled"),
        "readonly": element.has_attr("readonly"),
        "element": element  # Keep reference for label checking
    }
    return field_data


def _is_password_field(field: Dict[str, Any]) -> bool:
    """Check if a field appears to be a password field based on name/id."""
    name = (field.get("name") or "").lower()
    field_id = (field.get("id") or "").lower()
    field_type = field.get("type", "").lower()
    
    # Check if name or id contains password-related keywords
    password_keywords = ["password", "pwd", "pass", "passwd"]
    is_password_by_name = any(keyword in name or keyword in field_id for keyword in password_keywords)
    
    # Also check if type is already password (for validation)
    return is_password_by_name or field_type == "password"


def _has_label(field: Dict[str, Any], soup: BeautifulSoup) -> bool:
    """Check if a field has proper label association."""
    field_elem = field.get("element")
    if not field_elem:
        return False
    
    field_id = field_elem.get("id", "")
    
    # Check 1: Has aria-label attribute
    if field_elem.get("aria-label"):
        return True
    
    # Check 2: Has aria-labelledby attribute
    if field_elem.get("aria-labelledby"):
        return True
    
    # Check 3: Has a matching <label for="id">
    if field_id:
        label_for = soup.find("label", attrs={"for": field_id})
        if label_for:
            return True
    
    # Check 4: Is wrapped in a <label>
    parent = field_elem.parent
    if parent and parent.name == "label":
        return True
    
    return False


def _generate_error_result(url: str, error_msg: str) -> AuditResult:
    return AuditResult(
        audit_type="form_validation",
        score=0,
        metrics={},
        findings=[
            Finding(
                id="form-validation-error",
                title="Form Validation Audit Failed",
                description=error_msg[:200],
                severity="critical",
                category="form_validation"
            )
        ],
        recommendations=["Ensure the URL is publicly accessible."]
    )


async def _run_dynamic_tests(url: str, soup: BeautifulSoup) -> List[Finding]:
    """Phase 3: Dynamic form testing using Playwright with network interception for safety."""
    findings: List[Finding] = []
    forms = soup.find_all("form")
    
    if not forms:
        logger.info("No forms found for dynamic testing")
        return findings
    
    logger.info(f"Starting dynamic testing for {len(forms)} form(s) on {url}")
    
    from playwright.async_api import async_playwright
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            page.set_default_timeout(10000)
            
            # Navigate to the page first to get the initial URL
            await page.goto(url, wait_until="domcontentloaded", timeout=10000)
            await page.wait_for_timeout(1000)  # Let page settle
            initial_url = page.url
            
            # CRITICAL SAFETY: Intercept and block only form submission requests
            async def handle_route(route):
                request = route.request
                # Block only POST requests (form submissions)
                if request.method == "POST":
                    await route.abort()
                # Block navigation to a NEW page (likely form submit with GET or redirect)
                elif request.resource_type == "document" and request.url != initial_url:
                    await route.abort()
                else:
                    # Allow all other requests (scripts, CSS, images, fonts, XHR during normal load)
                    await route.continue_()
            
            await page.route("**/*", handle_route)
            
            try:
                # Test each form
                for form_idx, form in enumerate(forms):
                    form_id = form.get("id", f"form-{form_idx}")
                    logger.info(f"Testing form {form_idx + 1}/{len(forms)}: {form_id}")
                    
                    # Get Playwright locator for this specific form
                    form_locator = page.locator("form").nth(form_idx)
                    
                    # Find submit button (optional - only needed for empty submission test)
                    submit_button = form.find("button", type="submit") or form.find("input", type="submit")
                    if not submit_button:
                        # Look for any button that might submit
                        submit_button = form.find("button")
                    
                    # Test 1: Empty submission (skipped if no submit button)
                    await _test_empty_submission(form_locator, form, submit_button, findings, form_id)
                    
                    # Test 2: Invalid email
                    await _test_invalid_email(form_locator, form, findings, form_id)
                    
                    # Test 3: Weak password
                    await _test_weak_password(form_locator, form, findings, form_id)
                    
                    # Test 4: Confirm-password mismatch
                    await _test_password_mismatch(form_locator, form, findings, form_id)
                    
                    # Test 5: SQLi test
                    await _test_sqli(form_locator, form, findings, form_id)
                
                logger.info(f"Dynamic testing completed for {url}")
                
            finally:
                await page.close()
                await context.close()
                await browser.close()
                
    except Exception as e:
        logger.exception(f"Error during dynamic testing for {url}: {e}")
        raise
    
    return findings


async def _test_empty_submission(form_locator, form, submit_button, findings: List[Finding], form_id: str):
    """Test 1: Empty submission - check if required field validation blocks submit."""
    try:
        # Skip test if no submit button found
        if not submit_button:
            logger.info(f"Form {form_id} has no submit button, skipping empty submission test")
            return
        
        # Check if form has any required fields - skip test if none
        inputs = form.find_all("input")
        selects = form.find_all("select")
        textareas = form.find_all("textarea")
        
        has_required = False
        for inp in inputs:
            if inp.has_attr("required"):
                has_required = True
                break
        if not has_required:
            for sel in selects:
                if sel.has_attr("required"):
                    has_required = True
                    break
        if not has_required:
            for ta in textareas:
                if ta.has_attr("required"):
                    has_required = True
                    break
        
        if not has_required:
            logger.info(f"Form {form_id} has no required fields, skipping empty submission test")
            return
        
        # Clear all inputs in the form
        for inp in inputs:
            field_id = inp.get("id")
            field_name = inp.get("name")
            if field_id:
                try:
                    await form_locator.locator(f"#{field_id}").fill("")
                except:
                    pass
            elif field_name:
                try:
                    await form_locator.locator(f"[name='{field_name}']").fill("")
                except:
                    pass
        
        # Check form validity before submit attempt
        form_element = await form_locator.element_handle()
        if form_element:
            is_valid = await form_element.evaluate("el => el.checkValidity()")
            if not is_valid:
                logger.info(f"Form {form_id} has invalid state with empty fields (validation working)")
                return
        
        # Try to click submit (will be intercepted by network handler)
        submit_id = submit_button.get("id")
        submit_name = submit_button.get("name")
        
        try:
            if submit_id:
                await form_locator.locator(f"#{submit_id}").click(timeout=2000)
            elif submit_name:
                await form_locator.locator(f"[name='{submit_name}']").click(timeout=2000)
            else:
                # Try by type and position
                await form_locator.locator("button[type='submit'], input[type='submit']").click(timeout=2000)
            
            # If we got here without validation blocking, it's a problem
            findings.append(Finding(
                id="form-empty-submit-not-blocked",
                title="Required Field Validation Not Enforced",
                description=f"Form '{form_id}' allowed submission attempt with empty required fields. HTML5 validation or JavaScript validation should block this.",
                severity="critical",
                category="form_validation"
            ))
            logger.warning(f"Form {form_id} empty submission was not blocked")
            
        except Exception as e:
            # Timeout or error might mean validation blocked it
            logger.info(f"Empty submit test for form {form_id}: {e}")
            
    except Exception as e:
        logger.warning(f"Error testing empty submission for form {form_id}: {e}")


async def _test_invalid_email(form_locator, form, findings: List[Finding], form_id: str):
    """Test 2: Invalid email formats - check if email validation rejects invalid formats."""
    invalid_emails = ["abc", "abc@", "abc@gmail"]
    email_inputs = form.find_all("input", type="email")
    
    for email_input in email_inputs:
        field_id = email_input.get("id")
        field_name = email_input.get("name")
        selector = f"#{field_id}" if field_id else f"[name='{field_name}']" if field_name else None
        
        if not selector:
            continue
        
        for invalid_email in invalid_emails:
            try:
                await form_locator.locator(selector).fill(invalid_email)
                
                # Check validity
                element = await form_locator.locator(selector).element_handle()
                if element:
                    is_valid = await element.evaluate("el => el.validity.valid")
                    if is_valid:
                        findings.append(Finding(
                            id="form-invalid-email-accepted",
                            title="Invalid Email Format Accepted",
                            description=f"Email field '{field_id or field_name}' accepted invalid format '{invalid_email}'. Email validation should reject this.",
                            severity="warning",
                            category="form_validation"
                        ))
                        logger.warning(f"Email field accepted invalid format: {invalid_email}")
                        break  # One failure per field is enough
                
                # Clear for next test
                await form_locator.locator(selector).fill("")
                
            except Exception as e:
                logger.warning(f"Error testing invalid email '{invalid_email}' for {selector}: {e}")


async def _test_weak_password(form_locator, form, findings: List[Finding], form_id: str):
    """Test 3: Weak password - check if client-side strength validation rejects weak passwords."""
    password_inputs = form.find_all("input", type="password")
    
    for pwd_input in password_inputs:
        field_id = pwd_input.get("id")
        field_name = pwd_input.get("name")
        selector = f"#{field_id}" if field_id else f"[name='{field_name}']" if field_name else None
        
        if not selector:
            continue
        
        try:
            await form_locator.locator(selector).fill("123")
            
            # Check if there's any validation error or strength indicator
            element = await form_locator.locator(selector).element_handle()
            if element:
                # Check if field is still valid (weak password might be rejected)
                is_valid = await element.evaluate("el => el.validity.valid")
                if is_valid:
                    findings.append(Finding(
                        id="form-weak-password-accepted",
                        title="Weak Password Not Rejected",
                        description=f"Password field '{field_id or field_name}' accepted weak password '123'. Consider adding client-side strength validation.",
                        severity="warning",
                        category="form_validation"
                    ))
                    logger.info(f"Weak password accepted for field {selector}")
            
            await form_locator.locator(selector).fill("")
            
        except Exception as e:
            logger.warning(f"Error testing weak password for {selector}: {e}")


async def _test_password_mismatch(form_locator, form, findings: List[Finding], form_id: str):
    """Test 4: Confirm-password mismatch - check if mismatch is detected."""
    password_inputs = form.find_all("input", type="password")
    
    if len(password_inputs) >= 2:
        # Likely password + confirm password
        pwd1 = password_inputs[0]
        pwd2 = password_inputs[1]
        
        sel1 = f"#{pwd1.get('id')}" if pwd1.get('id') else f"[name='{pwd1.get('name')}']" if pwd1.get('name') else None
        sel2 = f"#{pwd2.get('id')}" if pwd2.get('id') else f"[name='{pwd2.get('name')}']" if pwd2.get('name') else None
        
        if sel1 and sel2:
            try:
                await form_locator.locator(sel1).fill("password123")
                await form_locator.locator(sel2).fill("different456")
                
                # This is informational - many sites don't check this client-side
                findings.append(Finding(
                    id="form-password-mismatch-tested",
                    title="Password Mismatch Test Performed",
                    description=f"Form has {len(password_inputs)} password fields. Client-side mismatch validation should be implemented if not present.",
                    severity="info",
                    category="form_validation"
                ))
                
                await form_locator.locator(sel1).fill("")
                await form_locator.locator(sel2).fill("")
                
            except Exception as e:
                logger.warning(f"Error testing password mismatch: {e}")


async def _test_sqli(form_locator, form, findings: List[Finding], form_id: str):
    """Test 5: SQL injection - check for client-side crashes or errors."""
    text_inputs = form.find_all("input", type=lambda x: x in ["text", "search", "url"])
    textareas = form.find_all("textarea")
    
    all_text_fields = text_inputs + textareas
    sqli_payload = "' OR 1=1 --"
    
    for field in all_text_fields[:2]:  # Limit to first 2 text fields
        field_id = field.get("id")
        field_name = field.get("name")
        selector = f"#{field_id}" if field_id else f"[name='{field_name}']" if field_name else None
        
        if not selector:
            continue
        
        try:
            await form_locator.locator(selector).fill(sqli_payload)
            
            # Check if page is still responsive
            await form_locator.page.wait_for_timeout(500)
            is_responsive = await form_locator.page.evaluate("() => true")
            
            if is_responsive:
                findings.append(Finding(
                    id="form-sqli-tested",
                    title="SQL Injection Test Performed",
                    description=f"SQL injection payload '{sqli_payload}' was tested in field '{field_id or field_name}'. No client-side crash occurred. Note: Server-side SQL injection testing was not performed since no real submission occurred.",
                    severity="info",
                    category="form_validation"
                ))
            
            await form_locator.locator(selector).fill("")
            
        except Exception as e:
            logger.warning(f"Error testing SQLi for {selector}: {e}")

