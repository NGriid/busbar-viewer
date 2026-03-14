import { create } from 'zustand';
import type { RawIoTMessage } from '../types/iot';
import { parseInboundPayload } from '../lib/iot/parser';
import type {
  GatewayState,
  BusbarState,
  TerminalState,
  UIState,
  GatewayRecord,
  BusbarRecord,
  TerminalRecord,
} from '../types/dashboard';

interface DashboardStore {
  // ─── Data State ───
  gateway: GatewayState | null;
  busbarsById: Record<string, BusbarState>;
  terminalsByBusbarId: Record<string, Record<number, TerminalState>>;
  recentRawMessages: RawIoTMessage[];
  initialHydrationComplete: boolean;

  // ─── Connection/Store Errors ───
  error: string | null;
  isIntentionallyDisconnected: boolean;

  // ─── UI State ───
  ui: UIState;

  // ─── Actions ───
  processInboundMessage: (msg: RawIoTMessage) => void;
  setView: (view: UIState['view']) => void;
  selectBusbar: (busbarId: string | null) => void;
  setSearchQuery: (query: string) => void;
  setFilterMode: (mode: UIState['filterMode']) => void;
  setSortMode: (mode: UIState['sortMode']) => void;
  clearMessages: () => void;
  setIntentionallyDisconnected: (isDisconnected: boolean) => void;
}

const MAX_RAW_MESSAGES = 100;

export const useDashboardStore = create<DashboardStore>((set) => ({
  gateway: null,
  busbarsById: {},
  terminalsByBusbarId: {},
  recentRawMessages: [],
  initialHydrationComplete: false,
  error: null,
  isIntentionallyDisconnected: false,

  ui: {
    view: 'overview',
    selectedBusbarId: null,
    selectedTerminalNumber: null,
    searchQuery: '',
    filterMode: 'all',
    sortMode: 'id',
  },

  setView: (view) => set((state) => ({ ui: { ...state.ui, view } })),
  selectBusbar: (busbarId) =>
    set((state) => ({
      ui: {
        ...state.ui,
        selectedBusbarId: busbarId,
        view: busbarId ? 'busbar-detail' : 'overview',
      },
    })),
  setSearchQuery: (query) => set((state) => ({ ui: { ...state.ui, searchQuery: query } })),
  setFilterMode: (mode) => set((state) => ({ ui: { ...state.ui, filterMode: mode } })),
  setSortMode: (mode) => set((state) => ({ ui: { ...state.ui, sortMode: mode } })),
  clearMessages: () => set({ recentRawMessages: [] }),
  setIntentionallyDisconnected: (isDisconnected) => set({ isIntentionallyDisconnected: isDisconnected }),

  processInboundMessage: (msg) =>
    set((state) => {
      // 1. Keep raw message for diagnostics
      const newMessages = [...state.recentRawMessages, msg].slice(-MAX_RAW_MESSAGES);

      // 2. Parse payload if valid JSON
      if (!msg.parsedJson) {
        return { recentRawMessages: newMessages };
      }

      const records = parseInboundPayload(msg.parsedJson);
      const now = new Date().toISOString();

      let newGateway = state.gateway;
      const newBusbars = { ...state.busbarsById };
      const newTerminals = { ...state.terminalsByBusbarId };

      let busbarChanged = false;

      // 3. Process each record
      for (const item of records) {
        if (item._type === 'gateway') {
          newGateway = mergeGateway(newGateway, item.record, now);
        } else if (item._type === 'busbar') {
          newBusbars[item.record.deviceId] = mergeBusbar(
            newBusbars[item.record.deviceId],
            item.record,
            now
          );
          busbarChanged = true;
        } else if (item._type === 'terminal') {
          const bId = item.busbarId;
          if (!newTerminals[bId]) {
            newTerminals[bId] = {};
          }
          newTerminals[bId] = {
            ...newTerminals[bId],
            [item.terminalNumber]: mergeTerminal(
              newTerminals[bId][item.terminalNumber],
              item.record,
              item.terminalNumber,
              now
            ),
          };
          // As per rule 3: If terminal changes, the busbar record is also usually uploaded.
          // We ensure the busbar exists.
          if (!newBusbars[bId]) {
            newBusbars[bId] = createEmptyBusbar(bId, now);
            busbarChanged = true;
          }
        }
      }

      const hydrationComplete =
        state.initialHydrationComplete || Object.keys(newBusbars).length >= 12;

      return {
        recentRawMessages: newMessages,
        gateway: newGateway,
        ...(busbarChanged ? { busbarsById: newBusbars } : {}),
        terminalsByBusbarId: newTerminals,
        initialHydrationComplete: hydrationComplete,
      };
    }),
}));

