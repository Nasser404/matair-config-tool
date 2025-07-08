from PyQt5.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QLabel, QLineEdit,
                             QPushButton, QFrame, QGroupBox, QMessageBox,QSizePolicy)
from PyQt5.QtGui import QFont, QPainter, QColor, QPen, QBrush, QPolygonF
from PyQt5.QtCore import Qt, QPointF, QRectF, pyqtSignal
import math
import json

# Custom Widget for Circular Capture Zone Display
class CircularCaptureWidget(QWidget):
    slot_clicked = pyqtSignal(int) # Signal to emit when a slot is clicked (1-32)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.num_slots = 32
        self.setMinimumSize(350, 350) # Ensure it has enough space to draw
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.selected_slot = -1 # No slot selected initially
        self.hovered_slot = -1  # For visual feedback on hover
        self.setMouseTracking(True) # Enable mouseMoveEvent even when no button is pressed

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = self.rect() # Get the current widget's rectangle
        side = min(rect.width(), rect.height()) # Use the smaller dimension for circle
        
        # Define drawing area for the circle, slightly padded
        padding = 10
        diameter = side - 2 * padding
        if diameter <= 0: return # Not enough space to draw

        ellipse_rect = QRectF(
            (rect.width() - diameter) / 2,
            (rect.height() - diameter) / 2,
            diameter,
            diameter
        )
        center = ellipse_rect.center()
        radius = diameter / 2

        # Draw segments
        angle_step = 360.0 / self.num_slots
        for i in range(self.num_slots):
            slot_number = i + 1
            start_angle = i * angle_step
            span_angle = angle_step

            painter.setPen(QPen(Qt.darkGray, 1))
            if slot_number == self.selected_slot:
                painter.setBrush(QBrush(QColor("#3498db"))) # Blue for selected
            elif slot_number == self.hovered_slot:
                painter.setBrush(QBrush(QColor("#bdc3c7"))) # Light gray for hover
            else:
                painter.setBrush(QBrush(QColor("#ecf0f1"))) # Light gray for normal

            # QPainter works with 16ths of a degree for startAngle and spanAngle
            painter.drawPie(ellipse_rect, int(start_angle * 16), int(span_angle * 16))

            # Draw slot numbers
            text_angle_rad = math.radians(start_angle + angle_step / 2)
            text_radius = radius * 0.75 # Position numbers inside the segments
            text_x = center.x() + text_radius * math.cos(text_angle_rad)
            text_y = center.y() - text_radius * math.sin(text_angle_rad) # Y is inverted in Qt painter coords

            painter.setPen(Qt.black)
            painter.setFont(QFont("Arial", 8))
            # Adjust text bounding box for centering
            text_rect = QRectF(text_x - 10, text_y - 7, 20, 14)
            painter.drawText(text_rect, Qt.AlignCenter, str(slot_number))
        
        # Draw an outer circle
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(Qt.black, 2))
        painter.drawEllipse(ellipse_rect)


    def mousePressEvent(self, event):
        slot = self._get_slot_at_pos(event.pos())
        if slot != -1:
            self.selected_slot = slot
            self.slot_clicked.emit(slot) # Emit signal with slot number (1-32)
            self.update() # Trigger repaint

    def mouseMoveEvent(self, event):
        slot = self._get_slot_at_pos(event.pos())
        if slot != self.hovered_slot:
            self.hovered_slot = slot
            self.update()

    def leaveEvent(self, event):
        self.hovered_slot = -1
        self.update()

    def _get_slot_at_pos(self, pos):
        rect = self.rect()
        side = min(rect.width(), rect.height())
        padding = 10
        diameter = side - 2 * padding
        if diameter <= 0: return -1

        center_x = rect.width() / 2
        center_y = rect.height() / 2
        radius = diameter / 2

        # Check if click is within the circle
        dx = pos.x() - center_x
        dy = pos.y() - center_y
        distance_from_center = math.sqrt(dx*dx + dy*dy)

        if distance_from_center > radius or distance_from_center < radius * 0.1: # Ignore clicks too close to center
            return -1

        # Calculate angle
        # Angle is 0 on positive X-axis, increases counter-clockwise.
        # atan2 returns angle in radians from -pi to pi.
        # We need to adjust it to match QPainter's 0 degrees at 3 o'clock, positive CCW.
        angle_rad = math.atan2(-dy, dx) # -dy because Qt Y is inverted
        angle_deg = math.degrees(angle_rad)
        if angle_deg < 0:
            angle_deg += 360

        angle_step = 360.0 / self.num_slots
        slot_index = math.floor(angle_deg / angle_step)
        return slot_index + 1 # Slot numbers are 1-32

    def update_selected_slot_display(self, slot_number):
        """Allows external update of selected slot, e.g., if set by other means"""
        self.selected_slot = slot_number
        self.update()


