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
        main_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)

        # --- Direct Control Group ---
        control_group = QGroupBox("Direct Linear Actuator Control")
        control_group.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        control_layout = QGridLayout(control_group)

        # Timed action buttons
        self.extend_button = QPushButton("Extend (Timed)")
        self.extend_button.setToolTip("Extend for the configured travel time.")
        self.extend_button.clicked.connect(lambda: self.serial_handler.send_command("la_ext"))
        control_layout.addWidget(self.extend_button, 0, 0)

        self.retract_button = QPushButton("Retract (Timed + Sensor)")
        self.retract_button.setToolTip("Retract for the configured travel time, stopping early if sensor is triggered.")
        self.retract_button.clicked.connect(lambda: self.serial_handler.send_command("la_ret"))
        control_layout.addWidget(self.retract_button, 0, 1)

        self.stop_button = QPushButton("Stop Actuator")
        self.stop_button.setToolTip("Immediately stop any actuator movement.")
        self.stop_button.clicked.connect(lambda: self.serial_handler.send_command("la_stop"))
        control_layout.addWidget(self.stop_button, 0, 2)
        
        # Continuous Jog buttons
        jog_label = QLabel("<b>Jog (Hold):</b>")
        control_layout.addWidget(jog_label, 1, 0)
        
        self.jog_extend_button = QPushButton("Extend (+)")
        self.jog_extend_button.pressed.connect(lambda: self.start_jog(True))
        self.jog_extend_button.released.connect(self.stop_jog)
        control_layout.addWidget(self.jog_extend_button, 1, 1)

        self.jog_retract_button = QPushButton("Retract (-)")
        self.jog_retract_button.pressed.connect(lambda: self.start_jog(False))
        self.jog_retract_button.released.connect(self.stop_jog)
        control_layout.addWidget(self.jog_retract_button, 1, 2)

        main_layout.addWidget(control_group)

        # --- Sensor Status Display ---
        sensor_group = QGroupBox("Sensor Status")
        sensor_layout = QHBoxLayout(sensor_group)
        sensor_group.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)

        sensor_layout.addWidget(QLabel("Retracted Sensor (Pin 13):"))
        self.retracted_sensor_display = QLabel("N/A")
        self.retracted_sensor_display.setFont(QFont("Arial", 10, QFont.Bold))
        sensor_layout.addWidget(self.retracted_sensor_display)
        
        self.get_sensor_status_button = QPushButton("Get Status Now")
        self.get_sensor_status_button.clicked.connect(self.request_all_statuses)
        sensor_layout.addWidget(self.get_sensor_status_button)
        sensor_layout.addStretch()
        main_layout.addWidget(sensor_group)

        # --- Configuration Group ---
        config_group = QGroupBox("Configuration")
        config_layout = QGridLayout(config_group)
        config_group.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)

        self.travel_time_label = QLabel("Full Travel Time (ms):")
        self.travel_time_input = QLineEdit()
        self.travel_time_input.setPlaceholderText("e.g., 650")
        self.travel_time_input.setFixedWidth(80)
        config_layout.addWidget(self.travel_time_label, 0, 0)
        config_layout.addWidget(self.travel_time_input, 0, 1)

        self.update_config_button = QPushButton("Update Config")
        self.update_config_button.clicked.connect(self.update_actuator_config)
        config_layout.addWidget(self.update_config_button, 1, 0, 1, 2) # Span 2 columns
        main_layout.addWidget(config_group)
        
        main_layout.addStretch() # Push all groups to the top

        self.load_fields_from_config()

        if self.serial_handler:
            self.serial_handler.data_received.connect(self.parse_esp32_response)
            self.status_update_timer = QTimer(self)
            self.status_update_timer.timeout.connect(self.request_all_statuses)
            self.serial_handler.connection_status_changed.connect(self.handle_connection_change_for_timer)

    def load_fields_from_config(self):
        print("ActuatorTab: Loading fields from config.")
        self.travel_time_input.setText(str(self.config_values.get("ACTUATOR_TRAVEL_TIME_MS", 650)))

    def update_actuator_config(self):
        try:
            travel_time = int(self.travel_time_input.text())
            if travel_time > 0:
                # Update Python dictionary
                self.config_values["ACTUATOR_TRAVEL_TIME_MS"] = travel_time
                # Send update to ESP32
                self.serial_handler.send_command(f"setconfig actuator_travel_time_ms {travel_time}")
                QMessageBox.information(self, "Success", "Actuator travel time updated .")
            else:
                QMessageBox.warning(self, "Input Error", "Travel time must be a positive number.")
        except ValueError:
            QMessageBox.warning(self, "Input Error", "Invalid number for travel time.")
        self.load_fields_from_config() # Refresh display to show stored value

    def start_jog(self, is_extending):
        command = "la_ext" if is_extending else "la_ret_nosensor" 
        self.serial_handler.send_command(command)
        
    def stop_jog(self):
        self.serial_handler.send_command("la_stop")

    def request_all_statuses(self):
        if self.serial_handler.is_connected():
            self.serial_handler.send_command("getallpos") 

    def handle_connection_change_for_timer(self, connected, port_name):
        if connected:
            self.status_update_timer.start(3000)
            self.request_all_statuses() # Get initial status
        else:
            self.status_update_timer.stop()
            self.retracted_sensor_display.setText("N/A")
            self.retracted_sensor_display.setStyleSheet("") # Reset color

    def parse_esp32_response(self, line):
        if line.startswith("POS:"):
            try:
                json_data = json.loads(line[4:])
                if "actuatorSensor" in json_data:
                    sensor_state = json_data["actuatorSensor"]
                    if sensor_state == 1: 
                        self.retracted_sensor_display.setText("RETRACTED")
                        self.retracted_sensor_display.setStyleSheet("color: green; font-weight: bold;")
                    else:
                        self.retracted_sensor_display.setText("NOT RETRACTED")
                        self.retracted_sensor_display.setStyleSheet("color: orange; font-weight: bold;")
            except json.JSONDecodeError:
                print(f"ActuatorTab: Error decoding POS JSON: {line}")
        elif line.startswith("ACK:"):
            if "Actuator" in line:
                self.request_all_statuses() 