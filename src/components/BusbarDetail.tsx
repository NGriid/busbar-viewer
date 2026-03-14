import { useDashboardStore } from '../store/dashboardStore';
import { TerminalCard } from './TerminalCard';
import { FreshnessBadge } from './FreshnessBadge';
import { getFreshnessLevel } from '../utils/freshness';
import { decodeGpsStatus, formatErrorFlagsHex, formatGpsFixType } from '../utils/gps';

const EMPTY_TERMINALS: Record<number, never> = {};

export function BusbarDetail() {
  const selectedId = useDashboardStore((s) => s.ui.selectedBusbarId);
  const busbar = useDashboardStore((s) => selectedId ? s.busbarsById[selectedId] : null);
  const terminals = useDashboardStore((s) =>
    selectedId ? s.terminalsByBusbarId[selectedId] ?? EMPTY_TERMINALS : EMPTY_TERMINALS
  );
  const selectBusbar = useDashboardStore((s) => s.selectBusbar);

  if (!busbar) {
    return (
      <div className="busbar-detail-empty">
        <button className="btn btn-small" onClick={() => selectBusbar(null)}>← Back to Dashboard</button>
        <p>Busbar {selectedId} not found.</p>
      </div>
    );
  }

  const freshness = getFreshnessLevel(busbar.lastSeenAt);
  const decodedGps = busbar.gpsStatus != null ? decodeGpsStatus(busbar.gpsStatus) : null;

  // We have 15 terminals. Show them in order.
  const terminalNumbers = Array.from({ length: 15 }, (_, i) => i + 1);

  return (
    <div className="busbar-detail-view">
      <button className="btn btn-small back-btn" onClick={() => selectBusbar(null)}>← Back to Dashboard</button>
      
      <div className="busbar-detail-header panel">
        <div className="title-row">
          <h2>Busbar: {busbar.deviceId}</h2>
          <FreshnessBadge level={freshness} lastSeenAt={busbar.lastSeenAt} />
        </div>

        <div className="detail-grid">
          <div className="detail-item">
            <label>Fix Validity</label>
            <span>{decodedGps ? (decodedGps.fixValid ? 'Valid' : 'Invalid') : '--'}</span>
          </div>
          <div className="detail-item">
            <label>Fix Type</label>
            <span>{decodedGps ? formatGpsFixType(decodedGps.fixType) : '--'}</span>
          </div>
          <div className="detail-item">
            <label>Satellites</label>
            <span>{decodedGps ? decodedGps.satellites : '--'}</span>
          </div>
          <div className="detail-item">
            <label>Location</label>
            <span>{busbar.latitude ?? '--'}, {busbar.longitude ?? '--'}</span>
          </div>
          <div className="detail-item">
            <label>Altitude / Speed</label>
            <span>{busbar.altitude ?? '--'}m / {busbar.speed ?? '--'}</span>
          </div>
          <div className="detail-item">
            <label>Frequency</label>
            <span>{busbar.frequency ? `${busbar.frequency.toFixed(1)} Hz` : '--'}</span>
          </div>
          <div className="detail-item">
            <label>Signal (RSSI)</label>
            <span>{busbar.loraRSSI != null ? `${busbar.loraRSSI} dBm` : '--'}</span>
          </div>
          <div className="detail-item">
            <label>Error Flags</label>
            <span>{busbar.errorFlags != null ? formatErrorFlagsHex(busbar.errorFlags) : '--'}</span>
          </div>
          <div className="detail-item">
            <label>Multi Paths</label>
            <span>{busbar.multiPaths ?? '--'}</span>
          </div>
          
          <div className="detail-item">
            <label>Chip Temps (M/S1/S2)</label>
            <span>{busbar.masterChipTemp ?? '--'}° / {busbar.slave1ChipTemp ?? '--'}° / {busbar.slave2ChipTemp ?? '--'}°</span>
          </div>
          <div className="detail-item">
            <label>Thermistor</label>
            <span>{busbar.thermistorTemp ?? '--'}°</span>
          </div>
          <div className="detail-item">
            <label>Ext Rg I (R / Y / B)</label>
            <span>{busbar.extRgIRed ?? '--'} / {busbar.extRgIYellow ?? '--'} / {busbar.extRgIBlue ?? '--'}</span>
          </div>
        </div>
      </div>

      <div className="terminals-section">
        <h3>Terminals (15)</h3>
        <div className="terminal-grid">
          {terminalNumbers.map(num => {
            const t = terminals[num];
            return <TerminalCard key={num} terminal={t} terminalNumber={num} busbarId={busbar.deviceId} />;
          })}
        </div>
      </div>
    </div>
  );
}