class CaptureTabWidget(QWidget):
    def __init__(self, config_values_ref, serial_handler_ref, parent=None):
        super().__init__(parent)
        self.config_values = config_values_ref
        self.serial_handler = serial_handler_ref

        main_layout = QHBoxLayout(self)

        # --- Circular Capture Zone Widget ---
        self.circular_capture_widget = CircularCaptureWidget()
        self.circular_capture_widget.slot_clicked.connect(self.on_capture_slot_click)
        main_layout.addWidget(self.circular_capture_widget, 2)

       # --- Info & Control Box ---
        self.info_box = QGroupBox("Capture Config")
        info_layout = QVBoxLayout() # Use QVBoxLayout
        self.info_box.setFixedWidth(300)

        self.selected_slot_label = QLabel("Selected Slot: None")
        # ... (font) ...
        info_layout.addWidget(self.selected_slot_label)

        # Slot Position
        slot_pos_layout = QHBoxLayout()
        self.slot_pos_label = QLabel("Capture Stepper Target:")
        self.slot_pos_val = QLineEdit()
        slot_pos_layout.addWidget(self.slot_pos_label)
        slot_pos_layout.addWidget(self.slot_pos_val)
        info_layout.addLayout(slot_pos_layout)


        self.update_slot_pos_button = QPushButton("Update Slot Position in App")
        self.update_slot_pos_button.clicked.connect(self.update_config_for_selected_slot)
        info_layout.addWidget(self.update_slot_pos_button)

        self.go_to_slot_button = QPushButton("Go to Slot (Full Sequence)") # Clarified name
        self.go_to_slot_button.clicked.connect(self.go_to_selected_capture_slot)
        info_layout.addWidget(self.go_to_slot_button)

        # <<< NEW BUTTON >>>
        self.move_to_displayed_capt_val_button = QPushButton("Move Stepper to Displayed Value")
        self.move_to_displayed_capt_val_button.clicked.connect(self.move_esp_to_displayed_capture_value)
        info_layout.addWidget(self.move_to_displayed_capt_val_button)
        # <<< END NEW BUTTON >>>
        
        self.get_esp_slot_pos_button = QPushButton("Get ESP Target for Slot")
        info_layout.addWidget(self.get_esp_slot_pos_button)
        
        info_layout.addSpacing(20)
        self.dropoff_label = QLabel("Capture Dropoff Settings:") # ... (rest of dropoff UI)
        self.dropoff_label.setFont(QFont("Arial", 11, QFont.Bold))
        info_layout.addWidget(self.dropoff_label)
        self.cart_capture_pos_label = QLabel("Cart Dropoff Position:")
        self.cart_capture_pos_val = QLineEdit()
        info_layout.addWidget(self.cart_capture_pos_label)
        info_layout.addWidget(self.cart_capture_pos_val)
        self.gripper_rot_capture_label = QLabel("Gripper Rotation for Capture:")
        self.gripper_rot_capture_val = QLineEdit()
        info_layout.addWidget(self.gripper_rot_capture_label)
        info_layout.addWidget(self.gripper_rot_capture_val)
        self.update_dropoff_button = QPushButton("Update Dropoff Settings in App")
        self.update_dropoff_button.clicked.connect(self.update_dropoff_config)
        info_layout.addWidget(self.update_dropoff_button)
        self.go_to_dropoff_pos_button = QPushButton("Go to CZ Dropoff")
        self.go_to_dropoff_pos_button.clicked.connect(self.go_to_configured_dropoff)
        info_layout.addWidget(self.go_to_dropoff_pos_button)

        info_layout.addStretch()
        self.info_box.setLayout(info_layout)
        main_layout.addWidget(self.info_box, 1)

        self.current_selected_slot_number = -1
        self.update_dropoff_fields_from_config()

        if self.serial_handler:
            self.serial_handler.data_received.connect(self.parse_esp32_response)

    def update_dropoff_fields_from_config(self): # Same
        self.cart_capture_pos_val.setText(str(self.config_values.get("CART_CAPTURE_POS", 0)))
        self.gripper_rot_capture_val.setText(str(self.config_values.get("GRIPPER_ROT_CAPTURE", 0)))

    # Connected to circular_capture_widget.slot_clicked signal
    def on_capture_slot_click(self, slot_number):
        self.current_selected_slot_number = slot_number
        self.selected_slot_label.setText(f"Selected Slot: {self.current_selected_slot_number}")
        
        capture_targets = self.config_values.get("captureTargets", [0]*32)
        if 0 <= self.current_selected_slot_number -1 < len(capture_targets):
            self.slot_pos_val.setText(str(capture_targets[self.current_selected_slot_number - 1]))
        else:
            self.slot_pos_val.setText("N/A")
        
        # Update the circular widget's display of selected slot
        self.circular_capture_widget.update_selected_slot_display(self.current_selected_slot_number)
        self.get_esp_target_for_slot()

    def update_dropoff_config(self): # Same
        try:
            self.config_values["CART_CAPTURE_POS"] = int(self.cart_capture_pos_val.text())
            self.config_values["GRIPPER_ROT_CAPTURE"] = int(self.gripper_rot_capture_val.text())
            QMessageBox.information(self, "Update", "Dropoff settings updated.")
        except ValueError: QMessageBox.warning(self, "Input Error", "Invalid number.")

    def go_to_selected_capture_slot(self): # Clarified, this does the full sequence
        if self.current_selected_slot_number == -1:
            QMessageBox.warning(self, "Go To Error", "No capture slot selected.")
            return
        # This existing method moves cart, rotates gripper, then moves capture stepper
        self.go_to_configured_dropoff(move_capture_stepper=True)

    def move_esp_to_displayed_capture_value(self): # <<< NEW METHOD
        if self.current_selected_slot_number == -1:
            QMessageBox.warning(self, "Error", "No capture slot selected.")
            return

        capt_val_str = self.slot_pos_val.text()
        if capt_val_str:
            try:
                capt_pos = int(capt_val_str)
                # This command ONLY moves the capture stepper.
                # User should manually position cart/gripper if needed for visual check.
                self.serial_handler.send_command(f"gotocapt {capt_pos}")
            except ValueError:
                QMessageBox.warning(self, "Input Error", f"Capture value '{capt_val_str}' is not a valid number.")
        else:
            QMessageBox.information(self, "Info", "No position value entered to send.")

    def update_config_for_selected_slot(self): # Same
        if self.current_selected_slot_number == -1: return
        try:
            val = int(self.slot_pos_val.text())
            slot_index = self.current_selected_slot_number - 1
            if 0 <= slot_index < len(self.config_values["captureTargets"]):
                self.config_values["captureTargets"][slot_index] = val
                QMessageBox.information(self, "Update", f"Slot {self.current_selected_slot_number} updated.")
        except ValueError: QMessageBox.warning(self, "Input Error", "Invalid number.")
        
        
    def get_esp_target_for_slot(self): # Same
        if self.current_selected_slot_number != -1:
            #self.serial_handler.send_command(f"getcaptpos {self.current_selected_slot_number}")
            pass
            
    def go_to_configured_dropoff(self, move_capture_stepper=False): # Same
        cart_pos = self.config_values.get("CART_CAPTURE_POS", 2250)
        rot_angle = self.config_values.get("GRIPPER_ROT_CAPTURE", 62)
        self.serial_handler.send_command(f"servorot {rot_angle}")
        self.serial_handler.send_command(f"gotocart {cart_pos}")
        if move_capture_stepper and self.current_selected_slot_number != -1:
            slot_pos_str = self.slot_pos_val.text()
            if slot_pos_str.isdigit():
                self.serial_handler.send_command(f"gotocapt {slot_pos_str}")
            else: QMessageBox.warning(self, "Go To Error", "Slot position input is invalid.")

    def parse_esp32_response(self, line): # Same
        if line.startswith("CAPTPOS:"):
            try:
                json_data = json.loads(line[8:])
                slot = json_data.get("slot", -1)
                capt_val = json_data.get("capture", "N/A")
                if self.current_selected_slot_number == slot:
                    self.slot_pos_val.setText(str(capt_val))
            except json.JSONDecodeError: print(f"CaptureTab: Error CAPTPOS JSON: {line}")
            
    def load_fields_from_config(self):
        """ Reloads all configurable fields on this tab from self.config_values. """
        print(f"CaptureTab: Loading fields from config. Current selected: {self.current_selected_slot_number}")
        self.cart_capture_pos_val.setText(str(self.config_values.get("CART_CAPTURE_POS", 0)))
        self.gripper_rot_capture_val.setText(str(self.config_values.get("GRIPPER_ROT_CAPTURE", 0)))

        if self.current_selected_slot_number != -1:
            # If a slot is selected, update its displayed position value
            slot_index = self.current_selected_slot_number - 1
            capture_targets = self.config_values.get("captureTargets", [0]*32)
            if 0 <= slot_index < len(capture_targets):
                self.slot_pos_val.setText(str(capture_targets[slot_index]))
            else:
                self.slot_pos_val.setText("N/A") # Should not happen if slot num is valid
        else:
            # If no slot is selected, clear the slot-specific position
            self.selected_slot_label.setText("Selected Slot: None")
            self.slot_pos_val.setText("")
        print("CaptureTab: Fields reloaded.")