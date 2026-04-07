# Google Earth Topo

Минимальный Python-сервер, который:

- проксирует XYZ-тайлы OpenStreetMap через `/tiles/{z}/{x}/{y}.png`
- отдает KML SuperOverlay через `/kml/...`, чтобы Google Earth мог загружать тайлы не зная про схему XYZ

## Запуск

```bash
python app.py
```

По умолчанию сервер стартует на `http://localhost:9088`.

## Полезные URL

- Корневой KML: `http://localhost:9088/kml/root.kml`
- Пример тайла: `http://localhost:9088/tiles/0/0/0.png`

## Переменные окружения

- `HOST` - адрес bind, по умолчанию `0.0.0.0`
- `PORT` - порт сервера, по умолчанию `9088`
- `BASE_URL` - внешний URL сервера; если не задан, определяется из заголовков запроса
- `TILE_SOURCE_TEMPLATE` - шаблон источника тайлов, по умолчанию `https://a.tile.opentopomap.org/{z}/{x}/{y}.png`
- `MAX_ZOOM` - максимальная глубина KML-дерева, по умолчанию `17`
- `MIN_LOD_PIXELS` - порог детализации для KML Region, по умолчанию `128`
- `MAX_LOD_PIXELS` - верхний порог детализации для KML Region, по умолчанию `-1`

## Как использовать в Google Earth

1. Запустить сервер.
2. Открыть в Google Earth ссылку `http://localhost:9088/kml/root.kml`.
3. Google Earth начнет загружать KML-узлы и соответствующие им PNG-тайлы через ваш сервер.

## Замечания

- Сервер намеренно без фреймворков, чтобы первый запуск был простым.
- По умолчанию используется OpenTopoMap. Официальная схема у сервиса публикуется как `https://{a|b|c}.tile.opentopomap.org/{z}/{x}/{y}.png`; в этом прототипе выбран сервер `a`.
- Для production имеет смысл добавить локальный кэш тайлов, rate limiting и более аккуратную работу с upstream.
