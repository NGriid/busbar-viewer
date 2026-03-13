import { useRef, useEffect } from 'react';
import type { RawIoTMessage } from '../types/iot';

interface Props {
    messages: readonly RawIoTMessage[];
    messageCount: number;
    lastTimestamp: string | null;
    isPaused: boolean;
    onClear: () => void;
    onTogglePause: () => void;
}

function formatTime(iso: string): string {
    try {
        return new Date(iso).toLocaleTimeString();
    } catch {
        return iso;
    }
}

export function MessageList({
    messages,
    messageCount,
    lastTimestamp,
    isPaused,
    onClear,
    onTogglePause,
}: Props) {
    const listRef = useRef<HTMLDivElement>(null);

    // Auto-scroll to bottom when new messages arrive (unless paused)
    useEffect(() => {
        if (!isPaused && listRef.current) {
            listRef.current.scrollTop = listRef.current.scrollHeight;
        }
    }, [messages, isPaused]);

    return (
        <div className="panel message-list-panel">
            <div className="panel-header">
                <h2>Messages</h2>
                <div className="message-stats">
                    <span className="stat">
                        Total: <strong>{messageCount}</strong>
                    </span>
                    {lastTimestamp && (
                        <span className="stat">
                            Last: <strong>{formatTime(lastTimestamp)}</strong>
                        </span>
                    )}
                </div>
            </div>

            <div className="button-row">
                <button className="btn btn-small" onClick={onTogglePause}>
                    {isPaused ? '▶ Resume' : '⏸ Pause'}
                </button>
                <button className="btn btn-small btn-danger" onClick={onClear}>
                    Clear
                </button>
            </div>

            {isPaused && (
                <div className="pause-indicator">⏸ Auto-scroll paused</div>
            )}

            <div className="message-list" ref={listRef}>
                {messages.length === 0 ? (
                    <div className="empty-state">No messages yet. Connect to start receiving data.</div>
                ) : (
                    messages.map((msg) => (
                        <div key={msg.id} className="message-item">
                            <div className="message-meta">
                                <span className="message-time">{formatTime(msg.receivedAt)}</span>
                                <span className="message-topic">{msg.topic}</span>
                                {msg.parseError && (
                                    <span className="message-error-badge">Parse Error</span>
                                )}
                            </div>
                            <pre className="message-body">
                                {msg.parsedJson
                                    ? JSON.stringify(msg.parsedJson, null, 2)
                                    : msg.rawText}
                            </pre>
                        </div>
                    ))
                )}
            </div>
        </div>
    );
}
