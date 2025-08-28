# --- START OF FILE esp32_config_tool/ui/servo_tab.py ---
from PyQt5.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QGridLayout, QLabel, QLineEdit,
                             QPushButton, QGroupBox, QMessageBox, QSlider, QSizePolicy, QScrollArea)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt, QTimer
import json


class ServoControlWidget(QGroupBox):

    def __init__(self, title, servo_id_str, serial_handler_ref, config_values_ref, parent_tab_widget=None):
        super().__init__(title, parent_tab_widget)
        self.servo_id_str = servo_id_str
        self.serial_handler = serial_handler_ref
        self.config_values = config_values_ref
        self.parent_tab_widget = parent_tab_widget
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        self.setMaximumHeight(300)
        layout = QVBoxLayout(self)
        current_angle_layout = QHBoxLayout()
        current_angle_layout.addWidget(QLabel("Current Angle:"))
        self.current_angle_display = QLabel("N/A")
        self.get_servo_angle_button = QPushButton("Get")
        self.get_servo_angle_button.setToolTip("Request current servo angles from ESP32")
        self.get_servo_angle_button.clicked.connect(self.request_current_angle)
        current_angle_layout.addWidget(self.current_angle_display)
        current_angle_layout.addWidget(self.get_servo_angle_button)
        current_angle_layout.addStretch()
        layout.addLayout(current_angle_layout)
        target_angle_layout = QHBoxLayout()
        target_angle_layout.addWidget(QLabel("Target Angle:"))
        self.target_angle_input = QLineEdit()
        self.target_angle_input.setPlaceholderText("0-180")
        self.target_angle_input.setFixedWidth(60)
        self.go_to_angle_button = QPushButton("Go")
        self.go_to_angle_button.clicked.connect(self.send_target_angle_from_input)
        target_angle_layout.addWidget(self.target_angle_input)
        target_angle_layout.addWidget(self.go_to_angle_button)
        target_angle_layout.addStretch()
        layout.addLayout(target_angle_layout)
        self.angle_slider = QSlider(Qt.Horizontal)
        self.angle_slider.setRange(0, 180); self.angle_slider.setValue(90)
        self.angle_slider.setTickInterval(15); self.angle_slider.setTickPosition(QSlider.TicksBelow)
        self.angle_slider.valueChanged.connect(self.slider_value_changed_display_only)
        self.angle_slider.sliderReleased.connect(self.send_target_angle_from_slider)
        layout.addWidget(self.angle_slider)
        jog_layout = QHBoxLayout()
        jog_layout.addWidget(QLabel("Jog Step:"))
        self.jog_minus_button = QPushButton("-"); self.jog_minus_button.setFixedWidth(40)
        self.jog_minus_button.clicked.connect(lambda: self.jog_servo(False))
        self.jog_plus_button = QPushButton("+"); self.jog_plus_button.setFixedWidth(40)
        self.jog_plus_button.clicked.connect(lambda: self.jog_servo(True))
        jog_layout.addStretch(); jog_layout.addWidget(self.jog_minus_button)
        jog_layout.addWidget(self.jog_plus_button); jog_layout.addStretch()
        layout.addLayout(jog_layout); layout.addStretch()
    def send_target_angle_from_input(self):
        try:
            angle = int(self.target_angle_input.text())
            if 0 <= angle <= 180: self.send_servo_command(angle); self.angle_slider.setValue(angle)
            else: QMessageBox.warning(self, "Input Error", "Angle must be 0-180.")
        except ValueError: QMessageBox.warning(self, "Input Error", "Invalid angle.")
    def slider_value_changed_display_only(self, value): self.target_angle_input.setText(str(value))
    def send_target_angle_from_slider(self): self.send_servo_command(self.angle_slider.value())
    def jog_servo(self, positive):
        try:
            current_val_str = self.target_angle_input.text()
            if not current_val_str or current_val_str == "N/A":
                current_val_str = self.current_angle_display.text()
                if current_val_str == "N/A": current_val_str = "90"
            current_angle = int(current_val_str)
            increment = int(self.config_values.get("MANUAL_JOG_SERVO_INCREMENT", 3))
            new_angle = min(180, current_angle + increment) if positive else max(0, current_angle - increment)
            self.target_angle_input.setText(str(new_angle)); self.angle_slider.setValue(new_angle)
            self.send_servo_command(new_angle)
        except ValueError: self.target_angle_input.setText("90"); self.angle_slider.setValue(90)
    def send_servo_command(self, angle):
        command_prefix = "servorot" if self.servo_id_str == "rot" else "servogrip"
        self.serial_handler.send_command(f"{command_prefix} {angle}")
    def request_current_angle(self):
        if self.parent_tab_widget: self.parent_tab_widget.request_all_positions_from_tab()
    def update_current_angle_display(self, angle):
        self.current_angle_display.setText(str(angle))
        if not self.target_angle_input.hasFocus() and not self.angle_slider.isSliderDown():
             self.target_angle_input.setText(str(angle)); self.angle_slider.setValue(int(angle))


