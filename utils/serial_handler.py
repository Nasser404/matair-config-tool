import serial
import serial.tools.list_ports
from PyQt5.QtCore import QObject, pyqtSignal, QTimer
from PyQt5.QtWidgets import QGroupBox, QHBoxLayout, QLabel, QComboBox, QPushButton, QMessageBox
import json


SERIAL_TIMEOUT = 0.1 # Shorter timeout for non-blocking read
SERIAL_BAUDRATE = 115200

class SerialHandler(QObject):
    # Signals
    connection_status_changed = pyqtSignal(bool, str) # connected (bool), port_name/message (str)
    data_received = pyqtSignal(str) # Raw line received from ESP32
    # Add more specific signals if needed, e.g., position_update_received = pyqtSignal(dict)

    def __init__(self, parent_window=None): # parent_window for showing QMessageBox
        super().__init__()
        self.serial_connection = None
        self.connected_port = None
        self.parent_window = parent_window

        self.serial_read_timer = QTimer(self)
        self.serial_read_timer.timeout.connect(self._read_serial_data)
        
        self._init_ui()

    def _init_ui(self):
        # Create UI elements for serial connection
        self.serial_group = QGroupBox("Serial Connection")
        serial_layout = QHBoxLayout()
        self.port_label = QLabel("Port:")
        self.port_combo_box = QComboBox()
        self.refresh_ports_button = QPushButton("Refresh Ports")
        self.refresh_ports_button.clicked.connect(self.populate_serial_ports)
        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self.toggle_connection)
        self.status_label = QLabel("Not Connected")
        self.status_label.setStyleSheet("color: red;")

        serial_layout.addWidget(self.port_label)
        serial_layout.addWidget(self.port_combo_box)
        serial_layout.addWidget(self.refresh_ports_button)
        serial_layout.addWidget(self.connect_button)
        serial_layout.addStretch()
        serial_layout.addWidget(self.status_label)
        self.serial_group.setLayout(serial_layout)
        self.populate_serial_ports()

    def get_serial_widgets(self):
        return self.serial_group

    def populate_serial_ports(self):
        self.port_combo_box.clear()
        ports = serial.tools.list_ports.comports()
        if not ports:
            self.port_combo_box.addItem("No ports found")
            self.port_combo_box.setEnabled(False)
        else:
            for port_info in ports:
                self.port_combo_box.addItem(f"{port_info.device} - {port_info.description}", port_info.device)
            self.port_combo_box.setEnabled(True)

    def toggle_connection(self):
        if self.serial_connection and self.serial_connection.is_open:
            self.disconnect_serial()
        else:
            self.connect_serial()

    def connect_serial(self):
        if self.port_combo_box.count() == 0 or self.port_combo_box.currentData() is None:
            QMessageBox.warning(self.parent_window, "Serial Error", "No serial port selected or available.")
            return False
        
        selected_port = self.port_combo_box.currentData()
        try:
            self.serial_connection = serial.Serial(selected_port, SERIAL_BAUDRATE, timeout=SERIAL_TIMEOUT)
            if self.serial_connection.is_open:
                self.connected_port = selected_port
                self.status_label.setText(f"Connected: {selected_port}")
                self.status_label.setStyleSheet("color: green;")
                self.connect_button.setText("Disconnect")
                self.port_combo_box.setEnabled(False)
                self.refresh_ports_button.setEnabled(False)
                self.serial_read_timer.start(50) # Read frequently
                self.send_command("ping") # Test connection
                self.connection_status_changed.emit(True, selected_port)
                print(f"Serial: Connected to {selected_port}")
                return True
            else:
                self.serial_connection = None # Ensure it's None if open fails
                QMessageBox.critical(self.parent_window, "Serial Error", f"Could not open port {selected_port}.")
        except serial.SerialException as e:
            QMessageBox.critical(self.parent_window, "Serial Error", f"Error connecting to {selected_port}: {e}")
        except Exception as e:
             QMessageBox.critical(self.parent_window, "Serial Error", f"An unexpected error occurred: {e}")
        
        self.disconnect_serial() # Ensure clean state on failure
        return False


    def disconnect_serial(self):
        if self.serial_connection and self.serial_connection.is_open:
            self.serial_read_timer.stop()
            self.serial_connection.close()
        self.serial_connection = None
        old_port = self.connected_port
        self.connected_port = None
        self.status_label.setText("Not Connected")
        self.status_label.setStyleSheet("color: red;")
        self.connect_button.setText("Connect")
        self.port_combo_box.setEnabled(True)
        self.refresh_ports_button.setEnabled(True)
        self.connection_status_changed.emit(False, old_port if old_port else "N/A")
        print(f"Serial: Disconnected from {old_port}" if old_port else "Serial: Disconnected")


    def is_connected(self):
        return self.serial_connection and self.serial_connection.is_open

    def send_command(self, command):
        if self.is_connected():
            try:
                print(f"SERIAL TX: {command}")
                self.serial_connection.write((command + "\n").encode('utf-8'))
                return True
            except Exception as e:
                print(f"Serial send error: {e}")
                self.disconnect_serial() # Disconnect on send error
                QMessageBox.warning(self.parent_window, "Serial Send Error", f"Error sending command: {e}\nDisconnected.")
        else:
            
            print("Serial: Not connected. Command not sent.")
            # QMessageBox.warning(self.parent_window, "Serial Error", "Not connected to ESP32 to send command.")
        return False

    def _read_serial_data(self):
        if not self.is_connected():
            return

        try:
            if self.serial_connection.in_waiting > 0:
                line = self.serial_connection.readline().decode('utf-8', errors='ignore').strip()
                if line:
                    print(f"SERIAL RX: {line}")
                    self.data_received.emit(line)
        except serial.SerialException as e: # Port might have been pulled
            print(f"Serial read error (port lost?): {e}")
            self.disconnect_serial()
            QMessageBox.critical(self.parent_window, "Serial Read Error", f"Lost connection or read error: {e}")
        except Exception as e:
            print(f"Unexpected serial read error: {e}")