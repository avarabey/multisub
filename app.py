import base64
import binascii
import logging
import os
import re
import uuid
from datetime import datetime
from urllib.parse import urlparse

import httpx
from flask import Flask, Response, abort, redirect, render_template, request, url_for
from flask_sqlalchemy import SQLAlchemy

BASE_DIR = os.path.dirname(__file__)
DEFAULT_DB_PATH = os.path.join(BASE_DIR, "multisub.db")

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", f"sqlite:///{DEFAULT_DB_PATH}")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["PUBLIC_BASE_URL"] = os.getenv("PUBLIC_BASE_URL", "").strip()

db = SQLAlchemy(app)

logging.basicConfig(level=logging.INFO)
app.logger.setLevel(logging.INFO)

PROXY_SCHEMES = (
    "vmess://",
    "vless://",
    "trojan://",
    "ss://",
    "ssr://",
    "hysteria://",
    "hy2://",
    "tuic://",
    "wireguard://",
    "socks://",
)
BASE64_RE = re.compile(r"^[A-Za-z0-9+/=\\s]+$")


def is_valid_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except Exception:
        return False


def _split_entries(payload: str) -> list[str]:
    return [line.strip() for line in payload.splitlines() if line.strip()]


def _looks_like_proxy_payload(payload: str) -> bool:
    entries = _split_entries(payload)
    if not entries:
        return False
    return any(entry.startswith(PROXY_SCHEMES) for entry in entries)


def _decode_base64_payload(payload: str) -> str | None:
    compact = "".join(payload.split())
    if not compact or not BASE64_RE.match(compact):
        return None

    padded = compact + "=" * (-len(compact) % 4)
    try:
        decoded = base64.b64decode(padded, validate=False)
    except (ValueError, binascii.Error):
        return None

    try:
        text = decoded.decode("utf-8")
    except UnicodeDecodeError:
        return None

    return text if _looks_like_proxy_payload(text) else None


def normalize_subscription_payload(payload: str) -> list[str]:
    raw = payload.strip()
    if not raw:
        return []

    decoded = _decode_base64_payload(raw)
    source = decoded if decoded is not None else raw
    return _split_entries(source)


def get_public_base_url() -> str:
    configured = app.config.get("PUBLIC_BASE_URL", "").strip()
    if configured:
        return configured.rstrip("/")
    return request.url_root.rstrip("/")


class Multisub(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    title = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    subscriptions = db.relationship("Subscription", backref="multisub", lazy=True, cascade="all, delete-orphan")


class Subscription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    multisub_id = db.Column(db.Integer, db.ForeignKey("multisub.id"), nullable=False)
    url = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


with app.app_context():
    db.create_all()


def generate_subscription_content(multisub: Multisub) -> str:
    def fetch_url(url: str, timeout: float = 8.0) -> str:
        try:
            response = httpx.get(url, timeout=timeout)
            if response.status_code == 200:
                return response.text
            app.logger.warning("Non-200 response %s for %s", response.status_code, url)
        except Exception as exc:
            app.logger.warning("Failed to fetch %s: %s", url, exc)
        return ""

    urls = [sub.url.strip() for sub in multisub.subscriptions if sub.url.strip() and is_valid_url(sub.url.strip())]

    merged_entries: list[str] = []
    seen: set[str] = set()

    for url in urls:
        payload = fetch_url(url)
        if not payload:
            continue

        for entry in normalize_subscription_payload(payload):
            if entry in seen:
                continue
            seen.add(entry)
            merged_entries.append(entry)

    if not merged_entries:
        return ""

    merged_payload = "\n".join(merged_entries)
    return base64.b64encode(merged_payload.encode("utf-8")).decode("utf-8")


@app.route("/")
def index():
    multisubs = Multisub.query.order_by(Multisub.created_at.desc()).all()
    return render_template("index.html", multisubs=multisubs, public_base_url=get_public_base_url())


@app.route("/create", methods=["GET", "POST"])
def create():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        if not title:
            abort(400, "Title is required")

        urls = request.form.getlist("urls[]")
        multisub = Multisub(title=title)
        db.session.add(multisub)
        db.session.flush()

        for url in urls:
            candidate = url.strip()
            if not candidate:
                continue
            if not is_valid_url(candidate):
                app.logger.warning("Skipping invalid URL on create: %s", candidate)
                continue
            db.session.add(Subscription(multisub_id=multisub.id, url=candidate))

        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            app.logger.exception("DB commit failed on create")
            abort(500)

        return redirect(url_for("index"))

    return render_template("edit.html", multisub=None)


@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit(id):
    multisub = Multisub.query.get_or_404(id)

    if request.method == "POST":
        multisub.title = request.form.get("title", multisub.title).strip() or multisub.title
        Subscription.query.filter_by(multisub_id=multisub.id).delete()

        urls = request.form.getlist("urls[]")
        for url in urls:
            candidate = url.strip()
            if not candidate:
                continue
            if not is_valid_url(candidate):
                app.logger.warning("Skipping invalid URL on edit: %s", candidate)
                continue
            db.session.add(Subscription(multisub_id=multisub.id, url=candidate))

        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            app.logger.exception("DB commit failed on edit")
            abort(500)

        return redirect(url_for("index"))

    return render_template("edit.html", multisub=multisub)


@app.route("/delete/<int:id>", methods=["POST"])
def delete(id):
    multisub = Multisub.query.get_or_404(id)

    try:
        db.session.delete(multisub)
        db.session.commit()
    except Exception:
        db.session.rollback()
        app.logger.exception("DB commit failed on delete")
        abort(500)

    return redirect(url_for("index"))


@app.route("/sub/<string:sub_uuid>")
def subscription(sub_uuid):
    multisub = Multisub.query.filter_by(uuid=sub_uuid).first_or_404()
    content = generate_subscription_content(multisub)
    return Response(content, mimetype="text/plain", headers={"Content-Disposition": "inline"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
