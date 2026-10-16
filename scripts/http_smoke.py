"""Exercise a live deployment through verified HTTPS without browser automation."""

import http.cookiejar
import json
import os
import re
import ssl
import time
import urllib.error
import urllib.request

base = os.environ.get("BASE_URL", "http://127.0.0.1:5000").rstrip("/")
jar = http.cookiejar.CookieJar()
client = urllib.request.build_opener(
    urllib.request.HTTPCookieProcessor(jar),
    urllib.request.HTTPSHandler(context=ssl.create_default_context()),
)


def request(path, method="GET", body=None, csrf=None):
    headers = {}
    if body is not None:
        headers["Content-Type"] = "application/json"
    if csrf:
        headers["X-CSRF-Token"] = csrf
    req = urllib.request.Request(
        base + path,
        method=method,
        data=None if body is None else json.dumps(body).encode(),
        headers=headers,
    )
    with client.open(req, timeout=60) as response:
        return response.status, response.headers, response.read().decode()


assert json.loads(request("/healthz")[2]) == {"status": "ok"}
status, headers, html = request("/")
assert status == 200 and "Campus life," in html and "made clearer." in html
if base.startswith("https:"):
    assert "Secure" in headers.get("Set-Cookie", "")
csrf = re.search(r'name="csrf-token" content="([^"]+)"', html).group(1)
try:
    for path, kind in [
        ("/static/js/chat.js", "javascript"),
        ("/static/css/style.css", "css"),
    ]:
        code, response_headers, asset = request(path)
        assert code == 200 and kind in response_headers["Content-Type"] and asset
    start = time.perf_counter()
    data = json.loads(
        request("/api/chat", "POST", {"message": "How do I register courses?"}, csrf)[2]
    )
    elapsed = time.perf_counter() - start
    assert data["intent"] == "course_registration" and "portal" in data["response"]
    history = json.loads(request("/api/history")[2])["messages"]
    assert len(history) == 1 and history[0]["id"] == data["query_id"]
    assert json.loads(
        request(
            "/api/feedback", "POST", {"query_id": data["query_id"], "rating": 1}, csrf
        )[2]
    )["ok"]
    assert json.loads(request("/api/history")[2])["messages"][0]["rating"] == 1
    try:
        request("/api/admin/data")
        raise AssertionError("Anonymous staff access was allowed.")
    except urllib.error.HTTPError as error:
        assert error.code == 401
    try:
        request("/api/chat", "POST", {"message": "hello"})
        raise AssertionError("Missing CSRF token was allowed.")
    except urllib.error.HTTPError as error:
        assert error.code == 403
    print(
        "PASS: health, HTML, assets, secure production cookie, chat, persistent history, feedback, staff access control and CSRF."
    )
    print(f"One end-to-end chat request: {elapsed:.3f}s (not a performance benchmark).")
finally:
    assert json.loads(request("/api/history", "DELETE", {}, csrf)[2])["ok"]
    assert json.loads(request("/api/history")[2])["messages"] == []
    print("PASS: this smoke-test session’s data was deleted.")
