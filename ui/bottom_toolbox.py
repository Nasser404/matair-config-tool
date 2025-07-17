from PyQt5.QtWidgets import (QFrame, QHBoxLayout, QPushButton, QGroupBox, QSizePolicy,
                             QMessageBox)
from PyQt5.QtCore import Qt

class BottomToolbox(QFrame):
    def __init__(self, config_values_ref, serial_handler_ref, show_config_callback, parent=None):
        super().__init__(parent)
        self.config_values = config_values_ref
        self.serial_handler = serial_handler_ref
        self.show_config_callback = show_config_callback

        self.setFrameShape(QFrame.StyledPanel)
        self.setFixedHeight(90) # Increased height slightly for groupbox
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)

        # --- Action Buttons Group ---
        action_group = QGroupBox("Common Actions")
        action_layout = QHBoxLayout(action_group)
        action_layout.setAlignment(Qt.AlignLeft)

        # Helper to create buttons
        def create_action_button(text, command, tooltip=""):
            btn = QPushButton(text)
            btn.setToolTip(tooltip)
            btn.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
            btn.clicked.connect(lambda checked=False, c=command: self.serial_handler.send_command(c))
            return btn

        action_layout.addWidget(create_action_button("Home All", "homeall", "Start homing sequence for all steppers."))
        
        # Separator for clarity
        separator1 = QFrame()
        separator1.setFrameShape(QFrame.VLine)
        separator1.setFrameShadow(QFrame.Sunken)
        action_layout.addWidget(separator1)

        action_layout.addWidget(create_action_button("LA Extend", "la_ext_timed", "Extend linear actuator for the configured time."))
        action_layout.addWidget(create_action_button("LA Retract", "la_ret", "Retract linear actuator, checking sensor."))
        
        separator2 = QFrame()
        separator2.setFrameShape(QFrame.VLine)
        separator2.setFrameShadow(QFrame.Sunken)
        action_layout.addWidget(separator2)
        
        action_layout.addWidget(create_action_button("Grip Open", "gripopen", "Move gripper servo to the configured 'Open' angle."))
        action_layout.addWidget(create_action_button("Grip Close", "gripclose", "Move gripper servo to the configured 'Close' angle."))
        
        separator3 = QFrame()
        separator3.setFrameShape(QFrame.VLine)
        separator3.setFrameShadow(QFrame.Sunken)
        action_layout.addWidget(separator3)
        
        action_layout.addWidget(create_action_button("Test Take", "take", "Execute the full blocking 'take' sequence."))
        action_layout.addWidget(create_action_button("Test Release", "release", "Execute the full blocking 'release' sequence."))

        # --- Position Shortcut Buttons ---
        pos_group = QGroupBox("Position Shortcuts")
        pos_layout = QHBoxLayout(pos_group)
        pos_layout.setAlignment(Qt.AlignLeft)

        btn_goto_cz = QPushButton("Go to CZ Dropoff")
        btn_goto_cz.setToolTip("Moves the Cart to the Capture Zone dropoff position.\nSafety checks will handle gripper rotation.")
        btn_goto_cz.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        btn_goto_cz.clicked.connect(self.go_to_capture_dropoff)
        pos_layout.addWidget(btn_goto_cz)

        btn_goto_board_center = QPushButton("Go to Board Center")
        btn_goto_board_center.setToolTip("Sends 'move d4' command to move to the approximate board center.")
        btn_goto_board_center.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        btn_goto_board_center.clicked.connect(lambda: self.serial_handler.send_command("move d4"))
        pos_layout.addWidget(btn_goto_board_center)


        # --- App-level Buttons ---
        app_group = QGroupBox("Application")
        app_layout = QHBoxLayout(app_group)
        app_layout.setAlignment(Qt.AlignRight)

        btn_save_config = QPushButton("Generate/Show Config.h")
        btn_save_config.setToolTip("Generate C++ header file content from all current app values.")
        btn_save_config.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        btn_save_config.clicked.connect(self.show_config_callback)
        app_layout.addWidget(btn_save_config)


        main_layout.addWidget(action_group, 3) # Action group takes more space
        main_layout.addWidget(pos_group, 2)    # Position group
        main_layout.addStretch(1)              # Flexible space
        main_layout.addWidget(app_group, 1)    # App group on the right


    def go_to_capture_dropoff(self):
        """
        Sends the command to move the cart to the capture dropoff position.
        The ESP32's `gotocart` command should handle all necessary safety checks,
        including rotating the gripper to the safe board angle if needed.
        Moving the gripper TO the capture angle should be part of a full
        `do ... captX` sequence, not this simple position shortcut.
        """
        try:
            cart_pos = int(self.config_values.get("CART_CAPTURE_POS", 2250))
            # The only command we need to send is to move the cart.
            # The ESP32's internal safety checks will handle the rest.
            print(f"Sending command to move cart to CZ Dropoff position: {cart_pos}")
            self.serial_handler.send_command(f"gotocart {cart_pos}")
        except ValueError:
            QMessageBox.warning(self, "Config Error", "CART_CAPTURE_POS in config is not a valid number.")