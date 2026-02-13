import base64

import httpx
import pytest

from app import Multisub, Subscription, app, db


@pytest.fixture
def client():
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["PUBLIC_BASE_URL"] = ""
    with app.app_context():
        db.drop_all()
        db.create_all()
        yield app.test_client()


def test_subscription_aggregation(monkeypatch, client):
    with app.app_context():
        ms = Multisub(title="test-multi")
        db.session.add(ms)
        db.session.flush()
        db.session.add(Subscription(multisub_id=ms.id, url="https://example.com/sub"))
        db.session.commit()
        uid = ms.uuid

    class DummyResp:
        def __init__(self, text, status_code=200):
            self.text = text
            self.status_code = status_code

    def fake_get(url, timeout=5.0):
        return DummyResp("serverA\nserverB")

    monkeypatch.setattr(httpx, "get", fake_get)

    resp = client.get(f"/sub/{uid}")
    assert resp.status_code == 200
    encoded = resp.get_data(as_text=True)
    assert encoded
    decoded = base64.b64decode(encoded.encode("utf-8")).decode("utf-8")
    assert "serverA" in decoded
    assert "serverB" in decoded


def test_merges_base64_and_plain_sources(monkeypatch, client):
    with app.app_context():
        ms = Multisub(title="mixed")
        db.session.add(ms)
        db.session.flush()
        db.session.add(Subscription(multisub_id=ms.id, url="https://example.com/sub1"))
        db.session.add(Subscription(multisub_id=ms.id, url="https://example.com/sub2"))
        db.session.commit()
        uid = ms.uuid

    encoded_source = base64.b64encode("vmess://a\nvmess://b".encode("utf-8")).decode("utf-8")

    class DummyResp:
        def __init__(self, text, status_code=200):
            self.text = text
            self.status_code = status_code

    def fake_get(url, timeout=5.0):
        if url.endswith("sub1"):
            return DummyResp(encoded_source)
        return DummyResp("vmess://b\nvmess://c")

    monkeypatch.setattr(httpx, "get", fake_get)

    resp = client.get(f"/sub/{uid}")
    assert resp.status_code == 200

    decoded = base64.b64decode(resp.get_data(as_text=True)).decode("utf-8")
    assert decoded.splitlines() == ["vmess://a", "vmess://b", "vmess://c"]


def test_index_uses_configured_public_base_url(client):
    app.config["PUBLIC_BASE_URL"] = "https://example.com/"
    with app.app_context():
        ms = Multisub(title="public-url")
        db.session.add(ms)
        db.session.commit()
        uid = ms.uuid

    resp = client.get("/")
    body = resp.get_data(as_text=True)
    assert resp.status_code == 200
    assert f"https://example.com/sub/{uid}" in body


def test_index_falls_back_to_request_host(client):
    with app.app_context():
        ms = Multisub(title="request-host")
        db.session.add(ms)
        db.session.commit()
        uid = ms.uuid

    resp = client.get("/", base_url="http://203.0.113.10")
    body = resp.get_data(as_text=True)
    assert resp.status_code == 200
    assert f"http://203.0.113.10/sub/{uid}" in body
