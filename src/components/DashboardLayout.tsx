import { useDashboardStore } from '../store/dashboardStore';
import { useAutoConnect } from '../hooks/useAutoConnect';
import { config } from '../config/env';
import { ErrorPanel } from './ErrorPanel';
import { GatewaySummary } from './GatewaySummary';
import { BusbarGrid } from './BusbarGrid';
import { BusbarDetail } from './BusbarDetail';
import { DiagnosticsPanel } from './DiagnosticsPanel';

export function DashboardLayout() {
  const isIntentionallyDisconnected = useDashboardStore((s) => s.isIntentionallyDisconnected);

  // Automatically connect the IoT service, unless the user manually disconnected
  useAutoConnect(!isIntentionallyDisconnected);

  const view = useDashboardStore((s) => s.ui.view);
  const setView = useDashboardStore((s) => s.setView);
  const isHydrated = useDashboardStore((s) => s.initialHydrationComplete);
  const error = useDashboardStore((s) => s.error);

  return (
    <div className="app-layout">
      {/* ─── Top Navigation ─── */}
      <header className="app-header">
        <div className="header-brand">
          <h1>{config.appTitle}</h1>
          {/* <span className="badge-phase">Phase 2</span> */}
        </div>
        
        <nav className="header-nav">
          <button 
            className={`nav-tab ${view === 'overview' || view === 'busbar-detail' ? 'active' : ''}`}
            onClick={() => setView('overview')}
          >
            Dashboard
          </button>
          <button 
            className={`nav-tab ${view === 'diagnostics' ? 'active' : ''}`}
            onClick={() => setView('diagnostics')}
          >
            Diagnostics
          </button>
        </nav>
      </header>

      {/* ─── Main Content Area ─── */}
      <main className="app-main">
        {/* We can still show the error panel globally if connection drops */}
        <ErrorPanel error={error} />

        {view === 'overview' && (
          <div className="view-overview">
            <GatewaySummary />
            <BusbarGrid />
            
            {!isHydrated && (
              <div className="hydration-warning">
                Awaiting full network snapshot. Partial data is shown. (Max 2m wait)
              </div>
            )}
          </div>
        )}

        {view === 'busbar-detail' && (
          <div className="view-detail">
            <BusbarDetail />
          </div>
        )}

        {view === 'diagnostics' && (
          <div className="view-diagnostics">
            <DiagnosticsPanel />
          </div>
        )}
      </main>
    </div>
  );
}
