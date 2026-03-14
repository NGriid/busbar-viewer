/** Freshness thresholds and helpers. */

import type { FreshnessLevel } from '../types/dashboard';

// Thresholds in milliseconds
export const FRESHNESS_LIVE_MS = 30_000;       // ≤ 30s
export const FRESHNESS_RECENT_MS = 2 * 60_000; // ≤ 2min
export const FRESHNESS_STALE_MS = 5 * 60_000;  // ≤ 5min
// > 5min = offline

/** Derive freshness level from a lastSeenAt ISO timestamp. */
export function getFreshnessLevel(lastSeenAt: string): FreshnessLevel {
  const age = Date.now() - new Date(lastSeenAt).getTime();
  if (age <= FRESHNESS_LIVE_MS) return 'live';
  if (age <= FRESHNESS_RECENT_MS) return 'recent';
  if (age <= FRESHNESS_STALE_MS) return 'stale';
  return 'offline';
}

/** Human-readable relative time string. */
export function getRelativeTime(iso: string): string {
  const age = Date.now() - new Date(iso).getTime();
  if (age < 0) return 'just now';
  if (age < 1_000) return 'just now';
  if (age < 60_000) return `${Math.floor(age / 1_000)}s ago`;
  if (age < 3600_000) return `${Math.floor(age / 60_000)}m ago`;
  if (age < 86400_000) return `${Math.floor(age / 3600_000)}h ago`;
  return `${Math.floor(age / 86400_000)}d ago`;
}

/** Full local date/time string. */
export function formatFullTime(iso: string): string {
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

/** CSS color for each freshness level. */
export function getFreshnessColor(level: FreshnessLevel): string {
  switch (level) {
    case 'live': return '#10b981';
    case 'recent': return '#f59e0b';
    case 'stale': return '#ef4444';
    case 'offline': return '#6b7280';
  }
}

/** Label for each freshness level. */
export function getFreshnessLabel(level: FreshnessLevel): string {
  switch (level) {
    case 'live': return 'Live';
    case 'recent': return 'Recent';
    case 'stale': return 'Stale';
    case 'offline': return 'Offline';
  }
}
