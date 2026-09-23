import { useEffect, useRef, useState } from 'react';
import type { LogEntry } from '../types';

export function LogPanel({ logs }: { logs: LogEntry[] }) {
  const [open, setOpen] = useState(true);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [logs]);

  return (
    <footer className={`log-dock ${open ? 'open' : 'closed'}`}>
      <div className="log-dock-bar">
        <strong>Log</strong>
        <button type="button" className="btn-secondary" onClick={() => setOpen((v) => !v)}>
          {open ? 'Hide' : 'Show'}
        </button>
      </div>
      {open && (
        <div className="log-scroll" ref={scrollRef}>
          {logs.length === 0 && <p className="muted">No messages yet.</p>}
          {logs.map((entry) => (
            <div key={entry.id} className={`log-line log-${entry.level}`}>
              <span className="log-time">{entry.time}</span>
              <span>{entry.text}</span>
            </div>
          ))}
        </div>
      )}
    </footer>
  );
}