class ServoTabWidget(QWidget):
    def __init__(self, config_values_ref, serial_handler_ref, parent=None):
        super().__init__(parent)
        self.serial_handler = serial_handler_ref
        self.config_values = config_values_ref

        tab_overall_layout = QVBoxLayout(self)
        
        servo_controls_layout = QHBoxLayout()
        servo_controls_layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)

        self.rotation_servo_control = ServoControlWidget("Rotation Servo (servo1)", "rot",
                                                         self.serial_handler, self.config_values, self)
        servo_controls_layout.addWidget(self.rotation_servo_control)

        self.gripper_servo_control = ServoControlWidget("Gripper Servo (servo2)", "grip",
                                                        self.serial_handler, self.config_values, self)
        servo_controls_layout.addWidget(self.gripper_servo_control)
        servo_controls_layout.addStretch()
        tab_overall_layout.addLayout(servo_controls_layout)

        servo_config_group = QGroupBox("Servo Configuration Parameters")
        servo_config_layout = QGridLayout(servo_config_group)
        servo_config_group.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        
        self.config_fields = {}

        # --- CORRECTED HELPER FUNCTION ---
        def add_servo_config_row(layout, label_text, config_key, default_value, row_idx, servo_command_prefix=None):
            label = QLabel(label_text)
            line_edit = QLineEdit()
            line_edit.setText(str(self.config_values.get(config_key, default_value)))
            line_edit.setPlaceholderText(str(default_value))
            line_edit.setFixedWidth(70)
            layout.addWidget(label, row_idx, 0)
            layout.addWidget(line_edit, row_idx, 1)
            
            # Only add the "Go to" button if a servo_command_prefix is provided
            if servo_command_prefix:
                preset_button = QPushButton("Go to")
                preset_button.setToolTip(f"Move servo to the configured '{label_text}' angle")
                preset_button.clicked.connect(
                    lambda checked=False, key=config_key, cmd=servo_command_prefix: 
                    self.send_configured_preset_angle(key, cmd)
                )
                layout.addWidget(preset_button, row_idx, 2)
            
            self.config_fields[config_key] = line_edit
            return row_idx + 1

        row = 0
        row = add_servo_config_row(servo_config_layout, "Board Angle:", "GRIPPER_ROT_BOARD", 180, row, servo_command_prefix="servorot")
        row = add_servo_config_row(servo_config_layout, "Capture Angle:", "GRIPPER_ROT_CAPTURE", 62, row, servo_command_prefix="servorot")
        row = add_servo_config_row(servo_config_layout, "Gripper Open Angle:", "GripperOpen", 160, row, servo_command_prefix="servogrip")
        row = add_servo_config_row(servo_config_layout, "Gripper Close Angle:", "GripperClose", 50, row, servo_command_prefix="servogrip")
        row = add_servo_config_row(servo_config_layout, "Jog Increment (°):", "MANUAL_JOG_SERVO_INCREMENT", 3, row, servo_command_prefix=None) # <<< No button here

        tab_overall_layout.addWidget(servo_config_group)

        self.update_servo_configs_button = QPushButton("Update all servo configs")
        self.update_servo_configs_button.clicked.connect(self.update_all_servo_configs)
        tab_overall_layout.addWidget(self.update_servo_configs_button, 0, Qt.AlignLeft)
        
        tab_overall_layout.addStretch()

        self.load_fields_from_config()

        if self.serial_handler:
            self.serial_handler.data_received.connect(self.parse_esp32_response)
            self.angle_update_timer = QTimer(self)
            self.angle_update_timer.timeout.connect(self.request_all_positions_from_tab)
            self.serial_handler.connection_status_changed.connect(self.handle_connection_change_for_timer)


    def send_configured_preset_angle(self, config_key, command_prefix):
        try:
            angle_str = self.config_fields[config_key].text()
            angle = int(angle_str)
            if 0 <= angle <= 180:
                self.serial_handler.send_command(f"{command_prefix} {angle}")
                if "rot" in command_prefix:
                    self.rotation_servo_control.target_angle_input.setText(str(angle))
                    self.rotation_servo_control.angle_slider.setValue(angle)
                else:
                    self.gripper_servo_control.target_angle_input.setText(str(angle))
                    self.gripper_servo_control.angle_slider.setValue(angle)
            else:
                QMessageBox.warning(self, "Preset Error", f"Angle for {config_key} is out of range.")
        except (ValueError, KeyError) as e:
            QMessageBox.warning(self, "Preset Error", f"Cannot send preset for {config_key}: {e}")

    def load_fields_from_config(self):
        print("ServoTab: Loading fields from config.")
        for key, line_edit_widget in self.config_fields.items():
            default_val = self.config_values.get(key, 0)
            line_edit_widget.setText(str(self.config_values.get(key, default_val)))
        print("ServoTab: Fields reloaded.")

    def update_all_servo_configs(self):
        try:
            for key, line_edit_widget in self.config_fields.items():
                value = int(line_edit_widget.text())
                self.config_values[key] = value
                esp32_key = key.lower()
                self.serial_handler.send_command(f"setconfig {esp32_key} {value}")
            QMessageBox.information(self, "Success", "Servo configs updated .")
        except ValueError:
            QMessageBox.warning(self, "Input Error", "Invalid number in a config field.")
        self.load_fields_from_config()

    def handle_connection_change_for_timer(self, connected, port_name):
        if connected:
            self.angle_update_timer.start(2500)
            self.request_all_positions_from_tab()
        else:
            self.angle_update_timer.stop()
            self.rotation_servo_control.update_current_angle_display("N/A")
            self.gripper_servo_control.update_current_angle_display("N/A")

    def request_all_positions_from_tab(self):
        if self.serial_handler.is_connected():
            self.serial_handler.send_command("getallpos")

    def parse_esp32_response(self, line):
        return
        if line.startswith("POS:"):
            try:
                json_data = json.loads(line[4:])
                if "rotServo" in json_data: self.rotation_servo_control.update_current_angle_display(json_data["rotServo"])
                if "gripServo" in json_data: self.gripper_servo_control.update_current_angle_display(json_data["gripServo"])
            except (json.JSONDecodeError, ValueError) as e: print(f"ServoTab: Error parsing POS JSON: {line} - {e}")