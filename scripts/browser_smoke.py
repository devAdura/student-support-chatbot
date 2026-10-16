"""Functional browser checks against a running local Gunicorn server."""

import os
from pathlib import Path
from playwright.sync_api import sync_playwright

base = os.environ.get("BASE_URL", "http://127.0.0.1:5000")
out = Path(os.environ.get("SCREENSHOT_DIR", "/workspace/scratch/chatbot-screenshots"))
out.mkdir(parents=True, exist_ok=True)
with sync_playwright() as p:
    browser = p.chromium.launch(
        executable_path="/usr/bin/chromium", headless=True, args=["--no-sandbox"]
    )
    context = browser.new_context(viewport={"width": 1440, "height": 1100})
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(base)
    page.get_by_text("Hi, welcome in!", exact=False).wait_for()
    page.get_by_role("button", name="Register courses ↗").click()
    page.get_by_text("Sign in to your institution", exact=False).wait_for()
    page.get_by_role("button", name="Helpful", exact=True).last.click()
    page.wait_for_function(
        "() => document.querySelector('.feedback button.selected') !== null"
    )
    page.reload()
    page.get_by_text("Sign in to your institution", exact=False).wait_for()
    payload = '<img src=x onerror="window.__xss=true">'
    page.get_by_label("Your question", exact=True).fill(payload)
    page.get_by_role("button", name="Send question", exact=True).click()
    page.wait_for_function(
        "() => document.querySelectorAll('.message-row.user').length === 2"
    )
    page.wait_for_function("() => document.querySelector('#send').disabled === false")
    assert page.locator(".message-row.user").last.inner_text() == payload
    assert page.locator(".message-text img").count() == 0
    assert page.evaluate("window.__xss") is None
    page.get_by_role("button", name="Clear chat", exact=True).click()
    page.wait_for_function(
        "() => document.querySelectorAll('.message-row.user').length === 0"
    )
    page.screenshot(path=str(out / "desktop.png"), full_page=True)
    page.set_viewport_size({"width": 390, "height": 844})
    page.screenshot(path=str(out / "mobile.png"), full_page=True)
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    page.get_by_label("Your question", exact=True).fill("Where is my exam timetable?")
    page.get_by_role("button", name="Send question", exact=True).click()
    page.get_by_text(
        "Look for the latest examination timetable", exact=False
    ).wait_for()
    page.goto(base + "/admin")
    page.get_by_role("heading", name="Staff workspace").wait_for()
    assert not errors, errors
    print(
        "PASS: desktop/mobile chat, history reload, feedback, delete, XSS safety, layout overflow, staff page; no browser JavaScript errors."
    )
    browser.close()
