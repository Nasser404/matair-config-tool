import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QTabWidget, 
                             QMessageBox, QFileDialog, QPushButton, QHBoxLayout) # Added QFileDialog
from PyQt5.QtCore import QTimer

# Import custom modules
from ui.board_tab import BoardTabWidget
from ui.capture_tab import CaptureTabWidget # Assuming this exists
from ui.servo_tab import ServoTabWidget     # Assuming this exists
from ui.stepper_tab import StepperTabWidget # Assuming this exists
from ui.actuator_tab import ActuatorTabWidget# Assuming this exists
from ui.test_tab import TestTabWidget       # Assuming this exists
from ui.network_tab import NetworkTabWidget   # Assuming this exists
from ui.bottom_toolbox import BottomToolbox
from ui.dialogs import ConfigOutputDialog
from utils.config_parser import load_config_values, generate_config_h_string, DEFAULT_CONFIG_VALUES # Import DEFAULT_CONFIG_VALUES
from utils.serial_handler import SerialHandler

# Global Configuration
CONFIG_VALUES = {} # Will be populated by load_config_values

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Mat@ir Configuration Tool")
        self.setGeometry(100, 100, 1000, 750)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        
        global CONFIG_VALUES # Ensure we are working with the global
        CONFIG_VALUES.clear() # Ensure it's empty before populating
        CONFIG_VALUES = DEFAULT_CONFIG_VALUES.copy() # Initialize with default
        
        self.init_ui_components()
         
         
    def init_ui_components(self) :
        # This method is called AFTER CONFIG_VALUES has its initial values
        # (either defaults or loaded from config.h)
        
        # --- Serial and File Operations UI ---
        top_bar_layout = QHBoxLayout()
        self.serial_handler = SerialHandler(self)
        top_bar_layout.addWidget(self.serial_handler.get_serial_widgets())
        top_bar_layout.addStretch(1)
        self.load_config_button = QPushButton("Load config.h File...")
        self.load_config_button.clicked.connect(self.prompt_load_config_file)
        top_bar_layout.addWidget(self.load_config_button)
        self.main_layout.addLayout(top_bar_layout)

        self.tabs = QTabWidget()
        self.main_layout.addWidget(self.tabs)

        # --- Initialize Tabs (Pass THE GLOBAL CONFIG_VALUES reference) ---
        self.board_tab_widget = BoardTabWidget(CONFIG_VALUES, self.serial_handler, self)
        self.tabs.addTab(self.board_tab_widget, "Board Config")

        self.capture_tab_widget = CaptureTabWidget(CONFIG_VALUES, self.serial_handler, self)
        self.tabs.addTab(self.capture_tab_widget, "Capture Zone")

        self.servo_tab_widget = ServoTabWidget(CONFIG_VALUES, self.serial_handler, self)
        self.tabs.addTab(self.servo_tab_widget, "Servos")

        self.stepper_tab_widget = StepperTabWidget(CONFIG_VALUES, self.serial_handler, self)
        self.tabs.addTab(self.stepper_tab_widget, "Steppers")

        self.actuator_tab_widget = ActuatorTabWidget(CONFIG_VALUES, self.serial_handler, self)
        self.tabs.addTab(self.actuator_tab_widget, "Linear Actuator")
        
        self.network_tab_widget = NetworkTabWidget(CONFIG_VALUES, self)
        self.tabs.addTab(self.network_tab_widget, "Network Config")

        self.test_tab_widget = TestTabWidget(CONFIG_VALUES, self.serial_handler, self)
        self.tabs.addTab(self.test_tab_widget, "Test Moves")

        self.bottom_toolbox_widget = BottomToolbox(CONFIG_VALUES, self.serial_handler, self.show_generated_config, self)
        self.main_layout.addWidget(self.bottom_toolbox_widget)

        # Initial population of all tab fields with current CONFIG_VALUES
        self.refresh_all_tab_fields()



    def load_and_update_config_from_file(self, file_path, silent_if_not_found=False):
        global CONFIG_VALUES
        print(f"Attempting to load config from: {file_path}")
        loaded_dict = load_config_values(file_path) # This now always returns a dictionary

        CONFIG_VALUES.clear() # Clear the current global
        CONFIG_VALUES.update(loaded_dict) # Update with new values (or defaults if load failed)

        if not silent_if_not_found:
            # Check if loaded_dict is different from default by comparing a few key values
            # or by checking if the filepath load was successful (needs flag from parser)
            # For now, a simple message:
            if file_path == "config.h" and id(loaded_dict) == id(DEFAULT_CONFIG_VALUES): # Crude check if it fell back
                QMessageBox.information(self, "Config Notice", f"Default config.h not found or failed to parse. Using application defaults.")
            else:
                QMessageBox.information(self, "Config Loaded", f"Configuration applied from:\n{file_path}")
        
        # If UI components exist, refresh them
        if hasattr(self, 'tabs'): # Check if tabs have been initialized
            self.refresh_all_tab_fields()
        return True

    def prompt_load_config_file(self):
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(self, "Load config.h File", "",
                                                   "Header Files (*.h);;All Files (*)", options=options)
        if file_path:
            self.load_and_update_config_from_file(file_path)

    def refresh_all_tab_fields(self): # Renamed for clarity
        """Calls the 'load_fields_from_config' method on each tab to populate its UI."""
        print("MainWindow: Refreshing all tab UI fields from CONFIG_VALUES...")
        if hasattr(self, 'board_tab_widget'): self.board_tab_widget.update_board_info_box() # Special case
        if hasattr(self, 'capture_tab_widget'): self.capture_tab_widget.load_fields_from_config()
        if hasattr(self, 'servo_tab_widget'): self.servo_tab_widget.load_fields_from_config()
        if hasattr(self, 'stepper_tab_widget'): self.stepper_tab_widget.load_config_fields()
        if hasattr(self, 'actuator_tab_widget'): self.actuator_tab_widget.load_config_fields()
        if hasattr(self, 'network_tab_widget'): self.network_tab_widget.load_fields_from_config()
        print("MainWindow: Tab UI fields refreshed.")

    def show_generated_config(self):
        global CONFIG_VALUES
        config_h_content = generate_config_h_string(CONFIG_VALUES)
        dialog = ConfigOutputDialog(config_h_content, self)
        dialog.exec_()

    def closeEvent(self, event):
        # Ensure serial port is closed when application exits
        if self.serial_handler.is_connected():
            self.serial_handler.disconnect_serial()
        event.accept()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_win = MainWindow()
    main_win.show()
    sys.exit(app.exec_())