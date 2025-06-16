# --- START OF FILE esp32_config_tool/ui/servo_tab.py ---
from PyQt5.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QGridLayout, QLabel, QLineEdit,
                             QPushButton, QGroupBox, QMessageBox, QSlider, QSizePolicy, QScrollArea)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt, QTimer
import json

class ServoControlWidget(QGroupBox):
    def __init__(self, title, servo_id_str, # "rot" or "grip"
                 serial_handler_ref, config_values_ref, parent_tab_widget=None):
        super().__init__(title, parent_tab_widget)
        self.servo_id_str = servo_id_str
        self.serial_handler = serial_handler_ref
        self.config_values = config_values_ref # For jog increment and preset values
        self.parent_tab_widget = parent_tab_widget

        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum) # Prevent vertical stretch
        self.setMaximumHeight(300) # Max height for the groupbox

        layout = QVBoxLayout(self)
        
        # Current Angle Display
        current_angle_layout = QHBoxLayout()
        self.current_angle_label = QLabel("Current Angle:")
        self.current_angle_display = QLabel("N/A")
        self.get_servo_angle_button = QPushButton("Get Angle")
        self.get_servo_angle_button.clicked.connect(self.request_current_angle)
        current_angle_layout.addWidget(self.current_angle_label)
        current_angle_layout.addWidget(self.current_angle_display)
        current_angle_layout.addWidget(self.get_servo_angle_button)
        current_angle_layout.addStretch()
        layout.addLayout(current_angle_layout)

        # Target Angle Input
        target_angle_layout = QHBoxLayout()
        target_angle_layout.addWidget(QLabel("Target Angle (0-180):"))
        self.target_angle_input = QLineEdit()
        self.target_angle_input.setPlaceholderText("0-180")
        self.target_angle_input.setFixedWidth(60)
        self.go_to_angle_button = QPushButton("Go")
        self.go_to_angle_button.clicked.connect(self.send_target_angle_from_input)
        target_angle_layout.addWidget(self.target_angle_input)
        target_angle_layout.addWidget(self.go_to_angle_button)
        target_angle_layout.addStretch()
        layout.addLayout(target_angle_layout)

        # Slider for Angle
        self.angle_slider = QSlider(Qt.Horizontal)
        self.angle_slider.setRange(0, 180)
        self.angle_slider.setValue(90) # Default slider position
        self.angle_slider.setTickInterval(15)
        self.angle_slider.setTickPosition(QSlider.TicksBelow)
        self.angle_slider.valueChanged.connect(self.slider_value_changed_display_only) # Update display only
        self.angle_slider.sliderReleased.connect(self.send_target_angle_from_slider) # Send on release
        layout.addWidget(self.angle_slider)
        
        # Jog Buttons
        jog_layout = QHBoxLayout()
        self.jog_minus_button = QPushButton("-")
        self.jog_minus_button.setFixedWidth(40)
        self.jog_minus_button.clicked.connect(lambda: self.jog_servo(False))
        self.jog_plus_button = QPushButton("+")
        self.jog_plus_button.setFixedWidth(40)
        self.jog_plus_button.clicked.connect(lambda: self.jog_servo(True))
        jog_layout.addStretch()
        jog_layout.addWidget(QLabel("Jog:"))
        jog_layout.addWidget(self.jog_minus_button)
        jog_layout.addWidget(self.jog_plus_button)
        jog_layout.addStretch()
        layout.addLayout(jog_layout)
        layout.addStretch() # Push content to top if presets aren't added below

    def send_target_angle_from_input(self):
        try:
            angle = int(self.target_angle_input.text())
            if 0 <= angle <= 180:
                self.send_servo_command(angle)
                self.angle_slider.setValue(angle) # Sync slider
            else:
                QMessageBox.warning(self, "Input Error", "Angle must be between 0 and 180.")
        except ValueError:
            QMessageBox.warning(self, "Input Error", "Invalid angle. Please enter a number.")

    def slider_value_changed_display_only(self, value):
        self.target_angle_input.setText(str(value))
        # Command is sent on sliderReleased

    def send_target_angle_from_slider(self):
        angle = self.angle_slider.value()
        self.send_servo_command(angle)

    def jog_servo(self, positive):
        try:
            current_val_str = self.target_angle_input.text()
            if not current_val_str or current_val_str == "N/A": # If empty or N/A
                current_val_str = self.current_angle_display.text()
                if current_val_str == "N/A": current_val_str = "90" # Default
            
            current_angle = int(current_val_str)
            increment = int(self.config_values.get("MANUAL_JOG_SERVO_INCREMENT", 3))
            
            if positive: new_angle = min(180, current_angle + increment)
            else: new_angle = max(0, current_angle - increment)
            
            self.target_angle_input.setText(str(new_angle))
            self.angle_slider.setValue(new_angle)
            self.send_servo_command(new_angle)
        except ValueError:
            self.target_angle_input.setText("90")
            self.angle_slider.setValue(90)

    def send_servo_command(self, angle):
        command_prefix = "servorot" if self.servo_id_str == "rot" else "servogrip"
        self.serial_handler.send_command(f"{command_prefix} {angle}")

    def request_current_angle(self):
        # ESP32 command: getallpos (which includes servo positions)
        if self.parent_tab_widget: # Check if parent_tab_widget is set
            self.parent_tab_widget.request_all_positions_from_tab()
        else: # Fallback if parent isn't directly accessible this way
            self.serial_handler.send_command("getallpos")


    def update_current_angle_display(self, angle):
        self.current_angle_display.setText(str(angle))
        # Update slider and input only if they don't have focus to avoid interrupting user typing
        if not self.target_angle_input.hasFocus() and not self.angle_slider.isSliderDown():
             self.target_angle_input.setText(str(angle))
             self.angle_slider.setValue(int(angle))


