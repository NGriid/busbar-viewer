/**
 * IoT Core MQTT-over-WSS connection service.
 *
 * Manages the full lifecycle: connect, disconnect, reconnect,
 * subscribe, resubscribe, and credential refresh.
 */

import mqtt from 'mqtt';
import type { MqttClient } from 'mqtt';
import { config } from '../../config/env';
import { getCredentials, getCredentialTTL, clearCredentials } from '../aws/credentials';
import { buildSignedUrl } from '../aws/sigv4';
import type { ConnectionState, RawIoTMessage } from '../../types/iot';

export interface IoTConnectionCallbacks {
    onStateChange: (state: ConnectionState, error?: string) => void;
    onMessage: (message: RawIoTMessage) => void;
}

const RECONNECT_DELAY_MS = 3_000;
const CREDENTIAL_REFRESH_MARGIN_MS = 5 * 60 * 1000;

let clientInstance: MqttClient | null = null;
let currentState: ConnectionState = 'idle';
let subscribedTopics = new Set<string>();
let observers = new Set<IoTConnectionCallbacks>();
let credentialRefreshTimer: ReturnType<typeof setTimeout> | null = null;
let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
let messageCounter = 0;

function generateClientId(): string {
    const random = Math.random().toString(36).slice(2, 10);
    return `busbar-${Date.now()}-${random}`;
}

function setState(state: ConnectionState, error?: string): void {
    currentState = state;
    for (const observer of observers) {
        observer.onStateChange(state, error);
    }
}

function parsePayload(topic: string, payload: Buffer): RawIoTMessage {
    const rawText = new TextDecoder('utf-8').decode(payload);
    const id = `msg-${++messageCounter}-${Date.now()}`;
    const receivedAt = new Date().toISOString();

    try {
        const parsedJson: unknown = JSON.parse(rawText);
        return { id, topic, receivedAt, rawText, parsedJson };
    } catch (err) {
        const parseError = err instanceof Error ? err.message : 'JSON parse failed';
        return { id, topic, receivedAt, rawText, parseError };
    }
}

async function subscribeToTopic(client: MqttClient, topic: string): Promise<void> {
    if (subscribedTopics.has(topic)) return;

    return new Promise((resolve, reject) => {
        client.subscribe(topic, { qos: 0 }, (err) => {
            if (err) {
                reject(new Error(`Subscribe to ${topic} failed: ${err.message}`));
            } else {
                subscribedTopics.add(topic);
                resolve();
            }
        });
    });
}

function scheduleCredentialRefresh(): void {
    clearCredentialRefreshTimer();

    const ttl = getCredentialTTL();
    if (ttl <= 0) return;

    // Refresh 5 min before expiry, minimum 30s from now
    const delay = Math.max(30_000, ttl - CREDENTIAL_REFRESH_MARGIN_MS);

    credentialRefreshTimer = setTimeout(async () => {
        try {
            clearCredentials();
            // Reconnect with fresh credentials
            await reconnect();
        } catch (err) {
            const msg = err instanceof Error ? err.message : 'Credential refresh failed';
            setState('error', msg);
        }
    }, delay);
}

function clearCredentialRefreshTimer(): void {
    if (credentialRefreshTimer) {
        clearTimeout(credentialRefreshTimer);
        credentialRefreshTimer = null;
    }
}

function clearReconnectTimer(): void {
    if (reconnectTimer) {
        clearTimeout(reconnectTimer);
        reconnectTimer = null;
    }
}

async function reconnect(): Promise<void> {
    if (currentState === 'connecting' || currentState === 'reconnecting') return;

    setState('reconnecting');

    // Tear down old client without triggering close handler loop
    if (clientInstance) {
        const old = clientInstance;
        clientInstance = null;
        subscribedTopics.clear();
        old.end(true);
    }

    try {
        await connectInternal();
    } catch (err) {
        const msg = err instanceof Error ? err.message : 'Reconnect failed';
        setState('error', msg);
        // Schedule another reconnect attempt
        clearReconnectTimer();
        reconnectTimer = setTimeout(() => {
            reconnect().catch(() => { /* handled via setState */ });
        }, RECONNECT_DELAY_MS);
    }
}

async function connectInternal(): Promise<void> {
    const credentials = await getCredentials();
    const url = await buildSignedUrl(credentials, config.awsRegion, config.iotEndpoint);

    const client = mqtt.connect(url, {
        clientId: generateClientId(),
        protocolVersion: 4,
        clean: true,
        reconnectPeriod: 0, // We handle reconnect ourselves
        connectTimeout: 10_000,
        keepalive: 30,
        // Transform WS options for browser
        transformWsUrl: (wsUrl: string) => wsUrl,
    });

    clientInstance = client;

    client.on('connect', async () => {
        setState('connected');
        try {
            await subscribeToTopic(client, config.iotTopic);
        } catch (err) {
            const msg = err instanceof Error ? err.message : 'Subscribe failed';
            setState('error', msg);
        }
        scheduleCredentialRefresh();
    });

    client.on('message', (topic: string, payload: Buffer) => {
        const message = parsePayload(topic, payload);
        for (const observer of observers) {
            observer.onMessage(message);
        }
    });

    client.on('error', (err: Error) => {
        setState('error', err.message);
    });

    client.on('close', () => {
        if (clientInstance === client) {
            // Unexpected close — schedule reconnect
            setState('disconnected');
            clearReconnectTimer();
            reconnectTimer = setTimeout(() => {
                reconnect().catch(() => { /* handled via setState */ });
            }, RECONNECT_DELAY_MS);
        }
    });

    client.on('offline', () => {
        if (clientInstance === client) {
            setState('reconnecting');
        }
    });
}

/** Connect to AWS IoT Core. Returns a function to unsubscribe callbacks. */
export async function connect(cbs: IoTConnectionCallbacks): Promise<() => void> {
    // Add the caller to the observer set
    observers.add(cbs);
    
    const unsubscribe = () => {
        observers.delete(cbs);
    };

    // If there's already an active client/session, just attach this observer.
    // Manual reconnects after a clean disconnect must still be allowed.
    if (
        clientInstance ||
        currentState === 'connecting' ||
        currentState === 'connected' ||
        currentState === 'reconnecting'
    ) {
        // Immediately sync the caller with current state
        cbs.onStateChange(currentState);
        return unsubscribe;
    }

    messageCounter = 0;
    subscribedTopics.clear();
    setState('connecting');

    try {
        await connectInternal();
        return unsubscribe;
    } catch (err) {
        const msg = err instanceof Error ? err.message : 'Connection failed';
        setState('error', msg);
        throw err;
    }
}

/** Disconnect and clean up all resources. */
export function disconnect(): void {
    clearCredentialRefreshTimer();
    clearReconnectTimer();

    if (clientInstance) {
        const client = clientInstance;
        clientInstance = null;
        subscribedTopics.clear();
        client.end(true);
    }

    setState('disconnected');
    // Clear observers so they don't leak memory on unmount
    observers.clear();
}

/** Get current connection state. */
export function getConnectionState(): ConnectionState {
    return currentState;
}

/** Get cached credential expiration time, if available. */
export function getCredentialExpiry(): Date | null {
    const ttl = getCredentialTTL();
    if (ttl <= 0) return null;
    return new Date(Date.now() + ttl);
}
