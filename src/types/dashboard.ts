/** Phase 2 dashboard types for gateway, busbar, terminal state and UI. */

// ─── Freshness ───

export type FreshnessLevel = 'live' | 'recent' | 'stale' | 'offline';

// ─── Raw inbound record shapes ───

export interface GatewayRecord {
  readonly deviceId: string;
  readonly device_desc: 'Gateway';
  readonly LoRa_SNR?: string;
  readonly No_of_subDevices?: string;
  readonly [key: string]: unknown;
}

export interface BusbarRecord {
  readonly deviceId: string;
  readonly device_desc: 'busbar';
  readonly gps_status?: number;
  readonly latitude?: number;
  readonly longitude?: number;
  readonly altitude?: number;
  readonly speed?: number;
  readonly gps_timestamp?: number;
  readonly master_chip_Temp?: number;
  readonly slave_1_chip_Temp?: number;
  readonly slave_2_chip_Temp?: number;
  readonly thermistor_Temp?: number;
  readonly ext_Rg_I_red?: number;
  readonly ext_Rg_I_yellow?: number;
  readonly ext_Rg_I_blue?: number;
  readonly frequency?: number;
  readonly LORA_RSSI?: number;
  readonly error_flags?: number;
  readonly multi_paths?: number;
  readonly [key: string]: unknown;
}

export interface TerminalRecord {
  readonly terminal_id: string;
  readonly voltage?: number;
  readonly current?: number;
  readonly power_factor?: number;
  readonly active_power?: number;
  readonly reactive_power?: number;
  readonly apparent_power?: number;
  readonly active_energy?: number;
  readonly reactive_energy?: number;
  readonly apparent_energy?: number;
  readonly harmonic_energy?: number;
  readonly overload_status?: number;
  readonly [key: string]: unknown;
}

export interface UnknownRecord {
  readonly _type: 'unknown';
  readonly data: unknown;
}

export type ParsedInboundRecord =
  | { _type: 'gateway'; record: GatewayRecord }
  | { _type: 'busbar'; record: BusbarRecord }
  | { _type: 'terminal'; record: TerminalRecord; busbarId: string; terminalNumber: number }
  | UnknownRecord;

// ─── Stored state entities ───

export interface GatewayState {
  deviceId: string;
  loraSNR: string | null;
  subDeviceCount: number | null;
  lastSeenAt: string;
  extra: Record<string, unknown>;
}

export interface BusbarState {
  deviceId: string;
  gpsStatus: number | null;
  latitude: number | null;
  longitude: number | null;
  altitude: number | null;
  speed: number | null;
  gpsTimestamp: number | null;
  masterChipTemp: number | null;
  slave1ChipTemp: number | null;
  slave2ChipTemp: number | null;
  thermistorTemp: number | null;
  extRgIRed: number | null;
  extRgIYellow: number | null;
  extRgIBlue: number | null;
  frequency: number | null;
  loraRSSI: number | null;
  errorFlags: number | null;
  multiPaths: number | null;
  lastSeenAt: string;
}

export interface TerminalState {
  terminalId: string;
  terminalNumber: number;
  voltage: number | null;
  current: number | null;
  powerFactor: number | null;
  activePower: number | null;
  reactivePower: number | null;
  apparentPower: number | null;
  activeEnergy: number | null;
  reactiveEnergy: number | null;
  apparentEnergy: number | null;
  harmonicEnergy: number | null;
  overloadStatus: number | null;
  lastSeenAt: string;
}

// ─── UI state ───

export type DashboardView = 'overview' | 'busbar-detail' | 'diagnostics';

export type FilterMode = 'all' | 'stale' | 'overloaded' | 'error';

export type SortMode = 'id' | 'lastSeen' | 'overloadCount';

export interface UIState {
  view: DashboardView;
  selectedBusbarId: string | null;
  selectedTerminalNumber: number | null;
  searchQuery: string;
  filterMode: FilterMode;
  sortMode: SortMode;
}
