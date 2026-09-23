import { stationIdName } from '../constants';
import type { StationState } from '../types';

function elapsedLabel(ts: number | null): string {
  if (!ts) return '--';
  const s = Math.floor((Date.now() - ts) / 1000);
  if (s < 1) return 'now';
  if (s < 60) return `${s}s`;
  return `${Math.floor(s / 60)}m ${s % 60}s`;
}

function ledStyle(on: boolean, color: string): React.CSSProperties {
  return {
    width: 14,
    height: 14,
    borderRadius: 2,
    background: on ? color : '#ccc',
    border: '1px solid #999',
  };
}

export function StationPanel({
  stations,
  visibleCount,
  onPlot,
}: {
  stations: StationState[];
  visibleCount: number;
  onPlot: (index: number) => void;
}) {
  return (
    <div className="station-grid">
      {stations.slice(0, visibleCount).map((s, i) => (
        <div key={i} className={`station-card ${s.active ? 'active' : ''}`}>
          <div className="station-card-header">
            <strong>Station {stationIdName(i)}</strong>
            <span className="muted">{elapsedLabel(s.lastUpdate)}</span>
          </div>
          <div className="station-angles">
            <span>Roll {s.roll}°</span>
            <span>Pitch {s.pitch}°</span>
            <span>Yaw {s.yaw}°</span>
          </div>
          <div className="led-row">
            <span style={ledStyle(s.led.r, '#c0392b')} title="R" />
            <span style={ledStyle(s.led.g, '#27ae60')} title="G" />
            <span style={ledStyle(s.led.b, '#2980b9')} title="B" />
          </div>
          <button type="button" className="btn-secondary" onClick={() => onPlot(i)}>
            Chart
          </button>
        </div>
      ))}
    </div>
  );
}
