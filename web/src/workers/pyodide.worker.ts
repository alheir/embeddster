import { loadPyodide, type PyodideInterface } from 'pyodide';
import { buildStationPy } from '../python/stationTemplate';

let pyodide: PyodideInterface | null = null;

const RUNTIME_HELPERS = `
import json
import sys

def _reset_src_modules():
    for name in list(sys.modules.keys()):
        if name == "src" or name.startswith("src."):
            del sys.modules[name]

def _serialize_messages(msgs):
    out = []
    for m in msgs:
        item = dict(m)
        if "data" in item and isinstance(item["data"], (bytes, bytearray)):
            item["data"] = list(item["data"])
        out.append(item)
    return json.dumps(out)

def _drain_logs():
    global _log_buffer
    text = _log_buffer.getvalue()
    _log_buffer.seek(0)
    _log_buffer.truncate(0)
    return text
`;

async function ensurePyodide(): Promise<PyodideInterface> {
  if (!pyodide) {
    pyodide = await loadPyodide({
      indexURL: `${import.meta.env.BASE_URL}pyodide/`,
    });
  }
  return pyodide;
}

function writeFs(py: PyodideInterface, stationCount: number, protocolCode: string) {
  const mkdir = (path: string) => {
    try {
      py.FS.mkdir(path);
    } catch {
      // already exists
    }
  };

  mkdir('/src');
  mkdir('/src/package');
  mkdir('/src/protocol');
  py.FS.writeFile('/src/package/__init__.py', '');
  py.FS.writeFile('/src/protocol/__init__.py', '');
  py.FS.writeFile('/src/__init__.py', '');
  py.FS.writeFile('/src/package/Station.py', buildStationPy(stationCount));
  py.FS.writeFile('/src/protocol/protocol_handler.py', protocolCode);
}

async function loadHandler(stationCount: number, protocolCode: string) {
  const py = await ensurePyodide();
  writeFs(py, stationCount, protocolCode);

  await py.runPythonAsync(`
import sys
from io import StringIO

_log_buffer = StringIO()

class _LogWriter:
    def write(self, s):
        if s:
            _log_buffer.write(s)
    def flush(self):
        pass

sys.stdout = _LogWriter()
sys.stderr = _LogWriter()

${RUNTIME_HELPERS}

_reset_src_modules()
from src.protocol.protocol_handler import ProtocolHandler
handler = ProtocolHandler()
`);
}

function drainLogs(py: PyodideInterface): string[] {
  const text = py.runPython('_drain_logs()') as string;
  if (!text) return [];
  return text.split('\n').filter((line) => line.length > 0);
}

function formatError(py: PyodideInterface, err: unknown): string {
  try {
    py.runPython('import traceback');
    const tb = py.runPython('traceback.format_exc()') as string;
    if (tb && tb !== 'NoneType: None\n') return tb;
  } catch {
    // ignore
  }
  return err instanceof Error ? err.message : String(err);
}

self.onmessage = async (event: MessageEvent) => {
  const { id, type, payload } = event.data;

  try {
    if (type === 'init') {
      const { stationCount, protocolCode } = payload as {
        stationCount: number;
        protocolCode: string;
      };
      await loadHandler(stationCount, protocolCode);
      const py = await ensurePyodide();
      self.postMessage({ id, ok: true, logs: drainLogs(py) });
      return;
    }

    const py = await ensurePyodide();

    if (type === 'on_bytes') {
      const { data } = payload as { data: Uint8Array };
      const byteList = JSON.stringify(Array.from(data));
      const raw = await py.runPythonAsync(`
msgs = handler.on_bytes(bytes(${byteList}))
_serialize_messages(msgs)
`);
      const messages = JSON.parse(String(raw));
      self.postMessage({ id, ok: true, messages, logs: drainLogs(py), error: null });
      return;
    }

    if (type === 'build_led_command') {
      const { stationIndex, r, g, b } = payload as {
        stationIndex: number;
        r: boolean;
        g: boolean;
        b: boolean;
      };
      const result = await py.runPythonAsync(`
result = handler.build_led_command(${stationIndex}, ${r ? 'True' : 'False'}, ${g ? 'True' : 'False'}, ${b ? 'True' : 'False'})
list(result)
`);
      const bytes = Array.from(result.toJs() as Iterable<number>);
      result.destroy();
      self.postMessage({ id, ok: true, bytes, logs: drainLogs(py), error: null });
      return;
    }

    self.postMessage({ id, ok: false, error: `Unknown worker message: ${type}` });
  } catch (err) {
    const py = pyodide;
    const logs = py ? drainLogs(py) : [];
    const error = py ? formatError(py, err) : String(err);
    self.postMessage({ id, ok: false, error, logs });
  }
};
