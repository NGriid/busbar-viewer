/**
 * Guest credential acquisition via Cognito Identity Pool.
 * No user login — uses unauthenticated identities only.
 */

import { fromCognitoIdentityPool } from '@aws-sdk/credential-providers';
import { config } from '../../config/env';
import type { AwsCredentials } from '../../types/iot';

const REFRESH_MARGIN_MS = 5 * 60 * 1000; // Refresh 5 minutes before expiry

let cachedCredentials: AwsCredentials | null = null;
let cachedExpiration: number = 0;

const credentialProvider = fromCognitoIdentityPool({
    identityPoolId: config.cognitoIdentityPoolId,
    clientConfig: { region: config.awsRegion },
});

/** Acquire or return cached temporary AWS credentials. */
export async function getCredentials(): Promise<AwsCredentials> {
    const now = Date.now();

    if (cachedCredentials && cachedExpiration - now > REFRESH_MARGIN_MS) {
        return cachedCredentials;
    }

    const raw = await credentialProvider();

    if (!raw.accessKeyId || !raw.secretAccessKey || !raw.sessionToken) {
        throw new Error('Cognito returned incomplete credentials');
    }

    cachedCredentials = {
        accessKeyId: raw.accessKeyId,
        secretAccessKey: raw.secretAccessKey,
        sessionToken: raw.sessionToken,
        expiration: raw.expiration,
    };

    cachedExpiration = raw.expiration ? raw.expiration.getTime() : now + 3600_000;

    return cachedCredentials;
}

/** Time in ms until current credentials expire. Returns 0 if none cached. */
export function getCredentialTTL(): number {
    if (!cachedCredentials) return 0;
    return Math.max(0, cachedExpiration - Date.now());
}

/** Force-clear cached credentials so the next call fetches fresh ones. */
export function clearCredentials(): void {
    cachedCredentials = null;
    cachedExpiration = 0;
}
