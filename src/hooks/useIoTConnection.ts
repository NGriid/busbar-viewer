/**
 * React hook for managing the IoT connection lifecycle and message state.
 */

import { useState, useCallback, useRef, useEffect } from 'react';
import type { ConnectionState, RawIoTMessage } from '../types/iot';
import {
    connect as iotConnect,
    disconnect as iotDisconnect,
    getCredentialExpiry,
} from '../lib/iot/connection';
import { MessageBuffer } from '../lib/iot/messageBuffer';

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
    const [connectionState, setConnectionState] = useState<ConnectionState>('idle');
    const [messages, setMessages] = useState<readonly RawIoTMessage[]>([]);
    const [messageCount, setMessageCount] = useState(0);
    const [lastTimestamp, setLastTimestamp] = useState<string | null>(null);
    const [credentialExpiry, setCredentialExpiry] = useState<Date | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [isPaused, setIsPaused] = useState(false);

    const bufferRef = useRef(new MessageBuffer());
    const pausedRef = useRef(false);

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

        // Only update visible list if not paused
        if (!pausedRef.current) {
            setMessages([...buffer.getAll()]);
        }
    }, []);

    const connect = useCallback(() => {
        setError(null);
        iotConnect({
            onStateChange: handleStateChange,
            onMessage: handleMessage,
        }).catch((err) => {
            const msg = err instanceof Error ? err.message : 'Connection failed';
            setError(msg);
        });
    }, [handleStateChange, handleMessage]);

    const disconnect = useCallback(() => {
        iotDisconnect();
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
            iotDisconnect();
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
