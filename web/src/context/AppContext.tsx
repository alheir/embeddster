import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react';
import {
  DEFAULT_BAUD,
  DEFAULT_STATION_COUNT,
  MAX_STATIONS,
  MIN_STATIONS,
  STORAGE_KEYS,
} from '../constants';
import { DEFAULT_PROTOCOL_HANDLER } from '../python/defaultProtocol';
import { ProtocolClient } from '../lib/protocolClient';
import { SerialConnection } from '../lib/serial';
import type { GodModeRow, LogEntry, ParsedMessage, StationState, ViewId } from '../types';

function createStations(count: number): StationState[] {
  return Array.from({ length: count }, () => ({
    roll: 0,
    pitch: 0,
    yaw: 0,
    active: false,
    lastUpdate: null,
    led: { r: false, g: false, b: false },
  }));
}

function nowTime(): string {
  const d = new Date();
  return d.toLocaleTimeString('en-GB', { hour12: false }) + '.' + String(d.getMilliseconds()).padStart(3, '0');
}

interface AppContextValue {
  view: ViewId;
  setView: (view: ViewId) => void;
  stationCount: number;
  setStationCount: (count: number) => void;
  visibleStations: number;
  setVisibleStations: (count: number) => void;
  baudRate: number;
  setBaudRate: (rate: number) => void;
  connected: boolean;
  connecting: boolean;
  protocolReady: boolean;
  protocolLoading: boolean;
  protocolError: string | null;
  godOpen: boolean;
  openGodMode: () => void;
  closeGodMode: () => void;
  protocolCode: string;
  setProtocolCode: (code: string) => void;
  reloadProtocol: (codeOverride?: string) => Promise<void>;
  connect: () => Promise<void>;
  disconnect: () => Promise<void>;
  writeSerial: (data: Uint8Array | string) => Promise<void>;
  sendLed: (stationIndex: number, r: boolean, g: boolean, b: boolean) => Promise<void>;
  injectBytes: (data: Uint8Array) => Promise<void>;
  stations: StationState[];
  logs: LogEntry[];
  addLog: (level: LogEntry['level'], text: string) => void;
  modelIndex: number;
  setModelIndex: (index: number) => void;
  chartStation: number;
  setChartStation: (index: number) => void;
  angleHistory: Record<number, { t: number; roll: number; pitch: number; yaw: number }[]>;
  godRows: GodModeRow[];
  godPaused: boolean;
  setGodPaused: (paused: boolean) => void;
  godFilterEnabled: boolean;
  setGodFilterEnabled: (enabled: boolean) => void;
  godFilterIds: string;
  setGodFilterIds: (value: string) => void;
  clearGodRows: () => void;
  exportGodLog: () => void;
  sendCanMode: (mode: 'NORMAL' | 'LOOPBACK') => Promise<void>;
  sendManualCan: (canId: number, data: Uint8Array) => Promise<void>;
  sendAngleGroups: (groups: number[], angleType: string, value: number) => Promise<void>;
  sendGodLed: (group: number, r: boolean, g: boolean, b: boolean) => Promise<void>;
  startRandomTraffic: (groups: number[], modes: string[], periodMs: number) => void;
  stopRandomTraffic: (silent?: boolean) => void;
  randomRunning: boolean;
}

const AppContext = createContext<AppContextValue | null>(null);

