# MultiSub

Language: **English** | [Русский](./readme.ru.md)

A web service that merges multiple subscription sources (3x-ui and compatible providers) into a single subscription URL for Shadowrocket, v2rayTun, V2Box, and other V2Ray-compatible clients.

## Implemented Features

- Create, edit, and delete multi-subscriptions via web UI.
- Add/remove source subscription URLs.
- Serve one merged URL in the format `/sub/<uuid>`.
- Handle both plain-text and base64 source subscriptions.
- Deduplicate nodes during merge.
- Configurable public base URL via `PUBLIC_BASE_URL`.

## Stack

- Python 3.10+
- Flask
- SQLAlchemy
- httpx
- SQLite (default)

## Project Structure

- `app.py` - Flask app, routes, and merge logic.
- `templates/index.html` - multi-subscription list page.
- `templates/edit.html` - create/edit form.
- `tests/test_app.py` - aggregation and public URL tests.
- `scripts/healthcheck.sh` - health probe with self-heal restart.
- `deploy/systemd/*.service|*.timer` - systemd units.

## Environment Variables

- `DATABASE_URL` - DB connection string (default: local `multisub.db`).
- `PUBLIC_BASE_URL` - public base URL used in UI-generated subscription links.

Examples:

- Domain: `PUBLIC_BASE_URL=https://example.com`
- IP-only server: `PUBLIC_BASE_URL=http://203.0.113.10`

If `PUBLIC_BASE_URL` is not set, the app falls back to request host (`Host` header), so IP-only deployment still works.

## Local Run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open: `http://127.0.0.1:5000`

Run tests:

```bash
.venv/bin/pytest -q
```

## Deploy on VDS (Ubuntu 22.04)

Production layout: `gunicorn + systemd + nginx`.

### 1. Prepare Server

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-venv python3-pip nginx certbot python3-certbot-nginx git
```

### 2. Clone Project

```bash
sudo mkdir -p /opt/multisub
sudo chown -R $USER:$USER /opt/multisub
git clone https://github.com/avarabey/multisub.git /opt/multisub
cd /opt/multisub
```

### 3. Create Virtualenv and Install Dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Validate App

```bash
.venv/bin/pytest -q
```

### 5. Configure Public URL

Choose one:

- Domain: `PUBLIC_BASE_URL=https://example.com`
- IP only: `PUBLIC_BASE_URL=http://<YOUR_VDS_IP>`

### 6. Install Main systemd Service (Autostart)

Project template: `deploy/systemd/multisub.service`.

```bash
sudo cp /opt/multisub/deploy/systemd/multisub.service /etc/systemd/system/multisub.service
```

If needed, edit `/etc/systemd/system/multisub.service` and set:

```ini
Environment="PUBLIC_BASE_URL=https://example.com"
```

or

```ini
Environment="PUBLIC_BASE_URL=http://<YOUR_VDS_IP>"
```

Enable autostart and run:

```bash
sudo chown -R www-data:www-data /opt/multisub
sudo systemctl daemon-reload
sudo systemctl enable --now multisub
sudo systemctl status multisub --no-pager
```

### 7. Configure Nginx

Create `/etc/nginx/sites-available/multisub`.

Domain variant:

```nginx
server {
    listen 80;
    server_name example.com www.example.com;

    client_max_body_size 10m;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

IP-only variant:

```nginx
server {
    listen 80 default_server;
    server_name _;

    client_max_body_size 10m;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable and reload:

```bash
sudo ln -s /etc/nginx/sites-available/multisub /etc/nginx/sites-enabled/multisub
sudo nginx -t
sudo systemctl reload nginx
```

### 8. TLS (Domain Only)

```bash
sudo certbot --nginx -d example.com -d www.example.com
sudo certbot renew --dry-run
```

If you only have IP, run over HTTP: `http://<YOUR_VDS_IP>`.

### 9. Periodic Healthcheck + Auto-Restart

Prepared files:

- `scripts/healthcheck.sh`
- `deploy/systemd/multisub-healthcheck.service`
- `deploy/systemd/multisub-healthcheck.timer`

Install:

```bash
sudo cp /opt/multisub/scripts/healthcheck.sh /usr/local/bin/multisub-healthcheck.sh
sudo chmod +x /usr/local/bin/multisub-healthcheck.sh
sudo cp /opt/multisub/deploy/systemd/multisub-healthcheck.service /etc/systemd/system/
sudo cp /opt/multisub/deploy/systemd/multisub-healthcheck.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now multisub-healthcheck.timer
sudo systemctl status multisub-healthcheck.timer --no-pager
```

Healthcheck behavior:

- Runs every minute.
- Checks `http://127.0.0.1:8000/`.
- If unhealthy, restarts `multisub.service`.

Logs:

```bash
sudo journalctl -u multisub-healthcheck.service -n 50 --no-pager
```

## Routes

- `GET /` - list multisubscriptions
- `GET /create` - create form
- `POST /create` - create entity
- `GET /edit/<id>` - edit form
- `POST /edit/<id>` - update entity
- `POST /delete/<id>` - delete entity
- `GET /sub/<uuid>` - merged subscription response (base64)

## Quick 502 Diagnostics

```bash
sudo systemctl status multisub --no-pager
sudo journalctl -u multisub -n 120 --no-pager
curl -I http://127.0.0.1:8000/
sudo nginx -t
sudo tail -n 120 /var/log/nginx/error.log
```

## Update on VDS

```bash
cd /opt/multisub
git pull
source .venv/bin/activate
pip install -r requirements.txt
.venv/bin/pytest -q
sudo systemctl restart multisub
```
