export type ViewId = 'main' | 'protocol';

export type AngleId = 0 | 1 | 2;

export interface ParsedMessage {
  type: 'angle' | 'led' | 'unknown';
  station_index?: number;
  angle?: AngleId;
  value?: number;
  r?: boolean;
  g?: boolean;
  b?: boolean;
  can_id: number;
  data: number[];
}

export interface StationState {
  roll: number;
  pitch: number;
  yaw: number;
  active: boolean;
  lastUpdate: number | null;
  led: { r: boolean; g: boolean; b: boolean };
}

export interface LogEntry {
  id: number;
  time: string;
  level: 'info' | 'warn' | 'error' | 'debug';
  text: string;
}

export interface GodModeRow {
  timestamp: string;
  canId: string;
  dlc: number;
  type: string;
  hex: string;
  ascii: string;
}

export interface ProtocolCallResult {
  messages: ParsedMessage[];
  logs: string[];
  error: string | null;
}
