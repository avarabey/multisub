# MultiSub

Язык: [English](./readme.md) | **Русский**

Веб-сервис для объединения нескольких источников подписок (3x-ui и совместимых провайдеров) в одну ссылку-подписку для Shadowrocket, v2rayTun, V2Box и других V2Ray-совместимых клиентов.

## Что реализовано

- Создание, редактирование и удаление мультиподписок через веб-интерфейс.
- Добавление/удаление URL исходных подписок.
- Выдача единой ссылки `/sub/<uuid>`.
- Обработка plain-text и base64 подписок.
- Дедупликация узлов при объединении.
- Настраиваемый публичный адрес через `PUBLIC_BASE_URL`.

## Переменные окружения

- `DATABASE_URL` - строка подключения к БД (по умолчанию `multisub.db`).
- `PUBLIC_BASE_URL` - базовый публичный URL для ссылок в UI.

Примеры:

- С доменом: `PUBLIC_BASE_URL=https://example.com`
- Только IP: `PUBLIC_BASE_URL=http://203.0.113.10`

Если `PUBLIC_BASE_URL` не задан, приложение берёт адрес из `Host` запроса, поэтому режим с IP тоже работает.

## Быстрый запуск

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

## Деплой на VDS (Ubuntu 22.04)

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-venv python3-pip nginx certbot python3-certbot-nginx git

sudo mkdir -p /opt/multisub
sudo chown -R $USER:$USER /opt/multisub
git clone https://github.com/avarabey/multisub.git /opt/multisub
cd /opt/multisub

python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
.venv/bin/pytest -q
```

Установка systemd и автозапуска:

```bash
sudo cp /opt/multisub/deploy/systemd/multisub.service /etc/systemd/system/multisub.service
sudo chown -R www-data:www-data /opt/multisub
sudo systemctl daemon-reload
sudo systemctl enable --now multisub
```

Проверка и авто-перезапуск по healthcheck:

```bash
sudo cp /opt/multisub/scripts/healthcheck.sh /usr/local/bin/multisub-healthcheck.sh
sudo chmod +x /usr/local/bin/multisub-healthcheck.sh
sudo cp /opt/multisub/deploy/systemd/multisub-healthcheck.service /etc/systemd/system/
sudo cp /opt/multisub/deploy/systemd/multisub-healthcheck.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now multisub-healthcheck.timer
```

## Диагностика 502

```bash
sudo systemctl status multisub --no-pager
sudo journalctl -u multisub -n 120 --no-pager
curl -I http://127.0.0.1:8000/
sudo nginx -t
sudo tail -n 120 /var/log/nginx/error.log
```
