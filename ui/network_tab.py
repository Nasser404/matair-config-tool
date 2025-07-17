from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QGridLayout, QLabel, QLineEdit,
                             QPushButton, QGroupBox, QMessageBox, QSizePolicy)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt
# Import the defaults to use them safely
from utils.config_parser import DEFAULT_CONFIG_VALUES

class NetworkTabWidget(QWidget):
    def __init__(self, config_values_ref, parent=None): # No serial_handler needed for config updates
        super().__init__(parent)
        self.config_values = config_values_ref

        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)

        network_config_group = QGroupBox("Network Default Credentials & Server")
        network_config_group.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        config_layout = QGridLayout(network_config_group)

        self.config_fields = {} # To store QLineEdit widgets

        row = 0
        row = self.add_network_config_row(config_layout, "Default WiFi SSID:", "DEFAULT_SSID", row)
        row = self.add_network_config_row(config_layout, "Default WiFi Password:", "DEFAULT_PWD", row, is_password=True)
        row = self.add_network_config_row(config_layout, "Default Server Host/IP:", "DEFAULT_HOST", row)
        row = self.add_network_config_row(config_layout, "Default Server Port:", "DEFAULT_PORT", row)

        main_layout.addWidget(network_config_group)

        self.update_network_configs_button = QPushButton("Update Network Configs")
        self.update_network_configs_button.setToolTip("Saves these values to the app memory for config generation.\nDoes not send to ESP32 as these are boot-time values.")
        self.update_network_configs_button.clicked.connect(self.update_all_network_configs_in_app)
        main_layout.addWidget(self.update_network_configs_button, 0, Qt.AlignLeft)

        main_layout.addStretch()

        # Load initial values from the global config dict
        self.load_fields_from_config()


    def add_network_config_row(self, layout, label_text, config_key, row_idx, is_password=False):
        """A method to create a row in the grid layout for a network config item."""
        default_value = self.config_values.get(config_key, "")
        label = QLabel(label_text)
        line_edit = QLineEdit()
        line_edit.setText(str(default_value))
        if is_password:
            line_edit.setEchoMode(QLineEdit.Password)
        # Use placeholder for string types if value is empty
        if isinstance(default_value, str) and not default_value:
             line_edit.setPlaceholderText("<Not Set>")
        else:
             line_edit.setPlaceholderText(str(default_value))

        layout.addWidget(label, row_idx, 0)
        layout.addWidget(line_edit, row_idx, 1)
        self.config_fields[config_key] = line_edit
        return row_idx + 1

    def load_fields_from_config(self):
        """Populates the input fields with values from the self.config_values dictionary."""
        print("NetworkTab: Loading fields from config.")
        for key, line_edit_widget in self.config_fields.items():
            default_val = DEFAULT_CONFIG_VALUES.get(key, "")
            line_edit_widget.setText(str(self.config_values.get(key, default_val)))
        print("NetworkTab: Fields reloaded.")

    def update_all_network_configs_in_app(self):
        """Updates the central config dictionary from the UI fields."""
        try:
            # Strings are taken as is
            self.config_values["DEFAULT_SSID"] = self.config_fields["DEFAULT_SSID"].text()
            self.config_values["DEFAULT_PWD"] = self.config_fields["DEFAULT_PWD"].text()
            self.config_values["DEFAULT_HOST"] = self.config_fields["DEFAULT_HOST"].text()
            # Port needs to be int
            self.config_values["DEFAULT_PORT"] = int(self.config_fields["DEFAULT_PORT"].text())
            
            # NOTE: We DO NOT send these with `setconfig`. These are default values used
            # by the main operational firmware when it can't load credentials from Preferences/Flash.
            # The calibration firmware connects using credentials already on the ESP32.
            # This button's purpose is to update the values for the *next time you generate config.h*.

            QMessageBox.information(self, "Success", "Network configuration parameters updated in app memory.\nThese values will be used when you generate the config.h file.")

        except ValueError:
            QMessageBox.warning(self, "Input Error", "Invalid number for Port. It must be an integer.")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not update network configs: {e}")