
import re

# DEFAULT_CONFIG_VALUES
DEFAULT_CONFIG_VALUES = {
    "DEFAULT_SSID": "", "DEFAULT_PWD": "", "DEFAULT_HOST": "127.0.0.1", "DEFAULT_PORT": 29920,
    "orbTargets": [4000, 3180, 2420, 1630, 840, 20, 5650, 4820],
    "cartTargets": [4480, 3850, 3200, 2520, 1960, 1360, 680, 0],
    "captureTargets": [
        2760, 2580, 2400, 2210, 2020, 1850, 1680, 1480, 1310, 1120, 920, 740,
        560, 380, 200, 30, 6240, 6060, 5880, 5690, 5510, 5330, 5140, 4950,
        4780, 4590, 4430, 4220, 4050, 3860, 3680, 3500
    ],
    "STEPPER_SPEED": 4000, "STEPPER_ACCEL": 5000, "HOMING_SPEED_CAPTURE": 1000,
    "HOMING_SPEED_CART_ORB": 1000, "HOMING_ACCEL": 1500, "GRIPPER_ROT_BOARD": 172,
    "GRIPPER_ROT_CAPTURE": 63, "CART_SAFETY_THRESHOLD": 2250,
    "CART_CAPTURE_HOME_THRESHOLD": 800, "CART_CAPTURE_POS": 2250,
    "GripperOpen": 140, "GripperClose": 45, "ACTUATOR_TRAVEL_TIME_MS": 650,
    "CAPTURE_HOME_BACKUP_STEPS": 200, "MANUAL_JOG_CART_SPEED": 1000,
    "MANUAL_JOG_ORB_SPEED": 500, "MANUAL_JOG_CAPTURE_SPEED": 500,
    "MANUAL_JOG_SERVO_INCREMENT": 15, "CART_MIN_POS": 10, "CART_MAX_POS": 4400,
    "ORB_MIN_POS": 10, "ORB_MAX_POS": 6000, "CAPTURE_MIN_POS": 100, "CAPTURE_MAX_POS": 6100
}


def load_config_values(filepath):
    """
    Loads configuration from a .h file. Starts with defaults and overwrites with
    any values found in the file. Returns a complete dictionary.
    """

    loaded_cfg = DEFAULT_CONFIG_VALUES.copy()
    try:
        with open(filepath, 'r') as f:
            content = f.read()
        print(f"Successfully read file: {filepath}")
    except (FileNotFoundError, Exception) as e:
        print(f"Warning: Could not read '{filepath}': {e}. Using all default values.")
        return loaded_cfg

   
    for key, default_value in DEFAULT_CONFIG_VALUES.items():
        # Build a specific regex pattern for each key
        
        # Handle Arrays
        if isinstance(default_value, list):
            # Pattern: const <any_type> KEY[<any_size>] = { ... };
            pattern = rf"const\s+\w+\s+{key}\[\d+\]\s*=\s*({{.+?}});"
            match = re.search(pattern, content, re.DOTALL) # DOTALL handles multi-line arrays
            if match:
                try:
                    values_str = match.group(1).strip("{} ")
                    # Clean up newlines, comments, and split
                    values_str = re.sub(r'//.*', '', values_str) # Remove comments
                    values_str = re.sub(r'\s+', '', values_str)   # Remove all whitespace
                    elements = values_str.split(',')
                    # Filter out potential empty strings from trailing commas
                    valid_elements = [int(el) for el in elements if el]
                    loaded_cfg[key] = valid_elements
                    # print(f"  Parsed array '{key}'") # Debug
                except (ValueError, IndexError) as e:
                    print(f"  WARNING: Could not parse array for key '{key}': {e}. Using default.")
                    loaded_cfg[key] = default_value # Revert to default on parse error
            continue # Move to next key

        # Handle Strings
        if isinstance(default_value, str):
            # Pattern: static const String KEY = "VALUE";
            pattern = rf"static\s+const\s+String\s+{key}\s*=\s*\"(.*?)\";"
            match = re.search(pattern, content)
            if match:
                loaded_cfg[key] = match.group(1)
                # print(f"  Parsed string '{key}'") # Debug
            continue

        # Handle all single Numeric values (int, float, long, etc.)
        if isinstance(default_value, (int, float)):
            # Pattern: const <any_type> KEY = VALUE;
            pattern = rf"const\s+\w+\s+{key}\s*=\s*([0-9.]+);"
            match = re.search(pattern, content)
            if match:
                try:
                    value_str = match.group(1)
                    # Cast to float if it contains a '.', otherwise int
                    loaded_cfg[key] = float(value_str) if '.' in value_str else int(value_str)
                    # print(f"  Parsed numeric '{key}'") # Debug
                except ValueError:
                    print(f"  WARNING: Could not parse numeric value for key '{key}': '{value_str}'. Using default.")
                    loaded_cfg[key] = default_value # Revert on parse error
            continue

    print(f"Config values parsed from {filepath}")
    return loaded_cfg


