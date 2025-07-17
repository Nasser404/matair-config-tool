import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QTabWidget,
                             QMessageBox, QFileDialog, QPushButton, QHBoxLayout)
from PyQt5.QtCore import QTimer, pyqtSignal # Added pyqtSignal

# Import custom modules
from ui.board_tab import BoardTabWidget
from ui.capture_tab import CaptureTabWidget
from ui.servo_tab import ServoTabWidget
from ui.stepper_tab import StepperTabWidget
from ui.actuator_tab import ActuatorTabWidget
from ui.network_tab import NetworkTabWidget
from ui.test_tab import TestTabWidget
from ui.bottom_toolbox import BottomToolbox
from ui.dialogs import ConfigOutputDialog
from utils.config_parser import load_config_values, generate_config_h_string, DEFAULT_CONFIG_VALUES
from utils.serial_handler import SerialHandler

# Global Configuration Dictionary - The single source of truth for all config values.
CONFIG_VALUES = {}

class MainWindow(QMainWindow):
    # Signal to notify all child widgets that the main config has been updated (e.g., from a file load)
    config_updated_signal = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Mat@ir Configuration Tool")
        self.setGeometry(100, 100, 1000, 750) # Slightly larger for better spacing

        # --- Initialize Global Config with Defaults ---
        global CONFIG_VALUES
        CONFIG_VALUES.clear()
        CONFIG_VALUES.update(DEFAULT_CONFIG_VALUES.copy())

        # --- Setup Main UI Layout ---
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)

        # --- Initialize UI Components ---
        self.init_ui_components()

        # --- Final step: Attempt to load a default config file and populate UI ---
        # This happens after all widgets have been created and signals connected.
        self.load_config_from_file("config.h", silent_if_not_found=True)

    def init_ui_components(self):
        """Creates and organizes all UI widgets."""
        
        # --- Serial and File Operations UI ---
        top_bar_layout = QHBoxLayout()
        self.serial_handler = SerialHandler(self) # Serial handler is crucial
        top_bar_layout.addWidget(self.serial_handler.get_serial_widgets())
        top_bar_layout.addStretch(1)
        self.load_config_button = QPushButton("Load config.h File...")
        self.load_config_button.setToolTip("Open a file dialog to load a config.h file.")
        self.load_config_button.clicked.connect(self.prompt_load_config_file)
        top_bar_layout.addWidget(self.load_config_button)
        self.main_layout.addLayout(top_bar_layout)

        self.tabs = QTabWidget()
        self.main_layout.addWidget(self.tabs)

        # --- Initialize and Add Tabs ---
        # Each tab is given a reference to the global CONFIG_VALUES and the serial_handler
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

        # --- Initialize Bottom Toolbox ---
        self.bottom_toolbox_widget = BottomToolbox(CONFIG_VALUES, self.serial_handler, self.show_generated_config, self)
        self.main_layout.addWidget(self.bottom_toolbox_widget)

        # --- Connect the config update signal to each tab's refresh method ---
        # This is the clean way to tell all tabs to update themselves.
        self.config_updated_signal.connect(self.board_tab_widget.update_board_info_box)
        self.config_updated_signal.connect(self.capture_tab_widget.load_fields_from_config)
        self.config_updated_signal.connect(self.servo_tab_widget.load_fields_from_config)
        self.config_updated_signal.connect(self.stepper_tab_widget.load_fields_from_config)
        self.config_updated_signal.connect(self.actuator_tab_widget.load_fields_from_config)
        self.config_updated_signal.connect(self.network_tab_widget.load_fields_from_config)

    def load_config_from_file(self, file_path, silent_if_not_found=False):
        """Loads config from a file, updates the global CONFIG_VALUES, and emits a signal."""
        global CONFIG_VALUES
        print(f"Attempting to load config from: {file_path}")
        
        # load_config_values always returns a full dictionary (either from file or default)
        loaded_dict = load_config_values(file_path)

        # Check if the load was successful by seeing if it's different from the default dict
        # This is a simple heuristic. A better way might be for the parser to return a success flag.
        load_was_successful = (id(loaded_dict) != id(DEFAULT_CONFIG_VALUES))

        # Update the global dictionary in-place to preserve references
        CONFIG_VALUES.clear()
        CONFIG_VALUES.update(loaded_dict)
        
        if not silent_if_not_found:
            if load_was_successful:
                QMessageBox.information(self, "Config Loaded", f"Successfully applied configuration from:\n{file_path}")
            else:
                QMessageBox.warning(self, "Load Notice", f"Could not load or parse configuration from:\n{file_path}\n\nReverted to application defaults.")

        # Emit the signal to tell all tabs to refresh their UI fields
        self.config_updated_signal.emit()
        return True

    def prompt_load_config_file(self):
        """Opens a file dialog for the user to select a config.h file."""
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(self, "Load config.h File", "",
                                                   "Header Files (*.h);;All Files (*)", options=options)
        if file_path:
            self.load_config_from_file(file_path)

    def show_generated_config(self):
        """Generates the config.h content and shows it in a dialog."""
        global CONFIG_VALUES
        config_h_content = generate_config_h_string(CONFIG_VALUES)
        dialog = ConfigOutputDialog(config_h_content, self)
        dialog.exec_()

    def closeEvent(self, event):
        """Ensures serial port is closed when application exits."""
        if self.serial_handler.is_connected():
            self.serial_handler.disconnect_serial()
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_win = MainWindow()
    main_win.show()
    sys.exit(app.exec_())