from PyQt5.QtWidgets import (QWidget, QHBoxLayout, QGridLayout, QLabel, QLineEdit,
                             QPushButton, QFrame, QGroupBox, QMessageBox, QVBoxLayout,
                             QSizePolicy)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt
import json

class ChessSquareButton(QPushButton):
    def __init__(self, text, x, y, is_label=False, parent=None):
        super().__init__(text, parent)
        self.x = x
        self.y = y
        self.is_label = is_label
        self.setMinimumSize(50, 50)
        self.setFont(QFont("Arial", 10))
        if not is_label:
            if (x + y) % 2 == 0: self.setStyleSheet("background-color: #FFEBCD; color: black;")
            else: self.setStyleSheet("background-color: #8B4513; color: white;")
        else: self.setStyleSheet("background-color: lightgray; border: 1px solid gray;")

class BoardTabWidget(QWidget):
    def __init__(self, config_values_ref, serial_handler_ref, parent=None):
        super().__init__(parent)
        self.config_values = config_values_ref
        self.serial_handler = serial_handler_ref

        layout = QHBoxLayout(self)
        board_grid_widget = QFrame()
        board_grid_widget.setFrameShape(QFrame.StyledPanel)
        grid_layout = QGridLayout(board_grid_widget)
        grid_layout.setSpacing(1)
        files = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
        ranks = ['8', '7', '6', '5', '4', '3', '2', '1']

        for i, file_char in enumerate(files):
            label_btn = ChessSquareButton(file_char, i, -1, is_label=True)
            label_btn.clicked.connect(self.on_board_element_click)
            grid_layout.addWidget(label_btn, 0, i + 1)
        for r, rank_char in enumerate(ranks):
            rank_label_btn = ChessSquareButton(rank_char, -1, r, is_label=True)
            rank_label_btn.clicked.connect(self.on_board_element_click)
            grid_layout.addWidget(rank_label_btn, r + 1, 0)
            for f, file_char in enumerate(files):
                square_name = file_char + rank_char
                square_btn = ChessSquareButton(square_name, f, r)
                square_btn.clicked.connect(self.on_board_element_click)
                grid_layout.addWidget(square_btn, r + 1, f + 1)
        layout.addWidget(board_grid_widget, 2)

        # --- Info Box ---
        self.info_box = QGroupBox("Selected Element Info")
        info_layout = QVBoxLayout(self.info_box)
        self.info_box.setFixedWidth(300) # Increased width slightly
        self.info_box.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)

        self.selected_element_label = QLabel("Selected: None")
        self.selected_element_label.setFont(QFont("Arial", 12, QFont.Bold))
        info_layout.addWidget(self.selected_element_label)

        # --- Orb/File Control ---
        orb_group = QGroupBox("Orb (File) Control")
        orb_layout = QVBoxLayout(orb_group)
        
        orb_target_layout = QHBoxLayout()
        self.selected_square_info_orb_label = QLabel("Target Position:")
        self.selected_square_info_orb_val = QLineEdit()
        self.selected_square_info_orb_val.setPlaceholderText("e.g., 840")
        orb_target_layout.addWidget(self.selected_square_info_orb_label)
        orb_target_layout.addWidget(self.selected_square_info_orb_val)
        orb_layout.addLayout(orb_target_layout)
        
        orb_jog_layout = QHBoxLayout()
        self.orb_jog_minus = QPushButton("Jog -")
        self.orb_jog_minus.pressed.connect(lambda: self.serial_handler.send_command("jog orb 0"))
        self.orb_jog_minus.released.connect(lambda: self.serial_handler.send_command("jogstop"))
        self.orb_jog_plus = QPushButton("Jog +")
        self.orb_jog_plus.pressed.connect(lambda: self.serial_handler.send_command("jog orb 1"))
        self.orb_jog_plus.released.connect(lambda: self.serial_handler.send_command("jogstop"))
        orb_jog_layout.addStretch()
        orb_jog_layout.addWidget(self.orb_jog_minus)
        orb_jog_layout.addWidget(self.orb_jog_plus)
        orb_jog_layout.addStretch()
        orb_layout.addLayout(orb_jog_layout)
        info_layout.addWidget(orb_group)
        self.orb_group = orb_group # Reference for visibility control

        # --- Cart/Rank Control ---
        cart_group = QGroupBox("Cart (Rank) Control")
        cart_layout = QVBoxLayout(cart_group)
        
        cart_target_layout = QHBoxLayout()
        self.selected_square_info_cart_label = QLabel("Target Position:")
        self.selected_square_info_cart_val = QLineEdit()
        self.selected_square_info_cart_val.setPlaceholderText("e.g., 4480")
        cart_target_layout.addWidget(self.selected_square_info_cart_label)
        cart_target_layout.addWidget(self.selected_square_info_cart_val)
        cart_layout.addLayout(cart_target_layout)
        
        cart_jog_layout = QHBoxLayout()
        self.cart_jog_minus = QPushButton("Jog -")
        self.cart_jog_minus.pressed.connect(lambda: self.serial_handler.send_command("jog cart 0"))
        self.cart_jog_minus.released.connect(lambda: self.serial_handler.send_command("jogstop"))
        self.cart_jog_plus = QPushButton("Jog +")
        self.cart_jog_plus.pressed.connect(lambda: self.serial_handler.send_command("jog cart 1"))
        self.cart_jog_plus.released.connect(lambda: self.serial_handler.send_command("jogstop"))
        cart_jog_layout.addStretch()
        cart_jog_layout.addWidget(self.cart_jog_minus)
        cart_jog_layout.addWidget(self.cart_jog_plus)
        cart_jog_layout.addStretch()
        cart_layout.addLayout(cart_jog_layout)
        info_layout.addWidget(cart_group)
        self.cart_group = cart_group

        # --- Action Buttons ---
        self.update_pos_button = QPushButton("Update position(s)")
        self.update_pos_button.clicked.connect(self.update_config_from_infobox)
        info_layout.addWidget(self.update_pos_button)
        
        self.move_to_displayed_vals_button = QPushButton("Move Steppers to position")
        self.move_to_displayed_vals_button.setToolTip("Sends individual 'gotoorb/gotocart' commands for fine-tuning.")
        self.move_to_displayed_vals_button.clicked.connect(self.move_esp_to_displayed_board_values)
        info_layout.addWidget(self.move_to_displayed_vals_button)
        
        """
        self.go_to_square_button = QPushButton("Go to Square (Full Sequence)")
        self.go_to_square_button.setToolTip("Sends 'move <square>' to ESP32 to test full sequence.")
        self.go_to_square_button.clicked.connect(self.go_to_selected_board_square)
        info_layout.addWidget(self.go_to_square_button)


        
        self.get_esp_pos_button = QPushButton("Get ESP Target for Square")
        self.get_esp_pos_button.clicked.connect(self.get_esp_target_for_square)
        info_layout.addWidget(self.get_esp_pos_button)"""
        """
    
        self.get_current_pos_button = QPushButton("Get Current ESP Positions")
        self.get_current_pos_button.clicked.connect(lambda: self.serial_handler.send_command("getallpos"))
        info_layout.addWidget(self.get_current_pos_button)
"""
        info_layout.addStretch()
        layout.addWidget(self.info_box, 1)

        self.current_selected_square_text = ""
        self.current_selected_is_label = False
        self.current_selected_x = -1 # File index (0-7 for A-H)
        self.current_selected_y = -1 # Rank index from top (0 for '8', 7 for '1')
        
        self.update_board_info_box() # Initial state setup

        if self.serial_handler:
            self.serial_handler.data_received.connect(self.parse_esp32_response)

    def on_board_element_click(self):
        # ... (same as before) ...
        sender = self.sender()
        self.current_selected_square_text = sender.text()
        self.current_selected_is_label = sender.is_label
        self.current_selected_x = sender.x
        self.current_selected_y = sender.y
        self.update_board_info_box()
        if not sender.is_label:
            self.get_esp_target_for_square()

    def update_board_info_box(self):
        # This method now controls visibility and populates values
        orb_targets = self.config_values.get("orbTargets", [0]*8)
        cart_targets = self.config_values.get("cartTargets", [0]*8)

        if not self.current_selected_square_text:
            self.selected_element_label.setText("Selected: None")
            self.orb_group.setVisible(False)
            self.cart_group.setVisible(False)
            #self.go_to_square_button.setEnabled(False)
            return

        #self.go_to_square_button.setEnabled(True)
        self.selected_element_label.setText(f"Selected: {self.current_selected_square_text}")
        
        is_file_sel = self.current_selected_is_label and self.current_selected_x != -1
        is_rank_sel = self.current_selected_is_label and self.current_selected_y != -1
        is_square_sel = not self.current_selected_is_label

        self.orb_group.setVisible(is_file_sel or is_square_sel)
        self.cart_group.setVisible(is_rank_sel or is_square_sel)
        #self.go_to_square_button.setEnabled(is_square_sel) # Only enable for full squares

        if is_file_sel:
            self.orb_group.setTitle(f"Orb ({self.current_selected_square_text}) Control")
            self.selected_square_info_orb_val.setText(str(orb_targets[self.current_selected_x]))
        elif is_rank_sel:
            self.cart_group.setTitle(f"Cart ({self.current_selected_square_text}) Control")
            rank_idx = 7 - self.current_selected_y
            self.selected_square_info_cart_val.setText(str(cart_targets[rank_idx]))
        elif is_square_sel:
            self.orb_group.setTitle(f"Orb ({self.current_selected_square_text[0]}) Control")
            self.cart_group.setTitle(f"Cart ({self.current_selected_square_text[1]}) Control")
            file_idx = self.current_selected_x
            rank_idx = 7 - self.current_selected_y
            self.selected_square_info_orb_val.setText(str(orb_targets[file_idx]))
            self.selected_square_info_cart_val.setText(str(cart_targets[rank_idx]))

    def update_config_from_infobox(self):
        if not self.current_selected_square_text: return
        try:
            # Update all values present in the info box
            # This simplifies logic: if an input is visible and has a value, update it.
            if self.orb_group.isVisible():
                orb_val = int(self.selected_square_info_orb_val.text())
                if self.current_selected_x != -1: # Works for file labels and squares
                    self.config_values["orbTargets"][self.current_selected_x] = orb_val
            
            if self.cart_group.isVisible():
                cart_val = int(self.selected_square_info_cart_val.text())
                if self.current_selected_y != -1: # Works for rank labels and squares
                    rank_idx = 7 - self.current_selected_y
                    self.config_values["cartTargets"][rank_idx] = cart_val
                    
            QMessageBox.information(self, "Update", "Position(s) updated")
        except ValueError: 
            QMessageBox.warning(self, "Input Error", "Invalid number for position.")
        self.update_board_info_box() # Refresh to show stored value

    def go_to_selected_board_square(self):
        if not self.current_selected_square_text or self.current_selected_is_label:
            QMessageBox.warning(self, "Go To Error", "A full board square must be selected.")
            return
        self.serial_handler.send_command(f"move {self.current_selected_square_text.lower()}")

    def move_esp_to_displayed_board_values(self): 
        if not self.current_selected_square_text:
            QMessageBox.warning(self, "Error", "No board element selected.")
            return

        orb_val_str = self.selected_square_info_orb_val.text()
        cart_val_str = self.selected_square_info_cart_val.text()
        commands_sent = 0

        if self.selected_square_info_orb_val.isVisible() and orb_val_str:
            try:
                orb_pos = int(orb_val_str)
                self.serial_handler.send_command(f"gotoorb {orb_pos}")
                commands_sent += 1
            except ValueError:
                QMessageBox.warning(self, "Input Error", f"Orb value '{orb_val_str}' is not a valid number.")
                return # Stop if one value is bad

        if self.selected_square_info_cart_val.isVisible() and cart_val_str:
            try:
                cart_pos = int(cart_val_str)
                # For cart, we should also send safety commands if applicable
                # This is tricky as safety depends on target. The ESP "gotocart" should handle it.
                self.serial_handler.send_command(f"gotocart {cart_pos}")
                commands_sent += 1
            except ValueError:
                QMessageBox.warning(self, "Input Error", f"Cart value '{cart_val_str}' is not a valid number.")
                return

        if commands_sent == 0:
            QMessageBox.information(self, "Info", "No position values entered or visible to send.")

    def get_esp_target_for_square(self):
        if self.current_selected_square_text and not self.current_selected_is_label:
            self.serial_handler.send_command(f"getsquarepos {self.current_selected_square_text.lower()}")

    def parse_esp32_response(self, line):
        return
        # This method will be connected to serial_handler.data_received signal
        #print(f"BoardTab received: {line}") # For debugging
        if line.startswith("SQPOS:"):
            try:
                json_data = json.loads(line[6:])
                square = json_data.get("square", "??").upper() # ESP sends lowercase
                orb_val = json_data.get("orb", "N/A")
                cart_val = json_data.get("cart", "N/A")

                # Only update if the currently selected square matches the response
                if self.current_selected_square_text == square and not self.current_selected_is_label:
                    self.selected_square_info_orb_val.setText(str(orb_val))
                    self.selected_square_info_cart_val.setText(str(cart_val))
                    print(f"Updated info box for {square} from ESP32 response.")
            except json.JSONDecodeError:
                print(f"BoardTab: Error decoding SQPOS JSON: {line}")
        # Add parsing for other relevant messages if needed by this tab
        
def load_fields_from_config(self):
    print("BoardTab: Reloading fields from config.")
    # Re-trigger info box update based on current selection
    self.update_board_info_box()