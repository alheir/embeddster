export const DEFAULT_PROTOCOL_HANDLER = `import logging
from typing import Any

from src.package.Station import STATION_COUNT


class ProtocolHandler:
    """
    Serial protocol bridge between the board and the GUI.

    Implement:
      - on_bytes(): frame incoming bytes and return parsed messages.
      - build_led_command(): build outgoing bytes for LED commands.
    """

    def __init__(self) -> None:
        self.buffer = b""
        logging.info("[ProtocolHandler] Ready.")

    def on_bytes(self, data: bytes) -> list[dict[str, Any]]:
        """
        Return a list of message dicts:
          angle: type, station_index, angle (0=R, 1=C, 2=O), value, can_id, data
          led:   type, station_index, r, g, b, can_id, data
        """
        raise NotImplementedError("Implement on_bytes")

    def build_led_command(self, station_index: int, r: bool, g: bool, b: bool) -> bytes:
        """Return bytes ready for serial write."""
        raise NotImplementedError("Implement build_led_command")
`;
