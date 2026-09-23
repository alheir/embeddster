import logging
from typing import Any

from src.package.Station import STATION_COUNT


class ProtocolHandler:
    """Reference parser for Embeddster ESP32 sniffer output (RXED: lines)."""

    def __init__(self) -> None:
        self.buffer = b""
        logging.info("[ProtocolHandler] Ready.")

    def on_bytes(self, data: bytes) -> list[dict[str, Any]]:
        self.buffer += data
        messages = []
        while b"\n" in self.buffer:
            line, self.buffer = self.buffer.split(b"\n", 1)
            line = line.decode("utf-8", errors="ignore").strip()
            if not line.startswith("RXED:"):
                continue
            try:
                parts = line.split()
                can_id = int(parts[1].split("=")[1], 16)
                data_part = parts[2]
                data_hex = data_part.split("=")[1]
                data_bytes = bytes.fromhex(data_hex[2:])
                data_len = int(parts[3].split("=")[1])

                if data_len == 1 and data_bytes[0] & 0x80:
                    station_index = (data_bytes[0] >> 4) & 0x07
                    messages.append({
                        "type": "led",
                        "station_index": station_index,
                        "r": bool((data_bytes[0] >> 2) & 1),
                        "g": bool((data_bytes[0] >> 1) & 1),
                        "b": bool(data_bytes[0] & 1),
                        "can_id": can_id,
                        "data": data_bytes,
                    })
                else:
                    ascii_part = data_part.split("=")[2].strip("'")
                    if len(ascii_part) >= 2 and ascii_part[0] in "RCO":
                        station_index = can_id - 0x100
                        if 0 <= station_index < STATION_COUNT:
                            angle_char = ascii_part[0]
                            value = int(ascii_part[1:])
                            angle_map = {"R": 0, "C": 1, "O": 2}
                            if angle_char in angle_map:
                                messages.append({
                                    "type": "angle",
                                    "station_index": station_index,
                                    "angle": angle_map[angle_char],
                                    "value": value,
                                    "can_id": can_id,
                                    "data": data_bytes,
                                })
                            else:
                                messages.append({"type": "unknown", "can_id": can_id, "data": data_bytes})
                        else:
                            messages.append({"type": "unknown", "can_id": can_id, "data": data_bytes})
                    else:
                        messages.append({"type": "unknown", "can_id": can_id, "data": data_bytes})
            except (ValueError, IndexError):
                logging.warning(f"Failed to parse: {line}")
        return messages

    def build_led_command(self, station_index: int, r: bool, g: bool, b: bool) -> bytes:
        cmd = f"LED_{station_index}_{int(r)}_{int(g)}_{int(b)}\n"
        logging.info(f"Built LED cmd: {cmd.strip()}")
        return cmd.encode("utf-8")
