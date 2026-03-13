/** Connection lifecycle states. */
export type ConnectionState =
    | 'idle'
    | 'connecting'
    | 'connected'
    | 'reconnecting'
    | 'disconnected'
    | 'error';

/** A single raw message received from IoT Core. */
export interface RawIoTMessage {
    readonly id: string;
    readonly topic: string;
    readonly receivedAt: string; // ISO-8601
    readonly rawText: string;
    readonly parsedJson?: unknown;
    readonly parseError?: string;
}

/** Gateway-level metadata extracted from the payload. */
export interface ParsedGatewayEnvelope {
    readonly gatewayId?: string;
    readonly timestamp?: string;
    readonly firmwareVersion?: string;
    readonly deviceCount?: number;
    readonly extra: Record<string, unknown>;
}

/** A single meter device reading. */
export interface MeterDeviceReading {
    readonly deviceId?: string;
    readonly voltage?: number;
    readonly current?: number;
    readonly power?: number;
    readonly energy?: number;
    readonly frequency?: number;
    readonly powerFactor?: number;
    readonly extra: Record<string, unknown>;
}

/** Normalized payload combining envelope, readings, and raw data. */
export interface NormalizedPayload {
    readonly envelope: ParsedGatewayEnvelope | null;
    readonly readings: MeterDeviceReading[];
    readonly raw: unknown;
}

/** Credentials shape used by the IoT connection layer. */
export interface AwsCredentials {
    readonly accessKeyId: string;
    readonly secretAccessKey: string;
    readonly sessionToken: string;
    readonly expiration?: Date;
}
