# ESP32 Chess Robot Configuration Tool

This repository contains the software for calibrating and configuring the "Mat@ir" Spherical Chess Robot. It consists of two main parts:

1.  **Calibration Firmware (`calibration_firmware.ino`):** A dedicated Arduino sketch for the ESP32 that provides a serial command interface to control all actuators.
2.  **Configuration App (Python/PyQt5):** A graphical user interface that communicates with the calibration firmware.

## How to Use


### Step 1: Upload the Calibration Firmware

1.  Open the `calibration_firmware/calibration_firmware.ino` sketch in the Arduino IDE.
2.  Ensure your board (`esp32dev` or similar) and the correct COM port are selected.
3.  Upload the firmware to your ESP32.
4.  Once uploaded, you can open the Serial Monitor (Baud Rate: **115200**) to see status messages. The ESP32 is now ready to receive commands.

### Step 2: Launch the Python Configuration App

1.  Make sure you have Python and the required libraries installed:
    ```bash
    pip install PyQt5 pyserial
    ```
2.  Navigate to the `esp32_config_tool` directory.
3.  Run the main application file:
    ```bash
    python main_app.py
    ```
    The application window should appear.

### Step 3: Connect to the ESP32



1.  **Select Port:** Choose your ESP32's COM port from the dropdown menu at the top of the application. If you don't see it, click "Refresh".
2.  **Connect:** Click the "Connect" button. The status label should turn green and display "Connected".

### Step 4: Calibrate Your Robot

The application is organized into tabs for different parts of the robot.

#### Using the Bottom Toolbox

The toolbox at the bottom of the window is always visible and provides quick access to common actions:
*   **Home All:** **This should be the first thing you do after connecting.** It moves all steppers to their limit switches to establish a zero position.
*   **LA Extend/Retract:** Perform a full timed extend or retract of the linear actuator.
*   **Grip Open/Close:** Move the gripper to its fully open or closed positions.
*   **Test Take/Release:** Run the complete, blocking "take" or "release" sequences to test the gripper and actuator timing.
*   **Go to CZ Dropoff:** A shortcut to move the Cart and Gripper to the position for interacting with the capture zone.

#### Board & Capture Zone Tabs

These tabs are for finding the exact stepper motor positions for each square and capture slot.

1.  **Select a Square/Slot:** Click on any square (e.g., "e4") on the "Board Config" tab or any slot number on the "Capture Zone" tab.
2.  **Go to Position:** In the info box on the right, click **"Move Steppers to Position"**. The robot will move to its currently configured position for that location.
3.  **Fine-Tune with Jog:** Use the **"Jog +"** and **"Jog -"** buttons for the Orb (File) and Cart (Rank) steppers to fine-tune the position until the gripper is perfectly centered.
4.  **Update in App:** Once you are happy with the position, click **"Update Position in App"**. This saves the new value *in the application's memory*.
5.  Repeat for all necessary squares and capture slots.


#### Stepper, Servo, & Actuator Tabs

These tabs allow for direct control and configuration of hardware parameters.

*   **Direct Control:** Enter a value in a "Target Position/Angle" field and click "Go" to move an actuator to a specific point.
*   **Jogging:** Use the "Jog" buttons to move an actuator continuously while the button is held.
*   **Configuration:** Adjust values like `STEPPER_SPEED`, `GripperOpen` angle, `ACTUATOR_TRAVEL_TIME_MS`, etc.
*   **Update Config:** Click the **"Update... Configs in App"** button on each tab to save your changes to the application's memory. This will also send the new values to the connected ESP32 so your next test uses the new settings immediately.

#### Network Tab

Use this tab to set the default WiFi SSID, Password, and Server Host/Port for your **main operational firmware**. These values are only used when generating the `config.h` file.

### Step 5: Generate and Save Your `config.h` File

Once you have finished calibrating all the positions and parameters, you are ready to generate the configuration file for your main robot firmware.

1.  In the bottom toolbox, click the **"Generate/Show Config.h"** button.
2.  A new window will appear showing the complete, formatted `config.h` content with all of your new values.
3.  **Copy to Clipboard:** Click this to copy the content. You can then paste it directly into your `config.h` file in your main project's source code.

