/**
 * SigV4 request signing for AWS IoT MQTT-over-WSS.
 * Uses the browser WebCrypto API — fully async, no Node.js dependencies.
 */

import type { AwsCredentials } from '../../types/iot';

/** Build a SigV4-signed WSS URL for AWS IoT Core. */
export async function buildSignedUrl(
    credentials: AwsCredentials,
    region: string,
    endpoint: string,
): Promise<string> {
    const host = endpoint;
    const datetime = toAmzDate(new Date());
    const date = datetime.slice(0, 8);
    const service = 'iotdevicegateway';
    const scope = `${date}/${region}/${service}/aws4_request`;
    const algorithm = 'AWS4-HMAC-SHA256';

    const queryParams = new URLSearchParams({
        'X-Amz-Algorithm': algorithm,
        'X-Amz-Credential': `${credentials.accessKeyId}/${scope}`,
        'X-Amz-Date': datetime,
        'X-Amz-SignedHeaders': 'host',
    });

    queryParams.sort();

    const canonicalRequest = [
        'GET',
        '/mqtt',
        queryParams.toString(),
        `host:${host}`,
        '',
        'host',
        'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
    ].join('\n');

    const hashedCanonical = await sha256Hex(canonicalRequest);
    const stringToSign = [algorithm, datetime, scope, hashedCanonical].join('\n');
    const signingKey = await deriveSigningKey(
        credentials.secretAccessKey,
        date,
        region,
        service,
    );
    const signature = await hmacHex(signingKey, stringToSign);

    queryParams.set('X-Amz-Signature', signature);
    queryParams.set('X-Amz-Security-Token', credentials.sessionToken);

    return `wss://${host}/mqtt?${queryParams.toString()}`;
}

// ─── Crypto helpers (WebCrypto API) ───

function toAmzDate(date: Date): string {
    return date.toISOString().replace(/[-:]/g, '').replace(/\.\d{3}/, '');
}

async function sha256Hex(data: string): Promise<string> {
    const encoded = new TextEncoder().encode(data);
    const hash = await crypto.subtle.digest('SHA-256', encoded);
    return bufferToHex(hash);
}

async function hmacSha256(
    key: ArrayBuffer,
    data: string,
): Promise<ArrayBuffer> {
    const cryptoKey = await crypto.subtle.importKey(
        'raw',
        key,
        { name: 'HMAC', hash: 'SHA-256' },
        false,
        ['sign'],
    );
    return crypto.subtle.sign('HMAC', cryptoKey, new TextEncoder().encode(data));
}

async function hmacHex(key: ArrayBuffer, data: string): Promise<string> {
    return bufferToHex(await hmacSha256(key, data));
}

async function deriveSigningKey(
    secretKey: string,
    date: string,
    region: string,
    service: string,
): Promise<ArrayBuffer> {
    const kDate = await hmacSha256(
        new TextEncoder().encode(`AWS4${secretKey}`).buffer as ArrayBuffer,
        date,
    );
    const kRegion = await hmacSha256(kDate, region);
    const kService = await hmacSha256(kRegion, service);
    return hmacSha256(kService, 'aws4_request');
}

function bufferToHex(buffer: ArrayBuffer): string {
    return Array.from(new Uint8Array(buffer))
        .map((b) => b.toString(16).padStart(2, '0'))
        .join('');
}
