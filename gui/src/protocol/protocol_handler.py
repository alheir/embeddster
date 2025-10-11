from typing import List, Dict, Any
import logging
from src.package.Station import STATION_COUNT

class ProtocolHandler:
    """
    Clase intermedia para manejar el protocolo de comunicación serial.

    Qué se debe implementar:
      - Framing y parseo en on_bytes(): acumular bytes, detectar fin de mensaje,
        validar y convertir a una estructura uniforme para la GUI según lo especificado.
      - Construcción de mensajes salientes en build_led_command().
    """
    def __init__(self) -> None:
        self.buffer = b""  # Buffer for accumulating incoming data
        logging.info("[ProtocolHandler] Inicializado. Listo para recibir bytes del puerto serie.")

    def on_bytes(self, data: bytes) -> List[Dict[str, Any]]:
        """
        Recibe bytes crudos desde el puerto serie y devuelve a la GUI una lista de mensajes parseados.

        Debe devolver: lista de mensajes. Cada mensaje es un dict con:
          - 'station_index': int (0..N-1)
          - 'angle': int en {0: roll, 1: pitch, 2: yaw}
          - 'value': float|int

        Ejemplos de retorno:
          # Un solo mensaje:
          # return [{'station_index': 0, 'angle': 0, 'value': 12.5}]  # roll de grupo 0
          # Varios mensajes:
          # return [
          #   {'station_index': 1, 'angle': 1, 'value': 20.0},  # pitch de grupo 1
          #   {'station_index': 1, 'angle': 2, 'value': -7.2},  # yaw de grupo 1
          # ]
          # Lista vacía si no hay frames completos:
          # return []
        """
        self.buffer += data
        messages = []
        while b'\n' in self.buffer:
            line, self.buffer = self.buffer.split(b'\n', 1)
            line = line.decode('utf-8', errors='ignore').strip()
            if line.startswith("RXED:"):
                # Parse ESP32's CAN message format: "RXED: ID=0x{id} Data=0x{data}='{ascii}' Len={len}"
                try:
                    parts = line.split()
                    can_id_hex = parts[1].split('=')[1]  # e.g., "0x100"
                    can_id = int(can_id_hex, 16)
                    ascii_part = parts[3].strip("'")  # e.g., "R45"
                    if 0x100 <= can_id < 0x100 + STATION_COUNT and len(ascii_part) >= 2: # Up to STATION_COUNT stations
                        station_index = can_id - 0x100
                        angle_char = ascii_part[0]
                        value = int(ascii_part[1:])
                        angle_map = {'R': 0, 'C': 1, 'O': 2}  # Roll, Pitch, Yaw
                        if angle_char in angle_map:
                            messages.append({
                                'station_index': station_index,
                                'angle': angle_map[angle_char],
                                'value': value
                            })
                except (ValueError, IndexError):
                    logging.warning(f"[ProtocolHandler] Failed to parse CAN message: {line}")
        return messages

    def build_led_command(self, station_index: int, r: bool, g: bool, b: bool) -> bytes:
        """
        Construye los bytes a enviar por serial para comandar LEDs de una estación.

        Parámetros:
          - station_index: int (0..N-1)
          - r, g, b: bools que indican encendido de cada color

        Debe devolver:
          - bytes listos para write() del puerto serie.
        """

        cmd = f"LED_{station_index}_{int(r)}_{int(g)}_{int(b)}\n"
        logging.info(f"[ProtocolHandler] Built LED cmd: {cmd.strip()}")
        return cmd.encode('utf-8')
