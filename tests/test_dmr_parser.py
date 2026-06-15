import json
import tempfile
import unittest
from pathlib import Path

import importlib.util


PARSER_PATH = Path(__file__).resolve().parents[1] / "dmr-parser" / "parser.py"
SPEC = importlib.util.spec_from_file_location("dmr_parser", PARSER_PATH)
dmr_parser = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(dmr_parser)


class DmrParserTests(unittest.TestCase):
    def test_emits_event_from_split_lines(self):
        state = dmr_parser.EventState(frequency_hz=430300000, protocol="DMR", ttl_seconds=30)
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            latest_path = base / "latest.json"
            history_path = base / "history.jsonl"
            parser_log_path = base / "parser.log"

            first = dmr_parser.process_line(
                state,
                "DMR Data Src: 9000001 Dst: 991 Slot 1 CC 1",
                latest_path,
                history_path,
                parser_log_path,
                max_points=10,
            )
            self.assertIsNone(first)

            second = dmr_parser.process_line(
                state,
                "GPS Latitude: 52.520123 Longitude: 13.404456",
                latest_path,
                history_path,
                parser_log_path,
                max_points=10,
            )

            self.assertIsNotNone(second)
            self.assertEqual(second["source_id"], 9000001)
            self.assertEqual(second["destination_id"], 991)
            self.assertEqual(second["slot"], 1)
            self.assertEqual(second["color_code"], 1)
            self.assertEqual(second["latitude"], 52.520123)
            self.assertEqual(second["longitude"], 13.404456)

            latest_payload = json.loads(latest_path.read_text(encoding="utf-8"))
            self.assertEqual(latest_payload["latitude"], 52.520123)

            history_lines = history_path.read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(history_lines), 1)

    def test_unparsed_candidate_is_logged_without_event(self):
        state = dmr_parser.EventState(frequency_hz=430300000, protocol="DMR", ttl_seconds=30)
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            latest_path = base / "latest.json"
            history_path = base / "history.jsonl"
            parser_log_path = base / "parser.log"

            event = dmr_parser.process_line(
                state,
                "LRRP payload 0x0102030405",
                latest_path,
                history_path,
                parser_log_path,
                max_points=10,
            )

            self.assertIsNone(event)
            self.assertFalse(latest_path.exists())
            self.assertIn("unparsed GPS candidate", parser_log_path.read_text(encoding="utf-8"))

    def test_history_is_trimmed_to_max_points(self):
        state = dmr_parser.EventState(frequency_hz=430300000, protocol="DMR", ttl_seconds=30)
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            latest_path = base / "latest.json"
            history_path = base / "history.jsonl"
            parser_log_path = base / "parser.log"

            for index in range(5):
                line = f"Lat={50 + index}.0 Lon={10 + index}.0"
                dmr_parser.process_line(
                    state,
                    line,
                    latest_path,
                    history_path,
                    parser_log_path,
                    max_points=3,
                )

            history_lines = history_path.read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(history_lines), 3)
            last_payload = json.loads(history_lines[-1])
            self.assertEqual(last_payload["latitude"], 54.0)


if __name__ == "__main__":
    unittest.main()
