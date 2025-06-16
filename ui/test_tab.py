from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                             QPushButton, QGroupBox, QMessageBox, QFormLayout, QRadioButton,
                             QButtonGroup)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt

class TestTabWidget(QWidget):
    def __init__(self, config_values_ref, serial_handler_ref, parent=None):
        super().__init__(parent)
        self.serial_handler = serial_handler_ref
        self.config_values = config_values_ref # Not directly used here, but good practice

        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)

        test_move_group = QGroupBox("Execute 'do <from> <to>' Sequence")
        form_layout = QFormLayout(test_move_group) # QFormLayout is good for label-input pairs

        # --- From Location ---
        self.from_label = QLabel("From Location:")
        self.from_input = QLineEdit()
        self.from_input.setPlaceholderText("e.g., e2 or capt5")
        form_layout.addRow(self.from_label, self.from_input)

        # --- To Location ---
        self.to_label = QLabel("To Location:")
        self.to_input = QLineEdit()
        self.to_input.setPlaceholderText("e.g., e4 or capt10")
        form_layout.addRow(self.to_label, self.to_input)
        
        # --- Promotion (Simple version for now, if needed later) ---
        # self.promotion_group = QGroupBox("Promotion (if applicable)")
        # promotion_layout = QHBoxLayout(self.promotion_group)
        # self.promote_to_label = QLabel("Promote to:")
        # self.promote_queen_rb = QRadioButton("Queen")
        # self.promote_rook_rb = QRadioButton("Rook")
        # self.promote_bishop_rb = QRadioButton("Bishop")
        # self.promote_knight_rb = QRadioButton("Knight")
        # self.promote_queen_rb.setChecked(True) # Default to Queen
        #
        # self.promotion_button_group = QButtonGroup(self) # For exclusive selection
        # self.promotion_button_group.addButton(self.promote_queen_rb)
        # self.promotion_button_group.addButton(self.promote_rook_rb)
        # # ... add others ...
        #
        # promotion_layout.addWidget(self.promote_to_label)
        # promotion_layout.addWidget(self.promote_queen_rb)
        # promotion_layout.addWidget(self.promote_rook_rb)
        # # ... add others ...
        # promotion_layout.addStretch()
        # # self.promotion_group.setVisible(False) # Initially hidden or always visible
        # form_layout.addRow(self.promotion_group)


        self.execute_button = QPushButton("Execute 'do' Move")
        self.execute_button.setFont(QFont("Arial", 11, QFont.Bold))
        self.execute_button.clicked.connect(self.send_do_command)
        form_layout.addRow(self.execute_button)

        main_layout.addWidget(test_move_group)
        main_layout.addStretch() # Push group to top

        if self.serial_handler:
            self.serial_handler.data_received.connect(self.parse_esp32_response)

    def send_do_command(self):
        from_loc = self.from_input.text().strip().lower()
        to_loc = self.to_input.text().strip().lower()

        if not from_loc or not to_loc:
            QMessageBox.warning(self, "Input Error", "Both 'From' and 'To' locations must be specified.")
            return

        # Basic validation (can be more sophisticated)
        # For now, just check they are not empty. ESP32 will do more validation.
        
        # TODO: If implementing promotion piece selection:
        # promoted_piece = "QUEEN" # Default
        # if self.promote_rook_rb.isChecked(): promoted_piece = "ROOK"
        # ...
        # command = f"do {from_loc} {to_loc} promote {promoted_piece}" # Example if ESP supports this
        
        command = f"do {from_loc} {to_loc}"
        
        if self.serial_handler.is_connected():
            QMessageBox.information(self, "Sending Command", f"Sending: {command}\n\nMonitor ESP32 serial output for progress and any errors from the robot itself.")
            self.serial_handler.send_command(command)
        else:
            QMessageBox.warning(self, "Serial Error", "Not connected to ESP32.")


    def parse_esp32_response(self, line):
        # This tab might not need to parse much beyond general ACKs or ERRs,
        # as the main feedback is the physical robot movement and ESP32 serial log.
        if line.startswith("ACK: Executing Do Sequence"):
            # Could update a status label on this tab if desired
            print(f"TestTab: ESP32 acknowledged 'do' command.")
        elif line.startswith("ERR:") and "do" in line.lower(): # Generic error related to do
             QMessageBox.critical(self, "ESP32 'do' Error", line)