# Release Notes

## 2026-02-13

### Added
- Добавлена поддержка настраиваемого публичного URL через переменную окружения `PUBLIC_BASE_URL`.
- Добавлен fallback на `Host` из запроса, если `PUBLIC_BASE_URL` не задан.
- Добавлен healthcheck-скрипт `/scripts/healthcheck.sh`.
- Добавлены systemd unit-файлы для авто-проверки и самовосстановления:
  - `deploy/systemd/multisub-healthcheck.service`
  - `deploy/systemd/multisub-healthcheck.timer`
- Добавлен шаблон основного systemd-сервиса в репозиторий:
  - `deploy/systemd/multisub.service`

### Changed
- Обновлена генерация ссылки подписки в UI: теперь используется `public_base_url` вместо захардкоженного домена.
- Улучшена агрегация подписок:
  - корректная обработка plain/base64 источников,
  - дедупликация узлов в итоговой подписке.
- README полностью обновлен под деплой на VDS:
  - сценарий с доменом `ffknd.ru`,
  - сценарий только с IP,
  - инструкции по автозапуску и healthcheck.

### Fixed
- Исправлена проблема запуска под production, добавлена зависимость `gunicorn` в `requirements.txt`.
- Устранен риск копирования некорректной ссылки подписки из UI.

### Tests
- Добавлены тесты на:
  - работу `PUBLIC_BASE_URL`,
  - fallback на IP/Host,
  - агрегацию mixed (base64 + plain) источников.
- Актуальный статус тестов: `4 passed`.
