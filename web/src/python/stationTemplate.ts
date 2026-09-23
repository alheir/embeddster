export function buildStationPy(stationCount: number): string {
  const ids = Array.from({ length: stationCount }, (_, i) => `b"${i}"`).join(', ');
  const names = Array.from({ length: stationCount }, (_, i) => `"0x${(0x100 + i).toString(16).toUpperCase()}"`).join(', ');

  return `STATION_ID = [${ids}]
STATION_ID_NAMES = [${names}]
STATION_ANGLES = [b"R", b"C", b"O"]
STATION_ANGLES_COUNT = len(STATION_ANGLES)
STATION_COUNT = len(STATION_ID)
`;
}
