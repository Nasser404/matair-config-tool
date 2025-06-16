from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QGridLayout, QLabel, QLineEdit,
                             QPushButton, QGroupBox, QMessageBox, QSizePolicy)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt

class NetworkTabWidget(QWidget):
    def __init__(self, config_values_ref, parent=None): # No serial_handler needed for this tab
        super().__init__(parent)
        self.config_values = config_values_ref

        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)

        network_config_group = QGroupBox("Network Default Credentials & Server")
        network_config_group.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        config_layout = QGridLayout(network_config_group)

        self.config_fields = {} # To store QLineEdit widgets

        def add_network_config_row(layout, label_text, config_key, default_value, row_idx, is_password=False):
            label = QLabel(label_text)
            line_edit = QLineEdit()
            line_edit.setText(str(self.config_values.get(config_key, default_value)))
            if is_password:
                line_edit.setEchoMode(QLineEdit.Password)
            line_edit.setPlaceholderText(str(default_value))
            layout.addWidget(label, row_idx, 0)
            layout.addWidget(line_edit, row_idx, 1)
            self.config_fields[config_key] = line_edit
            return row_idx + 1

        row = 0
        row = add_network_config_row(config_layout, "Default WiFi SSID:", "DEFAULT_SSID", "", row)
        row = add_network_config_row(config_layout, "Default WiFi Password:", "DEFAULT_PWD", "", row, is_password=True)
        row = add_network_config_row(config_layout, "Default Server Host/IP:", "DEFAULT_HOST", "127.0.0.1", row)
        row = add_network_config_row(config_layout, "Default Server Port:", "DEFAULT_PORT", 29920, row)
        # ORB_ID is static for now, not added here.

        main_layout.addWidget(network_config_group)

        self.update_network_configs_button = QPushButton("Update Network Configs in App")
        self.update_network_configs_button.clicked.connect(self.update_all_network_configs_in_app)
        main_layout.addWidget(self.update_network_configs_button, 0, Qt.AlignLeft) # Align button left

        main_layout.addStretch()

    def load_fields_from_config(self): # Call if CONFIG_VALUES is reloaded externally
        for key, line_edit_widget in self.config_fields.items():
            print(str(self.config_values.get(key, "")))
            line_edit_widget.setText(str(self.config_values.get(key, "")))

    def update_all_network_configs_in_app(self):
        try:
            # Strings are taken as is
            self.config_values["DEFAULT_SSID"] = self.config_fields["DEFAULT_SSID"].text()
            self.config_values["DEFAULT_PWD"] = self.config_fields["DEFAULT_PWD"].text()
            self.config_values["DEFAULT_HOST"] = self.config_fields["DEFAULT_HOST"].text()
            # Port needs to be int
            self.config_values["DEFAULT_PORT"] = int(self.config_fields["DEFAULT_PORT"].text())
            QMessageBox.information(self, "Success", "Network configuration parameters updated in app memory.")
        except ValueError:
            QMessageBox.warning(self, "Input Error", "Invalid number for Port.")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not update network configs: {e}")
        # self.load_fields_from_config() # No need to reload if directly updating from current text