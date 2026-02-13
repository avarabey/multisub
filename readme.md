# MultiSub

Веб-сервис для объединения нескольких подписок (3x-ui и совместимые источники) в одну мультиподписку для клиентов Shadowrocket, v2rayTun, V2Box и других V2Ray-совместимых приложений.

## Что уже реализовано

- Создание, редактирование и удаление мультиподписок через веб-интерфейс.
- Добавление/удаление URL исходных подписок.
- Выдача единой ссылки вида `/sub/<uuid>`.
- Агрегация как plain-текста, так и base64-подписок.
- Дедупликация узлов при объединении.

## Технологии

- Python 3.10+
- Flask
- SQLAlchemy
- httpx
- SQLite (по умолчанию)

## Структура

- `app.py` - Flask-приложение, маршруты и логика агрегации.
- `templates/index.html` - список мультиподписок.
- `templates/edit.html` - форма создания/редактирования.
- `tests/test_app.py` - тесты агрегации.

## Локальный запуск

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Открыть: `http://127.0.0.1:5000`

Запуск тестов:

```bash
.venv/bin/pytest -q
```

## Развертывание на VDS (Ubuntu 22.04)

Ниже инструкция для продакшн-схемы: `gunicorn + systemd + nginx + HTTPS`.

### 1. Подготовка сервера

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-venv python3-pip nginx certbot python3-certbot-nginx git
```

### 2. Клонирование проекта

```bash
sudo mkdir -p /opt/multisub
sudo chown -R $USER:$USER /opt/multisub
git clone <URL_ВАШЕГО_РЕПОЗИТОРИЯ> /opt/multisub
cd /opt/multisub
```

### 3. Виртуальное окружение и зависимости

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Проверка приложения

```bash
.venv/bin/pytest -q
```

Если тесты прошли, продолжаем.

### 5. systemd-сервис

Создать файл `/etc/systemd/system/multisub.service`:

```ini
[Unit]
Description=MultiSub Flask Service
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/opt/multisub
Environment="PATH=/opt/multisub/.venv/bin"
Environment="DATABASE_URL=sqlite:////opt/multisub/multisub.db"
ExecStart=/opt/multisub/.venv/bin/gunicorn --workers 2 --bind 127.0.0.1:8000 app:app
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

Выдать доступ и запустить:

```bash
sudo chown -R www-data:www-data /opt/multisub
sudo systemctl daemon-reload
sudo systemctl enable multisub
sudo systemctl start multisub
sudo systemctl status multisub --no-pager
```

### 6. Конфиг nginx

Создать файл `/etc/nginx/sites-available/multisub`:

```nginx
server {
    listen 80;
    server_name sub.example.com;

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

Активировать сайт:

```bash
sudo ln -s /etc/nginx/sites-available/multisub /etc/nginx/sites-enabled/multisub
sudo nginx -t
sudo systemctl reload nginx
```

### 7. HTTPS сертификат

Убедиться, что DNS-запись домена указывает на VDS, затем:

```bash
sudo certbot --nginx -d sub.example.com
sudo certbot renew --dry-run
```

## Проверка после деплоя

- Открыть `https://sub.example.com`
- Создать тестовую мультиподписку
- Добавить 1-2 URL подписок
- Скопировать ссылку `/sub/<uuid>` и проверить импорт в клиенте

## Маршруты приложения

- `GET /` - список мультиподписок
- `GET /create` - форма создания
- `POST /create` - создание
- `GET /edit/<id>` - форма редактирования
- `POST /edit/<id>` - обновление
- `POST /delete/<id>` - удаление
- `GET /sub/<uuid>` - выдача агрегированной подписки (base64)

## Типовые проблемы

1. `502 Bad Gateway`:
- проверить `sudo systemctl status multisub`
- проверить `sudo journalctl -u multisub -n 100 --no-pager`
- проверить `sudo nginx -t`

2. Пустой ответ по `/sub/<uuid>`:
- проверить доступность исходных URL
- убедиться, что источники возвращают 200
- посмотреть логи сервиса (`journalctl`)

3. После обновления кода изменения не применились:

```bash
cd /opt/multisub
sudo systemctl restart multisub
```

## Обновление проекта на VDS

```bash
cd /opt/multisub
git pull
source .venv/bin/activate
pip install -r requirements.txt
.venv/bin/pytest -q
sudo systemctl restart multisub
```
