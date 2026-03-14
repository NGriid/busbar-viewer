import { useDashboardStore } from '../store/dashboardStore';
import { FreshnessBadge } from './FreshnessBadge';
import { getFreshnessLevel } from '../utils/freshness';
import type { BusbarState } from '../types/dashboard';

interface BusbarCardProps {
  busbar: BusbarState;
}

const EMPTY_TERMINALS: Record<number, never> = {};

export function BusbarCard({ busbar }: BusbarCardProps) {
  const selectBusbar = useDashboardStore((s) => s.selectBusbar);
  const terminals = useDashboardStore(
    (s) => s.terminalsByBusbarId[busbar.deviceId] ?? EMPTY_TERMINALS
  );
  
  const freshness = getFreshnessLevel(busbar.lastSeenAt);
  const terminalsSeen = Object.keys(terminals).length;
  const overloadedCount = Object.values(terminals).filter(t => t.overloadStatus === 1).length;

  return (
    <div className="busbar-card panel" onClick={() => selectBusbar(busbar.deviceId)}>
      <div className="busbar-card-header">
        <h3 className="busbar-id">{busbar.deviceId}</h3>
        <FreshnessBadge level={freshness} lastSeenAt={busbar.lastSeenAt} showText={false} />
      </div>

      <div className="busbar-metrics">
        <div className="metric-row">
          <span className="label">Frequency:</span>
          <span className="val">{busbar.frequency ? `${busbar.frequency.toFixed(1)} Hz` : '--'}</span>
        </div>
        <div className="metric-row">
          <span className="label">RSSI:</span>
          <span className="val">{busbar.loraRSSI != null ? `${busbar.loraRSSI} dBm` : '--'}</span>
        </div>
        
        <div className="metric-status-badges">
          {busbar.errorFlags != null && busbar.errorFlags > 0 && (
            <span className="badge badge-error">Err: {busbar.errorFlags}</span>
          )}
          {overloadedCount > 0 && (
            <span className="badge badge-warning">{overloadedCount} Overload</span>
          )}
        </div>
      </div>

      <div className="busbar-card-footer">
        <div className="terminal-count">
          {terminalsSeen} / 15 terms
        </div>
        <div className="last-seen-text">
           {/* Just show relative natively via a simple tick block or static since the freshness badge ticks. */}
           <FreshnessBadge level={freshness} lastSeenAt={busbar.lastSeenAt} />
        </div>
      </div>
    </div>
  );
}
