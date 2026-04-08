# Google Earth Topo

Минимальный Python-сервер, который:

- проксирует XYZ-тайлы OpenTopoMap через `/tiles/{z}/{x}/{y}.png`
- отдает KML SuperOverlay через `/kml/...`, чтобы Google Earth мог загружать тайлы не зная про схему XYZ
- в docker-режиме работает вместе с `nginx`, который кэширует тайлы на диске

## Запуск

```bash
python app.py
```

По умолчанию сервер стартует на `http://localhost`.

В standalone-режиме Python сам обрабатывает `/tiles/...` и может ходить в upstream тайлов напрямую.

## Запуск через Docker Compose

```bash
docker compose up --build -d
```

Основной `docker-compose.yml` не публикует порты наружу. Сервис слушает внутри контейнера `80` и рассчитан на reverse proxy или общую docker-сеть.
В docker-режиме тайлы `/tiles/...` забирает и кэширует `nginx`; Python в этой схеме нужен для `/kml/...` и других будущих KML-слоев.

## Запуск через Docker Compose для разработки

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build -d
```

В dev-режиме сервис будет доступен на `http://localhost:9088/kml/root.kml`.
Внешний порт для dev задается через `APP_PORT`, по умолчанию `9088`.

Логи запросов будут сохраняться в `./data/server.log`.
Кэш тайлов `nginx` будет храниться в `./data/nginx-cache`, а его логи в `./data/nginx-logs`.

## Полезные URL

- Корневой KML: `http://localhost:9088/kml/root.kml`
- Пример тайла: `http://localhost:9088/tiles/0/0/0.png`

## Переменные окружения

- `PORT` - порт, на котором слушает standalone Python, по умолчанию `80`
- `PUBLIC_PORT` - внешний порт, который используется при генерации абсолютных KML URL, по умолчанию равен `PORT`
- `BASE_URL` - внешний URL сервера; если не задан, определяется из заголовков запроса
- `TILE_SOURCE_TEMPLATE` - шаблон источника тайлов для standalone-режима Python, по умолчанию `https://a.tile.opentopomap.org/{z}/{x}/{y}.png`
- `MAX_ZOOM` - максимальная глубина KML-дерева, по умолчанию `17`
- `MIN_LOD_PIXELS` - порог детализации для KML Region, по умолчанию `128`
- `MAX_LOD_PIXELS` - верхний порог детализации для KML Region, по умолчанию `-1`
- `LIVE_POINT_REFRESH_SECONDS` - как часто Google Earth запрашивает live-точку, по умолчанию `5`
- `LIVE_POINT_CENTER_LAT` - широта центра тестового движения, по умолчанию `43.238949`
- `LIVE_POINT_CENTER_LON` - долгота центра тестового движения, по умолчанию `76.889709`
- `LIVE_POINT_RADIUS_DEGREES` - радиус движения в градусах, по умолчанию `0.01`
- `LIVE_POINT_PERIOD_SECONDS` - полный период круга для тестовой точки, по умолчанию `600`

## Как использовать в Google Earth

1. Запустить сервер.
2. Открыть в Google Earth ссылку `http://localhost/kml/root.kml` для standalone на порту `80`, `http://localhost:9088/kml/root.kml` для dev compose или адрес своего reverse proxy для обычного Docker Compose.
3. Google Earth начнет загружать KML-узлы и соответствующие им PNG-тайлы через ваш сервер.

## Замечания

- Сервер намеренно без фреймворков, чтобы первый запуск был простым.
- Адрес bind не настраивается: сервер всегда слушает `0.0.0.0`.
- По умолчанию используется OpenTopoMap. Официальная схема у сервиса публикуется как `https://{a|b|c}.tile.opentopomap.org/{z}/{x}/{y}.png`; в этом прототипе выбран сервер `a`.
- В docker-конфигурации источник и кэш тайлов находятся в `nginx proxy_cache`, поэтому `TILE_SOURCE_TEMPLATE` там специально не дублируется.
- В `root.kml` автоматически подключается тестовая медленно движущаяся точка, чтобы можно было проверить live-обновление в Google Earth.
