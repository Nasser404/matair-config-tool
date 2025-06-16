from PyQt5.QtWidgets import QFrame, QHBoxLayout, QPushButton
from PyQt5.QtCore import Qt

class BottomToolbox(QFrame):
    def __init__(self, config_values_ref, serial_handler_ref, show_config_callback, parent=None):
        super().__init__(parent)
        self.config_values = config_values_ref
        self.serial_handler = serial_handler_ref
        self.show_config_callback = show_config_callback # Callback to MainWindow method

        self.setFrameShape(QFrame.StyledPanel)
        self.setFixedHeight(80)
        layout = QHBoxLayout(self)
        layout.setAlignment(Qt.AlignLeft)

        buttons_info = [
            ("Home All", "homeall"), ("LA Extend", "la_ext"), ("LA Retract", "la_ret"),
            ("Grip Open", "gripopen"), ("Grip Close", "gripclose"),
            ("Test Take", "take"), ("Test Release", "release")
        ]
        for text, cmd in buttons_info:
            btn = QPushButton(text)
            btn.clicked.connect(lambda checked=False, c=cmd: self.serial_handler.send_command(c))
            layout.addWidget(btn)

        btn_goto_cz = QPushButton("Go to CZ Dropoff")
        btn_goto_cz.clicked.connect(self.go_to_capture_dropoff)
        layout.addWidget(btn_goto_cz)

        btn_goto_board_center = QPushButton("Go to Board Center")
        btn_goto_board_center.clicked.connect(lambda: self.serial_handler.send_command("move d4"))
        layout.addWidget(btn_goto_board_center)

        layout.addStretch()
        btn_save_config = QPushButton("Generate/Show Config.h")
        btn_save_config.clicked.connect(self.show_config_callback) # Call MainWindow's method
        layout.addWidget(btn_save_config)

    def go_to_capture_dropoff(self):
        cart_pos = self.config_values.get("CART_CAPTURE_POS", 2250)
        rot_angle = self.config_values.get("GRIPPER_ROT_CAPTURE", 62)
        self.serial_handler.send_command(f"servorot {rot_angle}")
        self.serial_handler.send_command(f"gotocart {cart_pos}")