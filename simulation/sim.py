#!/usr/bin/env python3
"""Headless AWS IoT simulator for the Phase 2 busbar dashboard.

This replaces the old PyQt-based simulator with a simple loop that:
- maintains persistent gateway, busbar, and terminal state
- publishes only changed records during normal operation
- always includes the parent busbar record when any of its terminals change
- emits a full packet every 2 minutes so a new dashboard can rehydrate

Use `--dry-run` to print payload summaries locally without connecting to AWS IoT.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


SIM_DIR = Path(__file__).resolve().parent
DEFAULT_CERT = SIM_DIR / "aws_certs" / "Gateway_001-certificate.pem.crt"
DEFAULT_KEY = SIM_DIR / "aws_certs" / "Gateway_001-private.pem.key"
DEFAULT_CA = SIM_DIR / "aws_certs" / "AmazonRootCA1.pem"

DEFAULT_ENDPOINT = "a1fe4ehoaifpyx-ats.iot.eu-north-1.amazonaws.com"
DEFAULT_TOPIC = "ecwa_dt/events"
DEFAULT_CLIENT_ID = "gateway_1"
DEFAULT_GATEWAY_ID = "ND1234561"

BUSBAR_COUNT = 12
TERMINALS_PER_BUSBAR = 15
BUSBAR_IDS = [f"BB{index:04X}" for index in range(0x10, 0x10 + BUSBAR_COUNT)]

FREQUENCY_HZ = 50.0
OVERLOAD_CURRENT_A = 63.0
GATEWAY_SNR_RANGE = (7.0, 12.0)
RSSI_RANGE = (-112.0, -68.0)


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def round_float(value: float, digits: int = 2) -> float:
    return round(value, digits)


def random_gps_status(rng: random.Random) -> int:
    """Build a realistic packed GPS byte: valid(1b), fix_type(2b), sats(5b)."""
    fix_valid = 1 if rng.random() < 0.9 else 0

    if fix_valid:
        fix_type = rng.choices([1, 2], weights=[0.25, 0.75], k=1)[0]
        satellites = rng.randint(4, 10) if fix_type == 1 else rng.randint(7, 18)
    else:
        fix_type = 0
        satellites = rng.randint(0, 3)

    return (satellites << 3) | (fix_type << 1) | fix_valid


def compare_records(left: dict[str, Any], right: dict[str, Any]) -> bool:
    return left == right


def get_record_id(record: dict[str, Any]) -> str:
    if "terminal_id" in record:
        return str(record["terminal_id"])
    return str(record["deviceId"])


def calculate_terminal_metrics(voltage: float, current: float, power_factor: float) -> tuple[float, float, float, float]:
    apparent_power = voltage * current
    active_power = apparent_power * power_factor
    reactive_power = math.sqrt(max(apparent_power**2 - active_power**2, 0.0))
    harmonic_power = max(apparent_power - active_power, 0.0) * 0.12
    return active_power, reactive_power, apparent_power, harmonic_power


def apply_terminal_energy(terminal: dict[str, Any], now: float) -> None:
    elapsed_hours = max(now - float(terminal["_last_energy_ts"]), 0.0) / 3600.0
    if elapsed_hours <= 0:
        return

    active_power, reactive_power, apparent_power, harmonic_power = calculate_terminal_metrics(
        float(terminal["voltage"]),
        float(terminal["current"]),
        float(terminal["power_factor"]),
    )

    terminal["active_energy"] += active_power * elapsed_hours
    terminal["reactive_energy"] += reactive_power * elapsed_hours
    terminal["apparent_energy"] += apparent_power * elapsed_hours
    terminal["harmonic_energy"] += harmonic_power * elapsed_hours
    terminal["_last_energy_ts"] = now


def materialize_terminal_record(terminal: dict[str, Any]) -> dict[str, Any]:
    active_power, reactive_power, apparent_power, _harmonic_power = calculate_terminal_metrics(
        float(terminal["voltage"]),
        float(terminal["current"]),
        float(terminal["power_factor"]),
    )

    overload_status = 1 if float(terminal["current"]) >= OVERLOAD_CURRENT_A else 0

    return {
        "terminal_id": terminal["terminal_id"],
        "voltage": round_float(float(terminal["voltage"]), 1),
        "current": round_float(float(terminal["current"]), 2),
        "power_factor": round_float(float(terminal["power_factor"]), 2),
        "active_power": round_float(active_power, 2),
        "reactive_power": round_float(reactive_power, 2),
        "apparent_power": round_float(apparent_power, 2),
        "active_energy": round_float(float(terminal["active_energy"]), 4),
        "reactive_energy": round_float(float(terminal["reactive_energy"]), 4),
        "apparent_energy": round_float(float(terminal["apparent_energy"]), 4),
        "harmonic_energy": round_float(float(terminal["harmonic_energy"]), 4),
        "overload_status": overload_status,
    }


def materialize_gateway_record(gateway: dict[str, Any]) -> dict[str, Any]:
    return {
        "deviceId": gateway["deviceId"],
        "device_desc": gateway["device_desc"],
        "LoRa_SNR": f"{float(gateway['LoRa_SNR']):.1f}",
        "No_of_subDevices": str(gateway["No_of_subDevices"]),
    }


@dataclass
class AwsIoTPublisher:
    endpoint: str
    client_id: str
    cert_path: Path
    key_path: Path
    ca_path: Path
    topic: str

    def __post_init__(self) -> None:
        self._connection = None

    def connect(self) -> None:
        try:
            from awscrt import mqtt
            from awsiot import mqtt_connection_builder
        except ImportError as exc:
            raise RuntimeError(
                "Missing AWS IoT SDK dependencies. Install awscrt and awsiot-sdk."
            ) from exc

        self._mqtt = mqtt
        self._connection = mqtt_connection_builder.mtls_from_path(
            cert_filepath=str(self.cert_path),
            pri_key_filepath=str(self.key_path),
            ca_filepath=str(self.ca_path),
            endpoint=self.endpoint,
            client_id=self.client_id,
            clean_session=False,
            keep_alive_secs=30,
        )

        print(f"Connecting to {self.endpoint} with client ID '{self.client_id}'...")
        self._connection.connect().result()
        print("Connected to AWS IoT Core.")

    def publish(self, payload: str) -> None:
        if self._connection is None:
            raise RuntimeError("MQTT connection is not established.")

        self._connection.publish(
            topic=self.topic,
            payload=payload,
            qos=self._mqtt.QoS.AT_LEAST_ONCE,
        )

    def disconnect(self) -> None:
        if self._connection is not None:
            self._connection.disconnect().result()
            self._connection = None


class HeadlessSimulator:
    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.rng = random.Random(args.seed)
        self.last_published: dict[str, dict[str, Any]] = {}
        self.last_full_snapshot_monotonic = 0.0

        self.gateway = {
            "deviceId": DEFAULT_GATEWAY_ID,
            "device_desc": "Gateway",
            "LoRa_SNR": self.rng.uniform(*GATEWAY_SNR_RANGE),
            "No_of_subDevices": BUSBAR_COUNT,
        }

        self.busbars: dict[str, dict[str, Any]] = {}
        self.terminals: dict[str, dict[int, dict[str, Any]]] = {}
        self._init_state()

        self.publisher = None
        if not self.args.dry_run:
            self.publisher = AwsIoTPublisher(
                endpoint=self.args.endpoint,
                client_id=self.args.client_id,
                cert_path=self.args.cert,
                key_path=self.args.key,
                ca_path=self.args.ca,
                topic=self.args.topic,
            )

    def _init_state(self) -> None:
        now = time.time()
        base_lat = 9.0765
        base_lon = 7.3986

        for index, busbar_id in enumerate(BUSBAR_IDS):
            lat = base_lat + index * 0.0008
            lon = base_lon + index * 0.0008

            self.busbars[busbar_id] = {
                "deviceId": busbar_id,
                "device_desc": "busbar",
                "gps_status": random_gps_status(self.rng),
                "latitude": lat,
                "longitude": lon,
                "altitude": self.rng.uniform(380.0, 430.0),
                "speed": self.rng.uniform(0.0, 1.2),
                "gps_timestamp": int(now),
                "master_chip_Temp": self.rng.uniform(28.0, 38.0),
                "slave_1_chip_Temp": self.rng.uniform(27.0, 36.0),
                "slave_2_chip_Temp": self.rng.uniform(27.0, 36.0),
                "thermistor_Temp": self.rng.uniform(29.0, 40.0),
                "ext_Rg_I_red": 0.0,
                "ext_Rg_I_yellow": 0.0,
                "ext_Rg_I_blue": 0.0,
                "frequency": FREQUENCY_HZ,
                "LORA_RSSI": self.rng.uniform(*RSSI_RANGE),
                "error_flags": 0,
                "multi_paths": 1,
            }

            terminal_map: dict[int, dict[str, Any]] = {}
            for terminal_number in range(1, TERMINALS_PER_BUSBAR + 1):
                terminal_map[terminal_number] = {
                    "terminal_id": f"{busbar_id}-{terminal_number}",
                    "voltage": self.rng.uniform(100.0, 220.0),
                    "current": self.rng.uniform(0.1, 80.0),
                    "power_factor": self.rng.uniform(0.65, 1.0),
                    "active_energy": self.rng.uniform(0.0, 3.0),
                    "reactive_energy": self.rng.uniform(0.0, 2.0),
                    "apparent_energy": self.rng.uniform(0.0, 4.0),
                    "harmonic_energy": self.rng.uniform(0.0, 0.5),
                    "_last_energy_ts": now,
                }

            self.terminals[busbar_id] = terminal_map
            self._recompute_busbar(busbar_id, now, refresh_all_terminal_energy=False)

    def _recompute_busbar(self, busbar_id: str, now: float, refresh_all_terminal_energy: bool) -> None:
        busbar = self.busbars[busbar_id]
        terminals = self.terminals[busbar_id]

        phase_currents = [0.0, 0.0, 0.0]
        overload_count = 0
        current_sum = 0.0

        for terminal_number, terminal in terminals.items():
            if refresh_all_terminal_energy:
                apply_terminal_energy(terminal, now)

            terminal_current = float(terminal["current"])
            phase_currents[(terminal_number - 1) % 3] += terminal_current
            current_sum += terminal_current
            if terminal_current >= OVERLOAD_CURRENT_A:
                overload_count += 1

        average_current = current_sum / TERMINALS_PER_BUSBAR
        thermal_noise = self.rng.uniform(-0.4, 0.4)
        gps_valid = (int(busbar["gps_status"]) & 0b1) == 1

        busbar["ext_Rg_I_red"] = round_float(phase_currents[0], 2)
        busbar["ext_Rg_I_yellow"] = round_float(phase_currents[1], 2)
        busbar["ext_Rg_I_blue"] = round_float(phase_currents[2], 2)
        busbar["master_chip_Temp"] = round_float(30.0 + average_current * 0.18 + thermal_noise, 2)
        busbar["slave_1_chip_Temp"] = round_float(29.0 + average_current * 0.16 + thermal_noise, 2)
        busbar["slave_2_chip_Temp"] = round_float(29.0 + average_current * 0.17 - thermal_noise, 2)
        busbar["thermistor_Temp"] = round_float(31.0 + average_current * 0.20 + thermal_noise, 2)
        busbar["frequency"] = FREQUENCY_HZ
        busbar["multi_paths"] = self._multi_path_count(float(busbar["LORA_RSSI"]))

        error_flags = 0
        if overload_count > 0:
            error_flags |= 0x01
        if float(busbar["LORA_RSSI"]) <= -105.0:
            error_flags |= 0x02
        if not gps_valid:
            error_flags |= 0x04
        if float(busbar["master_chip_Temp"]) >= 70.0:
            error_flags |= 0x08
        if self.rng.random() < 0.02:
            error_flags |= 0x10
        busbar["error_flags"] = error_flags
        busbar["gps_timestamp"] = int(now)

    def _multi_path_count(self, rssi: float) -> int:
        if rssi >= -80:
            return 1
        if rssi >= -95:
            return 2
        if rssi >= -105:
            return 3
        return 4

    def _mutate_gateway(self) -> bool:
        if self.rng.random() >= 0.2:
            return False

        current = float(self.gateway["LoRa_SNR"])
        self.gateway["LoRa_SNR"] = round_float(clamp(current + self.rng.uniform(-0.4, 0.4), *GATEWAY_SNR_RANGE), 1)
        return True

    def _mutate_busbar_transport(self, busbar_id: str, now: float) -> bool:
        if self.rng.random() >= 0.3:
            return False

        busbar = self.busbars[busbar_id]
        busbar["LORA_RSSI"] = round_float(
            clamp(float(busbar["LORA_RSSI"]) + self.rng.uniform(-4.0, 4.0), *RSSI_RANGE),
            1,
        )
        busbar["speed"] = round_float(clamp(float(busbar["speed"]) + self.rng.uniform(-0.3, 0.5), 0.0, 8.0), 2)
        busbar["latitude"] = round_float(float(busbar["latitude"]) + self.rng.uniform(-0.0004, 0.0004), 6)
        busbar["longitude"] = round_float(float(busbar["longitude"]) + self.rng.uniform(-0.0004, 0.0004), 6)
        busbar["altitude"] = round_float(clamp(float(busbar["altitude"]) + self.rng.uniform(-0.8, 0.8), 360.0, 460.0), 2)

        if self.rng.random() < 0.4:
            busbar["gps_status"] = random_gps_status(self.rng)

        busbar["gps_timestamp"] = int(now)
        return True

    def _mutate_terminal(self, busbar_id: str, terminal_number: int, now: float) -> None:
        terminal = self.terminals[busbar_id][terminal_number]
        apply_terminal_energy(terminal, now)

        if self.rng.random() < 0.1:
            current = self.rng.uniform(65.0, 80.0)
        else:
            current = clamp(float(terminal["current"]) + self.rng.uniform(-8.0, 8.0), 0.1, 80.0)

        terminal["voltage"] = round_float(
            clamp(float(terminal["voltage"]) + self.rng.uniform(-12.0, 12.0), 100.0, 220.0),
            1,
        )
        terminal["current"] = round_float(current, 2)
        terminal["power_factor"] = round_float(
            clamp(float(terminal["power_factor"]) + self.rng.uniform(-0.05, 0.05), 0.65, 1.0),
            2,
        )

    def _maybe_change_busbar(self, busbar_id: str, now: float) -> list[dict[str, Any]]:
        terminal_numbers = list(range(1, TERMINALS_PER_BUSBAR + 1))
        changed_terminal_records: list[dict[str, Any]] = []
        terminals_changed = False

        if self.rng.random() < 0.45:
            changed_count = self.rng.randint(1, 3)
            for terminal_number in self.rng.sample(terminal_numbers, changed_count):
                self._mutate_terminal(busbar_id, terminal_number, now)
                changed_terminal_records.append(
                    materialize_terminal_record(self.terminals[busbar_id][terminal_number])
                )
                terminals_changed = True

        device_changed = self._mutate_busbar_transport(busbar_id, now)

        if not terminals_changed and not device_changed:
            return []

        self._recompute_busbar(busbar_id, now, refresh_all_terminal_energy=False)

        busbar_record = self._materialize_busbar_record(busbar_id)
        return [busbar_record, *changed_terminal_records]

    def _materialize_busbar_record(self, busbar_id: str) -> dict[str, Any]:
        busbar = self.busbars[busbar_id]
        return {
            "deviceId": busbar["deviceId"],
            "device_desc": busbar["device_desc"],
            "gps_status": int(busbar["gps_status"]),
            "latitude": round_float(float(busbar["latitude"]), 6),
            "longitude": round_float(float(busbar["longitude"]), 6),
            "altitude": round_float(float(busbar["altitude"]), 2),
            "speed": round_float(float(busbar["speed"]), 2),
            "gps_timestamp": int(busbar["gps_timestamp"]),
            "master_chip_Temp": round_float(float(busbar["master_chip_Temp"]), 2),
            "slave_1_chip_Temp": round_float(float(busbar["slave_1_chip_Temp"]), 2),
            "slave_2_chip_Temp": round_float(float(busbar["slave_2_chip_Temp"]), 2),
            "thermistor_Temp": round_float(float(busbar["thermistor_Temp"]), 2),
            "ext_Rg_I_red": round_float(float(busbar["ext_Rg_I_red"]), 2),
            "ext_Rg_I_yellow": round_float(float(busbar["ext_Rg_I_yellow"]), 2),
            "ext_Rg_I_blue": round_float(float(busbar["ext_Rg_I_blue"]), 2),
            "frequency": FREQUENCY_HZ,
            "LORA_RSSI": round_float(float(busbar["LORA_RSSI"]), 1),
            "error_flags": int(busbar["error_flags"]),
            "multi_paths": int(busbar["multi_paths"]),
        }

    def _full_snapshot_records(self, now: float) -> list[dict[str, Any]]:
        records = [materialize_gateway_record(self.gateway)]

        for busbar_id in BUSBAR_IDS:
            self._recompute_busbar(busbar_id, now, refresh_all_terminal_energy=True)
            records.append(self._materialize_busbar_record(busbar_id))
            for terminal_number in range(1, TERMINALS_PER_BUSBAR + 1):
                records.append(
                    materialize_terminal_record(self.terminals[busbar_id][terminal_number])
                )

        return records

    def _publish_records(self, records: list[dict[str, Any]], reason: str) -> None:
        if not records:
            return

        payload = json.dumps(records, separators=(",", ":"))
        summary = self._summarize_records(records)
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {reason}: {summary}")

        if self.args.dry_run:
            if self.args.print_payload:
                print(json.dumps(records, indent=2))
            return

        assert self.publisher is not None
        self.publisher.publish(payload)

    def _summarize_records(self, records: list[dict[str, Any]]) -> str:
        gateway_count = 0
        busbar_count = 0
        terminal_count = 0

        for record in records:
            if record.get("device_desc") == "Gateway":
                gateway_count += 1
            elif record.get("device_desc") == "busbar":
                busbar_count += 1
            elif "terminal_id" in record:
                terminal_count += 1

        return (
            f"{len(records)} records "
            f"(gateway={gateway_count}, busbars={busbar_count}, terminals={terminal_count})"
        )

    def _update_last_published(self, records: list[dict[str, Any]]) -> None:
        for record in records:
            self.last_published[get_record_id(record)] = record

    def run(self) -> None:
        if self.publisher is not None:
            self.publisher.connect()

        cycle = 0

        try:
            while True:
                cycle += 1
                now = time.time()
                monotonic_now = time.monotonic()
                full_snapshot_due = (
                    self.last_full_snapshot_monotonic == 0.0
                    or monotonic_now - self.last_full_snapshot_monotonic >= self.args.full_snapshot_seconds
                )

                if full_snapshot_due:
                    records = self._full_snapshot_records(now)
                    self._publish_records(records, "full snapshot")
                    self._update_last_published(records)
                    self.last_full_snapshot_monotonic = monotonic_now
                else:
                    records: list[dict[str, Any]] = []

                    if self._mutate_gateway():
                        gateway_record = materialize_gateway_record(self.gateway)
                        last_gateway = self.last_published.get(gateway_record["deviceId"])
                        if last_gateway is None or not compare_records(gateway_record, last_gateway):
                            records.append(gateway_record)

                    for busbar_id in BUSBAR_IDS:
                        candidate_records = self._maybe_change_busbar(busbar_id, now)
                        if not candidate_records:
                            continue

                        for record in candidate_records:
                            record_id = get_record_id(record)
                            last_record = self.last_published.get(record_id)
                            if record.get("device_desc") == "busbar" and any(
                                "terminal_id" in candidate for candidate in candidate_records
                            ):
                                records.append(record)
                                continue

                            if last_record is None or not compare_records(record, last_record):
                                records.append(record)

                    self._publish_records(records, "delta update")
                    self._update_last_published(records)

                if self.args.max_cycles and cycle >= self.args.max_cycles:
                    break

                time.sleep(self.args.tick_seconds)
        finally:
            if self.publisher is not None:
                self.publisher.disconnect()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Headless busbar MQTT simulator")
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT, help="AWS IoT endpoint")
    parser.add_argument("--topic", default=DEFAULT_TOPIC, help="MQTT topic for event payloads")
    parser.add_argument("--client-id", default=DEFAULT_CLIENT_ID, help="MQTT client ID")
    parser.add_argument("--cert", type=Path, default=DEFAULT_CERT, help="Path to client certificate PEM")
    parser.add_argument("--key", type=Path, default=DEFAULT_KEY, help="Path to private key PEM")
    parser.add_argument("--ca", type=Path, default=DEFAULT_CA, help="Path to CA certificate PEM")
    parser.add_argument("--tick-seconds", type=float, default=5.0, help="Seconds between simulation cycles")
    parser.add_argument(
        "--full-snapshot-seconds",
        type=float,
        default=120.0,
        help="Seconds between forced full packet uploads",
    )
    parser.add_argument("--seed", type=int, default=None, help="Optional RNG seed for repeatable data")
    parser.add_argument("--max-cycles", type=int, default=0, help="Stop after N cycles (0 = run forever)")
    parser.add_argument("--dry-run", action="store_true", help="Do not connect to AWS IoT")
    parser.add_argument("--print-payload", action="store_true", help="Print full JSON payloads for each publish")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if not args.dry_run:
        for path in (args.cert, args.key, args.ca):
            if not path.exists():
                print(f"Missing required certificate file: {path}", file=sys.stderr)
                return 1

    simulator = HeadlessSimulator(args)
    simulator.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
