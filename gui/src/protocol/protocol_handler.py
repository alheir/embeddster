import logging
from typing import Any

from src.package.Station import MAX_GROUP_COUNT


class ProtocolHandler:
    """Parse serial bytes into GUI messages, and build LED commands."""

    def __init__(self) -> None:
        self.buffer = b""
        logging.info("[ProtocolHandler] Ready")

    def on_bytes(self, data: bytes) -> list[dict[str, Any]]:
        """Parse raw serial bytes into messages.

        Return [] when the buffer has no complete line.

        Angle keys: type "angle", station_index, angle
        (0 roll, 1 pitch, 2 yaw), value, can_id, data.

        LED keys: type "led", station_index, r, g, b, can_id, data.
        """
        self.buffer += data
        messages = []
        while b"\n" in self.buffer:
            line, self.buffer = self.buffer.split(b"\n", 1)
            line = line.decode("utf-8", errors="ignore").strip()
            if line.startswith("RXED:"):
                try:
                    parts = line.split()
                    can_id_hex = parts[1].split("=")[1]
                    can_id = int(can_id_hex, 16)
                    data_part = parts[2]
                    data_hex = data_part.split("=")[1]  # e.g., "0x522B3135"
                    data_bytes = bytes.fromhex(data_hex[2:])
                    len_part = parts[3].split("=")[1]
                    data_len = int(len_part)

                    if data_len == 1 and data_bytes[0] & 0x80:
                        # LED command: 1JKL 0RGB
                        station_index = (data_bytes[0] >> 4) & 0x07
                        r = bool((data_bytes[0] >> 2) & 1)
                        g = bool((data_bytes[0] >> 1) & 1)
                        b = bool(data_bytes[0] & 1)
                        messages.append(
                            {
                                "type": "led",
                                "station_index": station_index,
                                "r": r,
                                "g": g,
                                "b": b,
                                "can_id": can_id,
                                "data": data_bytes,
                            }
                        )
                    else:
                        # Try to parse as angle message
                        ascii_part = data_part.split("=")[2].strip("'")
                        if len(ascii_part) >= 2 and ascii_part[0] in "RCO":
                            station_index = can_id - 0x100
                            if 0 <= station_index < MAX_GROUP_COUNT:
                                angle_char = ascii_part[0]
                                value_str = ascii_part[1:]
                                try:
                                    value = int(value_str)
                                    angle_map = {"R": 0, "C": 1, "O": 2}
                                    if angle_char in angle_map:
                                        messages.append(
                                            {
                                                "type": "angle",
                                                "station_index": station_index,
                                                "angle": angle_map[angle_char],
                                                "value": value,
                                                "can_id": can_id,
                                                "data": data_bytes,
                                            }
                                        )
                                except ValueError:
                                    # Not a valid angle, treat as unknown
                                    messages.append(
                                        {"type": "unknown", "can_id": can_id, "data": data_bytes}
                                    )
                        else:
                            # Not LED and not angle, unknown
                            messages.append(
                                {"type": "unknown", "can_id": can_id, "data": data_bytes}
                            )
                except (ValueError, IndexError):
                    logging.warning(f"[ProtocolHandler] Failed to parse CAN message: {line}")
        return messages

    def build_led_command(self, station_index: int, r: bool, g: bool, b: bool) -> bytes:
        """Serial bytes for one LED command.

        station_index is 0..N-1. r, g, and b are on or off.
        """

        cmd = f"LED_{station_index}_{int(r)}_{int(g)}_{int(b)}\n"
        logging.info(f"[ProtocolHandler] Built LED cmd: {cmd.strip()}")
        return cmd.encode("utf-8")
