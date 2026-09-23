import { useState } from 'react';
import { DEFAULT_PROTOCOL_HANDLER } from '../python/defaultProtocol';
import { useApp } from '../context/AppContext';

export function ProtocolEditor() {
  const {
    protocolCode,
    setProtocolCode,
    reloadProtocol,
    protocolLoading,
    protocolReady,
    protocolError,
    addLog,
  } = useApp();
  const [draft, setDraft] = useState(protocolCode);

  const apply = async (code: string) => {
    setProtocolCode(code);
    await reloadProtocol(code);
  };

  const onDownload = () => {
    const blob = new Blob([draft], { type: 'text/x-python' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'protocol_handler.py';
    a.click();
    URL.revokeObjectURL(url);
  };

  const onUpload = async (file: File) => {
    const text = await file.text();
    setDraft(text);
    addLog('info', `Loaded ${file.name}`);
    await apply(text);
  };

  return (
    <div className="protocol-page">
      <div className="panel">
        <h2>Protocol handler</h2>
        <p className="muted">
          Implement <code>on_bytes</code> and <code>build_led_command</code>, then apply. Upload a <code>.py</code> to load and run it.
        </p>
        <div className="row">
          <button
            type="button"
            className="btn-secondary"
            onClick={() => {
              setDraft(DEFAULT_PROTOCOL_HANDLER);
            }}
          >
            Reset stub
          </button>
          <label className="btn-secondary file-label">
            Load .py
            <input
              type="file"
              accept=".py"
              hidden
              onChange={(e) => {
                const f = e.target.files?.[0];
                e.target.value = '';
                if (f) void onUpload(f);
              }}
            />
          </label>
          <button type="button" className="btn-secondary" onClick={onDownload}>
            Download
          </button>
          <button type="button" className="btn-primary" disabled={protocolLoading} onClick={() => void apply(draft)}>
            {protocolLoading ? 'Loading...' : 'Apply'}
          </button>
          <span className={`status-pill ${protocolReady ? 'ok' : 'warn'}`}>
            {protocolLoading ? 'Loading' : protocolReady ? 'Loaded' : 'Not loaded'}
          </span>
        </div>
        {protocolError && <p className="protocol-error">{protocolError}</p>}
      </div>
      <textarea
        className="code-editor"
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        spellCheck={false}
      />
    </div>
  );
}