export function AppProvider({ children }: { children: ReactNode }) {
  const [view, setView] = useState<ViewId>('main');
  const [godOpen, setGodOpen] = useState(false);
  const [stationCount, setStationCountState] = useState(() => {
    const saved = localStorage.getItem(STORAGE_KEYS.stationCount);
    const n = saved ? Number(saved) : DEFAULT_STATION_COUNT;
    return Math.min(MAX_STATIONS, Math.max(MIN_STATIONS, n));
  });
  const [visibleStations, setVisibleStations] = useState(stationCount);
  const [baudRate, setBaudRateState] = useState(() => {
    const saved = localStorage.getItem(STORAGE_KEYS.baudRate);
    return saved ? Number(saved) : DEFAULT_BAUD;
  });
  const [protocolCode, setProtocolCodeState] = useState(() => {
    return localStorage.getItem(STORAGE_KEYS.protocol) ?? DEFAULT_PROTOCOL_HANDLER;
  });
  const [connected, setConnected] = useState(false);
  const [connecting, setConnecting] = useState(false);
  const [protocolReady, setProtocolReady] = useState(false);
  const [protocolLoading, setProtocolLoading] = useState(false);
  const [protocolError, setProtocolError] = useState<string | null>(null);
  const [stations, setStations] = useState(() => createStations(stationCount));
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [modelIndex, setModelIndex] = useState(0);
  const [chartStation, setChartStation] = useState(0);
  const [angleHistory, setAngleHistory] = useState<
    Record<number, { t: number; roll: number; pitch: number; yaw: number }[]>
  >({});
  const [godRows, setGodRows] = useState<GodModeRow[]>([]);
  const [godPaused, setGodPaused] = useState(false);
  const [godFilterEnabled, setGodFilterEnabled] = useState(false);
  const [godFilterIds, setGodFilterIds] = useState('');
  const [randomRunning, setRandomRunning] = useState(false);

  const logId = useRef(0);
  const prevStationCountRef = useRef<number | null>(null);
  const serialRef = useRef(new SerialConnection());
  const protocolRef = useRef<ProtocolClient | null>(null);
  const randomTimerRef = useRef<number | null>(null);
  const randomStateRef = useRef<Record<number, { mode: string; start: number; constValue: number }>>({});

  const addLog = useCallback((level: LogEntry['level'], text: string) => {
    logId.current += 1;
    setLogs((prev) => [
      ...prev.slice(-199),
      { id: logId.current, time: nowTime(), level, text },
    ]);
  }, []);

  const appendProtocolLogs = useCallback(
    (lines: string[]) => {
      for (const line of lines) {
        if (line.trim()) addLog('debug', line);
      }
    },
    [addLog],
  );

  const setStationCount = useCallback((count: number) => {
    const clamped = Math.min(MAX_STATIONS, Math.max(MIN_STATIONS, count));
    setStationCountState(clamped);
    localStorage.setItem(STORAGE_KEYS.stationCount, String(clamped));
    setVisibleStations((v) => Math.min(v, clamped));
    setStations(createStations(clamped));
    setAngleHistory({});
  }, []);

  const setBaudRate = useCallback((rate: number) => {
    setBaudRateState(rate);
    localStorage.setItem(STORAGE_KEYS.baudRate, String(rate));
  }, []);

  const setProtocolCode = useCallback((code: string) => {
    setProtocolCodeState(code);
    localStorage.setItem(STORAGE_KEYS.protocol, code);
  }, []);

  const processMessage = useCallback(
    (msg: ParsedMessage) => {
      if (!godPaused) {
        const filterSet = new Set(
          godFilterIds
            .split(',')
            .map((s) => s.trim())
            .filter(Boolean)
            .map((s) => parseInt(s, s.startsWith('0x') ? 16 : 10)),
        );
        if (!godFilterEnabled || filterSet.has(msg.can_id)) {
          const hex = msg.data.map((b) => b.toString(16).padStart(2, '0').toUpperCase()).join(' ');
          let ascii = msg.data.map((b) => (b >= 32 && b < 127 ? String.fromCharCode(b) : '.')).join('');
          if (msg.type === 'led' && msg.data.length === 1) {
            const binary = msg.data[0].toString(2).padStart(8, '0');
            ascii = `${binary[0]} ${binary.slice(1, 4)} ${binary[4]} ${binary.slice(5)}`;
          }
          setGodRows((prev) => [
            ...prev.slice(-999),
            {
              timestamp: nowTime(),
              canId: `0x${msg.can_id.toString(16).toUpperCase()}`,
              dlc: msg.data.length,
              type: msg.type === 'angle' ? 'Angle' : msg.type === 'led' ? 'LED' : 'Unknown',
              hex,
              ascii,
            },
          ]);
        }
      }

      if (
        msg.type === 'angle' &&
        msg.station_index !== undefined &&
        msg.angle !== undefined &&
        msg.value !== undefined
      ) {
        const idx = msg.station_index;
        const value = msg.value;
        const angle = msg.angle;
        setStations((prev) => {
          const next = [...prev];
          const s = { ...next[idx] };
          if (angle === 0) s.roll = value;
          if (angle === 1) s.pitch = value;
          if (angle === 2) s.yaw = value;
          s.active = true;
          s.lastUpdate = Date.now();
          next[idx] = s;
          return next;
        });
        setAngleHistory((prev) => {
          const list = prev[idx] ? [...prev[idx]] : [];
          const last = list[list.length - 1];
          const point = {
            t: Date.now(),
            roll: last?.roll ?? 0,
            pitch: last?.pitch ?? 0,
            yaw: last?.yaw ?? 0,
          };
          if (angle === 0) point.roll = value;
          if (angle === 1) point.pitch = value;
          if (angle === 2) point.yaw = value;
          list.push(point);
          return { ...prev, [idx]: list.slice(-50) };
        });
      }

      if (msg.type === 'led' && msg.station_index !== undefined) {
        const idx = msg.station_index;
        setStations((prev) => {
          const next = [...prev];
          next[idx] = {
            ...next[idx],
            led: { r: !!msg.r, g: !!msg.g, b: !!msg.b },
          };
          return next;
        });
      }
    },
    [godFilterEnabled, godFilterIds, godPaused],
  );

  const handleIncoming = useCallback(
    async (chunk: Uint8Array) => {
      const client = protocolRef.current;
      if (!client) return;
      const result = await client.onBytes(chunk);
      appendProtocolLogs(result.logs);
      if (result.error) addLog('error', result.error);
      if (result.messages.length > 0) {
        addLog('info', `Parsed ${result.messages.length} message(s)`);
      }
      for (const msg of result.messages) processMessage(msg);
    },
    [addLog, appendProtocolLogs, processMessage],
  );

  const reloadProtocol = useCallback(async (codeOverride?: string) => {
    const code = codeOverride ?? protocolCode;
    setProtocolLoading(true);
    setProtocolError(null);
    try {
      protocolRef.current?.dispose();
      const client = new ProtocolClient();
      const logs = await client.init(stationCount, code);
      protocolRef.current = client;
      appendProtocolLogs(logs);
      setProtocolReady(true);
      addLog('info', 'Protocol handler loaded');
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      setProtocolReady(false);
      setProtocolError(message);
      addLog('error', message);
    } finally {
      setProtocolLoading(false);
    }
  }, [addLog, appendProtocolLogs, protocolCode, stationCount]);

  useEffect(() => {
    void reloadProtocol();
    prevStationCountRef.current = stationCount;
    return () => protocolRef.current?.dispose();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- initial load only
  }, []);

  useEffect(() => {
    if (prevStationCountRef.current === null || prevStationCountRef.current === stationCount) {
      return;
    }
    prevStationCountRef.current = stationCount;
    void reloadProtocol();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- reload when station count changes
  }, [stationCount]);

  const writeSerial = useCallback(
    async (data: Uint8Array | string) => {
      const bytes = typeof data === 'string' ? new TextEncoder().encode(data) : data;
      await serialRef.current.write(bytes);
    },
    [],
  );

  const connect = useCallback(async () => {
    setConnecting(true);
    try {
      await serialRef.current.connect(baudRate, (chunk) => {
        void handleIncoming(chunk);
      });
      setConnected(true);
      addLog('info', `Connected at ${baudRate} baud`);
    } catch (err) {
      addLog('error', err instanceof Error ? err.message : String(err));
    } finally {
      setConnecting(false);
    }
  }, [addLog, baudRate, handleIncoming]);

  const disconnect = useCallback(async () => {
    try {
      if (connected) {
        await writeSerial('M1\n');
      }
    } catch {
      // ignore
    }
    await serialRef.current.disconnect();
    setConnected(false);
    setStations(createStations(stationCount));
    setAngleHistory({});
    addLog('info', 'Disconnected');
  }, [addLog, connected, stationCount, writeSerial]);

  const sendLed = useCallback(
    async (stationIndex: number, r: boolean, g: boolean, b: boolean) => {
      const client = protocolRef.current;
      if (!client) return;
      const result = await client.buildLedCommand(stationIndex, r, g, b);
      appendProtocolLogs(result.logs);
      if (result.error) {
        addLog('error', result.error);
        return;
      }
      if (connected) {
        await writeSerial(result.bytes);
        addLog('info', `LED sent to station ${stationIndex}`);
      } else {
        await handleIncoming(result.bytes);
        addLog('info', 'LED command parsed locally (not connected)');
      }
    },
    [addLog, appendProtocolLogs, connected, handleIncoming, writeSerial],
  );

  const injectBytes = useCallback(
    async (data: Uint8Array) => {
      if (connected) {
        await writeSerial(data);
        addLog('info', `Injected ${data.length} bytes to serial`);
      } else {
        await handleIncoming(data);
        addLog('info', `Injected ${data.length} bytes locally`);
      }
    },
    [addLog, connected, handleIncoming, writeSerial],
  );

  const sendCanMode = useCallback(
    async (mode: 'NORMAL' | 'LOOPBACK') => {
      await writeSerial(`MODE_${mode}\n`);
      addLog('info', `CAN mode set to ${mode}`);
    },
    [addLog, writeSerial],
  );

  const sendManualCan = useCallback(
    async (canId: number, data: Uint8Array) => {
      let cmd = `SEND_${canId.toString(16)}`;
      for (const b of data) cmd += `_${b.toString(16).padStart(2, '0')}`;
      cmd += '\n';
      await writeSerial(cmd);
      addLog('info', `Manual CAN TX ID=0x${canId.toString(16)} (${data.length} bytes)`);
    },
    [addLog, writeSerial],
  );

  const sendAngleGroups = useCallback(
    async (groups: number[], angleType: string, value: number) => {
      for (const group of groups) {
        const canId = 0x100 + group;
        const data = new TextEncoder().encode(`${angleType}${value >= 0 ? '+' : ''}${value}`);
        await sendManualCan(canId, data);
      }
    },
    [sendManualCan],
  );

  const sendGodLed = sendLed;

  const stopRandomTraffic = useCallback((silent = false) => {
    const wasRunning = randomTimerRef.current !== null;
    if (randomTimerRef.current) window.clearInterval(randomTimerRef.current);
    randomTimerRef.current = null;
    randomStateRef.current = {};
    setRandomRunning(false);
    if (wasRunning && !silent) addLog('info', 'Random traffic stopped');
  }, [addLog]);

  const startRandomTraffic = useCallback(
    (groups: number[], modes: string[], periodMs: number) => {
      stopRandomTraffic(true);
      const state: Record<number, { mode: string; start: number; constValue: number }> = {};
      for (const g of groups) {
        state[g] = {
          mode: modes[g] ?? 'Noise',
          start: Date.now(),
          constValue: Math.floor(Math.random() * 180) - 90,
        };
      }
      randomStateRef.current = state;
      randomTimerRef.current = window.setInterval(() => {
        const angles = ['R', 'C', 'O'];
        for (const [groupStr, st] of Object.entries(randomStateRef.current)) {
          const group = Number(groupStr);
          const angleType = angles[Math.floor(Math.random() * angles.length)];
          let value: number;
          if (st.mode === 'Sine') {
            const elapsed = (Date.now() - st.start) / 1000;
            value = Math.round(90 * Math.sin(elapsed * 0.5));
          } else if (st.mode === 'Const') {
            value = st.constValue;
          } else {
            value = Math.floor(Math.random() * 360) - 179;
          }
          value = Math.max(-179, Math.min(180, value));
          void sendAngleGroups([group], angleType, value);
        }
      }, periodMs);
      setRandomRunning(true);
      addLog('info', `Random traffic started (${periodMs} ms)`);
    },
    [addLog, sendAngleGroups, stopRandomTraffic],
  );

  const godOpenRef = useRef(false);

  const openGodMode = useCallback(() => {
    if (godOpenRef.current) return;
    godOpenRef.current = true;
    setGodOpen(true);
    if (serialRef.current.isConnected) {
      void writeSerial('M1\n').then(() => addLog('info', 'Sniffer mode (M1) enabled'));
    }
  }, [addLog, writeSerial]);

  const closeGodMode = useCallback(() => {
    if (!godOpenRef.current) return;
    godOpenRef.current = false;
    setGodOpen(false);
    stopRandomTraffic();
    if (serialRef.current.isConnected) {
      void (async () => {
        await writeSerial('MODE_NORMAL\n');
        await writeSerial('M1\n');
        addLog('info', 'God Mode closed: NORMAL + M1');
      })();
    }
  }, [addLog, stopRandomTraffic, writeSerial]);

  const clearGodRows = useCallback(() => setGodRows([]), []);

  const exportGodLog = useCallback(() => {
    const lines = godRows.map(
      (r) => `[${r.timestamp}] ID=${r.canId} DLC=${r.dlc} Type=${r.type} Data=[${r.hex}] ASCII=[${r.ascii}]`,
    );
    const blob = new Blob([lines.join('\n')], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'can_log.txt';
    a.click();
    URL.revokeObjectURL(url);
  }, [godRows]);

  const value = useMemo<AppContextValue>(
    () => ({
      view,
      setView,
      stationCount,
      setStationCount,
      visibleStations,
      setVisibleStations,
      baudRate,
      setBaudRate,
      connected,
      connecting,
      protocolReady,
      protocolLoading,
      protocolError,
      godOpen,
      openGodMode,
      closeGodMode,
      protocolCode,
      setProtocolCode,
      reloadProtocol,
      connect,
      disconnect,
      writeSerial,
      sendLed,
      injectBytes,
      stations,
      logs,
      addLog,
      modelIndex,
      setModelIndex,
      chartStation,
      setChartStation,
      angleHistory,
      godRows,
      godPaused,
      setGodPaused,
      godFilterEnabled,
      setGodFilterEnabled,
      godFilterIds,
      setGodFilterIds,
      clearGodRows,
      exportGodLog,
      sendCanMode,
      sendManualCan,
      sendAngleGroups,
      sendGodLed,
      startRandomTraffic,
      stopRandomTraffic,
      randomRunning,
    }),
    [
      view,
      stationCount,
      visibleStations,
      baudRate,
      connected,
      connecting,
      protocolReady,
      protocolLoading,
      protocolError,
      godOpen,
      openGodMode,
      closeGodMode,
      protocolCode,
      reloadProtocol,
      connect,
      disconnect,
      writeSerial,
      sendLed,
      injectBytes,
      stations,
      logs,
      addLog,
      modelIndex,
      chartStation,
      angleHistory,
      godRows,
      godPaused,
      godFilterEnabled,
      godFilterIds,
      clearGodRows,
      exportGodLog,
      sendCanMode,
      sendManualCan,
      sendAngleGroups,
      sendGodLed,
      startRandomTraffic,
      stopRandomTraffic,
      randomRunning,
      setStationCount,
      setBaudRate,
      setProtocolCode,
    ],
  );

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useApp() {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error('useApp must be used within AppProvider');
  return ctx;
}
