import { AppProvider, useApp } from './context/AppContext';
import { GodModeView } from './components/GodModeView';
import { LogPanel } from './components/LogPanel';
import { MainView } from './components/MainView';
import { ProtocolEditor } from './components/ProtocolEditor';
import { SerialConnection } from './lib/serial';
import './App.css';

function Shell() {
  const { view, setView, godOpen, openGodMode, logs } = useApp();

  return (
    <div className="app-shell">
      <header className="app-header">
        <div>
          <h1>Embeddster</h1>
          <p className="muted">Tilt network monitor for embedded systems lab</p>
        </div>
        <nav className="nav-tabs">
          <button type="button" className={view === 'main' ? 'active' : ''} onClick={() => setView('main')}>
            Main
          </button>
          <button type="button" className={view === 'protocol' ? 'active' : ''} onClick={() => setView('protocol')}>
            Protocol
          </button>
          <button type="button" className={godOpen ? 'active' : ''} onClick={openGodMode}>
            God Mode
          </button>
        </nav>
      </header>

      {!SerialConnection.isSupported() && (
        <div className="banner warn">
          Web Serial needs Chrome or Edge. Use localhost or HTTPS.
        </div>
      )}

      <main className="app-main">
        {view === 'main' && <MainView />}
        {view === 'protocol' && <ProtocolEditor />}
      </main>

      {godOpen && <GodModeView />}
      <LogPanel logs={logs} />
    </div>
  );
}

export default function App() {
  return (
    <AppProvider>
      <Shell />
    </AppProvider>
  );
}
