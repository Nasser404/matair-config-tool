# --- START OF FILE esp32_config_tool/utils/config_parser.py ---
import re

# DEFAULT_CONFIG_VALUES should be comprehensive
DEFAULT_CONFIG_VALUES = {
    "DEFAULT_SSID": "", "DEFAULT_PWD": "", "DEFAULT_HOST": "127.0.0.1", "DEFAULT_PORT": 29920,
    "orbTargets": [4350, 3550, 2750, 1950, 1150, 350, 5950, 5150],
    "cartTargets": [4450, 3850, 3270, 2670, 2000, 1380, 680, 0],
    "captureTargets": [
        2760, 2580, 2400, 2220, 2040, 1860, 1680, 1500, 1300, 1130, 940, 760,
        580, 400, 220, 0, 6260, 6080, 5890, 5710, 5530, 5350, 5170, 4970,
        4800, 4610, 4430, 4240, 4050, 3870, 3680, 3510
    ],
    "STEPPER_SPEED": 4000, "STEPPER_ACCEL": 5000, "HOMING_SPEED_CAPTURE": 1000,
    "HOMING_SPEED_CART_ORB": 1000, "HOMING_ACCEL": 1500, "GRIPPER_ROT_BOARD": 180,
    "GRIPPER_ROT_CAPTURE": 62, "CART_SAFETY_THRESHOLD": 2250,
    "CART_CAPTURE_HOME_THRESHOLD": 800, "CART_CAPTURE_POS": 2250,
    "GripperOpen": 160, "GripperClose": 50, "ACTUATOR_TRAVEL_TIME_MS": 650,
    "CAPTURE_HOME_BACKUP_STEPS": 200, "ORB_MANUAL_MIN_POS": 10,
    "ORB_MANUAL_MAX_POS": 6000, "MANUAL_ORB_SPEED": 500,
    "MANUAL_JOG_CART_SPEED": 1500, "MANUAL_JOG_ORB_SPEED": 1000,
    "MANUAL_JOG_CAPTURE_SPEED": 800, "MANUAL_JOG_SERVO_INCREMENT": 3
}

def load_config_values(filepath="config.h"):
    # Start with a fresh copy of defaults. This will be updated.
    loaded_cfg = DEFAULT_CONFIG_VALUES.copy()
    try:
        with open(filepath, 'r') as f:
            content = f.read()
        print(f"Successfully read file: {filepath}")

        def extract_value(pattern, text, is_array=False, type_cast_val=str, current_default=None):
            match = re.search(pattern, text, re.MULTILINE)
            if match:
                val_str = match.group(1).strip()
                if is_array:
                    elements_str = val_str.strip("{} ")
                    elements_str = re.sub(r'\s*\n\s*', '', elements_str)
                    elements = elements_str.split(',')
                    valid_elements = [el.strip().strip('"') for el in elements if el.strip()]
                    try:
                        return [type_cast_val(el) for el in valid_elements]
                    except ValueError: return current_default # Error in casting array elements
                else:
                    try:
                        return type_cast_val(val_str.strip('"')) if type_cast_val == str else type_cast_val(val_str)
                    except ValueError: return current_default # Error in casting single value
            return current_default # Pattern not found

        # Update loaded_cfg with values from the file, keeping defaults if not found/error
        loaded_cfg["DEFAULT_SSID"] = extract_value(r"static const String\s+DEFAULT_SSID\s*=\s*\"(.*?)\";", content, False, str, loaded_cfg["DEFAULT_SSID"])
        loaded_cfg["DEFAULT_PWD"] = extract_value(r"static const String\s+DEFAULT_PWD\s*=\s*\"(.*?)\";", content, False, str, loaded_cfg["DEFAULT_PWD"])
        loaded_cfg["DEFAULT_HOST"] = extract_value(r"static const String\s+DEFAULT_HOST\s*=\s*\"(.*?)\";", content, False, str, loaded_cfg["DEFAULT_HOST"])
        loaded_cfg["DEFAULT_PORT"] = extract_value(r"const uint32_t\s+DEFAULT_PORT\s*=\s*(\d+);", content, False, int, loaded_cfg["DEFAULT_PORT"])

        loaded_cfg["orbTargets"] = extract_value(r"const uint16_t orbTargets\[8\]\s*=\s*({[^;]*});", content, True, int, loaded_cfg["orbTargets"])
        loaded_cfg["cartTargets"] = extract_value(r"const uint16_t cartTargets\[8\]\s*=\s*({[^;]*});", content, True, int, loaded_cfg["cartTargets"])
        loaded_cfg["captureTargets"] = extract_value(r"const uint16_t captureTargets\[32\]\s*=\s*({[^;]*});", content, True, int, loaded_cfg["captureTargets"])

        for key in ["STEPPER_SPEED", "STEPPER_ACCEL", "HOMING_SPEED_CAPTURE",
                    "HOMING_SPEED_CART_ORB", "HOMING_ACCEL", "CART_SAFETY_THRESHOLD",
                    "CART_CAPTURE_HOME_THRESHOLD", "CART_CAPTURE_POS",
                    "ACTUATOR_TRAVEL_TIME_MS", "CAPTURE_HOME_BACKUP_STEPS",
                    "ORB_MANUAL_MAX_POS", "MANUAL_ORB_SPEED", # ORB_MANUAL_MIN_POS is uint8_t
                    "MANUAL_JOG_CART_SPEED", "MANUAL_JOG_ORB_SPEED",
                    "MANUAL_JOG_CAPTURE_SPEED"]:
            pattern = rf"const uint16_t {key}\s*=\s*(\d+);"
            loaded_cfg[key] = extract_value(pattern, content, False, int, loaded_cfg[key])

        for key in ["GRIPPER_ROT_BOARD", "GRIPPER_ROT_CAPTURE", "GripperOpen",
                    "GripperClose", "MANUAL_JOG_SERVO_INCREMENT", "ORB_MANUAL_MIN_POS"]: # Added ORB_MANUAL_MIN_POS
            pattern = rf"const uint8_t {key}\s*=\s*(\d+);"
            loaded_cfg[key] = extract_value(pattern, content, False, int, loaded_cfg[key])
        
        print(f"Config values parsed/defaulted from {filepath}")
    except FileNotFoundError:
        print(f"Warning: {filepath} not found. Using all default config values.")
    except Exception as e:
        print(f"Error parsing {filepath}: {e}. Using all default config values.")
    return loaded_cfg # Return the dictionary

