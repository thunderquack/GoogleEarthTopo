import json
import os
import re
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path


SOURCE_TARGET_PATTERN = re.compile(
    r"(?:Source|Src)\s*[:=]\s*(?P<src>\d+).*?"
    r"(?:Target|Destination|Dst)\s*[:=]\s*(?P<dst>\d+)",
    re.IGNORECASE,
)
LAT_LON_PATTERN = re.compile(
    r"(?:Latitude|Lat)\s*[:=]\s*(?P<lat>-?\d+(?:\.\d+)?).*?"
    r"(?:Longitude|Lon|Long)\s*[:=]\s*(?P<lon>-?\d+(?:\.\d+)?)",
    re.IGNORECASE,
)
SLOT_PATTERN = re.compile(r"\bSlot\s*[:=]?\s*(?P<slot>\d+)\b", re.IGNORECASE)
COLOR_CODE_PATTERN = re.compile(r"\b(?:Color Code|CC)\s*[:=]?\s*(?P<cc>\d+)\b", re.IGNORECASE)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_float(value: str) -> float | None:
    try:
        return float(value)
    except ValueError:
        return None


class EventState:
    def __init__(self, frequency_hz: int, protocol: str, ttl_seconds: int) -> None:
        self.frequency_hz = frequency_hz
        self.protocol = protocol
        self.ttl_seconds = ttl_seconds
        self._context: dict[str, int] = {}
        self._context_updated_at = 0.0

    def ingest_line(self, line: str) -> tuple[dict | None, str | None]:
        now = time.time()
        self._expire_context(now)

        ids = SOURCE_TARGET_PATTERN.search(line)
        if ids:
            self._context["source_id"] = int(ids.group("src"))
            self._context["destination_id"] = int(ids.group("dst"))
            self._context_updated_at = now

        slot_match = SLOT_PATTERN.search(line)
        if slot_match:
            self._context["slot"] = int(slot_match.group("slot"))
            self._context_updated_at = now

        color_code_match = COLOR_CODE_PATTERN.search(line)
        if color_code_match:
            self._context["color_code"] = int(color_code_match.group("cc"))
            self._context_updated_at = now

        coordinates = LAT_LON_PATTERN.search(line)
        if not coordinates:
            return None, None

        latitude = parse_float(coordinates.group("lat"))
        longitude = parse_float(coordinates.group("lon"))
        if latitude is None or longitude is None:
            return None, f"invalid coordinates: {line}"

        event = {
            "received_at": utc_now(),
            "protocol": self.protocol,
            "frequency_hz": self.frequency_hz,
            "source_id": self._context.get("source_id"),
            "destination_id": self._context.get("destination_id"),
            "slot": self._context.get("slot"),
            "color_code": self._context.get("color_code"),
            "latitude": latitude,
            "longitude": longitude,
            "speed_kmh": None,
            "heading_deg": None,
            "raw": line,
        }
        self._context_updated_at = now
        return event, None

    def _expire_context(self, now: float) -> None:
        if self._context and now - self._context_updated_at > self.ttl_seconds:
            self._context = {}
            self._context_updated_at = 0.0


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp_path.replace(path)


def append_jsonl(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def append_log(path: Path, message: str) -> None:
    timestamp = utc_now()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"{timestamp} {message}\n")


def is_unparsed_candidate(line: str) -> bool:
    upper_line = line.upper()
    return "GPS" in upper_line or "LRRP" in upper_line or "LAT" in upper_line or "LON" in upper_line


def trim_history(path: Path, max_points: int) -> None:
    if max_points <= 0 or not path.exists():
        return

    with path.open("r", encoding="utf-8") as handle:
        lines = deque(handle, maxlen=max_points)

    with path.open("w", encoding="utf-8") as handle:
        handle.writelines(lines)


def process_line(
    state: EventState,
    line: str,
    latest_path: Path,
    history_path: Path,
    parser_log_path: Path,
    max_points: int,
) -> dict | None:
    event, error = state.ingest_line(line)
    if error:
        append_log(parser_log_path, error)
        return None

    if event:
        write_json(latest_path, event)
        append_jsonl(history_path, event)
        trim_history(history_path, max_points)
        append_log(
            parser_log_path,
            f"emitted fix lat={event['latitude']} lon={event['longitude']} src={event['source_id']} dst={event['destination_id']}",
        )
        return event

    if is_unparsed_candidate(line):
        append_log(parser_log_path, f"unparsed GPS candidate: {line}")
    return None


def follow_file(raw_log_path: Path):
    raw_log_path.parent.mkdir(parents=True, exist_ok=True)
    raw_log_path.touch(exist_ok=True)

    with raw_log_path.open("r", encoding="utf-8", errors="replace") as handle:
        handle.seek(0, os.SEEK_END)
        while True:
            line = handle.readline()
            if line:
                yield line.rstrip("\r\n")
                continue
            time.sleep(0.5)


def main() -> int:
    frequency_hz = int(os.getenv("DMR_FREQUENCY_HZ", "430300000"))
    protocol = os.getenv("DMR_PROTOCOL", "DMR")
    raw_log_path = Path(os.getenv("DMR_RAW_LOG", "/data/dmr/raw.log"))
    latest_path = Path(os.getenv("DMR_LATEST_JSON", "/data/dmr/latest.json"))
    history_path = Path(os.getenv("DMR_HISTORY_JSONL", "/data/dmr/history.jsonl"))
    parser_log_path = Path(os.getenv("DMR_PARSER_LOG", "/data/dmr/parser.log"))
    max_points = int(os.getenv("LIVE_TRACK_MAX_POINTS", "300"))
    context_ttl_seconds = int(os.getenv("DMR_CONTEXT_TTL_SECONDS", "30"))

    state = EventState(
        frequency_hz=frequency_hz,
        protocol=protocol,
        ttl_seconds=context_ttl_seconds,
    )

    append_log(parser_log_path, "parser started")
    for line in follow_file(raw_log_path):
        process_line(
            state=state,
            line=line,
            latest_path=latest_path,
            history_path=history_path,
            parser_log_path=parser_log_path,
            max_points=max_points,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
