# --- START OF FILE esp32_config_tool/ui/stepper_tab.py ---
from PyQt5.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QGridLayout, QLabel, QLineEdit,
                             QPushButton, QGroupBox, QMessageBox, QSizePolicy, QScrollArea)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt, QTimer
import json
# Import the defaults to use them safely
from utils.config_parser import DEFAULT_CONFIG_VALUES

class StepperControlWidget(QGroupBox):
    # This class from the previous answer is correct and needs no changes.
    def __init__(self, title, stepper_id_str, serial_handler_ref, config_values_ref, parent_tab_widget=None):
        super().__init__(title, parent_tab_widget)
        self.stepper_id_str = stepper_id_str
        self.serial_handler = serial_handler_ref
        self.config_values = config_values_ref
        self.parent_tab_widget = parent_tab_widget
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        layout = QVBoxLayout(self)
        current_pos_layout = QHBoxLayout()
        current_pos_layout.addWidget(QLabel("Current Position:"))
        self.current_pos_display = QLabel("N/A")
        self.get_pos_button = QPushButton("Get")
        self.get_pos_button.setToolTip("Request current position from ESP32")
        self.get_pos_button.clicked.connect(self.request_specific_position)
        current_pos_layout.addWidget(self.current_pos_display)
        current_pos_layout.addWidget(self.get_pos_button)
        current_pos_layout.addStretch()
        layout.addLayout(current_pos_layout)
        target_pos_layout = QHBoxLayout()
        target_pos_layout.addWidget(QLabel("Target Position:"))
        self.target_pos_input = QLineEdit()
        self.target_pos_input.setPlaceholderText("e.g., 1200")
        self.target_pos_input.setFixedWidth(80)
        self.go_to_pos_button = QPushButton("Go")
        self.go_to_pos_button.clicked.connect(self.send_target_position)
        target_pos_layout.addWidget(self.target_pos_input)
        target_pos_layout.addWidget(self.go_to_pos_button)
        target_pos_layout.addStretch()
        layout.addLayout(target_pos_layout)
        jog_layout = QHBoxLayout()
        jog_layout.addWidget(QLabel("Jog (Hold):"))
        self.jog_minus_button = QPushButton("-")
        self.jog_minus_button.pressed.connect(lambda: self.start_jog(False))
        self.jog_minus_button.released.connect(self.stop_jog)
        self.jog_plus_button = QPushButton("+")
        self.jog_plus_button.pressed.connect(lambda: self.start_jog(True))
        self.jog_plus_button.released.connect(self.stop_jog)
        jog_layout.addStretch()
        jog_layout.addWidget(self.jog_minus_button)
        jog_layout.addWidget(self.jog_plus_button)
        jog_layout.addStretch()
        layout.addLayout(jog_layout)
        self.set_home_button = QPushButton("Set Current as 0 (Home)")
        self.set_home_button.clicked.connect(self.send_set_home)
        layout.addWidget(self.set_home_button)
        layout.addStretch()
    def request_specific_position(self):
        self.serial_handler.send_command(f"getpos {self.stepper_id_str}")
    def send_target_position(self):
        try:
            pos = int(self.target_pos_input.text())
            self.serial_handler.send_command(f"goto{self.stepper_id_str} {pos}")
        except ValueError:
            QMessageBox.warning(self, "Input Error", "Invalid position. Please enter a number.")
    def start_jog(self, positive):
        direction = 1 if positive else 0
        self.serial_handler.send_command(f"jog {self.stepper_id_str} {direction}")
    def stop_jog(self):
        self.serial_handler.send_command(f"jogstop")
    def send_set_home(self):
        reply = QMessageBox.question(self, "Confirm Set Home",
                                     f"Are you sure you want to set the current position of {self.title()} as 0 (Home)?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.serial_handler.send_command(f"sethome {self.stepper_id_str}")
    def update_current_position_display(self, position):
        self.current_pos_display.setText(str(position))


class StepperTabWidget(QWidget):
    def __init__(self, config_values_ref, serial_handler_ref, parent=None):
        super().__init__(parent)
        self.serial_handler = serial_handler_ref
        self.config_values = config_values_ref

        tab_overall_layout = QVBoxLayout(self)
        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        main_widget_for_scroll = QWidget()
        main_layout = QVBoxLayout(main_widget_for_scroll)
        scroll_area.setWidget(main_widget_for_scroll)
        tab_overall_layout.addWidget(scroll_area)

        individual_steppers_group = QGroupBox("Individual Stepper Control & Calibration")
        individual_steppers_layout = QHBoxLayout(individual_steppers_group)
        individual_steppers_layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.capture_stepper_control = StepperControlWidget("Capture", "capt", self.serial_handler, self.config_values, self)
        self.cart_stepper_control = StepperControlWidget("Cart", "cart", self.serial_handler, self.config_values, self)
        self.orb_stepper_control = StepperControlWidget("Orb", "orb", self.serial_handler, self.config_values, self)
        individual_steppers_layout.addWidget(self.capture_stepper_control)
        individual_steppers_layout.addWidget(self.cart_stepper_control)
        individual_steppers_layout.addWidget(self.orb_stepper_control)
        individual_steppers_layout.addStretch()
        main_layout.addWidget(individual_steppers_group)

        config_group = QGroupBox("Stepper Configuration")
        config_layout = QHBoxLayout(config_group)
        self.config_fields = {}
        
        col1_layout = QGridLayout()
        row = 0
        row = self.add_config_row(col1_layout, "Default Max Speed:", "STEPPER_SPEED", row)
        row = self.add_config_row(col1_layout, "Default Acceleration:", "STEPPER_ACCEL", row)
        row = self.add_config_row(col1_layout, "Homing Speed (Capture):", "HOMING_SPEED_CAPTURE", row)
        row = self.add_config_row(col1_layout, "Homing Speed (Cart/Orb):", "HOMING_SPEED_CART_ORB", row)
        row = self.add_config_row(col1_layout, "Homing Acceleration:", "HOMING_ACCEL", row)
        config_layout.addLayout(col1_layout)

        col2_layout = QGridLayout()
        row = 0
        row = self.add_config_row(col2_layout, "Jog Speed (Cart):", "MANUAL_JOG_CART_SPEED", row)
        row = self.add_config_row(col2_layout, "Jog Speed (Orb):", "MANUAL_JOG_ORB_SPEED", row)
        row = self.add_config_row(col2_layout, "Jog Speed (Capture):", "MANUAL_JOG_CAPTURE_SPEED", row)
        col2_layout.addWidget(QLabel("--- Travel Limits ---"), row, 0, 1, 2)
        row += 1
        row = self.add_config_row(col2_layout, "Cart Min Pos:", "CART_MIN_POS", row)
        row = self.add_config_row(col2_layout, "Cart Max Pos:", "CART_MAX_POS", row)
        row = self.add_config_row(col2_layout, "Orb Min Pos:", "ORB_MIN_POS", row)
        row = self.add_config_row(col2_layout, "Orb Max Pos:", "ORB_MAX_POS", row)
        row = self.add_config_row(col2_layout, "Capture Min Pos:", "CAPTURE_MIN_POS", row)
        row = self.add_config_row(col2_layout, "Capture Max Pos:", "CAPTURE_MAX_POS", row)
        config_layout.addLayout(col2_layout)
        config_layout.addStretch()
        main_layout.addWidget(config_group)

        self.update_stepper_configs_button = QPushButton("Update All Stepper Configs (App & ESP32)")
        self.update_stepper_configs_button.clicked.connect(self.update_all_stepper_configs)
        main_layout.addWidget(self.update_stepper_configs_button, 0, Qt.AlignLeft)
        main_layout.addStretch()

        if self.serial_handler:
            self.serial_handler.data_received.connect(self.parse_esp32_response)
            self.pos_update_timer = QTimer(self)
            self.pos_update_timer.timeout.connect(self.request_all_positions)
            self.serial_handler.connection_status_changed.connect(self.handle_connection_change_for_timer)
            if self.serial_handler.is_connected():
                self.handle_connection_change_for_timer(True, "") # Manually trigger once if already connected


    def add_config_row(self, layout, label_text, config_key, row_idx):
        default_value = self.config_values.get(config_key, 0)
        label = QLabel(label_text)
        line_edit = QLineEdit(str(default_value))
        line_edit.setPlaceholderText(str(default_value))
        layout.addWidget(label, row_idx, 0)
        layout.addWidget(line_edit, row_idx, 1)
        self.config_fields[config_key] = line_edit
        return row_idx + 1

    def load_fields_from_config(self):
        print("StepperTab: Loading fields from config.")
        for key, line_edit_widget in self.config_fields.items():
            default_val = DEFAULT_CONFIG_VALUES.get(key, 0)
            line_edit_widget.setText(str(self.config_values.get(key, default_val)))
        print("StepperTab: Fields reloaded.")

    def update_all_stepper_configs(self):
        try:
            for key, line_edit_widget in self.config_fields.items():
                value = int(line_edit_widget.text())
                self.config_values[key] = value
                esp32_key = key.lower()
                self.serial_handler.send_command(f"setconfig {esp32_key} {value}")
            QMessageBox.information(self, "Success", "Stepper configs updated .")
        except ValueError:
            QMessageBox.warning(self, "Input Error", "Invalid number in one of the config fields.")
        self.load_fields_from_config()

    def handle_connection_change_for_timer(self, connected, port_name):
        if connected:
            self.pos_update_timer.start(2000)
            self.request_all_positions()
        else:
            self.pos_update_timer.stop()
            self.capture_stepper_control.update_current_position_display("N/A")
            self.cart_stepper_control.update_current_position_display("N/A")
            self.orb_stepper_control.update_current_position_display("N/A")

    def request_all_positions(self):
        if self.serial_handler.is_connected():
            self.serial_handler.send_command("getallpos")

    def parse_esp32_response(self, line):
        if line.startswith("POS:"):
            try:
                json_data = json.loads(line[4:])
                if "captPos" in json_data: self.capture_stepper_control.update_current_position_display(json_data["captPos"])
                if "cartPos" in json_data: self.cart_stepper_control.update_current_position_display(json_data["cartPos"])
                if "orbPos" in json_data: self.orb_stepper_control.update_current_position_display(json_data["orbPos"])
            except json.JSONDecodeError: print(f"StepperTab: Error POS JSON: {line}")
        elif line.startswith("SPOS:"):
            parts = line.split(" ")
            if len(parts) == 3:
                stepper_id_resp, pos_str = parts[1], parts[2]
                try:
                    pos = int(pos_str)
                    if stepper_id_resp == "capt": self.capture_stepper_control.update_current_position_display(pos)
                    elif stepper_id_resp == "cart": self.cart_stepper_control.update_current_position_display(pos)
                    elif stepper_id_resp == "orb": self.orb_stepper_control.update_current_position_display(pos)
                except ValueError: print(f"StepperTab: Error parsing SPOS position: {line}")
        elif line.startswith("ACK: sethome"):
            self.request_all_positions()