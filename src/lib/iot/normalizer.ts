/**
 * Generic normalization layer for IoT payloads.
 *
 * Extracts gateway metadata and device readings when present,
 * tolerates missing/unknown fields, never discards the original payload.
 */

import type {
    NormalizedPayload,
    ParsedGatewayEnvelope,
    MeterDeviceReading,
} from '../../types/iot';

function isRecord(v: unknown): v is Record<string, unknown> {
    return typeof v === 'object' && v !== null && !Array.isArray(v);
}

function extractString(obj: Record<string, unknown>, ...keys: string[]): string | undefined {
    for (const key of keys) {
        const val = obj[key];
        if (typeof val === 'string' && val.length > 0) return val;
    }
    return undefined;
}

function extractNumber(obj: Record<string, unknown>, ...keys: string[]): number | undefined {
    for (const key of keys) {
        const val = obj[key];
        if (typeof val === 'number' && isFinite(val)) return val;
    }
    return undefined;
}

/** Extract envelope fields from top-level JSON. */
function extractEnvelope(json: Record<string, unknown>): ParsedGatewayEnvelope {
    const knownKeys = new Set([
        'gateway_id', 'gatewayId', 'gw_id',
        'timestamp', 'ts', 'time',
        'firmware_version', 'firmwareVersion', 'fw_version',
        'device_count', 'deviceCount', 'num_devices',
        'devices', 'readings', 'data', 'meters',
    ]);

    const extra: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(json)) {
        if (!knownKeys.has(k)) {
            extra[k] = v;
        }
    }

    return {
        gatewayId: extractString(json, 'gateway_id', 'gatewayId', 'gw_id'),
        timestamp: extractString(json, 'timestamp', 'ts', 'time'),
        firmwareVersion: extractString(json, 'firmware_version', 'firmwareVersion', 'fw_version'),
        deviceCount: extractNumber(json, 'device_count', 'deviceCount', 'num_devices'),
        extra,
    };
}

/** Extract a single device reading from an object. */
function extractReading(obj: unknown): MeterDeviceReading | null {
    if (!isRecord(obj)) return null;

    const knownKeys = new Set([
        'device_id', 'deviceId', 'id',
        'voltage', 'v',
        'current', 'i', 'amps',
        'power', 'p', 'watts',
        'energy', 'e', 'kwh',
        'frequency', 'freq', 'f',
        'power_factor', 'powerFactor', 'pf',
    ]);

    const extra: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(obj)) {
        if (!knownKeys.has(k)) {
            extra[k] = v;
        }
    }

    return {
        deviceId: extractString(obj, 'device_id', 'deviceId', 'id'),
        voltage: extractNumber(obj, 'voltage', 'v'),
        current: extractNumber(obj, 'current', 'i', 'amps'),
        power: extractNumber(obj, 'power', 'p', 'watts'),
        energy: extractNumber(obj, 'energy', 'e', 'kwh'),
        frequency: extractNumber(obj, 'frequency', 'freq', 'f'),
        powerFactor: extractNumber(obj, 'power_factor', 'powerFactor', 'pf'),
        extra,
    };
}

/** Extract device readings from known array fields. */
function extractReadings(json: Record<string, unknown>): MeterDeviceReading[] {
    for (const key of ['devices', 'readings', 'data', 'meters']) {
        const arr = json[key];
        if (Array.isArray(arr)) {
            return arr
                .map(extractReading)
                .filter((r): r is MeterDeviceReading => r !== null);
        }
    }
    return [];
}

/**
 * Normalize an unknown JSON payload into a structured form.
 * Always preserves the original payload under `raw`.
 */
export function normalizePayload(json: unknown): NormalizedPayload {
    if (!isRecord(json)) {
        return { envelope: null, readings: [], raw: json };
    }

    return {
        envelope: extractEnvelope(json),
        readings: extractReadings(json),
        raw: json,
    };
}
