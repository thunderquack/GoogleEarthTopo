# Google Earth Topo

Минимальный стек для Google Earth, который:

- проксирует XYZ-тайлы OpenTopoMap через `/tiles/{z}/{x}/{y}.png`
- отдает KML SuperOverlay через `/kml/...`, чтобы Google Earth мог загружать тайлы без знания XYZ-схемы
- принимает реальные координаты из DMR через `rtl-sdr -> DSD-FME -> parser`
- рисует live-точку и live-трек по последнему декодированному GPS fix
- в docker-режиме работает вместе с `nginx`, который кэширует тайлы на диске

## Архитектура

```text
rtl-sdr -> dmr-decoder (DSD-FME) -> /data/dmr/raw.log
                                     |
                                     v
                               dmr-parser
                         -> /data/dmr/latest.json
                         -> /data/dmr/history.jsonl
                                     |
                                     v
                           google-earth-topo (Python)
                         -> /kml/live-point.kml
                         -> /kml/live-track.kml
                         -> /api/live-point.json
                         -> /api/live-track.json
```

## Сервисы

- `google-earth-topo` — Python-сервер с KML и debug JSON endpoints
- `dmr-decoder` — контейнер с `DSD-FME`, читает `rtl-sdr` на `430.300 MHz`
- `dmr-parser` — парсит `DSD-FME` лог и сохраняет последнюю точку и историю
- `nginx` — reverse proxy и tile cache

## Требования

- Linux-хост с Docker Compose
- подключенный `rtl-sdr`
- внешняя docker-сеть `pidor-net`

Проверка донгла на хосте:

```bash
rtl_test -t
```

Если устройство занято DVB-драйвером:

```bash
sudo modprobe -r dvb_usb_rtl28xxu rtl2832 rtl2830
```

Чтобы отключение сохранилось:

```bash
echo "blacklist dvb_usb_rtl28xxu" | sudo tee /etc/modprobe.d/blacklist-rtl-sdr.conf
```

## Запуск через Docker Compose

```bash
docker compose up --build -d
```

Основной `docker-compose.yml` не публикует порты наружу. Сервис слушает внутри контейнера `80` и рассчитан на reverse proxy или общую docker-сеть.

## Запуск через Docker Compose для разработки

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build -d
```

В dev-режиме сервис будет доступен на `http://localhost:9088`.
Внешний порт задается через `APP_PORT`, по умолчанию `9088`.

## Полезные URL

- `http://localhost:9088/` — service info
- `http://localhost:9088/kml/root.kml` — корневой KML
- `http://localhost:9088/kml/live-point.kml` — live-точка
- `http://localhost:9088/kml/live-track.kml` — live-трек
- `http://localhost:9088/api/live-point.json` — последняя точка
- `http://localhost:9088/api/live-track.json` — последние точки трека
- `http://localhost:9088/tiles/0/0/0.png` — пример тайла

## Данные и логи

- `./data/server.log` — лог Python-сервиса
- `./data/dmr/raw.log` — сырой вывод `DSD-FME`
- `./data/dmr/parser.log` — лог parser-сервиса
- `./data/dmr/latest.json` — последний валидный GPS fix
- `./data/dmr/history.jsonl` — история GPS fix
- `./data/nginx-cache` — кэш тайлов `nginx`
- `./data/nginx-logs` — логи `nginx`

## Переменные окружения

### KML/Python

- `PORT` — порт standalone Python, по умолчанию `80`
- `PUBLIC_PORT` — внешний порт для абсолютных KML URL, по умолчанию равен `PORT`
- `BASE_URL` — внешний URL сервера; если не задан, определяется из заголовков запроса
- `TILE_SOURCE_TEMPLATE` — upstream для standalone tile proxy, по умолчанию `https://a.tile.opentopomap.org/{z}/{x}/{y}.png`
- `MAX_ZOOM` — максимальная глубина KML-дерева, по умолчанию `17`
- `MIN_LOD_PIXELS` — порог детализации KML Region, по умолчанию `128`
- `MAX_LOD_PIXELS` — верхний порог детализации KML Region, по умолчанию `-1`
- `LIVE_POINT_REFRESH_SECONDS` — интервал обновления live KML, по умолчанию `5`
- `LIVE_TRACK_MAX_POINTS` — сколько последних точек отдавать в track, по умолчанию `300`
- `DMR_LATEST_JSON` — путь до последней точки, по умолчанию `/data/dmr/latest.json`
- `DMR_HISTORY_JSONL` — путь до истории, по умолчанию `/data/dmr/history.jsonl`

### DMR decoder/parser

- `DMR_RTL_INPUT` — строка RTL-входа для `DSD-FME`, по умолчанию `rtl:0:430.300M:30:0:12:0:2`
- `DMR_FREQUENCY_HZ` — частота для JSON-событий, по умолчанию `430300000`
- `DMR_EXTRA_ARGS` — дополнительные флаги для `dsd-fme`, например `-xr`
- `DMR_CONTEXT_TTL_SECONDS` — сколько держать `Src/Dst/Slot/CC` между строками, по умолчанию `30`
- `DMR_RAW_LOG` — путь до сырого лога, по умолчанию `/data/dmr/raw.log`
- `DMR_PARSER_LOG` — путь до лога parser, по умолчанию `/data/dmr/parser.log`

## Отладка

Лог декодера:

```bash
docker compose logs -f dmr-decoder
```

Лог parser:

```bash
docker compose logs -f dmr-parser
```

Если DMR инвертирован, можно временно добавить:

```bash
DMR_EXTRA_ARGS=-xr
```

в `.env` или в окружение перед `docker compose up`.

## Как это работает в Google Earth

1. Запустить стек.
2. Открыть `http://localhost:9088/kml/root.kml` в dev-режиме или адрес reverse proxy в обычном compose.
3. Google Earth загрузит tile overlay, live-точку и live-трек.
4. Пока GPS fix еще не декодирован, live KML останется пустым, а `/api/live-point.json` будет отдавать `404 No live fix yet`.

## Ограничения первой версии

- parser сейчас рассчитывает на текстовые строки `DSD-FME`, в которых координаты уже видны как `Lat/Lon`
- если `DSD-FME` покажет только hex payload, parser запишет `unparsed GPS candidate` в `parser.log`, но не декодирует vendor-specific формат
- Windows-режим с локальным USB и без Linux-хоста не поддерживается
