import { useState } from 'react';
import type { TerminalState } from '../types/dashboard';
import { FreshnessBadge } from './FreshnessBadge';
import { getFreshnessLevel } from '../utils/freshness';
import { TerminalDetail } from './TerminalDetail';

interface TerminalCardProps {
  busbarId: string;
  terminalNumber: number;
  terminal: TerminalState | undefined;
}

export function TerminalCard({ terminalNumber, terminal }: TerminalCardProps) {
  const [isModalOpen, setIsModalOpen] = useState(false);

  if (!terminal) {
    return (
      <div className="terminal-card empty">
        <div className="terminal-header">T{terminalNumber}</div>
        <div className="empty-msg">No data yet</div>
      </div>
    );
  }

  const freshness = getFreshnessLevel(terminal.lastSeenAt);
  const isOverloaded = terminal.overloadStatus === 1;

  return (
    <>
      <div 
        className={`terminal-card ${isOverloaded ? 'overloaded' : ''}`}
        onClick={() => setIsModalOpen(true)}
      >
        <div className="terminal-header">
          <span className="term-num">T{terminalNumber}</span>
          <FreshnessBadge level={freshness} lastSeenAt={terminal.lastSeenAt} showText={false} />
        </div>

        <div className="terminal-body">
          <div className="term-row">
            <span className="lbl">Voltage</span>
            <span className="val">{terminal.voltage != null ? `${terminal.voltage} V` : '--'}</span>
          </div>
          <div className="term-row">
            <span className="lbl">Current</span>
            <span className="val">{terminal.current != null ? `${terminal.current} A` : '--'}</span>
          </div>
          <div className="term-row">
            <span className="lbl">Power</span>
            <span className="val">{terminal.activePower != null ? `${terminal.activePower} kW` : '--'}</span>
          </div>
          <div className="term-row">
            <span className="lbl">PF</span>
            <span className="val">{terminal.powerFactor != null ? terminal.powerFactor : '--'}</span>
          </div>
        </div>

        {isOverloaded && <div className="overload-badge">Overloaded</div>}
      </div>

      {isModalOpen && (
        <TerminalDetail 
          terminal={terminal} 
          onClose={() => setIsModalOpen(false)} 
        />
      )}
    </>
  );
}
