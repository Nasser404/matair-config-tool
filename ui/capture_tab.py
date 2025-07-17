from PyQt5.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QGridLayout, QLabel, QLineEdit,
                             QPushButton, QFrame, QGroupBox, QMessageBox, QSizePolicy)
from PyQt5.QtGui import QFont, QPainter, QColor, QPen, QBrush
from PyQt5.QtCore import Qt, QRectF, pyqtSignal
import math
import json

# CircularCaptureWidget class remains the same as before
class CircularCaptureWidget(QWidget):
    slot_clicked = pyqtSignal(int)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.num_slots = 32
        self.setMinimumSize(350, 350)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.selected_slot = -1
        self.hovered_slot = -1
        self.setMouseTracking(True)

    def paintEvent(self, event):
        # ... (no changes needed in paintEvent)
        painter = QPainter(self); painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect(); side = min(rect.width(), rect.height()); padding = 10
        diameter = side - 2 * padding
        if diameter <= 0: return
        ellipse_rect = QRectF((rect.width() - diameter) / 2, (rect.height() - diameter) / 2, diameter, diameter)
        center = ellipse_rect.center(); radius = diameter / 2
        angle_step = 360.0 / self.num_slots
        for i in range(self.num_slots):
            slot_number = i + 1; start_angle = i * angle_step
            painter.setPen(QPen(Qt.darkGray, 1))
            if slot_number == self.selected_slot: painter.setBrush(QBrush(QColor("#3498db")))
            elif slot_number == self.hovered_slot: painter.setBrush(QBrush(QColor("#bdc3c7")))
            else: painter.setBrush(QBrush(QColor("#ecf0f1")))
            painter.drawPie(ellipse_rect, int(start_angle * 16), int(angle_step * 16))
            text_angle_rad = math.radians(start_angle + angle_step / 2)
            text_radius = radius * 0.75
            text_x = center.x() + text_radius * math.cos(text_angle_rad)
            text_y = center.y() - text_radius * math.sin(text_angle_rad)
            painter.setPen(Qt.black); painter.setFont(QFont("Arial", 8))
            text_rect = QRectF(text_x - 10, text_y - 7, 20, 14)
            painter.drawText(text_rect, Qt.AlignCenter, str(slot_number))
        painter.setBrush(Qt.NoBrush); painter.setPen(QPen(Qt.black, 2)); painter.drawEllipse(ellipse_rect)

    def mousePressEvent(self, event): # ... (no change)
        slot = self._get_slot_at_pos(event.pos())
        if slot != -1: self.selected_slot = slot; self.slot_clicked.emit(slot); self.update()

    def mouseMoveEvent(self, event): # ... (no change)
        slot = self._get_slot_at_pos(event.pos())
        if slot != self.hovered_slot: self.hovered_slot = slot; self.update()

    def leaveEvent(self, event): # ... (no change)
        self.hovered_slot = -1; self.update()

    def _get_slot_at_pos(self, pos): # ... (no change)
        rect = self.rect(); side = min(rect.width(), rect.height()); padding = 10; diameter = side - 2 * padding
        if diameter <= 0: return -1
        center_x = rect.width()/2; center_y = rect.height()/2; radius = diameter / 2
        dx = pos.x() - center_x; dy = pos.y() - center_y
        dist = math.sqrt(dx*dx + dy*dy)
        if dist > radius or dist < radius * 0.1: return -1
        angle_deg = math.degrees(math.atan2(-dy, dx));
        if angle_deg < 0: angle_deg += 360
        return math.floor(angle_deg / (360.0 / self.num_slots)) + 1

    def update_selected_slot_display(self, slot_number): # ... (no change)
        self.selected_slot = slot_number; self.update()