# generate_config_h_string (ensure it uses .get(key, DEFAULT_CONFIG_VALUES[key]) for safety)
# ... (generate_config_h_string from previous correct version) ...
def generate_config_h_string(config_data):
    # Use .get() for every value, falling back to DEFAULT_CONFIG_VALUES if a key is somehow missing
    # from config_data (though load_config_values should ensure all keys are present).
    orb_targets_str = ", ".join(map(str, config_data.get("orbTargets", DEFAULT_CONFIG_VALUES["orbTargets"])))
    cart_targets_str = ", ".join(map(str, config_data.get("cartTargets", DEFAULT_CONFIG_VALUES["cartTargets"])))
    capture_targets_list = []
    ct_data = config_data.get("captureTargets", DEFAULT_CONFIG_VALUES["captureTargets"])
    for i in range(0, 32, 8):
        chunk = ", ".join(map(str, ct_data[i:i+8]))
        capture_targets_list.append(chunk)
    capture_targets_formatted_str = "\n  ".join(capture_targets_list)

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
const uint16_t orbTargets[8] = {{{orb_targets_str}}};   // a-h
const uint16_t cartTargets[8] = {{{cart_targets_str}}};     // ranks 1-8
const uint16_t captureTargets[32] = {{
  {capture_targets_formatted_str}
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

// WITH BUTTON
const uint8_t ORB_MANUAL_MIN_POS = {config_data.get("ORB_MANUAL_MIN_POS", DEFAULT_CONFIG_VALUES["ORB_MANUAL_MIN_POS"])};
const uint16_t ORB_MANUAL_MAX_POS = {config_data.get("ORB_MANUAL_MAX_POS", DEFAULT_CONFIG_VALUES["ORB_MANUAL_MAX_POS"])};
const uint16_t MANUAL_ORB_SPEED = {config_data.get("MANUAL_ORB_SPEED", DEFAULT_CONFIG_VALUES["MANUAL_ORB_SPEED"])};

// WITH NEXTION / Python App
const uint16_t MANUAL_JOG_CART_SPEED = {config_data.get("MANUAL_JOG_CART_SPEED", DEFAULT_CONFIG_VALUES["MANUAL_JOG_CART_SPEED"])};
const uint16_t MANUAL_JOG_ORB_SPEED = {config_data.get("MANUAL_JOG_ORB_SPEED", DEFAULT_CONFIG_VALUES["MANUAL_JOG_ORB_SPEED"])};
const uint16_t MANUAL_JOG_CAPTURE_SPEED = {config_data.get("MANUAL_JOG_CAPTURE_SPEED", DEFAULT_CONFIG_VALUES["MANUAL_JOG_CAPTURE_SPEED"])};
const uint8_t  MANUAL_JOG_SERVO_INCREMENT = {config_data.get("MANUAL_JOG_SERVO_INCREMENT", DEFAULT_CONFIG_VALUES["MANUAL_JOG_SERVO_INCREMENT"])};
"""
    return content