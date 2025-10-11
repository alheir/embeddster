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
          - Para ángulos: 'type': 'angle', 'station_index': int, 'angle': int, 'value': int, 'can_id': int, 'data': bytes
          - Para LEDs: 'type': 'led', 'station_index': int, 'r': bool, 'g': bool, 'b': bool, 'can_id': int, 'data': bytes

        Lista vacía si no hay frames completos.
        """
        self.buffer += data
        messages = []
        while b'\n' in self.buffer:
            line, self.buffer = self.buffer.split(b'\n', 1)
            line = line.decode('utf-8', errors='ignore').strip()
            if line.startswith("RXED:"):
                try:
                    parts = line.split()
                    can_id_hex = parts[1].split('=')[1]
                    can_id = int(can_id_hex, 16)
                    data_part = parts[2]
                    data_hex = data_part.split('=')[1]  # e.g., "0x522B3135"
                    data_bytes = bytes.fromhex(data_hex[2:])
                    len_part = parts[3].split('=')[1]
                    data_len = int(len_part)
                    
                    if data_len == 1 and data_bytes[0] & 0x80:
                        # LED command: 1JKL 0RGB
                        station_index = (data_bytes[0] >> 4) & 0x07
                        r = bool((data_bytes[0] >> 2) & 1)
                        g = bool((data_bytes[0] >> 1) & 1)
                        b = bool(data_bytes[0] & 1)
                        messages.append({
                            'type': 'led',
                            'station_index': station_index,
                            'r': r,
                            'g': g,
                            'b': b,
                            'can_id': can_id,
                            'data': data_bytes
                        })
                    else:
                        # Try to parse as angle message
                        ascii_part = data_part.split('=')[2].strip("'")
                        if len(ascii_part) >= 2 and ascii_part[0] in 'RCO':
                            station_index = can_id - 0x100
                            if 0 <= station_index < STATION_COUNT:
                                angle_char = ascii_part[0]
                                value_str = ascii_part[1:]
                                try:
                                    value = int(value_str)
                                    angle_map = {'R': 0, 'C': 1, 'O': 2}
                                    if angle_char in angle_map:
                                        messages.append({
                                            'type': 'angle',
                                            'station_index': station_index,
                                            'angle': angle_map[angle_char],
                                            'value': value,
                                            'can_id': can_id,
                                            'data': data_bytes
                                        })
                                except ValueError:
                                    # Not a valid angle, treat as unknown
                                    messages.append({
                                        'type': 'unknown',
                                        'can_id': can_id,
                                        'data': data_bytes
                                    })
                        else:
                            # Not LED and not angle, unknown
                            messages.append({
                                'type': 'unknown',
                                'can_id': can_id,
                                'data': data_bytes
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
