# --- START OF FILE esp32_config_tool/ui/stepper_tab.py ---
from PyQt5.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QGridLayout, QLabel, QLineEdit,
                             QPushButton, QGroupBox, QMessageBox, QSizePolicy, QScrollArea)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt, QTimer
import json

class StepperControlWidget(QGroupBox):
    def __init__(self, title, stepper_id_str, serial_handler_ref, config_values_ref, parent_tab_widget=None):
        super().__init__(title, parent_tab_widget)
        self.stepper_id_str = stepper_id_str 
        self.serial_handler = serial_handler_ref
        self.config_values = config_values_ref
        self.parent_tab_widget = parent_tab_widget # To call request_all_positions

        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        layout = QVBoxLayout(self)

        # Current Position Display
        current_pos_layout = QHBoxLayout()
        self.current_pos_label = QLabel("Current Position:")
        self.current_pos_display = QLabel("N/A")
        self.get_pos_button = QPushButton("Get Pos")
        self.get_pos_button.clicked.connect(self.request_specific_position)
        current_pos_layout.addWidget(self.current_pos_label)
        current_pos_layout.addWidget(self.current_pos_display)
        current_pos_layout.addWidget(self.get_pos_button)
        current_pos_layout.addStretch()
        layout.addLayout(current_pos_layout)

        # Target Position Input
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

        # Jog Buttons
        jog_layout = QHBoxLayout()
        self.jog_minus_button = QPushButton("Jog -")
        self.jog_minus_button.pressed.connect(lambda: self.start_jog(False))
        self.jog_minus_button.released.connect(self.stop_jog)
        self.jog_plus_button = QPushButton("Jog +")
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
        self.config_values = config_values_ref # Global CONFIG_VALUES dictionary

        # Main layout for the tab itself, holds the scroll area
        tab_overall_layout = QVBoxLayout(self)
        
        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        main_widget_for_scroll = QWidget() 
        main_layout = QVBoxLayout(main_widget_for_scroll) 
        scroll_area.setWidget(main_widget_for_scroll)
        tab_overall_layout.addWidget(scroll_area)


        # --- Individual Stepper Controls ---
        individual_steppers_group = QGroupBox("Individual Stepper Control & Calibration")
        individual_steppers_layout = QHBoxLayout(individual_steppers_group)
        individual_steppers_layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)

        self.capture_stepper_control = StepperControlWidget("Capture Stepper", "capt",
                                                            self.serial_handler, self.config_values, self)
        individual_steppers_layout.addWidget(self.capture_stepper_control)

        self.cart_stepper_control = StepperControlWidget("Cart Stepper", "cart",
                                                         self.serial_handler, self.config_values, self)
        individual_steppers_layout.addWidget(self.cart_stepper_control)

        self.orb_stepper_control = StepperControlWidget("Orb Stepper", "orb",
                                                        self.serial_handler, self.config_values, self)
        individual_steppers_layout.addWidget(self.orb_stepper_control)
        individual_steppers_layout.addStretch()
        main_layout.addWidget(individual_steppers_group) 

        # --- Shared Stepper Configuration ---
        shared_config_group = QGroupBox("Global Stepper Parameters")
        shared_config_layout = QGridLayout(shared_config_group)

        self.config_fields = {} # To store references to QLineEdit widgets

        # Helper to add a config row
        def add_config_row(layout, label_text, config_key, default_value, row_idx):
            label = QLabel(label_text)
            line_edit = QLineEdit()
            line_edit.setText(str(self.config_values.get(config_key, default_value)))
            line_edit.setPlaceholderText(str(default_value))
            layout.addWidget(label, row_idx, 0)
            layout.addWidget(line_edit, row_idx, 1)
            self.config_fields[config_key] = line_edit
            return row_idx + 1

        row = 0
        row = add_config_row(shared_config_layout, "Default Max Speed:", "STEPPER_SPEED", 4000, row)
        row = add_config_row(shared_config_layout, "Default Acceleration:", "STEPPER_ACCEL", 5000, row)
        main_layout.addWidget(shared_config_group)

        # --- Homing Configuration ---
        homing_config_group = QGroupBox("Homing Parameters")
        homing_config_layout = QGridLayout(homing_config_group)
        row = 0
        row = add_config_row(homing_config_layout, "Homing Speed (Capture):", "HOMING_SPEED_CAPTURE", 1000, row)
        row = add_config_row(homing_config_layout, "Homing Speed (Cart/Orb):", "HOMING_SPEED_CART_ORB", 1000, row)
        row = add_config_row(homing_config_layout, "Homing Acceleration:", "HOMING_ACCEL", 1500, row)
        main_layout.addWidget(homing_config_group)

        # --- Manual Jog Speed Configuration ---
        jog_config_group = QGroupBox("Manual Jog Speeds (for ESP32 firmware)")
        jog_config_layout = QGridLayout(jog_config_group)
        row = 0
        row = add_config_row(jog_config_layout, "Jog Speed (Cart):", "MANUAL_JOG_CART_SPEED", 1500, row)
        row = add_config_row(jog_config_layout, "Jog Speed (Orb):", "MANUAL_JOG_ORB_SPEED", 1000, row)
        row = add_config_row(jog_config_layout, "Jog Speed (Capture):", "MANUAL_JOG_CAPTURE_SPEED", 800, row)
        main_layout.addWidget(jog_config_group)

        # --- Update Button for all Configs on this Tab ---
        self.update_stepper_configs_button = QPushButton("Update All Stepper Configs in App")
        self.update_stepper_configs_button.clicked.connect(self.update_all_stepper_configs_in_app)
        main_layout.addWidget(self.update_stepper_configs_button)

        main_layout.addStretch() 

        if self.serial_handler:
            self.serial_handler.data_received.connect(self.parse_esp32_response)
            self.pos_update_timer = QTimer(self)
            self.pos_update_timer.timeout.connect(self.request_all_positions)
            if self.serial_handler.is_connected():
                 self.pos_update_timer.start(2000)
            self.serial_handler.connection_status_changed.connect(self.handle_connection_change_for_timer)

    def load_config_fields(self): # This method should already exist and be correct
        print("StepperTab: Loading fields from config.")
        for key, line_edit_widget in self.config_fields.items():
            print(key)
            # Use get with a default from DEFAULT_CONFIG_VALUES if key might be missing after a bad parse
            default_val = self.config_values.get(key, "") # Get from config_parser's defaults
            line_edit_widget.setText(str(self.config_values.get(key, default_val)))
        print("StepperTab: Fields reloaded.")

    def update_all_stepper_configs_in_app(self):
        try:
            for key, line_edit_widget in self.config_fields.items():
                # Assume all these config values are integers for now
                self.config_values[key] = int(line_edit_widget.text())
            QMessageBox.information(self, "Success", "Stepper config parameters updated in app memory.")
        except ValueError:
            QMessageBox.warning(self, "Input Error", "Invalid number in one of the config fields.")
        # self.load_config_fields() # No need to reload if directly updating from current text

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
                stepper_id_resp = parts[1]
                try:
                    pos = int(parts[2])
                    if stepper_id_resp == self.capture_stepper_control.stepper_id_str:
                        self.capture_stepper_control.update_current_position_display(pos)
                    elif stepper_id_resp == self.cart_stepper_control.stepper_id_str:
                        self.cart_stepper_control.update_current_position_display(pos)
                    elif stepper_id_resp == self.orb_stepper_control.stepper_id_str:
                        self.orb_stepper_control.update_current_position_display(pos)
                except ValueError: print(f"StepperTab: Error parsing SPOS position: {line}")
        elif line.startswith("ACK:") and "sethome" in line and "position set to 0" in line:
            # After a sethome command, the ESP32 sends an ACK.
            # We should re-request positions to update the display.
            self.request_all_positions()