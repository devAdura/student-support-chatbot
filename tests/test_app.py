import pytest


@pytest.mark.parametrize(
    "payload",
    [
        {},
        [],
        None,
        {"message": 3},
        {"message": True},
        {"message": " "},
        {"message": "a" * 1001},
    ],
)
def test_bad_input(client, headers, payload):
    import json

    r = client.post(
        "/api/chat",
        data=json.dumps(payload),
        content_type="application/json",
        headers=headers,
    )
    assert r.status_code == 400


def test_chat_history_feedback_delete(client, headers):
    r = client.post(
        "/api/chat", json={"message": "How do I register courses?"}, headers=headers
    )
    assert r.status_code == 200
    data = r.json
    assert data["intent"] == "course_registration"
    assert data["latency_seconds"] >= 0
    history = client.get("/api/history").json["messages"]
    assert len(history) == 1 and history[0]["response"] == data["response"]
    assert (
        client.post(
            "/api/feedback",
            json={"query_id": data["query_id"], "rating": 1},
            headers=headers,
        ).status_code
        == 200
    )
    assert client.get("/api/history").json["messages"][0]["rating"] == 1
    assert client.delete("/api/history", headers=headers, json={}).status_code == 200
    assert client.get("/api/history").json["messages"] == []


def test_session_isolation(app, client, headers):
    r = client.post(
        "/api/chat", json={"message": "exam timetable"}, headers=headers
    ).json
    other = app.test_client()
    other.get("/")
    with other.session_transaction() as s:
        h = {"X-CSRF-Token": s["csrf"]}
    assert other.get("/api/history").json["messages"] == []
    assert (
        other.post(
            "/api/feedback", json={"query_id": r["query_id"], "rating": 1}, headers=h
        ).status_code
        == 404
    )
    assert other.delete("/api/history", headers=h, json={}).status_code == 200
    assert len(client.get("/api/history").json["messages"]) == 1


def test_security(client, headers):
    assert client.post("/api/chat", json={"message": "hello"}).status_code == 403
    assert (
        client.post(
            "/api/chat",
            json={"message": "hello"},
            headers={**headers, "Origin": "https://evil.example"},
        ).status_code
        == 403
    )
    assert client.post("/api/chat", data="text", headers=headers).status_code == 415
    assert client.get("/api/admin/data").status_code == 401
    assert (
        client.put(
            "/api/admin/knowledge/results",
            json={"response": "attack", "source": "fake"},
            headers=headers,
        ).status_code
        == 401
    )
    assert "default-src 'self'" in client.get("/").headers["Content-Security-Policy"]


def test_admin_edit_metrics_and_logout(client, headers):
    assert (
        client.post(
            "/api/admin/login", json={"password": "wrong"}, headers=headers
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/api/admin/login", json={"password": "test-only-password"}, headers=headers
        ).status_code
        == 200
    )
    entry = client.get("/api/admin/data").json["entries"][0]
    assert (
        client.put(
            "/api/admin/knowledge/" + entry["intent"],
            json={"response": "Verified test guidance.", "source": "Test handbook"},
            headers=headers,
        ).status_code
        == 200
    )
    result = client.post(
        "/api/chat", json={"message": "How do I register courses?"}, headers=headers
    ).json
    assert (
        result["response"] == "Verified test guidance."
        and result["source"] == "Test handbook"
    )
    stats = client.get("/api/admin/data").json["stats"]
    assert stats["total"] == 1 and stats["fallbacks"] == 0
    assert client.post("/api/admin/logout", json={}, headers=headers).status_code == 200
    assert client.get("/api/admin/data").status_code == 401


def test_disabled_admin(app, client, headers):
    app.config["ADMIN_PASSWORD_HASH"] = ""
    assert (
        client.post(
            "/api/admin/login", json={"password": "any"}, headers=headers
        ).status_code
        == 503
    )


def test_unknown_and_ambiguous(client, headers):
    for query in [
        "quantum banana spaceship",
        "date",
        "the",
        "a",
        "write me a poem about rain",
    ]:
        r = client.post("/api/chat", json={"message": query}, headers=headers)
        assert r.status_code == 200 and r.json["intent"] == "fallback"


def test_health_and_topics(client):
    assert client.get("/healthz").json == {"status": "ok"}
    assert len(client.get("/api/topics").json["topics"]) == 12


def test_no_invented_deadline(client, headers):
    text = client.post(
        "/api/chat", json={"message": "fee deadline"}, headers=headers
    ).json["response"]
    assert "no verified" in text


def test_xss_stored_as_plain_text(client, headers):
    text = "<img src=x onerror=alert(1)>"
    assert (
        client.post("/api/chat", json={"message": text}, headers=headers).status_code
        == 200
    )
    assert client.get("/api/history").json["messages"][0]["message"] == text
    assert "<img src=x" not in client.get("/").text


def test_payload_limit(client, headers):
    assert (
        client.post(
            "/api/chat", json={"message": "a" * 9000}, headers=headers
        ).status_code
        == 413
    )


def test_invalid_feedback(client, headers):
    for value in [
        None,
        [],
        {"rating": True, "query_id": 1},
        {"rating": 2, "query_id": 1},
    ]:
        import json

        assert (
            client.post(
                "/api/feedback",
                data=json.dumps(value),
                content_type="application/json",
                headers=headers,
            ).status_code
            == 400
        )


def test_staff_can_improve_matching_examples(client, headers):
    client.post(
        "/api/admin/login", json={"password": "test-only-password"}, headers=headers
    )
    data = {
        "response": "Ask the bursary about approved aid.",
        "source": "Verified test handbook",
        "examples": [
            "financial aid for students",
            "bursary grants and hardship assistance",
        ],
    }
    assert (
        client.put(
            "/api/admin/knowledge/scholarship", json=data, headers=headers
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/api/chat",
            json={"message": "bursary grants and hardship assistance"},
            headers=headers,
        ).json["intent"]
        == "scholarship"
    )
    data["examples"] = ["only one"]
    assert (
        client.put(
            "/api/admin/knowledge/scholarship", json=data, headers=headers
        ).status_code
        == 400
    )


def test_production_requires_persistent_configuration(monkeypatch, tmp_path):
    from app import create_app

    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.delenv("SECRET_KEY", raising=False)
    with pytest.raises(RuntimeError, match="Vercel requires"):
        create_app(
            {
                "TESTING": False,
                "DATABASE_URL": None,
                "DATABASE_PATH": str(tmp_path / "unusable.sqlite3"),
            }
        )
