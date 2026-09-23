import { useState } from 'react';
import { useApp } from '../context/AppContext';

export function ByteInjector() {
  const { injectBytes } = useApp();
  const [text, setText] = useState('');
  const [format, setFormat] = useState<'ascii' | 'hex'>('ascii');

  const onSend = async () => {
    const trimmed = text.trim();
    if (!trimmed) return;
    let bytes: Uint8Array;
    if (format === 'hex') {
      bytes = new Uint8Array(trimmed.split(/\s+/).map((b) => parseInt(b, 16)));
    } else {
      bytes = new TextEncoder().encode(trimmed.endsWith('\n') ? trimmed : `${trimmed}\n`);
    }
    await injectBytes(bytes);
  };

  return (
    <div className="panel">
      <h3>Byte injector</h3>
      <div className="row">
        <select value={format} onChange={(e) => setFormat(e.target.value as 'ascii' | 'hex')}>
          <option value="ascii">ASCII</option>
          <option value="hex">Hex</option>
        </select>
        <input
          className="grow"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder={format === 'hex' ? '52 2D 31 30' : 'RXED: ...'}
        />
        <button type="button" className="btn-primary" onClick={() => void onSend()}>
          Send
        </button>
      </div>
    </div>
  );
}
