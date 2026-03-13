/** Typed application configuration derived from Vite environment variables. */

export interface AppConfig {
    readonly awsRegion: string;
    readonly cognitoIdentityPoolId: string;
    readonly iotEndpoint: string;
    readonly iotTopic: string;
    readonly appTitle: string;
    readonly basePath: string;
}

function requireEnv(key: string): string {
    const value = import.meta.env[key];
    if (!value || typeof value !== 'string') {
        throw new Error(`Missing required environment variable: ${key}`);
    }
    return value;
}

function optionalEnv(key: string, fallback: string): string {
    const value = import.meta.env[key];
    return typeof value === 'string' && value.length > 0 ? value : fallback;
}

export const config: AppConfig = Object.freeze({
    awsRegion: requireEnv('VITE_AWS_REGION'),
    cognitoIdentityPoolId: requireEnv('VITE_COGNITO_IDENTITY_POOL_ID'),
    iotEndpoint: requireEnv('VITE_AWS_IOT_ENDPOINT'),
    iotTopic: optionalEnv('VITE_IOT_TOPIC', 'ecwa_dt/events'),
    appTitle: optionalEnv('VITE_APP_TITLE', 'Busbar Viewer'),
    basePath: optionalEnv('VITE_BASE_PATH', '/busbar-viewer/'),
});
