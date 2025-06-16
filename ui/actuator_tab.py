from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                             QPushButton, QGroupBox, QMessageBox, QSizePolicy, QGridLayout)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt, QTimer
import json

class ActuatorTabWidget(QWidget):
    def __init__(self, config_values_ref, serial_handler_ref, parent=None):
        super().__init__(parent)
        self.serial_handler = serial_handler_ref
        self.config_values = config_values_ref

        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft) # Align content to top-left

        # --- Direct Control Group ---
        control_group = QGroupBox("Direct Linear Actuator Control")
        control_layout = QHBoxLayout(control_group) # Use QHBoxLayout for buttons side-by-side
        control_group.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)


        self.extend_button = QPushButton("Extend (Timed)")
        self.extend_button.clicked.connect(lambda: self.serial_handler.send_command("la_ext"))
        control_layout.addWidget(self.extend_button)

        self.retract_button = QPushButton("Retract (Timed + Sensor)")
        self.retract_button.clicked.connect(lambda: self.serial_handler.send_command("la_ret"))
        control_layout.addWidget(self.retract_button)

        self.stop_button = QPushButton("Stop Actuator")
        self.stop_button.clicked.connect(lambda: self.serial_handler.send_command("la_stop"))
        control_layout.addWidget(self.stop_button)
        control_layout.addStretch()
        main_layout.addWidget(control_group)

        # --- Sensor Status Display ---
        sensor_group = QGroupBox("Sensor Status")
        sensor_layout = QHBoxLayout(sensor_group)
        sensor_group.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)

        sensor_layout.addWidget(QLabel("Retracted Sensor (Pin 13):"))
        self.retracted_sensor_display = QLabel("N/A")
        self.retracted_sensor_display.setFont(QFont("Arial", 10, QFont.Bold))
        sensor_layout.addWidget(self.retracted_sensor_display)
        self.get_sensor_status_button = QPushButton("Get Status") # Will trigger getallpos
        self.get_sensor_status_button.clicked.connect(self.request_all_statuses) # Reusing getallpos
        sensor_layout.addWidget(self.get_sensor_status_button)
        sensor_layout.addStretch()
        main_layout.addWidget(sensor_group)

        # --- Configuration Group ---
        config_group = QGroupBox("Configuration")
        config_layout = QGridLayout(config_group) # Use QGridLayout for neat label-input
        config_group.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)


        self.travel_time_label = QLabel("Full Travel Time (ms):")
        self.travel_time_input = QLineEdit()
        self.travel_time_input.setPlaceholderText("e.g., 650")
        self.travel_time_input.setFixedWidth(80)
        config_layout.addWidget(self.travel_time_label, 0, 0)
        config_layout.addWidget(self.travel_time_input, 0, 1)

        self.update_config_button = QPushButton("Update Travel Time in App")
        self.update_config_button.clicked.connect(self.update_actuator_config_in_app)
        config_layout.addWidget(self.update_config_button, 1, 0, 1, 2) # Span 2 columns
        main_layout.addWidget(config_group)
        
        main_layout.addStretch() # Push groups to top

        # Load initial values
        self.load_config_fields()

        if self.serial_handler:
            self.serial_handler.data_received.connect(self.parse_esp32_response)
            self.status_update_timer = QTimer(self)
            self.status_update_timer.timeout.connect(self.request_all_statuses)
            if self.serial_handler.is_connected():
                self.status_update_timer.start(3000) # Update sensor status every 3 seconds
            self.serial_handler.connection_status_changed.connect(self.handle_connection_change_for_timer)


    def load_config_fields(self):
        self.travel_time_input.setText(str(self.config_values.get("ACTUATOR_TRAVEL_TIME_MS", 650)))

    def update_actuator_config_in_app(self):
        try:
            travel_time = int(self.travel_time_input.text())
            if travel_time > 0:
                self.config_values["ACTUATOR_TRAVEL_TIME_MS"] = travel_time
                QMessageBox.information(self, "Success", "Actuator travel time updated in app memory.")
            else:
                QMessageBox.warning(self, "Input Error", "Travel time must be a positive number.")
        except ValueError:
            QMessageBox.warning(self, "Input Error", "Invalid number for travel time.")
        self.load_config_fields() # Refresh display

    def request_all_statuses(self): # This will trigger getallpos
        if self.serial_handler.is_connected():
            self.serial_handler.send_command("getallpos")

    def handle_connection_change_for_timer(self, connected, port_name):
        if connected:
            self.status_update_timer.start(3000)
            self.request_all_statuses() # Get initial status
        else:
            self.status_update_timer.stop()
            self.retracted_sensor_display.setText("N/A")

    def parse_esp32_response(self, line):
        if line.startswith("POS:"): # getallpos response
            try:
                json_data = json.loads(line[4:])
                if "actuatorSensor" in json_data:
                    sensor_state = json_data["actuatorSensor"]
                    # Assuming ESP32 sends 1 for HIGH (retracted) and 0 for LOW (not retracted)
                    # This matches your active HIGH sensor logic
                    if sensor_state == 1: # Active HIGH
                        self.retracted_sensor_display.setText("RETRACTED (HIGH)")
                        self.retracted_sensor_display.setStyleSheet("color: green;")
                    elif sensor_state == 0:
                        self.retracted_sensor_display.setText("EXTENDED/MOVING (LOW)")
                        self.retracted_sensor_display.setStyleSheet("color: orange;")
                    else:
                        self.retracted_sensor_display.setText("Unknown")
                        self.retracted_sensor_display.setStyleSheet("")

            except json.JSONDecodeError:
                print(f"ActuatorTab: Error decoding POS JSON: {line}")
        elif line.startswith("ACK:"): # Could be from la_ext, la_ret, la_stop
            # After an action, refresh sensor status
            if "Linear Actuator" in line:
                self.request_all_statuses()