class CaptureTabWidget(QWidget):
    def __init__(self, config_values_ref, serial_handler_ref, parent=None):
        super().__init__(parent)
        self.config_values = config_values_ref
        self.serial_handler = serial_handler_ref

        main_layout = QHBoxLayout(self)

        self.circular_capture_widget = CircularCaptureWidget()
        self.circular_capture_widget.slot_clicked.connect(self.on_capture_slot_click)
        main_layout.addWidget(self.circular_capture_widget, 2)

        # --- Info & Control Box ---
        self.info_box = QGroupBox("Capture Zone Configuration")
        info_layout = QVBoxLayout(self.info_box)
        self.info_box.setFixedWidth(300)
        self.info_box.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        
        # --- Selected Slot Control ---
        slot_control_group = QGroupBox("Selected Slot Control")
        slot_control_layout = QVBoxLayout(slot_control_group)

        self.selected_slot_label = QLabel("Selected Slot: None")
        self.selected_slot_label.setFont(QFont("Arial", 12, QFont.Bold))
        slot_control_layout.addWidget(self.selected_slot_label)

        slot_pos_layout = QHBoxLayout()
        slot_pos_layout.addWidget(QLabel("Stepper Target:"))
        self.slot_pos_val = QLineEdit()
        slot_pos_layout.addWidget(self.slot_pos_val)
        slot_control_layout.addLayout(slot_pos_layout)
        
        slot_jog_layout = QHBoxLayout()
        self.capt_jog_minus = QPushButton("Jog -")
        self.capt_jog_minus.pressed.connect(lambda: self.serial_handler.send_command("jog capt 0"))
        self.capt_jog_minus.released.connect(lambda: self.serial_handler.send_command("jogstop"))
        self.capt_jog_plus = QPushButton("Jog +")
        self.capt_jog_plus.pressed.connect(lambda: self.serial_handler.send_command("jog capt 1"))
        self.capt_jog_plus.released.connect(lambda: self.serial_handler.send_command("jogstop"))
        slot_jog_layout.addStretch()
        slot_jog_layout.addWidget(self.capt_jog_minus)
        slot_jog_layout.addWidget(self.capt_jog_plus)
        slot_jog_layout.addStretch()
        slot_control_layout.addLayout(slot_jog_layout)

        slot_buttons_layout = QHBoxLayout()
        self.update_slot_pos_button = QPushButton("Update Position")
        self.update_slot_pos_button.clicked.connect(self.update_config_for_selected_slot)
        self.move_to_displayed_capt_val_button = QPushButton("Move to Displayed Value")
        self.move_to_displayed_capt_val_button.clicked.connect(self.move_esp_to_displayed_capture_value)
        slot_buttons_layout.addWidget(self.update_slot_pos_button)
        slot_buttons_layout.addWidget(self.move_to_displayed_capt_val_button)
        slot_control_layout.addLayout(slot_buttons_layout)
        info_layout.addWidget(slot_control_group)

        # --- Dropoff Position Configuration ---
        dropoff_group = QGroupBox("Capture Zone Dropoff Position")
        dropoff_layout = QGridLayout(dropoff_group)

        dropoff_layout.addWidget(QLabel("Cart Position:"), 0, 0)
        self.cart_capture_pos_val = QLineEdit()
        dropoff_layout.addWidget(self.cart_capture_pos_val, 0, 1)

        dropoff_layout.addWidget(QLabel("Gripper Rotation Angle:"), 1, 0)
        self.gripper_rot_capture_val = QLineEdit()
        dropoff_layout.addWidget(self.gripper_rot_capture_val, 1, 1)

        self.update_dropoff_button = QPushButton("Update CaptureZone Config")
        self.update_dropoff_button.clicked.connect(self.update_dropoff_config)
        dropoff_layout.addWidget(self.update_dropoff_button, 2, 0, 1, 2)
        
        self.go_to_dropoff_pos_button = QPushButton("Go to CaptureZone Position")
        self.go_to_dropoff_pos_button.clicked.connect(self.go_to_configured_dropoff)
        dropoff_layout.addWidget(self.go_to_dropoff_pos_button, 3, 0, 1, 2)
        info_layout.addWidget(dropoff_group)

        info_layout.addStretch()
        main_layout.addWidget(self.info_box, 1)

        self.current_selected_slot_number = -1
        self.load_fields_from_config() # Load initial values

        if self.serial_handler:
            self.serial_handler.data_received.connect(self.parse_esp32_response)

    def load_fields_from_config(self):
        print(f"CaptureTab: Loading fields from config.")
        self.cart_capture_pos_val.setText(str(self.config_values.get("CART_CAPTURE_POS", 0)))
        self.gripper_rot_capture_val.setText(str(self.config_values.get("GRIPPER_ROT_CAPTURE", 0)))
        # Re-trigger info display for the currently selected slot
        self.on_capture_slot_click(self.current_selected_slot_number)

    def on_capture_slot_click(self, slot_number):
        if slot_number == -1: # Deselect
            self.current_selected_slot_number = -1
            self.selected_slot_label.setText("Selected Slot: None")
            self.slot_pos_val.setText("")
        else:
            self.current_selected_slot_number = slot_number
            self.selected_slot_label.setText(f"Selected Slot: {self.current_selected_slot_number}")
            
            capture_targets = self.config_values.get("captureTargets", [0]*32)
            slot_index = self.current_selected_slot_number - 1
            if 0 <= slot_index < len(capture_targets):
                self.slot_pos_val.setText(str(capture_targets[slot_index]))
            else:
                self.slot_pos_val.setText("N/A")
        
        self.circular_capture_widget.update_selected_slot_display(self.current_selected_slot_number)

    def update_config_for_selected_slot(self):
        if self.current_selected_slot_number == -1:
            QMessageBox.warning(self, "Selection Error", "No capture slot selected.")
            return
        try:
            val = int(self.slot_pos_val.text())
            slot_index = self.current_selected_slot_number - 1
            if 0 <= slot_index < len(self.config_values["captureTargets"]):
                self.config_values["captureTargets"][slot_index] = val
                QMessageBox.information(self, "Update", f"Slot {self.current_selected_slot_number} position updated in app memory.")
            else:
                QMessageBox.warning(self, "Error", "Invalid slot index for update.")
        except ValueError:
            QMessageBox.warning(self, "Input Error", "Invalid number for position.")
    
    def update_dropoff_config(self):
        try:
            cart_pos = int(self.cart_capture_pos_val.text())
            rot_angle = int(self.gripper_rot_capture_val.text())

            self.config_values["CART_CAPTURE_POS"] = cart_pos
            self.config_values["GRIPPER_ROT_CAPTURE"] = rot_angle
            
            # Send updates to ESP32
            self.serial_handler.send_command(f"setconfig cart_capture_pos {cart_pos}")
            self.serial_handler.send_command(f"setconfig gripper_rot_capture {rot_angle}")

            QMessageBox.information(self, "Update", "Dropoff settings updated .")
        except ValueError:
            QMessageBox.warning(self, "Input Error", "Invalid number for dropoff settings.")

    def go_to_selected_capture_slot(self):
        if self.current_selected_slot_number == -1:
            QMessageBox.warning(self, "Go To Error", "No capture slot selected.")
            return
        # Send a sequence of commands for the full action
        self.go_to_configured_dropoff(move_capture_stepper=True)

    def move_esp_to_displayed_capture_value(self):
        if self.current_selected_slot_number == -1:
            QMessageBox.warning(self, "Error", "No capture slot selected.")
            return
        capt_val_str = self.slot_pos_val.text()
        if capt_val_str.isdigit():
            # This just moves the capture stepper
            self.serial_handler.send_command(f"gotocapt {capt_val_str}")
        else:
            QMessageBox.warning(self, "Input Error", "Capture position value is not a valid number.")

    def get_esp_target_for_slot(self):
        # This command is less useful if config is local, but can be for verification
        if self.current_selected_slot_number != -1:
            self.serial_handler.send_command(f"getcaptpos {self.current_selected_slot_number}")
            
    def go_to_configured_dropoff(self, move_capture_stepper=False):
        # Use values directly from input fields for immediate testing
        try:
            cart_pos = int(self.cart_capture_pos_val.text())
            rot_angle = int(self.gripper_rot_capture_val.text())
        except ValueError:
            QMessageBox.warning(self, "Input Error", "Dropoff position/angle are not valid numbers.")
            return

        # Order: Cart -> Capture -> Rotate
        self.serial_handler.send_command(f"gotocart {cart_pos}")
        
        if move_capture_stepper and self.current_selected_slot_number != -1:
            slot_pos_str = self.slot_pos_val.text()
            if slot_pos_str.isdigit():
                self.serial_handler.send_command(f"gotocapt {slot_pos_str}")
            else:
                QMessageBox.warning(self, "Go To Error", "Slot position input is invalid.")
                return # Stop sequence if slot pos is bad
        
        # We might need to wait for steppers to finish before rotating.
        # For calibration, sending commands sequentially is often okay.
        # A more robust system would wait for ACK from steppers before sending servo command.
        self.serial_handler.send_command(f"servorot {rot_angle}")

    def parse_esp32_response(self, line):
        return
        if line.startswith("CAPTPOS:"):
            try:
                json_data = json.loads(line[8:])
                slot = json_data.get("slot", -1)
                capt_val = json_data.get("capture", "N/A")
                if self.current_selected_slot_number == slot:
                    self.slot_pos_val.setText(str(capt_val))
                    print(f"Updated info box for Capture Slot {slot} from ESP32.")
            except json.JSONDecodeError:
                print(f"CaptureTab: Error decoding CAPTPOS JSON: {line}")