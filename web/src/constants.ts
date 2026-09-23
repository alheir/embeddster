export const BAUD_RATES = [
  2400, 4800, 9600, 19200, 38400, 57600, 115200, 230400, 460800, 921600,
] as const;

export const DEFAULT_BAUD = 115200;

export const MIN_STATIONS = 1;
export const MAX_STATIONS = 8;
export const DEFAULT_STATION_COUNT = 7;

export const STORAGE_KEYS = {
  protocol: 'embeddster.protocol.v2',
  stationCount: 'embeddster.stationCount',
  baudRate: 'embeddster.baudRate',
} as const;

export function stationIdName(index: number): string {
  return `0x${(0x100 + index).toString(16).toUpperCase()}`;
}
