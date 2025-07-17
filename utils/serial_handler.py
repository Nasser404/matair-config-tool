import serial
import serial.tools.list_ports
from PyQt5.QtCore import QObject, pyqtSignal, QTimer, QMutex, QMutexLocker
from PyQt5.QtWidgets import QGroupBox, QHBoxLayout, QLabel, QComboBox, QPushButton, QMessageBox
import json

# Constants
SERIAL_TIMEOUT = 0.1  # Timeout for readline() in seconds
SERIAL_BAUDRATE = 115200
READ_TIMER_INTERVAL_MS = 50 # How often to check for incoming serial data

class SerialHandler(QObject):
    # Signals to communicate with the rest of the application
    connection_status_changed = pyqtSignal(bool, str) # connected (bool), port_name/message (str)
    data_received = pyqtSignal(str) # Raw line received from ESP32

    def __init__(self, parent_window=None):
        super().__init__()
        self.serial_connection = None
        self.connected_port = None
        self.parent_window = parent_window
        self.is_disconnecting = False # Flag to prevent race conditions on disconnect

        # A Mutex is crucial for thread safety if communication gets very fast or complex
        # For now, it's good practice to protect the serial write operation.
        self.write_mutex = QMutex()

        # Timer for periodically reading serial data
        self.serial_read_timer = QTimer(self)
        self.serial_read_timer.timeout.connect(self._read_serial_data)
        
        # Initialize the UI components this handler manages
        self._init_ui()

    def _init_ui(self):
        self.serial_group = QGroupBox("Serial Connection")
        serial_layout = QHBoxLayout()
        serial_layout.addWidget(QLabel("Port:"))
        self.port_combo_box = QComboBox()
        self.refresh_ports_button = QPushButton("Refresh")
        self.refresh_ports_button.setToolTip("Refresh list of available serial ports")
        self.refresh_ports_button.clicked.connect(self.populate_serial_ports)
        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self.toggle_connection)
        self.status_label = QLabel("Not Connected")
        self.status_label.setStyleSheet("color: red; font-weight: bold;")
        
        serial_layout.addWidget(self.port_combo_box, 1) # Give combo box more stretch space
        serial_layout.addWidget(self.refresh_ports_button)
        serial_layout.addWidget(self.connect_button)
        serial_layout.addStretch()
        serial_layout.addWidget(self.status_label)
        self.serial_group.setLayout(serial_layout)
        
        self.populate_serial_ports()

    def get_serial_widgets(self):
        """Returns the QGroupBox containing all serial UI elements for embedding."""
        return self.serial_group

    def populate_serial_ports(self):
        """Finds and lists available COM ports."""
        if self.is_connected():
            return # Don't refresh while connected

        current_selection = self.port_combo_box.currentData()
        self.port_combo_box.clear()
        
        ports = sorted(serial.tools.list_ports.comports())
        found_ports = False
        for port_info in ports:
            # Filter for common USB-to-Serial chip descriptions
            if "USB" in port_info.description or "CH340" in port_info.description or \
               "CP210x" in port_info.description or "uart" in port_info.description.lower():
                self.port_combo_box.addItem(f"{port_info.device} - {port_info.description}", port_info.device)
                found_ports = True
        
        if not found_ports:
            self.port_combo_box.addItem("No suitable ports found")
            self.port_combo_box.setEnabled(False)
            self.connect_button.setEnabled(False)
        else:
            self.port_combo_box.setEnabled(True)
            self.connect_button.setEnabled(True)
            # Try to re-select the previously selected port if it still exists
            index = self.port_combo_box.findData(current_selection)
            if index != -1:
                self.port_combo_box.setCurrentIndex(index)

    def toggle_connection(self):
        if self.is_connected():
            self.disconnect_serial()
        else:
            self.connect_serial()

    def connect_serial(self):
        if self.is_connected(): return True
        if self.port_combo_box.count() == 0 or self.port_combo_box.currentData() is None:
            QMessageBox.warning(self.parent_window, "Serial Error", "No serial port selected.")
            return False
        
        selected_port = self.port_combo_box.currentData()
        try:
            # Open serial port
            self.serial_connection = serial.Serial(
                port=selected_port,
                baudrate=SERIAL_BAUDRATE,
                timeout=SERIAL_TIMEOUT,
                write_timeout=SERIAL_TIMEOUT # Add write timeout for safety
            )
            # Short delay to allow DTR/RTS to settle, may help with some ESP32 boards
            self.serial_connection.flushInput()
            self.serial_connection.flushOutput()
            QTimer.singleShot(50, self.finish_connection_setup) # Finish setup after a brief delay
            return True
        except serial.SerialException as e:
            QMessageBox.critical(self.parent_window, "Serial Error", f"Could not open port {selected_port}:\n{e}")
        except Exception as e:
             QMessageBox.critical(self.parent_window, "Connection Error", f"An unexpected error occurred:\n{e}")
        
        self.serial_connection = None # Ensure clean state on failure
        return False

    def finish_connection_setup(self):
        """Finalizes connection after a short delay."""
        if self.serial_connection and self.serial_connection.is_open:
            self.connected_port = self.serial_connection.port
            self.status_label.setText(f"Connected")
            self.status_label.setStyleSheet("color: green; font-weight: bold;")
            self.connect_button.setText("Disconnect")
            self.port_combo_box.setEnabled(False)
            self.refresh_ports_button.setEnabled(False)
            self.serial_read_timer.start(READ_TIMER_INTERVAL_MS)
            self.connection_status_changed.emit(True, self.connected_port)
            print(f"Serial: Connection to {self.connected_port} finalized.")
            self.send_command("ping") # Test with a ping
        else:
             # The connection might have failed in the short delay
             self.disconnect_serial()


    def disconnect_serial(self):
        if self.is_disconnecting: return # Prevent re-entry
        self.is_disconnecting = True

        self.serial_read_timer.stop()
        
        old_port = self.connected_port
        
        if self.serial_connection:
            try:
                self.serial_connection.close()
            except Exception as e:
                print(f"Error while closing serial port: {e}")
        
        self.serial_connection = None
        self.connected_port = None

        self.status_label.setText("Not Connected")
        self.status_label.setStyleSheet("color: red; font-weight: bold;")
        self.connect_button.setText("Connect")
        self.port_combo_box.setEnabled(True)
        self.refresh_ports_button.setEnabled(True)
        
        self.connection_status_changed.emit(False, old_port if old_port else "N/A")
        print(f"Serial: Disconnected from {old_port}" if old_port else "Serial: Disconnected")
        self.is_disconnecting = False

    def is_connected(self):
        return self.serial_connection and self.serial_connection.is_open

    def send_command(self, command):
        with QMutexLocker(self.write_mutex): # Protect write access
            if not self.is_connected():
                print("Serial: Not connected. Command not sent.")
                # Don't show a popup for every failed send, just log it.
                return False
            
            try:
                command_bytes = (command + "\n").encode('utf-8')
                self.serial_connection.write(command_bytes)
                if (command.startswith("getallpos") == False) :
                    print(f"SERIAL TX: {command}")
                return True
            except serial.SerialTimeoutException as e:
                print(f"Serial send timeout error: {e}")
                QMessageBox.warning(self.parent_window, "Serial Send Error", f"Timeout sending command: {e}")
                self.disconnect_serial()
            except Exception as e:
                print(f"Serial send error: {e}")
                QMessageBox.warning(self.parent_window, "Serial Send Error", f"Error sending command: {e}\nDisconnected.")
                self.disconnect_serial()
        return False

    def _read_serial_data(self):
        if not self.is_connected():
            return

        try:
            # Read all available lines in buffer to prevent lag
            while self.serial_connection.in_waiting > 0:
                line = self.serial_connection.readline().decode('utf-8', errors='ignore').strip()
                if line :
           
                    if (line.startswith("POS") == False) :
                        print(f"SERIAL RX: {line}")
                        
                    self.data_received.emit(line)
        except serial.SerialException as e:
            # This often happens if the USB cable is unplugged
            print(f"Serial read error (port likely lost): {e}")
            QMessageBox.critical(self.parent_window, "Serial Connection Lost", f"Lost connection to port:\n{e}")
            self.disconnect_serial()
        except Exception as e:
            print(f"Unexpected serial read error: {e}")