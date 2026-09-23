import logging
from typing import Any

from src.package.Station import STATION_COUNT


class ProtocolHandler:
    def __init__(self) -> None:
        self.buffer = b""
        logging.info("Ready")

    def on_bytes(self, data: bytes) -> list[dict[str, Any]]:
        self.buffer += data
        messages = []
        while b"\n" in self.buffer:
            line, self.buffer = self.buffer.split(b"\n", 1)
            line = line.decode("utf-8", errors="ignore").strip()
            if not line.startswith("RXED:"):
                continue
            parts = line.split()
            can_id = int(parts[1].split("=")[1], 16)
            data_part = parts[2]
            data_bytes = bytes.fromhex(data_part.split("=")[1][2:])
            ascii_part = data_part.split("=")[2].strip("'")
            if len(ascii_part) >= 2 and ascii_part[0] in "RCO":
                station_index = can_id - 0x100
                if 0 <= station_index < STATION_COUNT:
                    angle_map = {"R": 0, "C": 1, "O": 2}
                    messages.append(
                        {
                            "type": "angle",
                            "station_index": station_index,
                            "angle": angle_map[ascii_part[0]],
                            "value": int(ascii_part[1:]),
                            "can_id": can_id,
                            "data": data_bytes,
                        }
                    )
        return messages

    def build_led_command(self, station_index: int, r: bool, g: bool, b: bool) -> bytes:
        return f"LED_{station_index}_{int(r)}_{int(g)}_{int(b)}\n".encode("utf-8")