class ServoTabWidget(QWidget):
    def __init__(self, config_values_ref, serial_handler_ref, parent=None):
        super().__init__(parent)
        self.serial_handler = serial_handler_ref
        self.config_values = config_values_ref

        # Main layout for the tab itself, holds the scroll area
        tab_overall_layout = QVBoxLayout(self)
        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        main_widget_for_scroll = QWidget()
        main_layout = QVBoxLayout(main_widget_for_scroll)
        scroll_area.setWidget(main_widget_for_scroll)
        tab_overall_layout.addWidget(scroll_area)

        # --- Individual Servo Controls in a Horizontal Layout ---
        servo_controls_layout = QHBoxLayout()
        servo_controls_layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)

        self.rotation_servo_control = ServoControlWidget("Rotation Servo (servo1)", "rot",
                                                         self.serial_handler, self.config_values, self)
        servo_controls_layout.addWidget(self.rotation_servo_control)

        self.gripper_servo_control = ServoControlWidget("Gripper Servo (servo2)", "grip",
                                                        self.serial_handler, self.config_values, self)
        servo_controls_layout.addWidget(self.gripper_servo_control)
        servo_controls_layout.addStretch() # Push servo control boxes to the left
        main_layout.addLayout(servo_controls_layout)

        # --- Servo Configuration Parameters ---
        servo_config_group = QGroupBox("Servo Configuration Parameters")
        servo_config_layout = QGridLayout(servo_config_group)
        
        self.config_fields = {} # To store QLineEdit widgets for config values

        def add_servo_config_row(layout, label_text, config_key, default_value, row_idx):
            label = QLabel(label_text)
            line_edit = QLineEdit()
            line_edit.setText(str(self.config_values.get(config_key, default_value)))
            line_edit.setPlaceholderText(str(default_value))
            line_edit.setFixedWidth(70)
            layout.addWidget(label, row_idx, 0)
            layout.addWidget(line_edit, row_idx, 1)
            
            # Add a "Go to this preset" button
            preset_button = QPushButton(f"Go to {label_text.replace(':', '')}")
            # Determine which servo this config belongs to for the command
            servo_cmd_prefix = ""
            if "ROT" in config_key or "Board" in config_key or "Capture" in config_key and "GRIPPER" in config_key : # Heuristic
                servo_cmd_prefix = "servorot"
            elif "Grip" in config_key:
                servo_cmd_prefix = "servogrip"

            if servo_cmd_prefix:
                 preset_button.clicked.connect(
                     lambda checked=False, key=config_key, cmd_prefix=servo_cmd_prefix: 
                     self.send_configured_preset_angle(key, cmd_prefix)
                 )
            layout.addWidget(preset_button, row_idx, 2)
            self.config_fields[config_key] = line_edit
            return row_idx + 1

        row = 0
        # Rotation Servo Configs
        row = add_servo_config_row(servo_config_layout, "Gripper Board Angle:", "GRIPPER_ROT_BOARD", 180, row)
        row = add_servo_config_row(servo_config_layout, "Gripper Capture Angle:", "GRIPPER_ROT_CAPTURE", 62, row)
        # Gripper Servo Configs
        row = add_servo_config_row(servo_config_layout, "Gripper Open Angle:", "GripperOpen", 160, row)
        row = add_servo_config_row(servo_config_layout, "Gripper Close Angle:", "GripperClose", 50, row)


        main_layout.addWidget(servo_config_group)

        self.update_servo_configs_button = QPushButton("Update Servo Configs in App")
        self.update_servo_configs_button.clicked.connect(self.update_all_servo_configs_in_app)
        main_layout.addWidget(self.update_servo_configs_button)
        
        main_layout.addStretch() # Push content to top

        if self.serial_handler:
            self.serial_handler.data_received.connect(self.parse_esp32_response)
            # Optional: Timer to periodically get servo angles if ESP32 doesn't send them automatically
            self.angle_update_timer = QTimer(self)
            self.angle_update_timer.timeout.connect(self.request_all_positions_from_tab) # Use specific name
            if self.serial_handler.is_connected():
                self.angle_update_timer.start(2500) # e.g., every 2.5 seconds
            self.serial_handler.connection_status_changed.connect(self.handle_connection_change_for_timer)

    def send_configured_preset_angle(self, config_key, command_prefix):
        try:
            # Read the current value from the QLineEdit for this config_key
            angle_str = self.config_fields[config_key].text()
            angle = int(angle_str)
            if 0 <= angle <= 180:
                self.serial_handler.send_command(f"{command_prefix} {angle}")
                # Update the respective servo control widget's slider and input
                if command_prefix == "servorot":
                    self.rotation_servo_control.target_angle_input.setText(str(angle))
                    self.rotation_servo_control.angle_slider.setValue(angle)
                elif command_prefix == "servogrip":
                    self.gripper_servo_control.target_angle_input.setText(str(angle))
                    self.gripper_servo_control.angle_slider.setValue(angle)
            else:
                QMessageBox.warning(self, "Preset Error", f"Angle for {config_key} is out of range (0-180).")
        except ValueError:
            QMessageBox.warning(self, "Preset Error", f"Invalid number for {config_key} angle.")
        except KeyError:
            QMessageBox.warning(self, "Preset Error", f"Config key {config_key} not found for preset.")


    def load_fields_from_config(self):
        print("ServoTab: Loading fields from config.")
        for key, line_edit_widget in self.config_fields.items():
            # Use get with a default from DEFAULT_CONFIG_VALUES if key might be missing
            default_val = self.config_values.get(key, "") # Get from config_parser's defaults
            line_edit_widget.setText(str(self.config_values.get(key, default_val)))
        print("ServoTab: Fields reloaded.")

    def update_all_servo_configs_in_app(self):
        try:
            for key, line_edit_widget in self.config_fields.items():
                self.config_values[key] = int(line_edit_widget.text()) # Assume int for these
            QMessageBox.information(self, "Success", "Servo configuration parameters updated in app memory.")
        except ValueError:
            QMessageBox.warning(self, "Input Error", "Invalid number in one of the servo configuration fields.")
        # No need to call load_config_fields here as we just updated from them.

    def handle_connection_change_for_timer(self, connected, port_name):
        if connected:
            self.angle_update_timer.start(2500)
            self.request_all_positions_from_tab()
        else:
            self.angle_update_timer.stop()
            self.rotation_servo_control.update_current_angle_display("N/A")
            self.gripper_servo_control.update_current_angle_display("N/A")

    def request_all_positions_from_tab(self): # Renamed to avoid conflict if main_app also has one
        if self.serial_handler.is_connected():
            self.serial_handler.send_command("getallpos")

    def parse_esp32_response(self, line):
        if line.startswith("POS:"):
            try:
                json_data = json.loads(line[4:])
                if "rotServo" in json_data:
                    angle = int(json_data["rotServo"])
                    self.rotation_servo_control.update_current_angle_display(angle)
                if "gripServo" in json_data:
                    angle = int(json_data["gripServo"])
                    self.gripper_servo_control.update_current_angle_display(angle)
            except (json.JSONDecodeError, ValueError) as e:
                print(f"ServoTab: Error parsing POS JSON or angle: {line} - {e}")
        # Could add ACK parsing if ESP32 sends specific acks for servo commands