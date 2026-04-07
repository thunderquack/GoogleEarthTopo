import math
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "9088"))
MAX_ZOOM = int(os.getenv("MAX_ZOOM", "14"))
MIN_LOD_PIXELS = int(os.getenv("MIN_LOD_PIXELS", "128"))
MAX_LOD_PIXELS = int(os.getenv("MAX_LOD_PIXELS", "-1"))
TILE_SOURCE_TEMPLATE = os.getenv(
    "TILE_SOURCE_TEMPLATE",
    "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
)
USER_AGENT = os.getenv(
    "UPSTREAM_USER_AGENT",
    "GoogleEarthTopo/0.1 (+https://localhost)",
)
LOG_REQUESTS = os.getenv("LOG_REQUESTS", "1") != "0"


def get_base_url(headers):
    explicit = os.getenv("BASE_URL")
    if explicit:
        return explicit.rstrip("/")

    forwarded_proto = headers.get("X-Forwarded-Proto")
    proto = forwarded_proto.split(",")[0].strip() if forwarded_proto else "http"
    host = headers.get("Host", f"localhost:{PORT}")
    return f"{proto}://{host}"


def clamp_tile_x(x, z):
    limit = 2 ** z
    return ((x % limit) + limit) % limit


def is_valid_tile_y(y, z):
    return 0 <= y < 2 ** z


def tile_y_to_latitude(y, tiles_per_axis):
    mercator = math.pi * (1 - (2 * y) / tiles_per_axis)
    return math.degrees(math.atan(math.sinh(mercator)))


def tile_bounds(z, x, y):
    tiles_per_axis = 2 ** z
    west = (x / tiles_per_axis) * 360.0 - 180.0
    east = ((x + 1) / tiles_per_axis) * 360.0 - 180.0
    north = tile_y_to_latitude(y, tiles_per_axis)
    south = tile_y_to_latitude(y + 1, tiles_per_axis)
    return {
        "north": north,
        "south": south,
        "east": east,
        "west": west,
    }


def tile_source_url(z, x, y):
    return (
        TILE_SOURCE_TEMPLATE.replace("{z}", str(z))
        .replace("{x}", str(x))
        .replace("{y}", str(y))
    )


def build_network_links(base_url, z, x, y):
    if z >= MAX_ZOOM:
        return ""

    child_zoom = z + 1
    child_tiles = [
        (x * 2, y * 2),
        (x * 2 + 1, y * 2),
        (x * 2, y * 2 + 1),
        (x * 2 + 1, y * 2 + 1),
    ]

    links = []
    for child_x, child_y in child_tiles:
        bounds = tile_bounds(child_zoom, child_x, child_y)
        href = f"{base_url}/kml/{child_zoom}/{child_x}/{child_y}.kml"
        links.append(
            f"""
    <NetworkLink>
      <name>{child_zoom}/{child_x}/{child_y}</name>
      <Region>
        <LatLonAltBox>
          <north>{bounds["north"]}</north>
          <south>{bounds["south"]}</south>
          <east>{bounds["east"]}</east>
          <west>{bounds["west"]}</west>
        </LatLonAltBox>
        <Lod>
          <minLodPixels>{MIN_LOD_PIXELS}</minLodPixels>
          <maxLodPixels>{MAX_LOD_PIXELS}</maxLodPixels>
        </Lod>
      </Region>
      <Link>
        <href>{href}</href>
        <viewRefreshMode>onRegion</viewRefreshMode>
      </Link>
    </NetworkLink>""".rstrip()
        )

    return "\n".join(links)


def build_tile_kml(base_url, z, x, y):
    bounds = tile_bounds(z, x, y)
    tile_url = f"{base_url}/tiles/{z}/{x}/{y}.png"
    network_links = build_network_links(base_url, z, x, y)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>{z}/{x}/{y}</name>
    <Region>
      <LatLonAltBox>
        <north>{bounds["north"]}</north>
        <south>{bounds["south"]}</south>
        <east>{bounds["east"]}</east>
        <west>{bounds["west"]}</west>
      </LatLonAltBox>
      <Lod>
        <minLodPixels>{MIN_LOD_PIXELS}</minLodPixels>
        <maxLodPixels>{MAX_LOD_PIXELS}</maxLodPixels>
      </Lod>
    </Region>
    <GroundOverlay>
      <drawOrder>{z}</drawOrder>
      <Icon>
        <href>{tile_url}</href>
      </Icon>
      <LatLonBox>
        <north>{bounds["north"]}</north>
        <south>{bounds["south"]}</south>
        <east>{bounds["east"]}</east>
        <west>{bounds["west"]}</west>
      </LatLonBox>
    </GroundOverlay>
{network_links}
  </Document>
