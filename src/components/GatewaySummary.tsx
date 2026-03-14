import { useDashboardStore } from '../store/dashboardStore';
import { FreshnessBadge } from './FreshnessBadge';
import { getFreshnessLevel } from '../utils/freshness';
import { useIoTConnection } from '../hooks/useIoTConnection';

export function GatewaySummary() {
  const gateway = useDashboardStore((s) => s.gateway);
  const busbarsById = useDashboardStore((s) => s.busbarsById);
  const terminalsByBusbarId = useDashboardStore((s) => s.terminalsByBusbarId);
  const isHydrated = useDashboardStore((s) => s.initialHydrationComplete);
  
  // We can still use this specific piece to grab connection state visually
  const { connectionState } = useIoTConnection();

  const busbarList = Object.values(busbarsById);
  const knownCount = busbarList.length;
  const expectedCount = gateway?.subDeviceCount ?? 12;

  let staleCount = 0;
  let offlineCount = 0;
  for (const b of busbarList) {
    const freshness = getFreshnessLevel(b.lastSeenAt);
    if (freshness === 'stale') staleCount++;
    if (freshness === 'offline') offlineCount++;
  }

  let overloadedCount = 0;
  for (const busbarTerminals of Object.values(terminalsByBusbarId)) {
    for (const t of Object.values(busbarTerminals)) {
      if (t.overloadStatus === 1) overloadedCount++;
    }
  }

  return (
    <section className="gateway-summary">
      <div className="summary-card gateway-info">
        <h3>Gateway Status</h3>
        <div className="val">{gateway?.deviceId || 'Awaiting ping...'}</div>
        <div className="meta">
          {gateway && <FreshnessBadge level={getFreshnessLevel(gateway.lastSeenAt)} lastSeenAt={gateway.lastSeenAt} />}
        </div>
      </div>

      <div className="summary-card metric-card">
        <h3>Network Health</h3>
        <div className="val">{knownCount} <span className="dim">/ {expectedCount} items</span></div>
        <div className="meta">
          {staleCount > 0 && <span className="warning">{staleCount} stale</span>}
          {offlineCount > 0 && <span className="error">{offlineCount} offline</span>}
          {staleCount === 0 && offlineCount === 0 && <span className="ok">All active</span>}
        </div>
      </div>

      <div className="summary-card metric-card">
        <h3>Load Alerts</h3>
        <div className="val">{overloadedCount} <span className="dim">terminals</span></div>
        <div className="meta">
          {overloadedCount > 0 ? <span className="error">Overload detected</span> : <span className="ok">Normal load</span>}
        </div>
      </div>

      <div className="summary-card connection-card">
        <h3>Connection</h3>
        <div className="val status-indicator">
          <span className={`status-dot ${connectionState}`} />
          {connectionState}
        </div>
        <div className="meta">
          {isHydrated ? <span className="ok">Hydrated</span> : <span className="warning">Awaiting snapshot...</span>}
        </div>
      </div>
    </section>
  );
}
