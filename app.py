import os
import secrets
import time
import threading
from pathlib import Path
from collections import defaultdict, deque
from urllib.parse import urlsplit
from flask import Flask, render_template, request, jsonify, session
from sqlalchemy import text
from werkzeug.security import check_password_hash, generate_password_hash
from chatbot_engine import ChatbotEngine
from database import Database


def create_app(config=None):
    app = Flask(__name__, static_folder="public/static", static_url_path="/static")
    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY") or secrets.token_hex(32),
        DATABASE_PATH=os.environ.get(
            "DATABASE_PATH", str(Path(__file__).parent / "instance" / "chatbot.sqlite3")
        ),
        DATABASE_URL=os.environ.get("DATABASE_URL"),
        ADMIN_PASSWORD_HASH=os.environ.get("ADMIN_PASSWORD_HASH", ""),
        MAX_CONTENT_LENGTH=8192,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("COOKIE_SECURE") == "true",
    )
    if not app.config["ADMIN_PASSWORD_HASH"] and os.environ.get("ADMIN_PASSWORD"):
        if len(os.environ["ADMIN_PASSWORD"]) < 12:
            raise RuntimeError("ADMIN_PASSWORD must contain at least 12 characters.")
        app.config["ADMIN_PASSWORD_HASH"] = generate_password_hash(
            os.environ["ADMIN_PASSWORD"]
        )
    if config:
        app.config.update(config)
    if os.environ.get("VERCEL") and not app.config.get("TESTING"):
        if not os.environ.get("SECRET_KEY") or not app.config["DATABASE_URL"]:
            raise RuntimeError(
                "Vercel requires SECRET_KEY and DATABASE_URL for stable sessions and persistent storage."
            )
        app.config["SESSION_COOKIE_SECURE"] = True
    db = Database(app.config["DATABASE_PATH"], app.config["DATABASE_URL"])
    bot = ChatbotEngine()
    lock = threading.RLock()
    bot.load(db.entries(bot.entries, seed=True))
    app.extensions.update(database=db, chatbot=bot)
    limits = defaultdict(deque)
    rate_lock = threading.Lock()

    def user():
        if "user_id" not in session:
            session["user_id"] = secrets.token_hex(16)
        return session["user_id"]

    @app.before_request
    def protect():
        if request.method in ("POST", "PUT", "DELETE"):
            origin = request.headers.get("Origin")
            if origin and urlsplit(origin).netloc != request.host:
                return jsonify(error="Cross-origin requests are not allowed."), 403
            if not request.is_json:
                return jsonify(error="Send application/json."), 415
            if request.headers.get("X-CSRF-Token") != session.get(
                "csrf"
            ) or not session.get("csrf"):
                return jsonify(error="Refresh the page and try again."), 403
            if not app.config.get("TESTING"):
                key = request.remote_addr
                now = time.monotonic()
                with rate_lock:
                    for old in list(limits):
                        if not limits[old] or now - limits[old][-1] > 60:
                            del limits[old]
                    bucket = limits[key]
                    while bucket and now - bucket[0] > 60:
                        bucket.popleft()
                    if len(bucket) >= 30:
                        return (
                            jsonify(error="Too many requests. Please wait a minute."),
                            429,
                        )
                    bucket.append(now)

    @app.after_request
    def headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        )
        if request.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.errorhandler(413)
    def too_large(error):
        return jsonify(error="Request is too large."), 413

    @app.errorhandler(400)
    def bad_request(error):
        return jsonify(error="Invalid JSON request."), 400

    def page(name):
        user()
        session.setdefault("csrf", secrets.token_hex(32))
        return render_template(name, csrf=session["csrf"])

    @app.get("/")
    def home():
        return page("index.html")

    @app.get("/admin")
    def admin():
        return page("admin.html")

    @app.get("/healthz")
    def health():
        with db.connect() as conn:
            conn.execute(text("SELECT 1")).fetchone()
        return jsonify(status="ok")

    @app.get("/api/topics")
    def topics():
        with lock:
            return jsonify(
                topics=[
                    {k: e[k] for k in ("intent", "title", "category")}
                    for e in bot.entries
                ]
            )

    @app.post("/api/chat")
    def chat():
        start = time.perf_counter()
        data = request.get_json()
        message = data.get("message") if isinstance(data, dict) else None
        if not isinstance(message, str) or not message.strip() or len(message) > 1000:
            return (
                jsonify(error="Enter a question between 1 and 1,000 characters."),
                400,
            )
        with lock:
            # Reload shared database so edits reach every production worker.
            entries = db.entries(bot.entries)
            if entries != bot.entries:
                bot.load(entries)
            result = bot.match(message.strip())
        latency = round(time.perf_counter() - start, 4)
        query = db.save(user(), message.strip(), result, latency)
        return jsonify(**result, latency_seconds=latency, query_id=query)

    @app.get("/api/history")
    def history():
        return jsonify(messages=db.history(user()))

    @app.delete("/api/history")
    def clear():
        db.clear(user())
        return jsonify(ok=True)

    @app.post("/api/feedback")
    def feedback():
        data = request.get_json()
        if (
            not isinstance(data, dict)
            or type(data.get("query_id")) is not int
            or type(data.get("rating")) is not int
            or data["rating"] not in (-1, 1)
        ):
            return jsonify(error="Invalid feedback."), 400
        if not db.rate(user(), data["query_id"], data["rating"]):
            return jsonify(error="Message not found."), 404
        return jsonify(ok=True)

    @app.post("/api/admin/login")
    def login():
        stored = app.config["ADMIN_PASSWORD_HASH"]
        if not stored:
            return (
                jsonify(
                    error="Admin access is not configured. Set ADMIN_PASSWORD_HASH securely on the server."
                ),
                503,
            )
        data = request.get_json()
        password = data.get("password") if isinstance(data, dict) else None
        if not isinstance(password, str) or not check_password_hash(stored, password):
            return jsonify(error="Incorrect password."), 401
        session["admin"] = True
        return jsonify(ok=True)

    @app.post("/api/admin/logout")
    def logout():
        session.pop("admin", None)
        return jsonify(ok=True)

    @app.get("/api/admin/data")
    def admin_data():
        if not session.get("admin"):
            return jsonify(error="Sign in to continue."), 401
        with lock:
            entries = db.entries(bot.entries)
        return jsonify(stats=db.stats(), entries=entries)

    @app.put("/api/admin/knowledge/<intent>")
    def edit(intent):
        if not session.get("admin"):
            return jsonify(error="Sign in to continue."), 401
        data = request.get_json()
        if not isinstance(data, dict):
            return jsonify(error="Invalid entry."), 400
        with lock:
            entries = db.entries(bot.entries)
            entry = next((e for e in entries if e["intent"] == intent), None)
            if not entry:
                return jsonify(error="Topic not found."), 404
            for key in ("response", "source"):
                value = data.get(key)
                if not isinstance(value, str) or not value.strip() or len(value) > 3000:
                    return jsonify(error="Provide a valid response and source."), 400
                entry[key] = value.strip()
            examples = data.get("examples")
            if examples is not None:
                if (
                    not isinstance(examples, list)
                    or not 2 <= len(examples) <= 30
                    or any(
                        not isinstance(x, str) or not x.strip() or len(x) > 200
                        for x in examples
                    )
                ):
                    return (
                        jsonify(
                            error="Provide 2 to 30 example questions, up to 200 characters each."
                        ),
                        400,
                    )
                entry["examples"] = [x.strip() for x in examples]
            db.update_entry(entry)
        return jsonify(ok=True)

    return app


app = create_app()
if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", "5000")), debug=False)