</kml>
"""


def build_root_kml(base_url):
    href = f"{base_url}/kml/0/0/0.kml"
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <NetworkLink>
    <name>Google Earth Topo</name>
    <open>1</open>
    <Link>
      <href>{href}</href>
      <viewRefreshMode>onRegion</viewRefreshMode>
    </Link>
  </NetworkLink>
</kml>
"""


class RequestHandler(BaseHTTPRequestHandler):
    server_version = "GoogleEarthTopo/0.1"

    def do_GET(self):
        started_at = time.time()
        status = 500
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        try:
            if path == "/":
                status = self._send_bytes(
                    200,
                    (
                        "{\n"
                        '  "service": "google-earth-topo",\n'
                        '  "kml": "/kml/root.kml",\n'
                        '  "tileExample": "/tiles/0/0/0.png",\n'
                        f'  "maxZoom": {MAX_ZOOM}\n'
                        "}\n"
                    ).encode("utf-8"),
                    "application/json; charset=utf-8",
                )
                return

            if path == "/kml/root.kml":
                body = build_root_kml(get_base_url(self.headers)).encode("utf-8")
                status = self._send_bytes(
                    200,
                    body,
                    "application/vnd.google-earth.kml+xml; charset=utf-8",
                )
                return

            kml_match = re.fullmatch(r"/kml/(\d+)/(\d+)/(\d+)\.kml", path)
            if kml_match:
                status = self._handle_kml_tile(kml_match)
                return

            tile_match = re.fullmatch(r"/tiles/(\d+)/(-?\d+)/(-?\d+)\.png", path)
            if tile_match:
                status = self._handle_tile_proxy(tile_match)
                return

            status = self._send_text(404, "Not found")
        finally:
            self._log_request_line(status, started_at)

    def _handle_kml_tile(self, match):
        z = int(match.group(1))
        x = int(match.group(2))
        y = int(match.group(3))

        if z > MAX_ZOOM:
            return self._send_text(404, "Requested zoom exceeds MAX_ZOOM")

        if x < 0 or x >= 2 ** z or not is_valid_tile_y(y, z):
            return self._send_text(404, "Tile coordinates are outside valid bounds")

        body = build_tile_kml(get_base_url(self.headers), z, x, y).encode("utf-8")
        return self._send_bytes(200, body, "application/vnd.google-earth.kml+xml; charset=utf-8")

    def _handle_tile_proxy(self, match):
        z = int(match.group(1))
        x = int(match.group(2))
        y = int(match.group(3))

        if z < 0:
            return self._send_text(400, "Invalid tile zoom")

        if not is_valid_tile_y(y, z):
            return self._send_text(404, "Tile Y is outside Web Mercator bounds")

        wrapped_x = clamp_tile_x(x, z)
        upstream_url = tile_source_url(z, wrapped_x, y)
        request = urllib.request.Request(
            upstream_url,
            headers={"User-Agent": USER_AGENT},
        )

        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                content_type = response.headers.get_content_type()
                body = response.read()
                return self._send_bytes(
                    200,
                    body,
                    content_type,
                    extra_headers={"Cache-Control": "public, max-age=3600"},
                )
        except urllib.error.HTTPError as exc:
            return self._send_text(exc.code, f"Upstream tile error: {exc.reason}")
        except urllib.error.URLError as exc:
            return self._send_text(502, f"Upstream tile connection error: {exc.reason}")

    def _send_text(self, status, text):
        return self._send_bytes(status, text.encode("utf-8"), "text/plain; charset=utf-8")

    def _send_bytes(self, status, body, content_type, extra_headers=None):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        if extra_headers:
            for key, value in extra_headers.items():
                self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)
        return status

    def _log_request_line(self, status, started_at):
        if not LOG_REQUESTS:
            return

        duration_ms = int((time.time() - started_at) * 1000)
        client_ip = self.client_address[0] if self.client_address else "-"
        print(
            f"{client_ip} \"{self.command} {self.path}\" {status} {duration_ms}ms",
            flush=True,
        )

    def log_message(self, format_, *args):
        return


if __name__ == "__main__":
    server = ThreadingHTTPServer((HOST, PORT), RequestHandler)
    print(f"Google Earth Topo listening on http://{HOST}:{PORT}")
    server.serve_forever()
