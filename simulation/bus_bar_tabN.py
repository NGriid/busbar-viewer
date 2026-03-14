from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem, QPushButton, QSlider, QHBoxLayout,QGridLayout
)
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtWidgets import QFormLayout


class GatewayBusbar(QWidget):
    # def __init__(self, the_device_id, terminals, parent=None):
    def __init__(self, the_device_id, terminals, description="", notes="", parent=None, main_gui=None):
        super().__init__(parent)
        self.the_device_id = the_device_id
        self.terminals = terminals
        self.description = description  # Additional text to display
        self.notes = notes  # Additional notes to display
        self.elapsed_time = 0  # Time elapsed in seconds for Energy calculation

        # Timer variables for energy update
        self.energy_update_counter = 0  # Counter to track update cycles
        self.energy_update_interval = 10  # Perform energy update every 5 calls to update_data
        
        
        # Store control buttons and sliders
        self.controls = {}  # To store buttons, sliders, etc., for each terminal

        # Main Layout
        main_layout = QVBoxLayout(self)  # Rename to avoid shadowing `layout`

        # Header
        header = QLabel(f"Busbar {the_device_id} - Terminals Overview")
        main_layout.addWidget(header)

        # Table for terminal data
        self.terminal_table = QTableWidget(self)
        self.terminal_table.setRowCount(len(terminals))
        self.terminal_table.setColumnCount(11)  # Columns for terminal data
        self.terminal_table.setHorizontalHeaderLabels(
            [
                "Terminal", "Voltage (V)", "Voltage Slider", "Current (A)",
                "Current Slider", "Power (W)", "Energy (Wh)", "Temp. (°C)",
                "Temperature Slider", "Status", "S/C"
            ]
        )
        main_layout.addWidget(self.terminal_table)

        # Initialize table rows
        self.init_table()

        # Footer Section: Add labels for description and notes
        self.footer_description = QLabel(f"Description: {self.description}")
        main_layout.addWidget(self.footer_description)

        self.footer_notes = QLabel(f"Notes: {self.notes}")
        main_layout.addWidget(self.footer_notes)
        self.main_gui = main_gui  # Reference to MainTabbedGUI
        
        # Check if description is "Gateway" to add additional fields
        if self.description == "Gateway" or self.description == "DT Monitor" :
            self.add_gateway_specific_fields(main_layout)
        else:
            self.add_busbar_specific_fields(main_layout)

        # Timer for updating data
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_data)
        self.timer.start(1000)  # Update every second

    def init_table(self):
        """Initialize the table with widgets for each terminal."""
        for i, terminal in enumerate(self.terminals):
            # Terminal name
            self.terminal_table.setItem(i, 0, QTableWidgetItem(terminal))

            # Placeholder data for voltage, current, power, energy, temperature
            self.terminal_table.setItem(i, 1, QTableWidgetItem("220"))  # Voltage
            self.terminal_table.setItem(i, 3, QTableWidgetItem("10"))   # Current
            self.terminal_table.setItem(i, 5, QTableWidgetItem("2200"))  # Power
            self.terminal_table.setItem(i, 6, QTableWidgetItem("0"))     # Energy
            self.terminal_table.setItem(i, 7, QTableWidgetItem("25"))    # Temperature

            # Voltage slider
            voltage_slider = QSlider(Qt.Horizontal)
            voltage_slider.setMinimum(100)
            voltage_slider.setMaximum(240)
            voltage_slider.setValue(220)
            voltage_slider.valueChanged.connect(lambda value, idx=i: self.adjust_voltage(idx, value))
            self.terminal_table.setCellWidget(i, 2, voltage_slider)

            # Current slider
            current_slider = QSlider(Qt.Horizontal)
            current_slider.setMinimum(0)
            current_slider.setMaximum(30)
            current_slider.setValue(0) #10
            current_slider.valueChanged.connect(lambda value, idx=i: self.adjust_current(idx, value))
            self.terminal_table.setCellWidget(i, 4, current_slider)

            # Temperature slider
            temp_slider = QSlider(Qt.Horizontal)
            temp_slider.setMinimum(0)
            temp_slider.setMaximum(100)
            temp_slider.setValue(25)
            temp_slider.valueChanged.connect(lambda value, idx=i: self.adjust_temperature(idx, value))
            self.terminal_table.setCellWidget(i, 8, temp_slider)

            # ON/OFF control button
            control_button = QPushButton("OFF")
            control_button.clicked.connect(lambda _, idx=i: self.toggle_control(idx))
            self.terminal_table.setCellWidget(i, 9, control_button)
            
            # Short Circuit control button
            short_cct_button = QPushButton("OFF")
            short_cct_button.clicked.connect(lambda _, idx=i: self.toggle_short_cct_control(idx))
            self.terminal_table.setCellWidget(i, 10, short_cct_button)

            # Store controls for later reference
            self.controls[i] = {
                "voltage_slider": voltage_slider,
                "current_slider": current_slider,
                "temp_slider": temp_slider,
                "button": control_button,
                "short_cct_button": short_cct_button
            }

        # Adjust column width for sliders
        for col in [2, 4, 8]: # Adjust column width for sliders 
            self.terminal_table.setColumnWidth(col, 150) 
        for col in [9, 10]:  # Buttons
            self.terminal_table.setColumnWidth(col, 70)

    def update_data(self):
        """Update the data for each terminal and compute energy."""
        self.elapsed_time += 1  # Increment time by 1 second
        self.energy_update_counter += 1  # Increment energy update counter

        for i, terminal in enumerate(self.terminals):
            # Get the current slider values
            voltage = self.controls[i]["voltage_slider"].value()
            current = self.controls[i]["current_slider"].value()
            power = voltage * current
            temperature = self.controls[i]["temp_slider"].value()

            # Compute energy (Power × Time in seconds, converted to Wh)
            previous_energy = float(self.terminal_table.item(i, 6).text())
            energy = previous_energy + (power / 3600)

            # Update data in the table
            self.terminal_table.item(i, 1).setText(str(voltage))  # Voltage
            self.terminal_table.item(i, 3).setText(str(current))  # Current
            self.terminal_table.item(i, 5).setText(str(power))    # Power
            if self.energy_update_counter >= self.energy_update_interval:
                self.terminal_table.item(i, 6).setText(f"{energy:.2f}")  # Energy
            self.terminal_table.item(i, 7).setText(str(temperature))  # Temperature

            # Check for alerts
            over_voltage = voltage > 229
            over_current = current > 15

            # Highlight cells for alerts
            item = self.terminal_table.item(i, 1)  # Voltage cell
            if item:
                item.setBackground(Qt.red if over_voltage else Qt.white)

            item = self.terminal_table.item(i, 3)  # Current cell
            if item:
                item.setBackground(Qt.red if over_current else Qt.white)
                # Reset the energy update counter if it reaches the interval
        if self.energy_update_counter >= self.energy_update_interval:
            self.energy_update_counter = 0

    # def toggle_short_cct_control_0(self, index):
    #     """Toggle the ON/OFF state of the short_cct button."""
    #     button = self.controls[index]["short_cct_button"]
    #     if button.text() == "ON":
    #         button.setText("OFF")
    #         button.setStyleSheet("")  # Reset to default style
    #     else:
    #         button.setText("ON")
    #         button.setStyleSheet("background-color: red; color: white;")
    #     # Call the function in MainTabbedGUI


    def toggle_short_cct_control(self, index):
        """Toggle the ON/OFF state of the short_cct button."""
        button = self.controls[index]["short_cct_button"]
        # Set the behavior for when the button is pressed
        # button.pressed.connect(lambda: self.set_short_cct_active(button))
        # # Set the behavior for when the button is released
        # button.released.connect(lambda: self.reset_short_cct(button))
        if not button.signalsBlocked():
            button.pressed.connect(lambda: self.set_short_cct_active(button))
            button.released.connect(lambda: self.reset_short_cct(button))
        if self.main_gui:
            self.main_gui.handle_short_circuit(self.the_device_id, index)


    def set_short_cct_active(self, button):
        """Activate the Short Circuit state."""
        button.setText("ON")
        button.setStyleSheet("background-color: red; color: white;")

    def reset_short_cct(self, button):
        """Reset the Short Circuit state."""
        button.setText("OFF")
        button.setStyleSheet("")  # Reset to default style

    def toggle_control(self, index):
        """Toggle the ON/OFF state of the control button."""
        button = self.controls[index]["button"]
        if button.text() == "ON":
            button.setText("OFF")
            button.setStyleSheet("")  # Reset to default style
        else:
            button.setText("ON")
            button.setStyleSheet("background-color: green; color: white;")

    def adjust_voltage(self, index, value):
        """Adjust the Voltage value based on the slider."""
        print(f"Terminal {self.terminals[index]}: Voltage adjusted to {value} V")

    def adjust_current(self, index, value):
        """Adjust the Current value based on the slider."""
        print(f"Terminal {self.terminals[index]}: Current adjusted to {value} A")

    def adjust_temperature(self, index, value):
        """Adjust the Temperature value based on the slider."""
        print(f"Terminal {self.terminals[index]}: Temperature adjusted to {value} °C")

    def get_device_data(self): # send all the terminal data for the selected device
        """Retrieve the current state of all terminals."""
        data = []
        device_data = {
        "deviceId": self.the_device_id,
        "device_desc": self.description,
    
        
        "V_red_value": self.V_red_value.text() if hasattr(self, 'V_red_value') else "N/A",
        "V_yellow_value": self.V_yellow_value.text() if hasattr(self, 'V_yellow_value') else "N/A",
        "V_blue_value": self.V_blue_value.text() if hasattr(self, 'V_blue_value') else "N/A",
        
        "Internal_Rg_Curr_red": self.Internal_Rogw_Curr_red_value.text() if hasattr(self, 'Internal_Rogw_Curr_red_value') else "N/A",
        "Internal_Rg_Curr_yellow": self.Internal_Rogw_Curr_yellow_value.text() if hasattr(self, 'Internal_Rogw_Curr_yellow_value') else "N/A",
        "Internal_Rg_Curr_blue": self.Internal_Rogw_Curr_blue_value.text() if hasattr(self, 'Internal_Rogw_Curr_blue_value') else "N/A",
        
        "External_Rg_Curr_red": self.External_Rogw_Curr_red_value.text() if hasattr(self, 'External_Rogw_Curr_red_value') else "N/A",
        "External_Rg_Curr_yellow": self.External_Rogw_Curr_yellow_value.text() if hasattr(self, 'External_Rogw_Curr_yellow_value') else "N/A",
        "External_Rg_Curr_blue": self.External_Rogw_Curr_blue_value.text() if hasattr(self, 'External_Rogw_Curr_blue_value') else "N/A",
        
        "Latitude": self.lat_value.text() if hasattr(self, 'lat_value') else "N/A",
        "Longitude": self.long_value.text() if hasattr(self, 'long_value') else "N/A",
        "transformer_Temp": self.transformer_temp_value.text() if hasattr(self, 'transformer_temp_value') else "N/A",#will be N/A for busbar
        "device_Temp": self.Device_Temp_value.text() if hasattr(self, 'Device_Temp_value') else "N/A",
        "Battery_Volt": self.batt_volt_value.text() if hasattr(self, 'batt_volt_value') else "N/A",#will be N/A for busbar
        "Solar_Volt": self.solar_volt_value.text() if hasattr(self, 'solar_volt_value') else "N/A",#will be N/A for busbar
        "Door_Status": self.door_status_value.text() if hasattr(self, 'door_status_value') else "N/A",#will be N/A for busbar
        "No_of_subDevices": 15,
        }
        
        
        data.append(device_data)
        for i, terminal in enumerate(self.terminals):
            if i == 0:
                    terminal_data = {
                    # "device_id": self.the_device_id,  # Include bus bar ID
                    "terminal_id": f"{self.the_device_id}-{i+1}",  # Unique terminal ID
                    # "terminal_name": terminal,  # Terminal name for clarity
                    "voltage": int(self.terminal_table.item(i, 1).text()),
                    "current": int(self.terminal_table.item(i, 3).text()),
                    "power": int(self.terminal_table.item(i, 5).text()),
                    "energy": float(self.terminal_table.item(i, 6).text()),
                    "temperature": int(self.terminal_table.item(i, 7).text()),
                    "control_status": self.controls[i]["button"].text(),
                    "short_cct_status": self.controls[i]["short_cct_button"].text(),
                }
            else:
                terminal_data = {
                    "terminal_id": f"{self.the_device_id}-{i+1}",  # Unique terminal ID
                    # "terminal_name": terminal,  # Terminal name for clarity
                    "voltage": int(self.terminal_table.item(i, 1).text()),
                    "current": int(self.terminal_table.item(i, 3).text()),
                    "power": int(self.terminal_table.item(i, 5).text()),
                    "energy": float(self.terminal_table.item(i, 6).text()),
                    "temperature": int(self.terminal_table.item(i, 7).text()),
                    "control_status": self.controls[i]["button"].text(),
                    "short_cct_status": self.controls[i]["short_cct_button"].text(),
                }
            data.append(terminal_data)
        return data


    def update_terminal_data(self, data):
        """Update the state of terminals based on the given data."""
        for i, terminal_data in enumerate(data):
            self.terminal_table.item(i, 1).setText(str(terminal_data["voltage"]))
            self.terminal_table.item(i, 3).setText(str(terminal_data["current"]))
            self.terminal_table.item(i, 5).setText(str(terminal_data["power"]))
            self.terminal_table.item(i, 6).setText(f"{terminal_data['energy']:.2f}")
            self.terminal_table.item(i, 7).setText(str(terminal_data["temperature"]))

            # Update button states
            self.controls[i]["button"].setText(terminal_data["control_status"])
            self.controls[i]["short_cct_button"].setText(terminal_data["short_circuit_status"])


    def add_gateway_specific_fields0(self, layout):
        """Add additional fields for Gateway description."""
        def style_value_label(label, color="green"):
            """Style the value label with color and bounding rectangle."""
            label.setStyleSheet(
                """
                QLabel {
                    background-color: {color}; 
                    border: 1px solid #ccc; 
                    border-radius: 4px; 
                    padding: 4px;
                    color: #333;
                    font-weight: bold;
                }
                """
            )
            
        # Red Phase Volt
        V_red_layout = QHBoxLayout()
        V_red_label = QLabel("Red Phase Volt:")
        self.V_red_value = QLabel("220.0")
        style_value_label(self.V_red_value)
        V_red_slider = QSlider(Qt.Horizontal)
        V_red_slider.setMinimum(0)
        V_red_slider.setMaximum(415)
        V_red_slider.setValue(220)
        V_red_slider.setFixedWidth(415)
        V_red_slider.valueChanged.connect(lambda value: self.V_red_value.setText(f"{value:.1f}"))
        V_red_layout.addWidget(V_red_label)
        V_red_layout.addWidget(self.V_red_value)
        V_red_layout.addWidget(V_red_slider)
        layout.addLayout(V_red_layout)
            
         # Yellow Phase Volt
        V_yellow_layout = QHBoxLayout()
        V_yellow_label = QLabel("Yellow Phase Volt:")
        self.V_yellow_value = QLabel("220.0")
        style_value_label(self.V_yellow_value)
        V_yellow_slider = QSlider(Qt.Horizontal)
        V_yellow_slider.setMinimum(0)
        V_yellow_slider.setMaximum(415)
        V_yellow_slider.setValue(220)
        V_yellow_slider.setFixedWidth(415)
        V_yellow_slider.valueChanged.connect(lambda value: self.V_yellow_value.setText(f"{value:.1f}"))
        V_yellow_layout.addWidget(V_yellow_label)
        V_yellow_layout.addWidget(self.V_yellow_value)
        V_yellow_layout.addWidget(V_yellow_slider)
        layout.addLayout(V_yellow_layout)
        
                 # Blue Phase Volt
        V_blue_layout = QHBoxLayout()
        V_blue_label = QLabel("Blue Phase Volt:")
        self.V_blue_value = QLabel("220.0")
        style_value_label(self.V_blue_value)
        V_blue_slider = QSlider(Qt.Horizontal)
        V_blue_slider.setMinimum(0)
        V_blue_slider.setMaximum(415)
        V_blue_slider.setValue(220)
        V_blue_slider.setFixedWidth(415)
        V_blue_slider.valueChanged.connect(lambda value: self.V_blue_value.setText(f"{value:.1f}"))
        V_blue_layout.addWidget(V_blue_label)
        V_blue_layout.addWidget(self.V_blue_value)
        V_blue_layout.addWidget(V_blue_slider)
        layout.addLayout(V_blue_layout)
        
        # Latitude
        lat_layout = QHBoxLayout()
        lat_label = QLabel("Latitude:")
        self.lat_value = QLabel("0.0")
        style_value_label(self.lat_value)
        lat_slider = QSlider(Qt.Horizontal)
        lat_slider.setMinimum(-90)
        lat_slider.setMaximum(90)
        lat_slider.setValue(0)
        lat_slider.setFixedWidth(250)
        lat_slider.valueChanged.connect(lambda value: self.lat_value.setText(f"{value:.1f}"))
        lat_layout.addWidget(lat_label)
        lat_layout.addWidget(self.lat_value)
        lat_layout.addWidget(lat_slider)
        layout.addLayout(lat_layout)

        # Longitude
        long_layout = QHBoxLayout()
        long_label = QLabel("Longitude:")
        self.long_value = QLabel("0.0")
        style_value_label(self.long_value)
        long_slider = QSlider(Qt.Horizontal)
        long_slider.setMinimum(-180)
        long_slider.setMaximum(180)
        long_slider.setValue(0)
        long_slider.setFixedWidth(250)
        long_slider.valueChanged.connect(lambda value: self.long_value.setText(f"{value:.1f}"))
        long_layout.addWidget(long_label)
        long_layout.addWidget(self.long_value)
        long_layout.addWidget(long_slider)
        layout.addLayout(long_layout)

        # Transformer Temperature
        ext_temp_layout = QHBoxLayout()
        ext_temp_label = QLabel("Transformer Temp:")
        self.transformer_temp_value = QLabel("25.0")
        style_value_label(self.transformer_temp_value)
        ext_temp_slider = QSlider(Qt.Horizontal)
        ext_temp_slider.setMinimum(-40)
        ext_temp_slider.setMaximum(85)
        ext_temp_slider.setValue(25)
        ext_temp_slider.setFixedWidth(250)
        ext_temp_slider.valueChanged.connect(lambda value: self.transformer_temp_value.setText(f"{value:.1f} °C"))
        ext_temp_layout.addWidget(ext_temp_label)
        ext_temp_layout.addWidget(self.transformer_temp_value)
        ext_temp_layout.addWidget(ext_temp_slider)
        layout.addLayout(ext_temp_layout)
        
        # Device_Temp
        dev_temp_layout = QHBoxLayout()
        dev_temp_label = QLabel("Device Temp:")
        self.Device_Temp_value = QLabel("10.0")
        style_value_label(self.Device_Temp_value)
        dev_temp_slider = QSlider(Qt.Horizontal)
        dev_temp_slider.setMinimum(0)
        dev_temp_slider.setMaximum(80)
        dev_temp_slider.setValue(10)
        dev_temp_slider.setFixedWidth(250)
        dev_temp_slider.valueChanged.connect(lambda value: self.Device_Temp_value.setText(f"{value:.1f}"))
        dev_temp_layout.addWidget(dev_temp_label)
        dev_temp_layout.addWidget(self.Device_Temp_value)
        dev_temp_layout.addWidget(dev_temp_slider)
        layout.addLayout(dev_temp_layout)

        # Battery Voltage
        batt_volt_layout = QHBoxLayout()
        batt_volt_label = QLabel("Battery Voltage:")
        self.batt_volt_value = QLabel("12.0")
        style_value_label(self.batt_volt_value)
        batt_volt_slider = QSlider(Qt.Horizontal)
        batt_volt_slider.setMinimum(10)
        batt_volt_slider.setMaximum(15)
        batt_volt_slider.setValue(12)
        batt_volt_slider.setFixedWidth(250)
        batt_volt_slider.valueChanged.connect(lambda value: self.batt_volt_value.setText(f"{value:.1f} V"))
        batt_volt_layout.addWidget(batt_volt_label)
        batt_volt_layout.addWidget(self.batt_volt_value)
        batt_volt_layout.addWidget(batt_volt_slider)
        layout.addLayout(batt_volt_layout)

        # Door Status
        door_status_layout = QHBoxLayout()
        door_status_label = QLabel("Door Status:")
        self.door_status_value = QLabel("CLOSED")
        style_value_label(self.door_status_value)
        door_status_layout.addWidget(door_status_label)
        door_status_layout.addWidget(self.door_status_value)
        layout.addLayout(door_status_layout)

    def add_gateway_specific_fields(self, layout):
        """Add additional fields for Gateway description in a two-column grid layout."""
        def style_value_label(label, color="green"):
            """Style the value label with color and bounding rectangle."""
            label.setStyleSheet(
                """
                QLabel {
                    background-color: %s; 
                    border: 1px solid #ccc; 
                    border-radius: 4px; 
                    padding: 4px;
                    color: #333;
                    font-weight: bold;
                }
                """ % color
            )

        # Create field layouts (same as before)
        # Red Phase Volt
        V_red_layout = QHBoxLayout()
        V_red_label = QLabel("Red Phase Volt:")
        self.V_red_value = QLabel("220.0")
        style_value_label(self.V_red_value)
        V_red_slider = QSlider(Qt.Horizontal)
        V_red_slider.setMinimum(0)
        V_red_slider.setMaximum(415)
        V_red_slider.setValue(220)
        V_red_slider.setFixedWidth(415)
        V_red_slider.valueChanged.connect(lambda value: self.V_red_value.setText(f"{value:.1f}"))
        V_red_layout.addWidget(V_red_label)
        V_red_layout.addWidget(self.V_red_value)
        V_red_layout.addWidget(V_red_slider)

        # Yellow Phase Volt
        V_yellow_layout = QHBoxLayout()
        V_yellow_label = QLabel("Yellow Phase Volt:")
        self.V_yellow_value = QLabel("220.0")
        style_value_label(self.V_yellow_value)
        V_yellow_slider = QSlider(Qt.Horizontal)
        V_yellow_slider.setMinimum(0)
        V_yellow_slider.setMaximum(415)
        V_yellow_slider.setValue(220)
        V_yellow_slider.setFixedWidth(415)
        V_yellow_slider.valueChanged.connect(lambda value: self.V_yellow_value.setText(f"{value:.1f}"))
        V_yellow_layout.addWidget(V_yellow_label)
        V_yellow_layout.addWidget(self.V_yellow_value)
        V_yellow_layout.addWidget(V_yellow_slider)

        # Blue Phase Volt
        V_blue_layout = QHBoxLayout()
        V_blue_label = QLabel("Blue Phase Volt:")
        self.V_blue_value = QLabel("220.0")
        style_value_label(self.V_blue_value)
        V_blue_slider = QSlider(Qt.Horizontal)
        V_blue_slider.setMinimum(0)
        V_blue_slider.setMaximum(415)
        V_blue_slider.setValue(220)
        V_blue_slider.setFixedWidth(415)
        V_blue_slider.valueChanged.connect(lambda value: self.V_blue_value.setText(f"{value:.1f}"))
        V_blue_layout.addWidget(V_blue_label)
        V_blue_layout.addWidget(self.V_blue_value)
        V_blue_layout.addWidget(V_blue_slider)
        
        # Red Phase Internal Rogwoski  Current
        Internal_Rogw_Curr_red_layout = QHBoxLayout()
        Internal_Rogw_Curr_red_label = QLabel("Red Internal Rog Curr:")
        self.Internal_Rogw_Curr_red_value = QLabel("0.0")
        style_value_label(self.Internal_Rogw_Curr_red_value)
        Internal_Rogw_Curr_red_slider = QSlider(Qt.Horizontal)
        Internal_Rogw_Curr_red_slider.setMinimum(0)
        Internal_Rogw_Curr_red_slider.setMaximum(415)
        Internal_Rogw_Curr_red_slider.setValue(0)
        Internal_Rogw_Curr_red_slider.setFixedWidth(415)
        Internal_Rogw_Curr_red_slider.valueChanged.connect(lambda value: self.Internal_Rogw_Curr_red_value.setText(f"{value:.1f}"))
        Internal_Rogw_Curr_red_layout.addWidget(Internal_Rogw_Curr_red_label)
        Internal_Rogw_Curr_red_layout.addWidget(self.Internal_Rogw_Curr_red_value)
        Internal_Rogw_Curr_red_layout.addWidget(Internal_Rogw_Curr_red_slider)

        # Yellow Phase Internal Rogwoski Current
        Internal_Rogw_Curr_yellow_layout = QHBoxLayout()
        Internal_Rogw_Curr_yellow_label = QLabel("Yellow Internal Rog Curr:")
        self.Internal_Rogw_Curr_yellow_value = QLabel("0.0")
        style_value_label(self.Internal_Rogw_Curr_yellow_value)
        Internal_Rogw_Curr_yellow_slider = QSlider(Qt.Horizontal)
        Internal_Rogw_Curr_yellow_slider.setMinimum(0)
        Internal_Rogw_Curr_yellow_slider.setMaximum(415)
        Internal_Rogw_Curr_yellow_slider.setValue(0)
        Internal_Rogw_Curr_yellow_slider.setFixedWidth(415)
        Internal_Rogw_Curr_yellow_slider.valueChanged.connect(lambda value: self.Internal_Rogw_Curr_yellow_value.setText(f"{value:.1f}"))
        Internal_Rogw_Curr_yellow_layout.addWidget(Internal_Rogw_Curr_yellow_label)
        Internal_Rogw_Curr_yellow_layout.addWidget(self.Internal_Rogw_Curr_yellow_value)
        Internal_Rogw_Curr_yellow_layout.addWidget(Internal_Rogw_Curr_yellow_slider)

        # Blue Phase Internal Rogwoski Current
        Internal_Rogw_Curr_blue_layout = QHBoxLayout()
        Internal_Rogw_Curr_blue_label = QLabel("Blue Internal Rog Curr:")
        self.Internal_Rogw_Curr_blue_value = QLabel("0.0")
        style_value_label(self.Internal_Rogw_Curr_blue_value)
        Internal_Rogw_Curr_blue_slider = QSlider(Qt.Horizontal)
        Internal_Rogw_Curr_blue_slider.setMinimum(0)
        Internal_Rogw_Curr_blue_slider.setMaximum(415)
        Internal_Rogw_Curr_blue_slider.setValue(0)
        Internal_Rogw_Curr_blue_slider.setFixedWidth(415)
        Internal_Rogw_Curr_blue_slider.valueChanged.connect(lambda value: self.Internal_Rogw_Curr_blue_value.setText(f"{value:.1f}"))
        Internal_Rogw_Curr_blue_layout.addWidget(Internal_Rogw_Curr_blue_label)
        Internal_Rogw_Curr_blue_layout.addWidget(self.Internal_Rogw_Curr_blue_value)
        Internal_Rogw_Curr_blue_layout.addWidget(Internal_Rogw_Curr_blue_slider)
        
        # Red Phase External Rogwoski Current
        External_Rogw_Curr_red_layout = QHBoxLayout()
        External_Rogw_Curr_red_label = QLabel("Red External Rog Curr:")
        self.External_Rogw_Curr_red_value = QLabel("0.0")
        style_value_label(self.External_Rogw_Curr_red_value)
        External_Rogw_Curr_red_slider = QSlider(Qt.Horizontal)
        External_Rogw_Curr_red_slider.setMinimum(0)
        External_Rogw_Curr_red_slider.setMaximum(415)
        External_Rogw_Curr_red_slider.setValue(0)
        External_Rogw_Curr_red_slider.setFixedWidth(415)
        External_Rogw_Curr_red_slider.valueChanged.connect(lambda value: self.External_Rogw_Curr_red_value.setText(f"{value:.1f}"))
        External_Rogw_Curr_red_layout.addWidget(External_Rogw_Curr_red_label)
        External_Rogw_Curr_red_layout.addWidget(self.External_Rogw_Curr_red_value)
        External_Rogw_Curr_red_layout.addWidget(External_Rogw_Curr_red_slider)

        # Yellow Phase External Rogwoski Current
        External_Rogw_Curr_yellow_layout = QHBoxLayout()
        External_Rogw_Curr_yellow_label = QLabel("Yellow External Rog Curr:")
        self.External_Rogw_Curr_yellow_value = QLabel("0.0")
        style_value_label(self.External_Rogw_Curr_yellow_value)
        External_Rogw_Curr_yellow_slider = QSlider(Qt.Horizontal)
        External_Rogw_Curr_yellow_slider.setMinimum(0)
        External_Rogw_Curr_yellow_slider.setMaximum(415)
        External_Rogw_Curr_yellow_slider.setValue(0)
        External_Rogw_Curr_yellow_slider.setFixedWidth(415)
        External_Rogw_Curr_yellow_slider.valueChanged.connect(lambda value: self.External_Rogw_Curr_yellow_value.setText(f"{value:.1f}"))
        External_Rogw_Curr_yellow_layout.addWidget(External_Rogw_Curr_yellow_label)
        External_Rogw_Curr_yellow_layout.addWidget(self.External_Rogw_Curr_yellow_value)
        External_Rogw_Curr_yellow_layout.addWidget(External_Rogw_Curr_yellow_slider)

        # Blue Phase External Rogwoski Current
        External_Rogw_Curr_blue_layout = QHBoxLayout()
        External_Rogw_Curr_blue_label = QLabel("Blue External Rog Curr:")
        self.External_Rogw_Curr_blue_value = QLabel("0.0")
        style_value_label(self.External_Rogw_Curr_blue_value)
        External_Rogw_Curr_blue_slider = QSlider(Qt.Horizontal)
        External_Rogw_Curr_blue_slider.setMinimum(0)
        External_Rogw_Curr_blue_slider.setMaximum(415)
        External_Rogw_Curr_blue_slider.setValue(0)
        External_Rogw_Curr_blue_slider.setFixedWidth(415)
        External_Rogw_Curr_blue_slider.valueChanged.connect(lambda value: self.External_Rogw_Curr_blue_value.setText(f"{value:.1f}"))
        External_Rogw_Curr_blue_layout.addWidget(External_Rogw_Curr_blue_label)
        External_Rogw_Curr_blue_layout.addWidget(self.External_Rogw_Curr_blue_value)
        External_Rogw_Curr_blue_layout.addWidget(External_Rogw_Curr_blue_slider)

        # Latitude
        lat_layout = QHBoxLayout()
        lat_label = QLabel("Latitude:")
        self.lat_value = QLabel("0.0")
        style_value_label(self.lat_value)
        lat_slider = QSlider(Qt.Horizontal)
        lat_slider.setMinimum(0)
        lat_slider.setMaximum(180)
        lat_slider.setValue(0)
        lat_slider.setFixedWidth(250)
        lat_slider.valueChanged.connect(lambda value: self.lat_value.setText(f"{value:.1f}"))
        lat_layout.addWidget(lat_label)
        lat_layout.addWidget(self.lat_value)
        lat_layout.addWidget(lat_slider)

        # Longitude
        long_layout = QHBoxLayout()
        long_label = QLabel("Longitude:")
        self.long_value = QLabel("0.0")
        style_value_label(self.long_value)
        long_slider = QSlider(Qt.Horizontal)
        long_slider.setMinimum(0)
        long_slider.setMaximum(360)
        long_slider.setValue(0)
        long_slider.setFixedWidth(250)
        long_slider.valueChanged.connect(lambda value: self.long_value.setText(f"{value:.1f}"))
        long_layout.addWidget(long_label)
        long_layout.addWidget(self.long_value)
        long_layout.addWidget(long_slider)

        # Transformer Temperature
        ext_temp_layout = QHBoxLayout()
        ext_temp_label = QLabel("Transformer Temp:")
        self.transformer_temp_value = QLabel("25.0")
        style_value_label(self.transformer_temp_value)
        ext_temp_slider = QSlider(Qt.Horizontal)
        ext_temp_slider.setMinimum(-40)
        ext_temp_slider.setMaximum(85)
        ext_temp_slider.setValue(25)
        ext_temp_slider.setFixedWidth(250)
        ext_temp_slider.valueChanged.connect(lambda value: self.transformer_temp_value.setText(f"{value:.1f} °C"))
        ext_temp_layout.addWidget(ext_temp_label)
        ext_temp_layout.addWidget(self.transformer_temp_value)
        ext_temp_layout.addWidget(ext_temp_slider)

        # Device Temperature
        dev_temp_layout = QHBoxLayout()
        dev_temp_label = QLabel("Device Temp:")
        self.Device_Temp_value = QLabel("10.0")
        style_value_label(self.Device_Temp_value)
        dev_temp_slider = QSlider(Qt.Horizontal)
        dev_temp_slider.setMinimum(0)
        dev_temp_slider.setMaximum(80)
        dev_temp_slider.setValue(10)
        dev_temp_slider.setFixedWidth(250)
        dev_temp_slider.valueChanged.connect(lambda value: self.Device_Temp_value.setText(f"{value:.1f}"))
        dev_temp_layout.addWidget(dev_temp_label)
        dev_temp_layout.addWidget(self.Device_Temp_value)
        dev_temp_layout.addWidget(dev_temp_slider)

        # Battery Voltage
        batt_volt_layout = QHBoxLayout()
        batt_volt_label = QLabel("Battery Voltage:")
        self.batt_volt_value = QLabel("12.0")
        style_value_label(self.batt_volt_value)
        batt_volt_slider = QSlider(Qt.Horizontal)
        batt_volt_slider.setMinimum(10)
        batt_volt_slider.setMaximum(15)
        batt_volt_slider.setValue(12)
        batt_volt_slider.setFixedWidth(250)
        batt_volt_slider.valueChanged.connect(lambda value: self.batt_volt_value.setText(f"{value:.1f} V"))
        batt_volt_layout.addWidget(batt_volt_label)
        batt_volt_layout.addWidget(self.batt_volt_value)
        batt_volt_layout.addWidget(batt_volt_slider)
        
        # Solar Voltage
        solar_volt_layout = QHBoxLayout()
        solar_volt_label = QLabel("Solar Voltage:")
        self.solar_volt_value = QLabel("12.0")
        style_value_label(self.solar_volt_value)
        solar_volt_slider = QSlider(Qt.Horizontal)
        solar_volt_slider.setMinimum(10)
        solar_volt_slider.setMaximum(15)
        solar_volt_slider.setValue(12)
        solar_volt_slider.setFixedWidth(250)
        solar_volt_slider.valueChanged.connect(lambda value: self.solar_volt_value.setText(f"{value:.1f} V"))
        solar_volt_layout.addWidget(solar_volt_label)
        solar_volt_layout.addWidget(self.solar_volt_value)
        solar_volt_layout.addWidget(solar_volt_slider)

        # Door Status (for example, taking the whole width or adding to a specific column)
        door_status_layout = QHBoxLayout()
        door_status_label = QLabel("Door Status:")
        self.door_status_value = QLabel("CLOSED")
        style_value_label(self.door_status_value)
        door_status_layout.addWidget(door_status_label)
        door_status_layout.addWidget(self.door_status_value)

        # --- Arrange these layouts in a grid ---
        grid_layout = QGridLayout()

        grid_layout.addLayout(V_red_layout, 0, 0)
        grid_layout.addLayout(Internal_Rogw_Curr_red_layout, 0, 1)
        
        grid_layout.addLayout(V_yellow_layout, 1, 0)
        grid_layout.addLayout(Internal_Rogw_Curr_yellow_layout, 1, 1)
        
        grid_layout.addLayout(V_blue_layout, 2, 0)
        grid_layout.addLayout(Internal_Rogw_Curr_blue_layout, 2, 1)
        
        grid_layout.addLayout(External_Rogw_Curr_red_layout, 3, 0)
        grid_layout.addLayout(External_Rogw_Curr_yellow_layout, 3, 1)
        
        grid_layout.addLayout(External_Rogw_Curr_blue_layout, 4, 0)
        grid_layout.addLayout(door_status_layout, 4, 1)
        
        grid_layout.addLayout(dev_temp_layout, 5, 0)
        grid_layout.addLayout(ext_temp_layout, 5, 1)
        
        
        grid_layout.addLayout(batt_volt_layout, 6, 1)
        grid_layout.addLayout(solar_volt_layout, 6, 0)
        
        grid_layout.addLayout(lat_layout, 7, 0)
        grid_layout.addLayout(long_layout, 7, 1)
        
        # You can span the door status across both columns if desired
        # grid_layout.addLayout(door_status_layout, 8, 0, 1, 2)

        # Finally, add the grid layout to the main layout
        layout.addLayout(grid_layout)

    def add_busbar_specific_fields(self, layout):
        """Add additional fields for Gateway description."""
        def style_value_label(label, color="green"):
            """Style the value label with color and bounding rectangle."""
            label.setStyleSheet(
                """
                QLabel {
                    background-color: {color}; 
                    border: 1px solid #ccc; 
                    border-radius: 4px; 
                    padding: 4px;
                    color: #333;
                    font-weight: bold;
                }
                """
            )

        # Latitude
        lat_layout = QHBoxLayout()
        lat_label = QLabel("Latitude:")
        self.lat_value = QLabel("0.0")
        style_value_label(self.lat_value)
        lat_slider = QSlider(Qt.Horizontal)
        lat_slider.setMinimum(-90)
        lat_slider.setMaximum(90)
        lat_slider.setValue(0)
        lat_slider.setFixedWidth(250)
        lat_slider.valueChanged.connect(lambda value: self.lat_value.setText(f"{value:.1f}"))
        lat_layout.addWidget(lat_label)
        lat_layout.addWidget(self.lat_value)
        lat_layout.addWidget(lat_slider)
        layout.addLayout(lat_layout)

        # Longitude
        long_layout = QHBoxLayout()
        long_label = QLabel("Longitude:")
        self.long_value = QLabel("0.0")
        style_value_label(self.long_value)
        long_slider = QSlider(Qt.Horizontal)
        long_slider.setMinimum(-180)
        long_slider.setMaximum(180)
        long_slider.setValue(0)
        long_slider.setFixedWidth(250)
        long_slider.valueChanged.connect(lambda value: self.long_value.setText(f"{value:.1f}"))
        long_layout.addWidget(long_label)
        long_layout.addWidget(self.long_value)
        long_layout.addWidget(long_slider)
        layout.addLayout(long_layout)

        # Device_Temp
        dev_temp_layout = QHBoxLayout()
        dev_temp_label = QLabel("Device Temp:")
        self.Device_Temp_value = QLabel("10.0")
        style_value_label(self.Device_Temp_value)
        dev_temp_slider = QSlider(Qt.Horizontal)
        dev_temp_slider.setMinimum(0)
        dev_temp_slider.setMaximum(80)
        dev_temp_slider.setValue(10)
        dev_temp_slider.setFixedWidth(250)
        dev_temp_slider.valueChanged.connect(lambda value: self.Device_Temp_value.setText(f"{value:.1f}"))
        dev_temp_layout.addWidget(dev_temp_label)
        dev_temp_layout.addWidget(self.Device_Temp_value)
        dev_temp_layout.addWidget(dev_temp_slider)
        layout.addLayout(dev_temp_layout)
        
    def style_value_label(label, color="green"):
        """Style the value label with color and bounding rectangle."""
        label.setStyleSheet(
            """
            QLabel {
                background-color: {color}; 
                border: 1px solid #ccc; 
                border-radius: 4px; 
                padding: 4px;
                color: #333;
                font-weight: bold;
            }
            """
        )

    def create_field_with_slider(self, value_label, slider):
        """Helper function to combine value label and slider into one widget."""
        field_layout = QHBoxLayout()
        field_layout.addWidget(value_label)
        field_layout.addWidget(slider)
        field_widget = QWidget()
        field_widget.setLayout(field_layout)
        return field_widget
