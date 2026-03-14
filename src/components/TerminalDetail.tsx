import type { TerminalState } from '../types/dashboard';
import { FreshnessBadge } from './FreshnessBadge';
import { getFreshnessLevel, formatFullTime } from '../utils/freshness';

interface TerminalDetailProps {
  terminal: TerminalState;
  onClose: () => void;
}

export function TerminalDetail({ terminal, onClose }: TerminalDetailProps) {
  const freshness = getFreshnessLevel(terminal.lastSeenAt);

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content terminal-detail-modal" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h3>Terminal {terminal.terminalNumber} Details</h3>
          <button className="close-btn" onClick={onClose}>×</button>
        </div>

        <div className="modal-body">
          <div className="term-info-row">
            <strong>ID:</strong> {terminal.terminalId}
          </div>
          <div className="term-info-row">
            <FreshnessBadge level={freshness} lastSeenAt={terminal.lastSeenAt} />
            <span className="full-time">({formatFullTime(terminal.lastSeenAt)})</span>
          </div>

          <div className="term-metrics-grid">
            <div className="t-metric"><label>Voltage</label> <span>{terminal.voltage ?? '--'} V</span></div>
            <div className="t-metric"><label>Current</label> <span>{terminal.current ?? '--'} A</span></div>
            <div className="t-metric"><label>Power Factor</label> <span>{terminal.powerFactor ?? '--'}</span></div>
            
            <div className="t-metric"><label>Active Power</label> <span>{terminal.activePower ?? '--'} kW</span></div>
            <div className="t-metric"><label>Reactive Power</label> <span>{terminal.reactivePower ?? '--'} kvar</span></div>
            <div className="t-metric"><label>Apparent Power</label> <span>{terminal.apparentPower ?? '--'} kVA</span></div>
            
            <div className="t-metric"><label>Active Energy</label> <span>{terminal.activeEnergy ?? '--'} kWh</span></div>
            <div className="t-metric"><label>Reactive Energy</label> <span>{terminal.reactiveEnergy ?? '--'} kvarh</span></div>
            <div className="t-metric"><label>Apparent Energy</label> <span>{terminal.apparentEnergy ?? '--'} kVAh</span></div>
            
            <div className="t-metric"><label>Harmonic Energy</label> <span>{terminal.harmonicEnergy ?? '--'} kWh</span></div>
            
            <div className={`t-metric ${terminal.overloadStatus === 1 ? 'critical' : ''}`}>
              <label>Overload Status</label> 
              <span>{terminal.overloadStatus === 1 ? 'OVERLOADED' : 'NORMAL'}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
