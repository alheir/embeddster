import { useEffect, useState } from 'react';
import { stationIdName } from '../constants';
import { useApp } from '../context/AppContext';

const ANGLE_TYPES = ['Roll (R)', 'Pitch (C)', 'Yaw (O)'];
const ANGLE_CODES = ['R', 'C', 'O'];
const RANDOM_MODES = ['Sine', 'Const', 'Noise'];

export function GodModeView() {
  const {
    stationCount,
    connected,
    godRows,
    godPaused,
    setGodPaused,
    godFilterEnabled,
    setGodFilterEnabled,
    godFilterIds,
    setGodFilterIds,
    clearGodRows,
    exportGodLog,
    closeGodMode,
    sendCanMode,
    sendManualCan,
    sendAngleGroups,
    sendGodLed,
    startRandomTraffic,
    stopRandomTraffic,
    randomRunning,
    stations,
  } = useApp();

  const [manualId, setManualId] = useState('0x100');
  const [manualData, setManualData] = useState('R+10');
  const [manualHex, setManualHex] = useState(false);
  const [angleTypeIdx, setAngleTypeIdx] = useState(0);
  const [angleValue, setAngleValue] = useState(0);
  const [angleGroups, setAngleGroups] = useState<boolean[]>(() => Array(stationCount).fill(false));
  const [ledGroup, setLedGroup] = useState(0);
  const [ledR, setLedR] = useState(false);
  const [ledG, setLedG] = useState(true);
  const [ledB, setLedB] = useState(false);
  const [randomPeriod, setRandomPeriod] = useState(500);
  const [randomGroups, setRandomGroups] = useState<boolean[]>(() => Array(stationCount).fill(true));
  const [randomModes, setRandomModes] = useState<string[]>(() => Array(stationCount).fill('Noise'));

  useEffect(() => {
    setAngleGroups((prev) => {
      const next = Array(stationCount).fill(false);
      for (let i = 0; i < Math.min(prev.length, stationCount); i++) next[i] = prev[i];
      return next;
    });
    setRandomGroups((prev) => {
      const next = Array(stationCount).fill(true);
      for (let i = 0; i < Math.min(prev.length, stationCount); i++) next[i] = prev[i];
      return next;
    });
    setRandomModes((prev) => {
      const next = Array(stationCount).fill('Noise');
      for (let i = 0; i < Math.min(prev.length, stationCount); i++) next[i] = prev[i];
      return next;
    });
  }, [stationCount]);

  const sendManual = async () => {
    const canId = parseInt(manualId.trim(), manualId.trim().startsWith('0x') ? 16 : 10);
    const data = manualHex
      ? new Uint8Array(manualData.split(/\s+/).map((b) => parseInt(b, 16)))
      : new TextEncoder().encode(manualData);
    await sendManualCan(canId, data);
  };

  const sendAngle = async () => {
    const groups = angleGroups.map((on, i) => (on ? i : -1)).filter((i) => i >= 0);
    const type = ANGLE_CODES[angleTypeIdx];
    await sendAngleGroups(groups, type, angleValue);
  };

  const toggleRandom = () => {
    if (randomRunning) {
      stopRandomTraffic();
      return;
    }
    const groups = randomGroups.map((on, i) => (on ? i : -1)).filter((i) => i >= 0);
    startRandomTraffic(groups, randomModes, randomPeriod);
  };

  return (
    <div className="god-window" role="dialog" aria-label="God Mode">
      <div className="god-window-bar">
        <strong>God Mode</strong>
        <button type="button" className="btn-secondary" onClick={closeGodMode}>
          Close
        </button>
      </div>
      <div className="god-layout">
      <div className="panel god-controls">
        <div className="row">
          <button type="button" className="btn-secondary" disabled={!connected} onClick={() => void sendCanMode('NORMAL')}>
            Normal mode
          </button>
          <button type="button" className="btn-secondary" disabled={!connected} onClick={() => void sendCanMode('LOOPBACK')}>
            Loopback mode
          </button>
          <button type="button" className="btn-secondary" onClick={() => setGodPaused(!godPaused)}>
            {godPaused ? 'Resume' : 'Pause'}
          </button>
          <button type="button" className="btn-secondary" onClick={clearGodRows}>Clear</button>
          <button type="button" className="btn-secondary" onClick={exportGodLog}>Export</button>
          <label>
            <input type="checkbox" checked={godFilterEnabled} onChange={(e) => setGodFilterEnabled(e.target.checked)} />
            Filter IDs
          </label>
          <input
            className="grow"
            disabled={!godFilterEnabled}
            value={godFilterIds}
            onChange={(e) => setGodFilterIds(e.target.value)}
            placeholder="0x100,0x101"
          />
        </div>
      </div>

      <div className="god-columns">
        <div className="god-left">
          <div className="panel">
            <h3>Manual CAN</h3>
            <label>ID <input value={manualId} onChange={(e) => setManualId(e.target.value)} /></label>
            <label>
              <input type="checkbox" checked={manualHex} onChange={(e) => setManualHex(e.target.checked)} /> Hex data
            </label>
            <input value={manualData} onChange={(e) => setManualData(e.target.value)} />
            <button type="button" className="btn-primary" disabled={!connected} onClick={() => void sendManual()}>
              Send
            </button>
          </div>

          <div className="panel">
            <h3>Angle message</h3>
            <select value={angleTypeIdx} onChange={(e) => setAngleTypeIdx(Number(e.target.value))}>
              {ANGLE_TYPES.map((t) => <option key={t}>{t}</option>)}
            </select>
            <label>
              Value
              <input type="number" min={-179} max={180} value={angleValue} onChange={(e) => setAngleValue(Number(e.target.value))} />
            </label>
            <div className="checkbox-grid">
              {Array.from({ length: stationCount }, (_, i) => (
                <label key={i}>
                  <input
                    type="checkbox"
                    checked={angleGroups[i]}
                    onChange={(e) => {
                      const next = [...angleGroups];
                      next[i] = e.target.checked;
                      setAngleGroups(next);
                    }}
                  />
                  G{i}
                </label>
              ))}
            </div>
            <button type="button" className="btn-primary" disabled={!connected} onClick={() => void sendAngle()}>
              Send angle
            </button>
          </div>

          <div className="panel">
            <h3>LED command</h3>
            <label>
              Group
              <input type="number" min={0} max={stationCount - 1} value={ledGroup} onChange={(e) => setLedGroup(Number(e.target.value))} />
            </label>
            <div className="row">
              <label><input type="checkbox" checked={ledR} onChange={(e) => setLedR(e.target.checked)} /> R</label>
              <label><input type="checkbox" checked={ledG} onChange={(e) => setLedG(e.target.checked)} /> G</label>
              <label><input type="checkbox" checked={ledB} onChange={(e) => setLedB(e.target.checked)} /> B</label>
            </div>
            <button type="button" className="btn-primary" disabled={!connected} onClick={() => void sendGodLed(ledGroup, ledR, ledG, ledB)}>
              Send LED
            </button>
          </div>

          <div className="panel">
            <h3>Random traffic</h3>
            <label>
              Period (ms)
              <input type="number" min={100} value={randomPeriod} onChange={(e) => setRandomPeriod(Number(e.target.value))} />
            </label>
            {Array.from({ length: stationCount }, (_, i) => (
              <div key={i} className="row">
                <label>
                  <input
                    type="checkbox"
                    checked={randomGroups[i]}
                    onChange={(e) => {
                      const next = [...randomGroups];
                      next[i] = e.target.checked;
                      setRandomGroups(next);
                    }}
                  />
                  G{i}
                </label>
                <select
                  value={randomModes[i]}
                  onChange={(e) => {
                    const next = [...randomModes];
                    next[i] = e.target.value;
                    setRandomModes(next);
                  }}
                >
                  {RANDOM_MODES.map((m) => <option key={m}>{m}</option>)}
                </select>
              </div>
            ))}
            <button type="button" className="btn-primary" disabled={!connected} onClick={toggleRandom}>
              {randomRunning ? 'Stop random' : 'Start random'}
            </button>
          </div>
        </div>

        <div className="god-right">
          <div className="panel table-panel">
            <h3>RX table ({godRows.length})</h3>
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>Time</th>
                    <th>ID</th>
                    <th>DLC</th>
                    <th>Type</th>
                    <th>Hex</th>
                    <th>ASCII</th>
                  </tr>
                </thead>
                <tbody>
                  {godRows.map((row, i) => (
                    <tr key={i}>
                      <td>{row.timestamp}</td>
                      <td>{row.canId}</td>
                      <td>{row.dlc}</td>
                      <td>{row.type}</td>
                      <td>{row.hex}</td>
                      <td>{row.ascii}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="panel">
            <h3>Station snapshot</h3>
            <table>
              <thead>
                <tr>
                  <th>Station</th>
                  <th>Roll</th>
                  <th>Pitch</th>
                  <th>Yaw</th>
                </tr>
              </thead>
              <tbody>
                {stations.map((s, i) => (
                  <tr key={i}>
                    <td>{stationIdName(i)}</td>
                    <td>{s.roll}</td>
                    <td>{s.pitch}</td>
                    <td>{s.yaw}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
      </div>
    </div>
  );
}
