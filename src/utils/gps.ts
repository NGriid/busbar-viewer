export interface DecodedGpsStatus {
  fixValid: boolean;
  fixType: number;
  satellites: number;
}

// Assumes the packed byte layout described in data-format.md:
// bit 0 = fix_valid, bits 1-2 = fix_type, bits 3-7 = sat_count
export function decodeGpsStatus(status: number): DecodedGpsStatus {
  return {
    fixValid: (status & 0b1) === 1,
    fixType: (status >> 1) & 0b11,
    satellites: (status >> 3) & 0b1_1111,
  };
}

export function formatGpsFixType(fixType: number): string {
  switch (fixType) {
    case 0:
      return 'No fix';
    case 1:
      return '2D fix';
    case 2:
      return '3D fix';
    default:
      return `Reserved (${fixType})`;
  }
}

export function formatErrorFlagsHex(errorFlags: number): string {
  const hex = errorFlags.toString(16).toUpperCase();
  return `0x${hex.padStart(2, '0')}`;
}