// ─── Merge Helpers ───

function mergeGateway(
  prev: GatewayState | null,
  record: GatewayRecord,
  now: string
): GatewayState {
  return {
    deviceId: record.deviceId,
    loraSNR: record.LoRa_SNR ?? prev?.loraSNR ?? null,
    subDeviceCount: record.No_of_subDevices ? parseInt(record.No_of_subDevices, 10) : prev?.subDeviceCount ?? null,
    lastSeenAt: now,
    extra: { ...prev?.extra, ...record },
  };
}

function mergeBusbar(
  prev: BusbarState | undefined,
  record: BusbarRecord,
  now: string
): BusbarState {
  return {
    deviceId: record.deviceId,
    gpsStatus: record.gps_status ?? prev?.gpsStatus ?? null,
    latitude: record.latitude ?? prev?.latitude ?? null,
    longitude: record.longitude ?? prev?.longitude ?? null,
    altitude: record.altitude ?? prev?.altitude ?? null,
    speed: record.speed ?? prev?.speed ?? null,
    gpsTimestamp: record.gps_timestamp ?? prev?.gpsTimestamp ?? null,
    masterChipTemp: record.master_chip_Temp ?? prev?.masterChipTemp ?? null,
    slave1ChipTemp: record.slave_1_chip_Temp ?? prev?.slave1ChipTemp ?? null,
    slave2ChipTemp: record.slave_2_chip_Temp ?? prev?.slave2ChipTemp ?? null,
    thermistorTemp: record.thermistor_Temp ?? prev?.thermistorTemp ?? null,
    extRgIRed: record.ext_Rg_I_red ?? prev?.extRgIRed ?? null,
    extRgIYellow: record.ext_Rg_I_yellow ?? prev?.extRgIYellow ?? null,
    extRgIBlue: record.ext_Rg_I_blue ?? prev?.extRgIBlue ?? null,
    frequency: record.frequency ?? prev?.frequency ?? null,
    loraRSSI: record.LORA_RSSI ?? prev?.loraRSSI ?? null,
    errorFlags: record.error_flags ?? prev?.errorFlags ?? null,
    multiPaths: record.multi_paths ?? prev?.multiPaths ?? null,
    lastSeenAt: now,
  };
}

function mergeTerminal(
  prev: TerminalState | undefined,
  record: TerminalRecord,
  terminalNumber: number,
  now: string
): TerminalState {
  return {
    terminalId: record.terminal_id,
    terminalNumber,
    voltage: record.voltage ?? prev?.voltage ?? null,
    current: record.current ?? prev?.current ?? null,
    powerFactor: record.power_factor ?? prev?.powerFactor ?? null,
    activePower: record.active_power ?? prev?.activePower ?? null,
    reactivePower: record.reactive_power ?? prev?.reactivePower ?? null,
    apparentPower: record.apparent_power ?? prev?.apparentPower ?? null,
    activeEnergy: record.active_energy ?? prev?.activeEnergy ?? null,
    reactiveEnergy: record.reactive_energy ?? prev?.reactiveEnergy ?? null,
    apparentEnergy: record.apparent_energy ?? prev?.apparentEnergy ?? null,
    harmonicEnergy: record.harmonic_energy ?? prev?.harmonicEnergy ?? null,
    overloadStatus: record.overload_status ?? prev?.overloadStatus ?? null,
    lastSeenAt: now,
  };
}

function createEmptyBusbar(deviceId: string, now: string): BusbarState {
  return {
    deviceId,
    gpsStatus: null,
    latitude: null,
    longitude: null,
    altitude: null,
    speed: null,
    gpsTimestamp: null,
    masterChipTemp: null,
    slave1ChipTemp: null,
    slave2ChipTemp: null,
    thermistorTemp: null,
    extRgIRed: null,
    extRgIYellow: null,
    extRgIBlue: null,
    frequency: null,
    loraRSSI: null,
    errorFlags: null,
    multiPaths: null,
    lastSeenAt: now,
  };
}
