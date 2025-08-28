
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                             QPushButton, QGroupBox, QMessageBox, QFormLayout, QGridLayout,
                             QFrame, QSizePolicy, QScrollArea)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt

# Import the visual components from other tabs
from .board_tab import ChessSquareButton
from .capture_tab import CircularCaptureWidget

class TestTabWidget(QWidget):
    def __init__(self, config_values_ref, serial_handler_ref, parent=None):
        super().__init__(parent)
        self.serial_handler = serial_handler_ref
        self.config_values = config_values_ref

        # --- State for move selection ---
        self.selecting_from = True # Start by selecting the 'From' location
        self.from_location_str = ""
        self.to_location_str = ""

        # --- Main Layout ---
        tab_overall_layout = QVBoxLayout(self)
        tab_overall_layout.setContentsMargins(0, 0, 0, 0)
        
        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
    
        main_widget_for_scroll = QWidget()
        main_layout = QHBoxLayout(main_widget_for_scroll) 
        
        scroll_area.setWidget(main_widget_for_scroll)
        tab_overall_layout.addWidget(scroll_area)
        
        # --- Left Side: Selection Grids ---
        selection_area = QVBoxLayout()
        selection_area.setAlignment(Qt.AlignTop)

        # Board Grid for selection
        board_group = QGroupBox("Select from Board")
        board_grid_widget = QFrame()
        board_grid_layout = QGridLayout(board_grid_widget)
        board_grid_layout.setSpacing(1)
        files = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
        ranks = ['8', '7', '6', '5', '4', '3', '2', '1']
        for r, rank_char in enumerate(ranks):
            for f, file_char in enumerate(files):
                square_name = file_char + rank_char
                square_btn = ChessSquareButton(square_name, f, r)
                square_btn.clicked.connect(self.on_location_selected)
                board_grid_layout.addWidget(square_btn, r, f)
        board_group.setLayout(board_grid_layout)
        selection_area.addWidget(board_group)

        # Capture Zone Grid for selection
        capture_group = QGroupBox("Select from Capture Zone")
        self.circular_capture_widget = CircularCaptureWidget()
        self.circular_capture_widget.slot_clicked.connect(self.on_location_selected)
        capture_layout = QVBoxLayout(capture_group)
        capture_layout.addWidget(self.circular_capture_widget)
        selection_area.addWidget(capture_group)
        
        main_layout.addLayout(selection_area, 2) 

        # --- Right Side: Control Box ---
        control_box = QGroupBox("Move Execution")
        control_layout = QVBoxLayout(control_box)
        control_box.setFixedWidth(300)
        control_box.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)

        self.instruction_label = QLabel("1. Select 'From' location...")
        self.instruction_label.setFont(QFont("Arial", 11, QFont.Bold))
        self.instruction_label.setWordWrap(True)
        control_layout.addWidget(self.instruction_label)

        form_layout = QFormLayout()
        self.from_display = QLineEdit()
        self.from_display.setReadOnly(True)
        self.from_display.setStyleSheet("background-color: #f0f0f0;")
        form_layout.addRow("From:", self.from_display)

        self.to_display = QLineEdit()
        self.to_display.setReadOnly(True)
        self.to_display.setStyleSheet("background-color: #f0f0f0;")
        form_layout.addRow("To:", self.to_display)
        control_layout.addLayout(form_layout)

        self.execute_button = QPushButton("Execute 'do' Move")
        self.execute_button.setFont(QFont("Arial", 11, QFont.Bold))
        self.execute_button.setEnabled(False) # Disabled until both From and To are selected
        self.execute_button.clicked.connect(self.send_do_command)
        control_layout.addWidget(self.execute_button)

        self.clear_button = QPushButton("Clear Selection")
        self.clear_button.clicked.connect(self.clear_selection)
        control_layout.addWidget(self.clear_button)

        control_layout.addStretch()
        main_layout.addWidget(control_box, 1)

    def on_location_selected(self):
        location_str = ""
        sender = self.sender()

        if isinstance(sender, ChessSquareButton):
            location_str = sender.text().lower()
        elif isinstance(sender, CircularCaptureWidget):
         
            if isinstance(self.sender(), CircularCaptureWidget):
                slot_num = self.sender().selected_slot 
                location_str = f"capt{slot_num}"
                # Update the visual selection in the widget
                self.circular_capture_widget.update_selected_slot_display(slot_num)

        if not location_str:
            return

        if self.selecting_from:
            self.from_location_str = location_str
            self.from_display.setText(self.from_location_str)
            self.to_location_str = "" # Clear 'To' if re-selecting 'From'
            self.to_display.setText("")
            self.instruction_label.setText("2. Select 'To' location...")
            self.selecting_from = False # Switch to selecting 'To'
            self.execute_button.setEnabled(False)
        else: # We are selecting 'To'
            self.to_location_str = location_str
            self.to_display.setText(self.to_location_str)
            self.instruction_label.setText("Ready to execute move.")
            self.selecting_from = True # Next click will be a new 'From'
            self.execute_button.setEnabled(True)

    def clear_selection(self):
        self.from_location_str = ""
        self.to_location_str = ""
        self.from_display.setText("")
        self.to_display.setText("")
        self.selecting_from = True
        self.instruction_label.setText("1. Select 'From' location...")
        self.execute_button.setEnabled(False)
        self.circular_capture_widget.update_selected_slot_display(-1) # Clear visual selection

    def send_do_command(self):
        if not self.from_location_str or not self.to_location_str:
            QMessageBox.warning(self, "Input Error", "Both 'From' and 'To' locations must be selected.")
            return

        command = f"do {self.from_location_str} {self.to_location_str}"
        
        if self.serial_handler.is_connected():
            QMessageBox.information(self, "Sending Command", f"Sending: {command}\n\nMonitor ESP32 serial output for progress.")
            self.serial_handler.send_command(command)
            # After sending, clear for the next move
            self.clear_selection()
        else:
            QMessageBox.warning(self, "Serial Error", "Not connected to ESP32.")

    def parse_esp32_response(self, line):
      
        if "Do Sequence Complete" in line:
            QMessageBox.information(self, "ESP32 Feedback", "The 'do' sequence has completed successfully.")
        elif line.startswith("ERR:") and "do" in line.lower():
             QMessageBox.critical(self, "ESP32 'do' Error", line)