def generate_config_h_string(config_data):
    def format_array(data_list):
        lines = []
        for i in range(0, len(data_list), 8):
            chunk = ", ".join(map(str, data_list[i:i+8]))
            lines.append(chunk)
        return (",\n  ").join(lines)

    orb_targets_str = format_array(config_data.get("orbTargets", DEFAULT_CONFIG_VALUES["orbTargets"]))
    cart_targets_str = format_array(config_data.get("cartTargets", DEFAULT_CONFIG_VALUES["cartTargets"]))
    capture_targets_str = format_array(config_data.get("captureTargets", DEFAULT_CONFIG_VALUES["captureTargets"]))
    
    content = f"""\
#pragma once
#include <Arduino.h>

#define SSID_MAX_LEN    32
#define PWD_MAX_LEN     64
#define HOST_MAX_LEN    32

static const String  ORB_ID         = "ORB IVRY";
static const String  DEFAULT_SSID   = "{config_data.get("DEFAULT_SSID", DEFAULT_CONFIG_VALUES["DEFAULT_SSID"])}";
static const String  DEFAULT_PWD    = "{config_data.get("DEFAULT_PWD", DEFAULT_CONFIG_VALUES["DEFAULT_PWD"])}";
static const String  DEFAULT_HOST   = "{config_data.get("DEFAULT_HOST", DEFAULT_CONFIG_VALUES["DEFAULT_HOST"])}";
const uint32_t       DEFAULT_PORT   = {config_data.get("DEFAULT_PORT", DEFAULT_CONFIG_VALUES["DEFAULT_PORT"])};

// --- POSITION CONFIG ----
const uint16_t orbTargets[8] = {{
  {orb_targets_str}
}};   // a-h
const uint16_t cartTargets[8] = {{
  {cart_targets_str}
}};     // ranks 1-8
const uint16_t captureTargets[32] = {{
  {capture_targets_str}
}};

// --- Constants ---
const uint16_t STEPPER_SPEED = {config_data.get("STEPPER_SPEED", DEFAULT_CONFIG_VALUES["STEPPER_SPEED"])};
const uint16_t STEPPER_ACCEL = {config_data.get("STEPPER_ACCEL", DEFAULT_CONFIG_VALUES["STEPPER_ACCEL"])};
const uint16_t HOMING_SPEED_CAPTURE = {config_data.get("HOMING_SPEED_CAPTURE", DEFAULT_CONFIG_VALUES["HOMING_SPEED_CAPTURE"])};
const uint16_t HOMING_SPEED_CART_ORB = {config_data.get("HOMING_SPEED_CART_ORB", DEFAULT_CONFIG_VALUES["HOMING_SPEED_CART_ORB"])};
const uint16_t HOMING_ACCEL = {config_data.get("HOMING_ACCEL", DEFAULT_CONFIG_VALUES["HOMING_ACCEL"])};

const uint8_t GRIPPER_ROT_BOARD = {config_data.get("GRIPPER_ROT_BOARD", DEFAULT_CONFIG_VALUES["GRIPPER_ROT_BOARD"])};
const uint8_t GRIPPER_ROT_CAPTURE = {config_data.get("GRIPPER_ROT_CAPTURE", DEFAULT_CONFIG_VALUES["GRIPPER_ROT_CAPTURE"])};
const uint16_t CART_SAFETY_THRESHOLD = {config_data.get("CART_SAFETY_THRESHOLD", DEFAULT_CONFIG_VALUES["CART_SAFETY_THRESHOLD"])};
const uint16_t CART_CAPTURE_HOME_THRESHOLD = {config_data.get("CART_CAPTURE_HOME_THRESHOLD", DEFAULT_CONFIG_VALUES["CART_CAPTURE_HOME_THRESHOLD"])};
const uint16_t CART_CAPTURE_POS = {config_data.get("CART_CAPTURE_POS", DEFAULT_CONFIG_VALUES["CART_CAPTURE_POS"])};

const uint8_t GripperOpen = {config_data.get("GripperOpen", DEFAULT_CONFIG_VALUES["GripperOpen"])};
const uint8_t GripperClose = {config_data.get("GripperClose", DEFAULT_CONFIG_VALUES["GripperClose"])};

const uint16_t ACTUATOR_TRAVEL_TIME_MS = {config_data.get("ACTUATOR_TRAVEL_TIME_MS", DEFAULT_CONFIG_VALUES["ACTUATOR_TRAVEL_TIME_MS"])};

const uint8_t CAPTURE_HOME_BACKUP_STEPS = {config_data.get("CAPTURE_HOME_BACKUP_STEPS", DEFAULT_CONFIG_VALUES["CAPTURE_HOME_BACKUP_STEPS"])};

const uint16_t MANUAL_JOG_CART_SPEED = {config_data.get("MANUAL_JOG_CART_SPEED", DEFAULT_CONFIG_VALUES["MANUAL_JOG_CART_SPEED"])};
const uint16_t MANUAL_JOG_ORB_SPEED = {config_data.get("MANUAL_JOG_ORB_SPEED", DEFAULT_CONFIG_VALUES["MANUAL_JOG_ORB_SPEED"])};
const uint16_t MANUAL_JOG_CAPTURE_SPEED = {config_data.get("MANUAL_JOG_CAPTURE_SPEED", DEFAULT_CONFIG_VALUES["MANUAL_JOG_CAPTURE_SPEED"])};
const uint8_t  MANUAL_JOG_SERVO_INCREMENT = {config_data.get("MANUAL_JOG_SERVO_INCREMENT", DEFAULT_CONFIG_VALUES["MANUAL_JOG_SERVO_INCREMENT"])};

// --- Travel Limits ---
const long CART_MIN_POS = {config_data.get("CART_MIN_POS", DEFAULT_CONFIG_VALUES["CART_MIN_POS"])};
const long CART_MAX_POS = {config_data.get("CART_MAX_POS", DEFAULT_CONFIG_VALUES["CART_MAX_POS"])}; 

const long ORB_MIN_POS = {config_data.get("ORB_MIN_POS", DEFAULT_CONFIG_VALUES["ORB_MIN_POS"])};
const long ORB_MAX_POS = {config_data.get("ORB_MAX_POS", DEFAULT_CONFIG_VALUES["ORB_MAX_POS"])}; 

const long CAPTURE_MIN_POS = {config_data.get("CAPTURE_MIN_POS", DEFAULT_CONFIG_VALUES["CAPTURE_MIN_POS"])};
const long CAPTURE_MAX_POS = {config_data.get("CAPTURE_MAX_POS", DEFAULT_CONFIG_VALUES["CAPTURE_MAX_POS"])};
"""
    return content