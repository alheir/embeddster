import { useState } from 'react';
import { BAUD_RATES, MAX_STATIONS, MIN_STATIONS, stationIdName } from '../constants';
import { useApp } from '../context/AppContext';
import { AngleChart } from './AngleChart';
import { ByteInjector } from './ByteInjector';
import { StationPanel } from './StationPanel';
import { StationViewer } from './StationViewer';

export function MainView() {
  const {
    visibleStations,
    setVisibleStations,
    stationCount,
    setStationCount,
    baudRate,
    setBaudRate,
    connected,
    connecting,
    connect,
    disconnect,
    sendLed,
    stations,
    modelIndex,
    setModelIndex,
    chartStation,
    setChartStation,
    angleHistory,
    protocolLoading,
  } = useApp();

  const [ledStation, setLedStation] = useState(0);
  const [ledR, setLedR] = useState(false);
  const [ledG, setLedG] = useState(false);
  const [ledB, setLedB] = useState(false);
  const [showChart, setShowChart] = useState(false);
  const [customBaud, setCustomBaud] = useState(String(baudRate));
  const presetBaud = (BAUD_RATES as readonly number[]).includes(baudRate);

  return (
    <div className="main-layout">
      <aside className="sidebar">
        <div className="panel">
          <h3>Serial</h3>
          <label>
            Baud rate
            <select
              value={presetBaud ? baudRate : 'custom'}
              disabled={connected}
              onChange={(e) => {
                if (e.target.value === 'custom') return;
                const rate = Number(e.target.value);
                setBaudRate(rate);
                setCustomBaud(String(rate));
              }}
            >
              {BAUD_RATES.map((b) => (
                <option key={b} value={b}>{b}</option>
              ))}
              <option value="custom">Custom</option>
            </select>
          </label>
          <label>
            Custom baud
            <input
              type="number"
              min={300}
              max={2000000}
              disabled={connected}
              value={customBaud}
              onChange={(e) => setCustomBaud(e.target.value)}
              onBlur={() => {
                const rate = Number(customBaud);
                if (rate >= 300) setBaudRate(rate);
              }}
            />
          </label>
          <button
            type="button"
            className="btn-primary full"
            disabled={connecting || protocolLoading}
            onClick={() => void (connected ? disconnect() : connect())}
          >
            {connected ? 'Disconnect' : connecting ? 'Connecting...' : 'Connect'}
          </button>
        </div>

        <div className="panel">
          <h3>Stations</h3>
          <label>
            Protocol station count
            <input
              type="number"
              min={MIN_STATIONS}
              max={MAX_STATIONS}
              value={stationCount}
              disabled={connected}
              onChange={(e) => setStationCount(Number(e.target.value))}
            />
          </label>
          <label>
            Visible on screen
            <input
              type="number"
              min={MIN_STATIONS}
              max={stationCount}
              value={visibleStations}
              onChange={(e) => setVisibleStations(Number(e.target.value))}
            />
          </label>
          <label>
            Model
            <select value={modelIndex} onChange={(e) => setModelIndex(Number(e.target.value))}>
              <option value={0}>FRDM-K64F</option>
              <option value={1}>Plane</option>
            </select>
          </label>
        </div>

        <div className="panel">
          <h3>LED command</h3>
          <label>
            Station
            <select value={ledStation} onChange={(e) => setLedStation(Number(e.target.value))}>
              {Array.from({ length: stationCount }, (_, i) => (
                <option key={i} value={i}>{stationIdName(i)}</option>
              ))}
            </select>
          </label>
          <div className="row">
            <label><input type="checkbox" checked={ledR} onChange={(e) => setLedR(e.target.checked)} /> R</label>
            <label><input type="checkbox" checked={ledG} onChange={(e) => setLedG(e.target.checked)} /> G</label>
            <label><input type="checkbox" checked={ledB} onChange={(e) => setLedB(e.target.checked)} /> B</label>
          </div>
          <button
            type="button"
            className="btn-primary full"
            onClick={() => void sendLed(ledStation, ledR, ledG, ledB)}
          >
            Send LED
          </button>
        </div>

        <ByteInjector />
      </aside>

      <section className="main-content">
        <StationViewer stations={stations} visibleCount={visibleStations} modelIndex={modelIndex} />
        <StationPanel
          stations={stations}
          visibleCount={visibleStations}
          onPlot={(i) => {
            setChartStation(i);
            setShowChart(true);
          }}
        />
        {showChart && (
          <AngleChart stationIndex={chartStation} data={angleHistory[chartStation] ?? []} />
        )}
      </section>
    </div>
  );
}
