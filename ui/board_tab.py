from PyQt5.QtWidgets import QWidget, QHBoxLayout, QGridLayout, QLabel, QLineEdit, QPushButton, QFrame, QGroupBox, QMessageBox, QVBoxLayout
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt
import json # For parsing responses

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
        self.config_values = config_values_ref # Reference to global CONFIG_VALUES
        self.serial_handler = serial_handler_ref # Reference to SerialHandler instance

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
        info_layout = QVBoxLayout() # Use QVBoxLayout for better arrangement
        self.info_box.setFixedWidth(250)

        self.selected_element_label = QLabel("Selected: None")
        self.selected_element_label.setFont(QFont("Arial", 12, QFont.Bold))
        info_layout.addWidget(self.selected_element_label)

        # Orb/File Info
        orb_layout = QHBoxLayout()
        self.selected_square_info_orb_label = QLabel("Orb (File) Target:")
        self.selected_square_info_orb_val = QLineEdit()
        self.selected_square_info_orb_val.setPlaceholderText("e.g., 350")
        orb_layout.addWidget(self.selected_square_info_orb_label)
        orb_layout.addWidget(self.selected_square_info_orb_val)
        info_layout.addLayout(orb_layout)

        # Cart/Rank Info
        cart_layout = QHBoxLayout()
        self.selected_square_info_cart_label = QLabel("Cart (Rank) Target:")
        self.selected_square_info_cart_val = QLineEdit()
        self.selected_square_info_cart_val.setPlaceholderText("e.g., 4450")
        cart_layout.addWidget(self.selected_square_info_cart_label)
        cart_layout.addWidget(self.selected_square_info_cart_val)
        info_layout.addLayout(cart_layout)
        
        self.update_pos_button = QPushButton("Update Position in App")
        self.update_pos_button.clicked.connect(self.update_config_from_infobox)
        info_layout.addWidget(self.update_pos_button)
        
        self.go_to_square_button = QPushButton("Go to Square") # Renamed from go_to_pos_button
        self.go_to_square_button.clicked.connect(self.go_to_selected_board_square) # Renamed slot
        info_layout.addWidget(self.go_to_square_button)

        # <<< NEW BUTTON >>>
        self.move_to_displayed_vals_button = QPushButton("Move Steppers to Displayed Values")
        self.move_to_displayed_vals_button.clicked.connect(self.move_esp_to_displayed_board_values)
        info_layout.addWidget(self.move_to_displayed_vals_button)
        # <<< END NEW BUTTON >>>
        
        self.get_esp_pos_button = QPushButton("Get ESP Target for Square")
        self.get_esp_pos_button.clicked.connect(self.get_esp_target_for_square)
        info_layout.addWidget(self.get_esp_pos_button)

        info_layout.addStretch()
        self.info_box.setLayout(info_layout)
        layout.addWidget(self.info_box, 1)

        self.current_selected_square_text = ""
        self.current_selected_is_label = False
        self.current_selected_x = -1 # File index (0-7 for A-H)
        self.current_selected_y = -1 # Rank index from top (0 for '8', 7 for '1')

        if self.serial_handler:
            self.serial_handler.data_received.connect(self.parse_esp32_response)


    def on_board_element_click(self):
        sender = self.sender()
        self.current_selected_square_text = sender.text()
        self.current_selected_is_label = sender.is_label
        self.current_selected_x = sender.x
        self.current_selected_y = sender.y
        self.update_board_info_box()
        if not sender.is_label:
            self.get_esp_target_for_square()

    def update_board_info_box(self):
        if not self.current_selected_square_text:
            # ... (logic to hide/clear info box elements) ...
            self.selected_element_label.setText("Selected: None")
            self.selected_square_info_orb_val.setText("")
            self.selected_square_info_cart_val.setText("")
            self.selected_square_info_orb_label.setVisible(False) # etc.
            return

        self.selected_element_label.setText(f"Selected: {self.current_selected_square_text}")
        orb_targets = self.config_values.get("orbTargets", [0]*8)
        cart_targets = self.config_values.get("cartTargets", [0]*8)

        if self.current_selected_is_label:
            if self.current_selected_x != -1: # File
                self.selected_square_info_orb_label.setText(f"Orb ({self.current_selected_square_text}) Target:")
                self.selected_square_info_orb_val.setText(str(orb_targets[self.current_selected_x]))
                self.selected_square_info_orb_label.setVisible(True); self.selected_square_info_orb_val.setVisible(True)
                self.selected_square_info_cart_label.setVisible(False); self.selected_square_info_cart_val.setVisible(False)
            elif self.current_selected_y != -1: # Rank
                rank_idx = 7 - self.current_selected_y
                self.selected_square_info_cart_label.setText(f"Cart ({self.current_selected_square_text}) Target:")
                self.selected_square_info_cart_val.setText(str(cart_targets[rank_idx]))
                self.selected_square_info_orb_label.setVisible(False); self.selected_square_info_orb_val.setVisible(False)
                self.selected_square_info_cart_label.setVisible(True); self.selected_square_info_cart_val.setVisible(True)
        else: # Square
            file_idx = self.current_selected_x
            rank_idx = 7 - self.current_selected_y
            self.selected_square_info_orb_label.setText(f"Orb ({chr(ord('A') + file_idx)}) Target:")
            self.selected_square_info_orb_val.setText(str(orb_targets[file_idx]))
            self.selected_square_info_cart_label.setText(f"Cart ({8 - rank_idx}) Target:") # Rank display 1-8
            self.selected_square_info_cart_val.setText(str(cart_targets[rank_idx]))
            self.selected_square_info_orb_label.setVisible(True); self.selected_square_info_orb_val.setVisible(True)
            self.selected_square_info_cart_label.setVisible(True); self.selected_square_info_cart_val.setVisible(True)

    def update_config_from_infobox(self):
        if not self.current_selected_square_text: return
        try:
            if self.current_selected_is_label:
                if self.current_selected_x != -1: # File
                    self.config_values["orbTargets"][self.current_selected_x] = int(self.selected_square_info_orb_val.text())
                elif self.current_selected_y != -1: # Rank
                    self.config_values["cartTargets"][7 - self.current_selected_y] = int(self.selected_square_info_cart_val.text())
            else: # Square
                self.config_values["orbTargets"][self.current_selected_x] = int(self.selected_square_info_orb_val.text())
                self.config_values["cartTargets"][7 - self.current_selected_y] = int(self.selected_square_info_cart_val.text())
            QMessageBox.information(self, "Update", "Position updated in app. Save to generate config.h.")
        except ValueError: QMessageBox.warning(self, "Input Error", "Invalid number for position.")
        self.update_board_info_box()

    def go_to_selected_board_square(self): # Renamed method
        if not self.current_selected_square_text:
            QMessageBox.warning(self, "Go To Error", "No element selected.")
            return
        
        if self.current_selected_is_label:
            QMessageBox.information(self, "Info", "Sending individual goto for File/Rank label.\nUse 'Move Steppers to Displayed Values' to send entered value, or click a square.")
            # For labels, the original 'Go to Position' (now go_to_selected_board_square) will use config values.
            # To send the *displayed* (potentially edited) value for a label:
            if self.current_selected_x != -1: # File label
                orb_pos_str = self.selected_square_info_orb_val.text()
                if orb_pos_str.isdigit(): self.serial_handler.send_command(f"gotoorb {orb_pos_str}")
                else: QMessageBox.warning(self, "Input Error", "Orb value is not a number.")
            elif self.current_selected_y != -1: # Rank label
                cart_pos_str = self.selected_square_info_cart_val.text()
                if cart_pos_str.isdigit(): self.serial_handler.send_command(f"gotocart {cart_pos_str}")
                else: QMessageBox.warning(self, "Input Error", "Cart value is not a number.")
        else: # Full square
            self.serial_handler.send_command(f"move {self.current_selected_square_text.lower()}")

    def move_esp_to_displayed_board_values(self): # <<< NEW METHOD
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
            #self.serial_handler.send_command(f"getsquarepos {self.current_selected_square_text.lower()}")
            pass

    def parse_esp32_response(self, line):
        # This method will be connected to serial_handler.data_received signal
        print(f"BoardTab received: {line}") # For debugging
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