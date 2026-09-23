import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { stationIdName } from '../constants';

export function AngleChart({
  stationIndex,
  data,
}: {
  stationIndex: number;
  data: { t: number; roll: number; pitch: number; yaw: number }[];
}) {
  const chartData = data.map((p, i) => ({
    i,
    roll: p.roll,
    pitch: p.pitch,
    yaw: p.yaw,
  }));

  return (
    <div className="panel chart-panel">
      <h3>Chart: {stationIdName(stationIndex)}</h3>
      {chartData.length === 0 ? (
        <p className="muted">No angle data yet.</p>
      ) : (
        <ResponsiveContainer width="100%" height={220}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="i" hide />
            <YAxis domain={[-180, 180]} />
            <Tooltip />
            <Legend />
            <Line type="monotone" dataKey="roll" stroke="#c0392b" dot={false} />
            <Line type="monotone" dataKey="pitch" stroke="#27ae60" dot={false} />
            <Line type="monotone" dataKey="yaw" stroke="#2980b9" dot={false} />
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
