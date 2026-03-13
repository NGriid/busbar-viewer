import type { ConnectionState } from '../types/iot';
import { config } from '../config/env';

interface Props {
    connectionState: ConnectionState;
    credentialExpiry: Date | null;
    onConnect: () => void;
    onDisconnect: () => void;
}

const STATE_COLORS: Record<ConnectionState, string> = {
    idle: '#6b7280',
    connecting: '#f59e0b',
    connected: '#10b981',
    reconnecting: '#f59e0b',
    disconnected: '#ef4444',
    error: '#ef4444',
};

function formatExpiry(date: Date | null): string {
    if (!date) return '—';
    const diff = date.getTime() - Date.now();
    if (diff <= 0) return 'Expired';
    const minutes = Math.floor(diff / 60_000);
    const seconds = Math.floor((diff % 60_000) / 1_000);
    return `${minutes}m ${seconds}s`;
}

export function ConnectionStatus({
    connectionState,
    credentialExpiry,
    onConnect,
    onDisconnect,
}: Props) {
    const isConnected = connectionState === 'connected';
    const isConnecting =
        connectionState === 'connecting' || connectionState === 'reconnecting';

    return (
        <div className="panel connection-status">
            <h2>Connection</h2>

            <div className="status-row">
                <span className="status-label">State:</span>
                <span
                    className="status-indicator"
                    style={{ color: STATE_COLORS[connectionState] }}
                >
                    <span className="status-dot" style={{ backgroundColor: STATE_COLORS[connectionState] }} />
                    {connectionState}
                </span>
            </div>

            <div className="status-row">
                <span className="status-label">Topic:</span>
                <code className="topic-name">{config.iotTopic}</code>
            </div>

            <div className="status-row">
                <span className="status-label">Credential Expiry:</span>
                <span className="credential-expiry">{formatExpiry(credentialExpiry)}</span>
            </div>

            <div className="button-row">
                <button
                    className="btn btn-connect"
                    onClick={onConnect}
                    disabled={isConnected || isConnecting}
                >
                    {isConnecting ? 'Connecting…' : 'Connect'}
                </button>
                <button
                    className="btn btn-disconnect"
                    onClick={onDisconnect}
                    disabled={!isConnected && !isConnecting}
                >
                    Disconnect
                </button>
            </div>
        </div>
    );
}
