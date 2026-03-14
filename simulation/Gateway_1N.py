from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication, QMainWindow, QTabWidget
from awscrt import mqtt
from awsiot import mqtt_connection_builder
import json
import threading
from bus_bar_tabN import GatewayBusbar

# MQTT Constants
CERT_FILEPATH = "./aws_certs/Gateway_001-certificate.pem.crt"
PRIVATE_KEY_FILEPATH = "./aws_certs/Gateway_001-private.pem.key"
CA_FILEPATH = "./aws_certs/AmazonRootCA1.pem"
ENDPOINT = "a1fe4ehoaifpyx-ats.iot.eu-north-1.amazonaws.com"
CLIENT_ID = "gateway_1"
COMMAND_TOPIC = "ecwa_dt/commands"
EVENT_TOPIC = "ecwa_dt/events"

class MainTabbedGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AEDC PILOT ECWA-DT-GateWay 1")
        self.setGeometry(100, 100, 1230, 600)

        # Create tab widget.
        self.tabs = QTabWidget(self)
        self.setCentralWidget(self.tabs)

        self.last_uploaded_data = {}  # Store the last uploaded data for change detection.

        # Add Gateway tab (Node) – description "Gateway" so that get_device_data returns node data.
        self.add_Gateway_tab("ND1234561", [f"Terminal {i+1}" for i in range(9)], description="Gateway")
        
        # Add BusBar tabs – simulate 10 busbars per gateway.
        for i in range(1, 11):
            deviceId = f"BB{str(i).zfill(4)}"
            self.add_bus_bar_tab(deviceId, [f"Terminal {j+1}" for j in range(15)])
            
        # Initialize AWS IoT MQTT connection.
        self.mqtt_connection = self.initialize_mqtt()

        # Timer for automatic uploads every 60 seconds.
        self.upload_timer = QTimer(self)
        self.upload_timer.timeout.connect(self.upload_to_cloud_at_interval)
        # self.upload_timer.start(60000)
        
        # Timer for detecting data changes every 2 seconds.
        self.change_detection_timer = QTimer(self)
        self.change_detection_timer.timeout.connect(self.upload_to_cloud_when_data_change)
        self.change_detection_timer.start(2000)

    def initialize_mqtt(self):
        """Initialize AWS IoT MQTT connection."""
        mqtt_connection = mqtt_connection_builder.mtls_from_path(
            cert_filepath=CERT_FILEPATH,
            pri_key_filepath=PRIVATE_KEY_FILEPATH,
            ca_filepath=CA_FILEPATH,
            endpoint=ENDPOINT,
            client_id=CLIENT_ID,
            clean_session=False,
            keep_alive_secs=30,
            on_connection_interrupted=self.on_connection_interrupted,
            on_connection_resumed=self.on_connection_resumed,
        )

        print(f"Connecting to {ENDPOINT} with client ID '{CLIENT_ID}'...")
        connect_future = mqtt_connection.connect()
        connect_future.result()
        print("Connected!")

        # Subscribe to COMMAND_TOPIC.
        print(f"Subscribing to topic '{COMMAND_TOPIC}'...")
        subscribe_future, _ = mqtt_connection.subscribe(
            topic=COMMAND_TOPIC,
            qos=mqtt.QoS.AT_LEAST_ONCE,
            callback=self.on_message_received,
        )
        subscribe_future.result()
        print(f"Subscribed to topic '{COMMAND_TOPIC}'.")

        return mqtt_connection

    def on_connection_interrupted(self, connection, error, **kwargs):
        print(f"Connection interrupted. Error: {error}")

    def on_connection_resumed(self, connection, return_code, session_present, **kwargs):
        print(f"Connection resumed. Return code: {return_code}, Session present: {session_present}")

    def on_message_received(self, topic, payload, dup, qos, retain, **kwargs):
        """Handle messages received on the COMMAND_TOPIC."""
        print(f"Received message from topic '{topic}': {payload}")
        data = json.loads(payload)
        self.download_from_cloud(data)

    def add_bus_bar_tab(self, the_device_id, terminals, description="", notes=""):
        """Add a new BusBar tab."""
        bus_bar_tab = GatewayBusbar(the_device_id, terminals, description, notes, parent=self, main_gui=self)
        self.tabs.addTab(bus_bar_tab, f"BusBar {the_device_id}")

    def add_Gateway_tab(self, gateway_id, terminals, description="", notes=""):
        """Add a new Gateway (Node) tab."""
        gateway_tab = GatewayBusbar(gateway_id, terminals, description, notes, parent=self, main_gui=self)
        self.tabs.addTab(gateway_tab, f"Gateway {gateway_id}")

    def upload_to_cloud_at_interval(self):
        """Aggregate data from the node and busbar tabs and upload to the cloud."""
        # print(f"upload_to_cloud_at_interval ")
        node_data = None
        busbars_data = []
        # Retrieve node data from the Gateway tab.
        for i in range(self.tabs.count()):
            tab = self.tabs.widget(i)
            if isinstance(tab, GatewayBusbar):
                if tab.description in ["Gateway", "DT Monitor"]:
                    node_data = tab.get_device_data()
                else:
                    busbars_data.append(tab.get_device_data())
        overall_data = {
            "timestamp": "2025-02-08T12:30:00.000Z",
            "node": node_data,
            "busbars": busbars_data,
            "pole": {
                "poleId": "P123456",
                "loc_latitude": 6.5244,
                "loc_longitude": 3.3792,
                "loc_altitude": 15.2,
                "pole_is_bent": False
            }
        }
        message = json.dumps(overall_data)
        print(f"Uploading aggregated data: {message}")
        self.mqtt_connection.publish(
            topic=EVENT_TOPIC,
            payload=message,
            qos=mqtt.QoS.AT_LEAST_ONCE,
        )
        # Update the last uploaded data with the full payload.
        self.last_uploaded_data = overall_data

    def normalize_busbar(self, busbar):
        """
        Normalize busbar data:
        - If busbar is a list (old structure: first element device info, rest terminals),
          convert it into a dictionary with keys "deviceId" and "terminals".
        - Otherwise, return as is.
        """
        if isinstance(busbar, list):
            device_info = busbar[0]
            terminals = busbar[1:]
            normalized = {}
            normalized["deviceId"] = device_info.get("deviceId") or device_info.get("device_id")
            normalized["Latitude"] = device_info.get("Latitude") 
            normalized["Longitude"] = device_info.get("Longitude")
            normalized["device_Temp"] = device_info.get("device_Temp")
            normalized["terminals"] = terminals  # assume terminals are already dictionaries
            return normalized
        return busbar

    def get_busbar_id(self, busbar):
        """Extract the busbar's unique id (normalized) from its data."""
        busbar = self.normalize_busbar(busbar)
        return busbar.get("deviceId") or busbar.get("device_id")

    def compare_dicts(self, d1, d2, tol=1e-2):
        """
        Compare two dictionaries recursively.
        If d1 and d2 are lists, delegate to compare_data_lists.
        For numeric values, differences smaller than tol are ignored.
        For dictionaries, compare keys and values recursively.
        For other types, check for equality.
        """
        # If both are lists, use compare_data_lists.
        if isinstance(d1, list) and isinstance(d2, list):
            return self.compare_data_lists(d1, d2, tol)
        # If they are not both dicts, do a direct equality check.
        if not (isinstance(d1, dict) and isinstance(d2, dict)):
            return d1 == d2
        if d1.keys() != d2.keys():
            return False
        for key in d1:
            v1 = d1[key]
            v2 = d2[key]
            if isinstance(v1, (int, float)) and isinstance(v2, (int, float)):
                if abs(v1 - v2) > tol:
                    print(f"Numeric difference for key '{key}': {v1} vs {v2}")
                    return False
            elif isinstance(v1, dict) and isinstance(v2, dict):
                if not self.compare_dicts(v1, v2, tol):
                    return False
            elif isinstance(v1, list) and isinstance(v2, list):
                if not self.compare_data_lists(v1, v2, tol):
                    return False
            else:
                if v1 != v2:
                    print(f"Difference for key '{key}': {v1} vs {v2}")
                    return False
        return True

    def compare_data_lists(self, list1, list2, tol=1e-2):
        """
        Compare two lists of dictionaries (or simple values).
        Assumes that both lists are in the same order.
        """
        if list1 is None or list2 is None:
            return list1 == list2
        if len(list1) != len(list2):
            print(f"List length difference: {len(list1)} vs {len(list2)}")
            return False
        for item1, item2 in zip(list1, list2):
            if isinstance(item1, dict) and isinstance(item2, dict):
                if not self.compare_dicts(item1, item2, tol):
                    return False
            else:
                if item1 != item2:
                    return False
        return True

    def flatten_overall_data(self, nested):
        """
        Convert the nested overall data into a flat list of records.
        For the node:
          - If it is a dict, the node record is added,
          - Then each terminal in node["terminals"] is added as a separate record.
        For each busbar (assumed to be a dict with a "terminals" key):
          - The busbar record (all keys except "terminals") is added,
          - Then each terminal in busbar["terminals"] is added.
        The pole is added as its own record.
        """
        flat_list = []
        # Process node
        node = nested.get("node")
        if node:
            if isinstance(node, dict):
                flat_list.append(node)
                for term in node.get("terminals", []):
                    flat_list.append(term)
            elif isinstance(node, list) and len(node) > 0:
                # Legacy format: first element is node info, rest are terminals.
                flat_list.append(node[0])
                for term in node[1:]:
                    flat_list.append(term)
        # Process busbars
        busbars = nested.get("busbars", [])
        for busbar in busbars:
            # Normalize busbar in case it is a legacy list.
            normalized = self.normalize_busbar(busbar)
            # Add busbar device info (all keys except "terminals")
            busbar_info = {k: v for k, v in normalized.items() if k != "terminals"}
            flat_list.append(busbar_info)
            # Add each terminal record.
            for term in normalized.get("terminals", []):
                flat_list.append(term)
        # Process pole
        pole = nested.get("pole")
        if pole:
            flat_list.append(pole)
        return flat_list

    def get_record_id(self, record):
        """
        Return a unique ID for a record:
          - For node records, use "deviceId".
          - For terminal records, use "terminal_id".
          - For pole records, use "poleId".
        """
        if "deviceId" in record:
            return record["deviceId"]
        if "terminal_id" in record:
            return record["terminal_id"]
        if "poleId" in record:
            return record["poleId"]
        return None

    def upload_to_cloud_when_data_change(self):
        """
        Gather the overall data, flatten it, compare with the last uploaded flat records,
        and publish only the records that have changed.
        """
        # Gather overall data (nested structure) from all tabs.
        node_data = None
        busbars_data = []
        for i in range(self.tabs.count()):
            tab = self.tabs.widget(i)
            if isinstance(tab, GatewayBusbar):
                if tab.description in ["Gateway", "DT Monitor"]:
                    node_data = tab.get_device_data()
                else:
                    busbars_data.append(tab.get_device_data())
        overall_data = {
            "timestamp": "2025-02-08T12:30:00.000Z",
            "node": node_data,
            "busbars": busbars_data
            # "pole": {
            #     "poleId": "P123456",
            #     "upriserId": "UPR56789",
            #     "loc_latitude": 6.5244,
            #     "loc_longitude": 3.3792,
            #     "bus_bar_nos": 3,
            #     "loc_altitude": 15.2,
            #     "pole_is_bent": False,
            #     "created_at": "2025-02-08T12:30:45.678Z"
            # }
        }
        # Flatten the overall data.
        # print(f"overall_data: {overall_data}")
        current_flat = self.flatten_overall_data(overall_data)
        # Build a lookup dictionary for the current flat data.
        current_lookup = {}
        for rec in current_flat:
            rec_id = self.get_record_id(rec)
            if rec_id:
                current_lookup[rec_id] = rec

        # Build a lookup dictionary for the last uploaded flat data.
        last_lookup = getattr(self, "last_uploaded_flat", {})
        # Compare: only include records that are new or differ.
        changed_records = {}
        for rec_id, rec in current_lookup.items():
            if rec_id not in last_lookup or not self.compare_dicts(rec, last_lookup[rec_id]):
                changed_records[rec_id] = rec

        if not changed_records:
            return

        # Prepare the changed flat list.
        changed_flat_list = list(changed_records.values())
        message = json.dumps(changed_flat_list)
        print(f"Uploading changed flat data: {message}")
        self.mqtt_connection.publish(
            topic=EVENT_TOPIC,
            payload=message,
            qos=mqtt.QoS.AT_LEAST_ONCE,
        )
        # Update last_uploaded_flat to current_lookup for future comparisons.
        self.last_uploaded_flat = current_lookup


    def upload_to_cloud_when_data_change0(self):
        """
        Upload only changed device data.
        For the node and each busbar, compare the current data with the last uploaded data.
        Only include in the update those sections (or terminals) that have changed.
        """
        changed_payload = {}
        
        # Process node (gateway) data.
        current_node = None
        for i in range(self.tabs.count()):
            tab = self.tabs.widget(i)
            if isinstance(tab, GatewayBusbar) and tab.description in ["Gateway", "DT Monitor"]:
                current_node = tab.get_device_data()
                break
        if current_node:
            last_node = self.last_uploaded_data.get("node") if self.last_uploaded_data else None
            if (not last_node) or (not self.compare_dicts(current_node, last_node)):
                #####%%
                changed_payload["node"] = current_node

        # Process busbar data.
        current_busbars = []
        for i in range(self.tabs.count()):
            tab = self.tabs.widget(i)
            if isinstance(tab, GatewayBusbar) and tab.description not in ["Gateway", "DT Monitor"]:
                # print(f" tab.get_device_data() { tab.get_device_data()}")
                current_busbars.append(tab.get_device_data())
        changed_busbars = []
        # Convert last uploaded busbars into a lookup dictionary.
        last_busbars = {}
        if self.last_uploaded_data and "busbars" in self.last_uploaded_data:
            busbars_list = self.last_uploaded_data.get("busbars", [])
            for b in busbars_list:
                normalized = self.normalize_busbar(b)
                busbar_id = normalized.get("deviceId") or normalized.get("device_id")
                if busbar_id:
                    last_busbars[busbar_id] = normalized
        for busbar in current_busbars:
            normalized_current = self.normalize_busbar(busbar)
            busbar_id = self.get_busbar_id(normalized_current)
            last_busbar = last_busbars.get(busbar_id)
            if (not last_busbar) or (not self.compare_dicts(normalized_current, last_busbar)):
                changed_busbars.append(normalized_current)
        if changed_busbars:
            changed_payload["busbars"] = changed_busbars

        # Process pole data (assumed fixed in this simulation).
        current_pole = {
            "poleId": "P123456",
            "upriserId": "UPR56789",
            "loc_latitude": 6.5244,
            "loc_longitude": 3.3792,
            "bus_bar_nos": 3,
            "loc_altitude": 15.2,
            "pole_is_bent": False,
            "created_at": "2025-02-08T12:30:45.678Z"
        }
        last_pole = self.last_uploaded_data.get("pole") if self.last_uploaded_data else None
        if (not last_pole) or (not self.compare_dicts(current_pole, last_pole)):
            changed_payload["pole"] = current_pole

        # If nothing has changed, do not upload.
        if not changed_payload:
            return

        # Add timestamp.
        changed_payload["timestamp"] = "2025-02-08T12:30:00.000Z"
        
        message = json.dumps(changed_payload)
        print(f"Uploading combined changed data: {message}")
        self.mqtt_connection.publish(
            topic=EVENT_TOPIC,
            payload=message,
            qos=mqtt.QoS.AT_LEAST_ONCE,
        )

        # Merge changes into last_uploaded_data.
        if not self.last_uploaded_data:
            self.last_uploaded_data = {}
        if "node" in changed_payload:
            self.last_uploaded_data["node"] = changed_payload["node"]
        if "busbars" in changed_payload:
            if "busbars" not in self.last_uploaded_data:
                self.last_uploaded_data["busbars"] = []
            updated_busbars = {}
            busbars_list = self.last_uploaded_data.get("busbars", [])
            for b in busbars_list:
                normalized = self.normalize_busbar(b)
                busbar_id = normalized.get("deviceId") or normalized.get("device_id")
                if busbar_id:
                    updated_busbars[busbar_id] = normalized
            for b in changed_payload["busbars"]:
                busbar_id = b.get("deviceId") or b.get("device_id")
                if busbar_id:
                    updated_busbars[busbar_id] = b
            self.last_uploaded_data["busbars"] = list(updated_busbars.values())
        if "pole" in changed_payload:
            self.last_uploaded_data["pole"] = changed_payload["pole"]

    def download_from_cloud(self, data):
        """Update all tabs with data from the cloud."""
        for i in range(self.tabs.count()):
            tab = self.tabs.widget(i)
            if isinstance(tab, GatewayBusbar):
                if tab.the_device_id in data:
                    print(f"Updating data for {tab.the_device_id}")
                    tab.update_terminal_data(data[tab.the_device_id])

    def handle_short_circuit(self, the_device_id, terminal_index):
        """Handle short circuit event triggered by a GatewayBusbar."""
        print(f"Short circuit detected on BusBar {the_device_id}, Terminal {terminal_index+1}")
        # Add custom logic here as needed.

if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    main_gui = MainTabbedGUI()
    main_gui.show()
    sys.exit(app.exec_())
