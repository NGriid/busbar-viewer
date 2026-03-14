/**
 * React hook for managing the IoT connection lifecycle and message state.
 */

import { useState, useCallback, useRef, useEffect } from 'react';
import type { ConnectionState, RawIoTMessage } from '../types/iot';
import {
    connect as iotConnect,
    disconnect as iotDisconnect,
    getCredentialExpiry,
    getConnectionState,
} from '../lib/iot/connection';
import { MessageBuffer } from '../lib/iot/messageBuffer';
import { useDashboardStore } from '../store/dashboardStore';

export { useAutoConnect } from './useAutoConnect';

interface UseIoTConnectionReturn {
    connectionState: ConnectionState;
    messages: readonly RawIoTMessage[];
    messageCount: number;
    lastTimestamp: string | null;
    credentialExpiry: Date | null;
    error: string | null;
    isPaused: boolean;
    connect: () => void;
    disconnect: () => void;
    clearMessages: () => void;
    togglePause: () => void;
}

export function useIoTConnection(): UseIoTConnectionReturn {
    // Sync React state directly with the underlying singleton state upon mount
    const [connectionState, setConnectionState] = useState<ConnectionState>(getConnectionState());
    
    // We only use messages for Phase 1 Diagnostics view compatibility
    const [messages, setMessages] = useState<readonly RawIoTMessage[]>([]);
    const [messageCount, setMessageCount] = useState(0);
    const [lastTimestamp, setLastTimestamp] = useState<string | null>(null);
    const [credentialExpiry, setCredentialExpiry] = useState<Date | null>(getCredentialExpiry());
    const [error, setError] = useState<string | null>(null);
    const [isPaused, setIsPaused] = useState(false);

    const bufferRef = useRef(new MessageBuffer());
    const pausedRef = useRef(false);
    const unsubscribeRef = useRef<(() => void) | null>(null);

    // Keep ref in sync with state
    useEffect(() => {
        pausedRef.current = isPaused;
    }, [isPaused]);

    const handleStateChange = useCallback(
        (state: ConnectionState, errorMsg?: string) => {
            setConnectionState(state);
            setError(errorMsg ?? null);

            if (state === 'connected') {
                setCredentialExpiry(getCredentialExpiry());
            }
        },
        [],
    );

    const handleMessage = useCallback((message: RawIoTMessage) => {
        const buffer = bufferRef.current;
        buffer.push(message);

        // Always update count and timestamp
        setMessageCount(buffer.getTotalCount());
        setLastTimestamp(buffer.getLastTimestamp());

        // Immediately push to Zustand store, bypassing React state limits
        useDashboardStore.getState().processInboundMessage(message);

        // Only update visible list if not paused
        if (!pausedRef.current) {
            setMessages([...buffer.getAll()]);
        }
    }, []);

    const connect = useCallback(() => {
        setError(null);
        // Only trigger connection if we aren't already connected
        if (getConnectionState() === 'idle' || getConnectionState() === 'disconnected') {
             iotConnect({
                onStateChange: handleStateChange,
                onMessage: handleMessage,
            }).then((unsub) => {
                unsubscribeRef.current = unsub;
            }).catch((err) => {
                const msg = err instanceof Error ? err.message : 'Connection failed';
                setError(msg);
            });
        } else {
            // If already connected, just register our callbacks to get sync updates
            iotConnect({
                onStateChange: handleStateChange,
                onMessage: handleMessage,
            }).then((unsub) => {
                unsubscribeRef.current = unsub;
            });
        }
    }, [handleStateChange, handleMessage]);

    const disconnect = useCallback(() => {
        iotDisconnect();
        // Force the react hook to know we disconnected without waiting for the callback
        setConnectionState('disconnected');
    }, []);

    const clearMessages = useCallback(() => {
        bufferRef.current.clear();
        setMessages([]);
        setMessageCount(0);
        setLastTimestamp(null);
    }, []);

    const togglePause = useCallback(() => {
        setIsPaused((prev) => {
            const next = !prev;
            if (!next) {
                // Resuming — sync display with buffer
                setMessages([...bufferRef.current.getAll()]);
            }
            return next;
        });
    }, []);

    // Cleanup on unmount
    useEffect(() => {
        return () => {
             if (unsubscribeRef.current) {
                 unsubscribeRef.current();
             }
            // iotDisconnect is not called here intentionally to persist connection across routes
        };
    }, []);

    return {
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
    };
}
