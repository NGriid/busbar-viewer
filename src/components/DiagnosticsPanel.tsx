import { useIoTConnection } from '../hooks/useIoTConnection';
import { ConnectionStatus } from './ConnectionStatus';
import { MessageList } from './MessageList';
import { RawPayloadPanel } from './RawPayloadPanel';
import { useDashboardStore } from '../store/dashboardStore';

export function DiagnosticsPanel() {
  const {
    connectionState,
    credentialExpiry,
    connect,
    disconnect,
    isPaused,
    togglePause,
  } = useIoTConnection();

  const setIntentionallyDisconnected = useDashboardStore((s) => s.setIntentionallyDisconnected);

  const handleConnect = () => {
    setIntentionallyDisconnected(false);
    connect();
  };

  const handleDisconnect = () => {
    setIntentionallyDisconnected(true);
    disconnect();
  };

  // Phase 1 message list logic relied on `useIoTConnection` state, but now
  // we are buffering in Zustand for memory leak prevention and centralized control.
  const messages = useDashboardStore((s) => s.recentRawMessages);
  const clearMessages = useDashboardStore((s) => s.clearMessages);
  
  const messageCount = messages.length;
  const lastTimestamp = messages.length > 0 ? messages[messages.length - 1].receivedAt : null;
  const latestMessage = messages.length > 0 ? messages[messages.length - 1] : null;

  return (
    <div className="diagnostics-panel">
      <div className="panel-hint">
        <h2>Developer Tools & Diagnostics</h2>
        <p>This is the raw Phase 1 debug console view. It shows the raw MQTT stream backing the normalized store.</p>
      </div>
      
      <div className="dashboard-grid">
        <ConnectionStatus
          connectionState={connectionState}
          credentialExpiry={credentialExpiry}
          onConnect={handleConnect}
          onDisconnect={handleDisconnect}
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
