import type { RawIoTMessage } from '../types/iot';

interface Props {
    message: RawIoTMessage | null;
}

export function RawPayloadPanel({ message }: Props) {
    if (!message) {
        return (
            <div className="panel raw-payload-panel">
                <h2>Latest Payload</h2>
                <div className="empty-state">Waiting for first message…</div>
            </div>
        );
    }

    return (
        <div className="panel raw-payload-panel">
            <h2>Latest Payload</h2>
            <div className="payload-meta">
                <span>Topic: <code>{message.topic}</code></span>
                <span>Received: {new Date(message.receivedAt).toLocaleTimeString()}</span>
            </div>
            <pre className="payload-body">
                {message.parsedJson
                    ? JSON.stringify(message.parsedJson, null, 2)
                    : message.rawText}
            </pre>
            {message.parseError && (
                <div className="payload-error">
                    ⚠ Parse error: {message.parseError}
                </div>
            )}
        </div>
    );
}
