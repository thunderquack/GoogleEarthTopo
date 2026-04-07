# Google Earth Topo

Минимальный Python-сервер, который:

- проксирует XYZ-тайлы OpenTopoMap через `/tiles/{z}/{x}/{y}.png`
- отдает KML SuperOverlay через `/kml/...`, чтобы Google Earth мог загружать тайлы не зная про схему XYZ

## Запуск

```bash
python app.py
```

По умолчанию сервер стартует на `http://localhost:9088`.

## Запуск через Docker Compose

```bash
docker compose up --build -d
```

Основной `docker-compose.yml` не публикует порты наружу. Сервис слушает внутри контейнера `80` и рассчитан на reverse proxy или общую docker-сеть.

## Запуск через Docker Compose для разработки

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build -d
```

В dev-режиме сервис будет доступен на `http://localhost:9088/kml/root.kml`.

Логи запросов будут сохраняться в `./data/server.log`.

## Полезные URL

- Корневой KML: `http://localhost:9088/kml/root.kml`
- Пример тайла: `http://localhost:9088/tiles/0/0/0.png`

## Переменные окружения

- `PORT` - порт сервера, по умолчанию `9088`
- `BASE_URL` - внешний URL сервера; если не задан, определяется из заголовков запроса
- `TILE_SOURCE_TEMPLATE` - шаблон источника тайлов, по умолчанию `https://a.tile.opentopomap.org/{z}/{x}/{y}.png`
- `MAX_ZOOM` - максимальная глубина KML-дерева, по умолчанию `17`
- `MIN_LOD_PIXELS` - порог детализации для KML Region, по умолчанию `128`
- `MAX_LOD_PIXELS` - верхний порог детализации для KML Region, по умолчанию `-1`

## Как использовать в Google Earth

1. Запустить сервер.
2. Открыть в Google Earth ссылку `http://localhost:9088/kml/root.kml` для локального Python-запуска или dev compose. Для обычного Docker Compose используй адрес своего reverse proxy или имя контейнера внутри docker-сети.
3. Google Earth начнет загружать KML-узлы и соответствующие им PNG-тайлы через ваш сервер.

## Замечания

- Сервер намеренно без фреймворков, чтобы первый запуск был простым.
- Адрес bind не настраивается: сервер всегда слушает `0.0.0.0`.
- По умолчанию используется OpenTopoMap. Официальная схема у сервиса публикуется как `https://{a|b|c}.tile.opentopomap.org/{z}/{x}/{y}.png`; в этом прототипе выбран сервер `a`.
- Для production имеет смысл добавить локальный кэш тайлов, rate limiting и более аккуратную работу с upstream.
