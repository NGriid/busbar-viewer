import { config } from '../config/env';
import { useIoTConnection } from '../hooks/useIoTConnection';
import { ConnectionStatus } from './ConnectionStatus';
import { MessageList } from './MessageList';
import { RawPayloadPanel } from './RawPayloadPanel';
import { ErrorPanel } from './ErrorPanel';

export function DebugDashboard() {
    const {
        connectionState,
        messages,
        messageCount,
        lastTimestamp,
        credentialExpiry,
        error,
        isPaused,
        connect,
        disconnect,
        clearMessages,
        togglePause,
    } = useIoTConnection();

    const latestMessage = messages.length > 0 ? messages[messages.length - 1] : null;

    return (
        <div className="debug-dashboard">
            <header className="dashboard-header">
                <h1>{config.appTitle}</h1>
                <span className="subtitle">Phase 1 — Debug Console</span>
            </header>

            <ErrorPanel error={error} />

            <div className="dashboard-grid">
                <ConnectionStatus
                    connectionState={connectionState}
                    credentialExpiry={credentialExpiry}
                    onConnect={connect}
                    onDisconnect={disconnect}
                />

                <RawPayloadPanel message={latestMessage} />
            </div>

            <MessageList
                messages={messages}
                messageCount={messageCount}
                lastTimestamp={lastTimestamp}
                isPaused={isPaused}
                onClear={clearMessages}
                onTogglePause={togglePause}
            />
        </div>
    );
}
