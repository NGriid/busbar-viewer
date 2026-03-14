/**
 * Parse inbound MQTT payload (JSON array) into typed records.
 * Never crashes — logs unknown/malformed records and continues.
 */

import type { ParsedInboundRecord } from '../../types/dashboard';

function isRecord(v: unknown): v is Record<string, unknown> {
  return typeof v === 'object' && v !== null && !Array.isArray(v);
}

/** Parse a terminal_id like "BB0010-1" into { busbarId, terminalNumber }. */
function parseTerminalId(id: string): { busbarId: string; terminalNumber: number } | null {
  const lastDash = id.lastIndexOf('-');
  if (lastDash < 1) return null;
  const busbarId = id.slice(0, lastDash);
  const num = parseInt(id.slice(lastDash + 1), 10);
  if (isNaN(num) || num < 1) return null;
  return { busbarId, terminalNumber: num };
}

/** Classify a single record from the inbound payload array. */
function classifyRecord(item: unknown): ParsedInboundRecord {
  if (!isRecord(item)) {
    return { _type: 'unknown', data: item };
  }

  // Gateway record
  if (item.device_desc === 'Gateway' && typeof item.deviceId === 'string') {
    return {
      _type: 'gateway',
      record: item as ParsedInboundRecord & { _type: 'gateway' } extends { record: infer R } ? R : never,
    };
  }

  // Busbar device record
  if (item.device_desc === 'busbar' && typeof item.deviceId === 'string') {
    return {
      _type: 'busbar',
      record: item as ParsedInboundRecord & { _type: 'busbar' } extends { record: infer R } ? R : never,
    };
  }

  // Terminal record
  if (typeof item.terminal_id === 'string') {
    const parsed = parseTerminalId(item.terminal_id);
    if (parsed) {
      return {
        _type: 'terminal',
        record: item as ParsedInboundRecord & { _type: 'terminal' } extends { record: infer R } ? R : never,
        busbarId: parsed.busbarId,
        terminalNumber: parsed.terminalNumber,
      };
    }
  }

  return { _type: 'unknown', data: item };
}

/**
 * Parse an inbound MQTT message payload.
 * Expects a JSON array of mixed record types.
 */
export function parseInboundPayload(json: unknown): ParsedInboundRecord[] {
  // The payload is a JSON array
  if (Array.isArray(json)) {
    return json.map(classifyRecord);
  }

  // Single object — wrap in array
  if (isRecord(json)) {
    return [classifyRecord(json)];
  }

  // Neither array nor object
  return [{ _type: 'unknown', data: json }];
}
