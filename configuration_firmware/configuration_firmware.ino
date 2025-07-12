// --- START OF FILE calibration_firmware.ino ---
#include <AccelStepper.h>
#include <ESP32Servo.h>
#include <ArduinoJson.h>

// === Pin Definitions (Match your Python app's hardware_pins.h assumptions if possible) ===
// Stepper 1 (Capture)
const int CAPTURE_STEP_PIN = 23;
const int CAPTURE_DIR_PIN  = 19;
const int ENDSTOP_CAPTURE_PIN = 27;

// Stepper 2 (Cart)
const int CART_STEP_PIN = 18;
const int CART_DIR_PIN  = 5;
const int ENDSTOP_CART_PIN = 25;

// Stepper 3 (Orb)
const int ORB_STEP_PIN = 4;
const int ORB_DIR_PIN  = 0;
const int ENDSTOP_ORB_PIN = 26;

// Servos
const int ROTATION_SERVO_PIN = 14; // Servo1 (Gripper Rotation)
const int GRIPPER_SERVO_PIN = 12;  // Servo2 (Gripper Open/Close)

// Linear Actuator
const int ACTUATOR_IN1_PIN = 32;
const int ACTUATOR_IN2_PIN = 33;
const int ACTUATOR_RETRACTED_SENSE_PIN = 13; // Active HIGH

// === Stepper & Servo Objects ===
AccelStepper stepperCapture(AccelStepper::DRIVER, CAPTURE_STEP_PIN, CAPTURE_DIR_PIN);
AccelStepper stepperCart(AccelStepper::DRIVER, CART_STEP_PIN, CART_DIR_PIN);
AccelStepper stepperOrb(AccelStepper::DRIVER, ORB_STEP_PIN, ORB_DIR_PIN);

Servo servoRotation;
Servo servoGripper;

// === CONFIGURABLE VALUES (These would be in config.h for the main operational firmware) ===
// For calibration, we use these directly. The Python app helps find/set these for the *real* config.h
float STEPPER_SPEED = 4000;
float STEPPER_ACCEL = 5000;

int GRIPPER_OPEN_ANGLE = 140;
int GRIPPER_CLOSE_ANGLE = 45;

int GRIPPER_ROT_BOARD = 172;
int GRIPPER_ROT_CAPTURE = 63;

long CART_CAPTURE_POS = 2250;
long CART_SAFETY_THRESHOLD = 2250; // Cart position below which gripper must be at GRIPPER_ROT_BOARD
long CART_CAPTURE_HOME_THRESHOLD = 800; // Cart position below which capture stepper must be home (0)

unsigned long ACTUATOR_TRAVEL_TIME_MS = 650;

float HOMING_SPEED_CAPTURE = 1000;
float HOMING_SPEED_CART_ORB = 1000;
float HOMING_ACCEL = 1500;

float MANUAL_JOG_CART_SPEED = 1500;
float MANUAL_JOG_ORB_SPEED = 1000;
float MANUAL_JOG_CAPTURE_SPEED = 800;
// MANUAL_JOG_SERVO_INCREMENT handled by Python side for jog commands

// === Global State for Calibration ===
String serialInputBuffer = "";
bool homingInProgress_flag = false; // Renamed to avoid conflict if any library uses "homingInProgress"
bool captureHomed_flag = false;
bool cartHomed_flag = false;
bool orbHomed_flag = false;

enum JoggingActuator { JOG_ACT_NONE, JOG_ACT_CART, JOG_ACT_ORB, JOG_ACT_CAPTURE };
JoggingActuator currentJoggingStepper = JOG_ACT_NONE;

// For "do" sequence internal parsing
enum LocationTypeCalib { LOC_CALIB_INVALID, LOC_CALIB_BOARD, LOC_CALIB_CAPTURE };
// Combined safety check
void enforceAllSafetyForCart(long targetCartPos) {
    // Serial.println("DEBUG: enforceAllSafetyForCart called for target: " + String(targetCartPos)); // Optional Debug
    enforceCaptureHomedForLowCart(targetCartPos); // Check this first (Capture stepper must be home for very low cart)
    enforceCartSafetyRotation(targetCartPos);   // Then this (Gripper rotation must be safe for low cart)
}

// Ensure enforceCartSafetyRotation and enforceCaptureHomedForLowCart are defined BEFORE this one
// or add forward declarations if you place it earlier in the file.

void enforceCartSafetyRotation(long targetCartPos) {
  if (targetCartPos < CART_SAFETY_THRESHOLD) { // Use the global config values
    if (servoRotation.read() != GRIPPER_ROT_BOARD) {
      Serial.println("SAFETY: Cart target low, forcing gripper to board angle.");
      servoRotation.write(GRIPPER_ROT_BOARD);
      delay(500); // Blocking for safety is acceptable here
    }
  }
}

void enforceCaptureHomedForLowCart(long targetCartPos) {
    const unsigned long SAFETY_HOMING_TIMEOUT_MS = 15000;
    // const unsigned long WS_POLL_INTERVAL_MS = 100; // Not used here

  if (targetCartPos < CART_CAPTURE_HOME_THRESHOLD) { // Use global config
    // Also check the homed flag, because setCurrentPosition(0) might have been used
    // without a physical homing process if 'sethome' was used.
    // However, for this safety check, we usually want to ensure it *is* at the physical endstop.
    // For calibration, relying on currentPosition() might be okay if sethome is used carefully.
    // Let's stick to currentPosition() for now to align with sethome.
    if (stepperCapture.currentPosition() != 0) {
      Serial.println("SAFETY: Cart target very low, forcing Capture home.");
      float o_sp = stepperCapture.maxSpeed(); float o_ac = stepperCapture.acceleration();
      stepperCapture.setMaxSpeed(abs(HOMING_SPEED_CAPTURE)); // Use config
      stepperCapture.setAcceleration(HOMING_ACCEL);    // Use config
      stepperCapture.enableOutputs(); stepperCapture.move(-30000);
      unsigned long startT = millis(); bool SChomed = false;
      while (!SChomed && (millis() - startT < SAFETY_HOMING_TIMEOUT_MS)) {
        if (digitalRead(ENDSTOP_CAPTURE_PIN) == LOW) {
          stepperCapture.stop(); stepperCapture.setCurrentPosition(0); SChomed = true;
          Serial.println("  SAFETY: Capture homed.");
        } else { stepperCapture.run(); } delay(1);
      }
      if (!SChomed) { Serial.println("ERR: SAFETY Capture homing timeout!"); stepperCapture.stop(); }
      else { captureHomed_flag = true; } // Update global status if safety homing was successful

      stepperCapture.setMaxSpeed(o_sp); stepperCapture.setAcceleration(o_ac);
      stepperCapture.runToPosition(); // Ensure it settles
    }
  }
}

void setup() {
    Serial.begin(115200);
    unsigned long setupStartTime = millis();
    while (!Serial && (millis() - setupStartTime < 3000)) { // Wait max 3s for Serial
        delay(10);
    }
    Serial.println("ACK: Calibration Firmware Ready. Send 'help'.");

    pinMode(ENDSTOP_CAPTURE_PIN, INPUT_PULLUP);
    pinMode(ENDSTOP_CART_PIN, INPUT_PULLUP);
    pinMode(ENDSTOP_ORB_PIN, INPUT_PULLUP);

    pinMode(ACTUATOR_IN1_PIN, OUTPUT);
    pinMode(ACTUATOR_IN2_PIN, OUTPUT);
    digitalWrite(ACTUATOR_IN1_PIN, LOW);
    digitalWrite(ACTUATOR_IN2_PIN, LOW);
    pinMode(ACTUATOR_RETRACTED_SENSE_PIN, INPUT); // Active HIGH based on discussion

    servoRotation.attach(ROTATION_SERVO_PIN, 500, 2500);
    servoGripper.attach(GRIPPER_SERVO_PIN, 500, 2500);
    servoRotation.write(GRIPPER_ROT_BOARD); // Start safe
    servoGripper.write(GRIPPER_OPEN_ANGLE); // Start open

    stepperCapture.setMaxSpeed(STEPPER_SPEED);
    stepperCapture.setAcceleration(STEPPER_ACCEL);
    stepperCart.setMaxSpeed(STEPPER_SPEED);
    stepperCart.setAcceleration(STEPPER_ACCEL);
    stepperOrb.setMaxSpeed(STEPPER_SPEED);
    stepperOrb.setAcceleration(STEPPER_ACCEL);

    Serial.println("INFO: Homing required for full functionality. Send 'homeall'.");
}

void loop() {
    readSerialCommands();

    if (homingInProgress_flag) {
        handleHoming(); // Manages its own stepper.run() calls
    } else {
        stepperCapture.run();
        stepperCart.run();
        stepperOrb.run();
    }
    // Jogging with setSpeed relies on the above run() calls.
    // Servos and direct LA control don't need continuous updates in loop beyond command execution.
}

// ========================== SERIAL COMMANDS =============================
void readSerialCommands() {
    while (Serial.available()) {
        char inChar = (char)Serial.read();
        if (inChar == '\n' || inChar == '\r') {
            if (serialInputBuffer.length() > 0) {
                processCommand(serialInputBuffer);
                serialInputBuffer = "";
            }
        } else if (isprint(inChar)) {
            serialInputBuffer += inChar;
        }
    }
}

void processCommand(String cmd) {
    cmd.trim();
    // Serial.print("RX_RAW: "); Serial.println(cmd); // Optional raw echo

    if (cmd.equalsIgnoreCase("help")) { sendHelp(); }
    else if (cmd.equalsIgnoreCase("ping")) { Serial.println("ACK: pong"); }
    else if (cmd.equalsIgnoreCase("getallpos")) { sendAllPositions(); }
    else if (cmd.startsWith("getpos ")) { // E.g., getpos cart
        String stepperId = cmd.substring(7);
        sendSpecificPosition(stepperId);
    }
    else if (cmd.equalsIgnoreCase("homeall")) { startHomingAll(); }
    else if (cmd.startsWith("sethome ")) { // E.g., sethome capt
        String stepperId = cmd.substring(8);
        setStepperHome(stepperId);
    }
    else if (cmd.startsWith("gotocart ")) {
        long pos = cmd.substring(9).toInt();
        enforceAllSafetyForCart(pos);
        stepperCart.moveTo(pos);
        Serial.println("ACK: Cart moving to " + String(pos));
    } else if (cmd.startsWith("gotoorb ")) {
        long pos = cmd.substring(8).toInt();
        if (servoRotation.read() != GRIPPER_ROT_BOARD) {
             Serial.println("WARN: Orb move with gripper rotated. Setting to board angle.");
             servoRotation.write(GRIPPER_ROT_BOARD); delay(400);
        }
        stepperOrb.moveTo(pos);
        Serial.println("ACK: Orb moving to " + String(pos));
    } else if (cmd.startsWith("gotocapt ")) {
        long pos = cmd.substring(9).toInt();
        stepperCapture.moveTo(pos);
        Serial.println("ACK: Capture moving to " + String(pos));
    } else if (cmd.startsWith("servorot ")) {
        int angle = cmd.substring(9).toInt();
        servoRotation.write(constrain(angle, 0, 180));
        Serial.println("ACK: Rotation Servo to " + String(angle));
    } else if (cmd.startsWith("servogrip ")) {
        int angle = cmd.substring(10).toInt();
        servoGripper.write(constrain(angle, GRIPPER_CLOSE_ANGLE, GRIPPER_OPEN_ANGLE));
        Serial.println("ACK: Gripper Servo to " + String(angle));
    } else if (cmd.equalsIgnoreCase("gripopen")) {
        servoGripper.write(GRIPPER_OPEN_ANGLE);
        Serial.println("ACK: Gripper Open");
    } else if (cmd.equalsIgnoreCase("gripclose")) {
        servoGripper.write(GRIPPER_CLOSE_ANGLE);
        Serial.println("ACK: Gripper Close");
    } else if (cmd.equalsIgnoreCase("la_ext")) {
        commandExtendActuator(true);
        Serial.println("ACK: Linear Actuator Extending (timed)");
    } else if (cmd.equalsIgnoreCase("la_ret")) {
        commandRetractActuator(true, true); // Timed, with sensor
        Serial.println("ACK: Linear Actuator Retracting (timed, sensor)");
    } else if (cmd.equalsIgnoreCase("la_stop")) {
        commandStopActuator();
        Serial.println("ACK: Linear Actuator Stopped");
    } else if (cmd.startsWith("jog ")) { // jog cart 1
        int firstSpace = cmd.indexOf(' ');
        int secondSpace = cmd.indexOf(' ', firstSpace + 1);
        if (firstSpace != -1 && secondSpace != -1) {
            String actStr = cmd.substring(firstSpace + 1, secondSpace);
            bool dir = cmd.substring(secondSpace + 1).toInt() == 1;
            startJog(actStr, dir);
        } else { Serial.println("ERR: Invalid jog format. Use: jog <act_id> <0/1>"); }
    } else if (cmd.equalsIgnoreCase("jogstop")) { // Changed from jogstop <act_id>
        stopJog(); // Stops any active stepper jog
    } else if (cmd.equalsIgnoreCase("take")) {
        executeTakeSequence();
    } else if (cmd.equalsIgnoreCase("release")) {
        executeReleaseSequence();
    } else if (cmd.startsWith("do ")) {
        int firstSpace = cmd.indexOf(' ');
        int secondSpace = cmd.indexOf(' ', firstSpace + 1);
        if (firstSpace != -1 && secondSpace != -1) {
            String fromStr = cmd.substring(firstSpace + 1, secondSpace);
            String toStr = cmd.substring(secondSpace + 1);
            executeDoSequence(fromStr, toStr);
        } else { Serial.println("ERR: Invalid 'do' format. Use: do <from> <to>"); }
    } else if (cmd.startsWith("getsquarepos ")) {
        String square = cmd.substring(13);
        sendSquareTargetData(square);
    } else if (cmd.startsWith("getcaptpos ")) {
        int slot = cmd.substring(11).toInt();
        sendCaptureSlotTargetData(slot);
    }
    else {
        Serial.println("ERR: Unknown command: " + cmd);
    }
}

void sendHelp() {
    Serial.println("--- Calibration Firmware Help ---");
    Serial.println("ping                    - Test connection");
    Serial.println("getallpos               - Get current stepper/servo positions & sensor");
    Serial.println("getpos <id>             - Get specific stepper pos (capt, cart, orb)");
    Serial.println("homeall                 - Start homing all steppers");
    Serial.println("sethome <id>            - Set current pos of stepper (capt,cart,orb) to 0");
    Serial.println("gotocart <pos>          - Move Cart stepper");
    Serial.println("gotoorb <pos>           - Move Orb stepper");
    Serial.println("gotocapt <pos>          - Move Capture stepper");
    Serial.println("servorot <angle>        - Set Rotation Servo (0-180)");
    Serial.println("servogrip <angle>       - Set Gripper Servo");
    Serial.println("gripopen                - Open gripper fully");
    Serial.println("gripclose               - Close gripper fully");
    Serial.println("la_ext                  - Extend linear actuator (timed)");
    Serial.println("la_ret                  - Retract linear actuator (timed, checks sensor)");
    Serial.println("la_stop                 - Stop linear actuator");
    Serial.println("jog <id> <dir (1/0)>    - Start continuous jog (cart,orb,capt)");
    Serial.println("jogstop                 - Stop any active stepper jog");
    Serial.println("take                    - Execute test Take sequence");
    Serial.println("release                 - Execute test Release sequence");
    Serial.println("do <from_sq> <to_sq>    - Execute test Do sequence (e.g., do a1 capt5)");
    Serial.println("getsquarepos <sq>       - Get target stepper values for board square (e.g., a1)");
    Serial.println("getcaptpos <slot_num>   - Get target stepper value for capture slot (1-32)");
    Serial.println("-------------------------------");
}

// ========================== POSITION REPORTING ============================
void sendAllPositions() {
    StaticJsonDocument<256> doc;
    doc["cartPos"] = stepperCart.currentPosition();
    doc["orbPos"] = stepperOrb.currentPosition();
    doc["captPos"] = stepperCapture.currentPosition();
    doc["rotServo"] = servoRotation.read();
    doc["gripServo"] = servoGripper.read();
    doc["actuatorSensor"] = digitalRead(ACTUATOR_RETRACTED_SENSE_PIN); // 1 if HIGH (retracted), 0 if LOW
    String output;
    serializeJson(doc, output);
    Serial.println("POS: " + output);
}

void sendSpecificPosition(String stepperId) {
    stepperId.toLowerCase();
    long currentPos = 0; // Default
    bool found = false;
    if (stepperId.equals("capt")) { currentPos = stepperCapture.currentPosition(); found = true; }
    else if (stepperId.equals("cart")) { currentPos = stepperCart.currentPosition(); found = true; }
    else if (stepperId.equals("orb")) { currentPos = stepperOrb.currentPosition(); found = true; }

    if (found) {
        Serial.println("SPOS: " + stepperId + " " + String(currentPos));
    } else {
        Serial.println("ERR: Unknown stepper ID for getpos: " + stepperId);
    }
}

void sendSquareTargetData(String square) {
    long orbT, cartT;
    if (getTargetsForSquareInternal(square, orbT, cartT)) {
        StaticJsonDocument<128> doc;
        doc["square"] = square; doc["orb"] = orbT; doc["cart"] = cartT;
        String output; serializeJson(doc, output);
        Serial.println("SQPOS: " + output);
    } else { Serial.println("ERR: Invalid square for getsquarepos: " + square); }
}

void sendCaptureSlotTargetData(int slot) {
    long captT;
    if (slot >= 1 && slot <= 32 && getTargetForCaptureInternal(slot, captT)) {
        StaticJsonDocument<128> doc;
        doc["slot"] = slot; doc["capture"] = captT;
        String output; serializeJson(doc, output);
        Serial.println("CAPTPOS: " + output);
    } else { Serial.println("ERR: Invalid slot for getcaptpos: " + String(slot)); }
}

// ========================== HOMING =======================================
// (handleHoming and startHomingAll remain largely the same, ensure speeds are from _CONFIG)
unsigned long homingTimeoutStart;
const unsigned long HOMING_TIMEOUT_DURATION = 20000;

void startHomingAll() {
    if (homingInProgress_flag) { Serial.println("ERR: Homing already in progress."); return; }
    Serial.println("ACK: Homing sequence started...");
    homingInProgress_flag = true; captureHomed_flag = false; cartHomed_flag = false; orbHomed_flag = false;

    Serial.println("  Homing Capture stepper...");
    stepperCapture.setMaxSpeed(HOMING_SPEED_CAPTURE); // Use config value
    stepperCapture.setAcceleration(HOMING_ACCEL);    // Use config value
    stepperCapture.enableOutputs(); stepperCapture.move(-30000);
    homingTimeoutStart = millis();
}

void handleHoming() {
    if (!homingInProgress_flag) return;
    if (!captureHomed_flag) { /* ... same logic as before, use _CONFIG speeds ... */
        stepperCapture.run();
        if (digitalRead(ENDSTOP_CAPTURE_PIN) == LOW) {
            stepperCapture.stop(); stepperCapture.setCurrentPosition(0); captureHomed_flag = true;
            Serial.println("  Capture stepper homed at 0.");
            stepperCapture.setMaxSpeed(STEPPER_SPEED); stepperCapture.setAcceleration(STEPPER_ACCEL);
            Serial.println("  Homing Cart and Orb steppers...");
            stepperCart.setMaxSpeed(HOMING_SPEED_CART_ORB); stepperCart.setAcceleration(HOMING_ACCEL);
            stepperCart.enableOutputs(); stepperCart.move(-30000);
            stepperOrb.setMaxSpeed(HOMING_SPEED_CART_ORB); stepperOrb.setAcceleration(HOMING_ACCEL);
            stepperOrb.enableOutputs(); stepperOrb.move(-30000);
            homingTimeoutStart = millis();
        } else if (millis() - homingTimeoutStart > HOMING_TIMEOUT_DURATION) { /* timeout */ 
            Serial.println("ERR: Capture homing timeout!"); stepperCapture.stop(); homingInProgress_flag = false;
        }
    } else if (!cartHomed_flag || !orbHomed_flag) { /* ... same logic for cart/orb ... */
        if (!cartHomed_flag) {
            stepperCart.run();
            if (digitalRead(ENDSTOP_CART_PIN) == LOW) {
                stepperCart.stop(); stepperCart.setCurrentPosition(0); cartHomed_flag = true;
                Serial.println("  Cart stepper homed at 0.");
                stepperCart.setMaxSpeed(STEPPER_SPEED); stepperCart.setAcceleration(STEPPER_ACCEL);
            }
        }
        if (!orbHomed_flag) {
            stepperOrb.run();
            if (digitalRead(ENDSTOP_ORB_PIN) == LOW) {
                stepperOrb.stop(); stepperOrb.setCurrentPosition(0); orbHomed_flag = true;
                Serial.println("  Orb stepper homed at 0.");
                stepperOrb.setMaxSpeed(STEPPER_SPEED); stepperOrb.setAcceleration(STEPPER_ACCEL);
            }
        }
        if (cartHomed_flag && orbHomed_flag) { Serial.println("ACK: All steppers homed."); homingInProgress_flag = false; }
        else if (millis() - homingTimeoutStart > HOMING_TIMEOUT_DURATION) { /* timeout */
            Serial.println("ERR: Cart/Orb homing timeout!");
            if (!cartHomed_flag) stepperCart.stop(); if (!orbHomed_flag) stepperOrb.stop();
            homingInProgress_flag = false;
        }
    }
}

void setStepperHome(String stepperId) {
    stepperId.toLowerCase();
    bool success = false;
    if (stepperId.equals("capt")) {
        stepperCapture.stop(); stepperCapture.setCurrentPosition(0); captureHomed_flag = true; success = true;
    } else if (stepperId.equals("cart")) {
        stepperCart.stop(); stepperCart.setCurrentPosition(0); cartHomed_flag = true; success = true;
    } else if (stepperId.equals("orb")) {
        stepperOrb.stop(); stepperOrb.setCurrentPosition(0); orbHomed_flag = true; success = true;
    }
    if (success) {
        Serial.println("ACK: sethome " + stepperId + " position set to 0.");
        sendAllPositions(); // Send updated positions
    } else {
        Serial.println("ERR: Unknown stepper ID for sethome: " + stepperId);
    }
}


// ========================== JOGGING ======================================
void startJog(String actuatorId, bool positive) {
    stopJog(); // Stop any previous jog
    actuatorId.toLowerCase();
    Serial.print("ACK: Jog Start - "); Serial.print(actuatorId); Serial.println(positive ? " POS" : " NEG");

    if (actuatorId.equals("cart")) {
        currentJoggingStepper = JOG_ACT_CART;
        enforceAllSafetyForCart(stepperCart.currentPosition() + (positive ? 1000 : -1000)); // Check intended direction
        stepperCart.enableOutputs();
        stepperCart.setSpeed(positive ? MANUAL_JOG_CART_SPEED : -MANUAL_JOG_CART_SPEED);
    } else if (actuatorId.equals("orb")) {
        currentJoggingStepper = JOG_ACT_ORB;
        if (servoRotation.read() != GRIPPER_ROT_BOARD) { servoRotation.write(GRIPPER_ROT_BOARD); delay(400); }
        stepperOrb.enableOutputs();
        stepperOrb.setSpeed(positive ? MANUAL_JOG_ORB_SPEED : -MANUAL_JOG_ORB_SPEED);
    } else if (actuatorId.equals("capt")) {
        currentJoggingStepper = JOG_ACT_CAPTURE;
        stepperCapture.enableOutputs();
        stepperCapture.setSpeed(positive ? MANUAL_JOG_CAPTURE_SPEED : -MANUAL_JOG_CAPTURE_SPEED);
    }
    // Servo and LA jog are not continuous from ESP side based on current python app design
    // Python app will send discrete servorot/servogrip/la_ext/la_ret commands if jogged.
    // If you want ESP-side continuous servo/LA jog:
    // else if (actuatorId.equals("rotservo")) { currentJogActuator = JOG_ACT_ROT_SERVO; jogDirectionPositive = positive; }
    // else if (actuatorId.equals("gripservo")) { currentJogActuator = JOG_ACT_GRIP_SERVO; jogDirectionPositive = positive; }
    // else if (actuatorId.equals("linact")) { currentJogActuator = JOG_ACT_LIN_ACT; if (positive) commandExtendActuator(false); else commandRetractActuator(false, false); }
    else {
        Serial.println("ERR: Unknown actuator for jog: " + actuatorId);
    }
}

void stopJog() {
    if (currentJoggingStepper != JOG_ACT_NONE) {
        Serial.println("ACK: Jog Stop");
        switch (currentJoggingStepper) {
            case JOG_ACT_CART: stepperCart.setSpeed(0); break;
            case JOG_ACT_ORB: stepperOrb.setSpeed(0); break;
            case JOG_ACT_CAPTURE: stepperCapture.setSpeed(0); break;
            default: break;
        }
        currentJoggingStepper = JOG_ACT_NONE;
        // For safety, could run steppers for a short duration to decelerate
        unsigned long stopStartTime = millis();
        while(millis() - stopStartTime < 100){ // Run for 100ms to allow deceleration
            stepperCart.run(); stepperOrb.run(); stepperCapture.run();
            delay(1);
        }
    }
}

// ========================== ACTUATORS ====================================
void commandExtendActuator(bool timed) { /* ... same, use _CONFIG values ... */
    Serial.println("CMD: Extend Actuator");
    digitalWrite(ACTUATOR_IN1_PIN, LOW); digitalWrite(ACTUATOR_IN2_PIN, HIGH);
    if (timed) { delay(ACTUATOR_TRAVEL_TIME_MS); commandStopActuator(); Serial.println("  Extend (timed) complete."); }
}
void commandRetractActuator(bool timed, bool useSensor) { /* ... same, use _CONFIG values, Active HIGH sensor ... */
    Serial.println("CMD: Retract Actuator");
      Serial.println("CMD: Extend Actuator");
    digitalWrite(ACTUATOR_IN1_PIN, HIGH); digitalWrite(ACTUATOR_IN2_PIN, LOW);
    if (timed) { delay(ACTUATOR_TRAVEL_TIME_MS); commandStopActuator(); Serial.println("  Extend (timed) complete."); }
}
void commandStopActuator() { /* ... same ... */
    digitalWrite(ACTUATOR_IN1_PIN, LOW); digitalWrite(ACTUATOR_IN2_PIN, LOW);
    // Serial.println("CMD: Stop Actuator"); // Can be noisy if called often
}

// ========================== HIGH-LEVEL SEQUENCES =========================
// Blocking versions for calibration sketch simplicity
void executeTakeSequence() { /* ... same as before ... */
    Serial.println("ACK: Executing Take Sequence...");
    servoGripper.write(GRIPPER_OPEN_ANGLE); delay(300);
    commandExtendActuator(true);
    servoGripper.write(GRIPPER_CLOSE_ANGLE); delay(700);
    commandRetractActuator(true, true); // Use sensor for take
    Serial.println("  Take Sequence Complete.");
}
void executeReleaseSequence() { /* ... same as before ... */
    Serial.println("ACK: Executing Release Sequence...");
    commandExtendActuator(true);
    servoGripper.write(GRIPPER_OPEN_ANGLE); delay(300);
    commandRetractActuator(true, false); // Timed is fine for release
    Serial.println("  Release Sequence Complete.");
}

void waitForSteppersBlocking(const String& moveName) { /* ... same as before ... */
    Serial.print("  Waiting for '"); Serial.print(moveName); Serial.println("' steppers (blocking)...");
    unsigned long moveStartTime = millis();
    bool cartMoving = stepperCart.distanceToGo() != 0;
    bool orbMoving = stepperOrb.distanceToGo() != 0;
    bool captMoving = stepperCapture.distanceToGo() != 0;

    while (cartMoving || orbMoving || captMoving) {
        if (cartMoving) { stepperCart.run(); if (stepperCart.distanceToGo() == 0) cartMoving = false; }
        if (orbMoving)  { stepperOrb.run();  if (stepperOrb.distanceToGo() == 0)  orbMoving = false;  }
        if (captMoving) { stepperCapture.run(); if (stepperCapture.distanceToGo() == 0) captMoving = false;}

        if (millis() - moveStartTime > 20000) {
            Serial.println("ERR: Stepper move timeout during 'do' sequence!");
            stepperCart.stop(); stepperOrb.stop(); stepperCapture.stop();
            return;
        }
        delay(1);
    }
    Serial.println("    Steppers arrived.");
}

void executeDoSequence(String fromStr, String toStr) { /* ... same logic as before, using waitForSteppersBlocking ... */
    Serial.print("ACK: Executing Do Sequence: "); Serial.print(fromStr); Serial.print(" -> "); Serial.println(toStr);
    if (!captureHomed_flag || !cartHomed_flag || !orbHomed_flag) { Serial.println("ERR: Steppers not homed."); return; }

    long o1,c1,p1,o2,c2,p2; int r1,r2;
    LocationTypeCalib t1 = parseLocationCalib(fromStr,o1,c1,p1,r1);
    LocationTypeCalib t2 = parseLocationCalib(toStr,o2,c2,p2,r2);
    if(t1==LOC_CALIB_INVALID || t2==LOC_CALIB_INVALID){Serial.println("ERR: Invalid loc in DO"); return;}

    Serial.println("  1. Moving to Source: " + fromStr);
    enforceAllSafetyForCart(c1);
    if(t1==LOC_CALIB_CAPTURE){
        if(servoRotation.read()!=GRIPPER_ROT_BOARD) {servoRotation.write(GRIPPER_ROT_BOARD);delay(400);}
        stepperCart.moveTo(c1); stepperOrb.moveTo(o1); waitForSteppersBlocking("Cart/Orb to CZ Align (Source)");
        servoRotation.write(r1); delay(400); stepperCapture.moveTo(p1); waitForSteppersBlocking("Capture to Slot (Source)");
    } else {
        if(servoRotation.read()!=r1) {servoRotation.write(r1);delay(400);}
        stepperCart.moveTo(c1); stepperOrb.moveTo(o1); stepperCapture.moveTo(p1); waitForSteppersBlocking("Board Source");
    }
    Serial.println("  2. Performing Take..."); executeTakeSequence();
    Serial.println("  3. Moving to Dest: " + toStr);
    enforceAllSafetyForCart(c2);
    if(t2==LOC_CALIB_CAPTURE){
        if(servoRotation.read()!=GRIPPER_ROT_BOARD) {servoRotation.write(GRIPPER_ROT_BOARD);delay(400);}
        stepperCart.moveTo(c2); stepperOrb.moveTo(o2); waitForSteppersBlocking("Cart/Orb to CZ Align (Dest)");
        servoRotation.write(r2); delay(400); stepperCapture.moveTo(p2); waitForSteppersBlocking("Capture to Slot (Dest)");
    } else {
        if(servoRotation.read()!=r2) {servoRotation.write(r2);delay(400);}
        stepperCart.moveTo(c2); stepperOrb.moveTo(o2); stepperCapture.moveTo(p2); waitForSteppersBlocking("Board Dest");
    }
    Serial.println("  4. Performing Release..."); executeReleaseSequence();
    Serial.println("  Do Sequence Complete.");
}

// ========================== CALIBRATION PARSERS ==========================
// (getTargetsForSquareInternal, getTargetForCaptureInternal, parseLocationCalib - these are your
// current getTargetsForSquare, getTargetForCapture, parseLocation, but renamed to avoid
// potential conflicts if you were to include other libraries. They use fixed values from this sketch)

bool getTargetsForSquareInternal(String square, long &orbTarget, long &cartTarget) {
  square.trim(); square.toLowerCase();
  if (square.length() != 2) { Serial.println("ERR: Square fmt (e.g. a1)"); return false; }
  char o = square.charAt(0); char c = square.charAt(1);
  switch(o){
    case 'a': orbTarget = 4100; break; case 'b': orbTarget = 3280; break; case 'c': orbTarget = 2500; break;
    case 'd': orbTarget = 1700; break; case 'e': orbTarget = 900;  break; case 'f': orbTarget = 80;   break;
    case 'g': orbTarget = 5700; break; case 'h': orbTarget = 4950; break;
    default: Serial.println("ERR: Invalid file"); return false;
  }
  switch(c){
    case '1': cartTarget = 4500; break; case '2': cartTarget = 3900; break; case '3': cartTarget = 3400; break;
    case '4': cartTarget = 2750; break; case '5': cartTarget = 2050; break; case '6': cartTarget = 1400; break;
    case '7': cartTarget = 725;  break; case '8': cartTarget = 0;   break;
    default: Serial.println("ERR: Invalid rank"); return false;
  }
  return true;
}

bool getTargetForCaptureInternal(int slot, long &val) {
  switch(slot){
    case 1: val = 2780; break; case 2: val = 2600; break; case 3: val = 2420; break;
    case 4: val = 2240; break; case 5: val = 2060; break; case 6: val = 1880; break;
    case 7: val = 1700; break; case 8: val = 1520; break; case 9: val = 1300; break;
    case 10: val = 1130; break; case 11: val = 920; break; case 12: val = 720; break;
    case 13: val = 550; break; case 14: val = 380; break; case 15: val = 200; break;
    case 16: val = 0; break; case 17: val = 6250; break; case 18: val = 6050; break;
    case 19: val = 5850; break; case 20: val = 5700; break; case 21: val = 5500; break;
    case 22: val = 5300; break; case 23: val = 5150; break; case 24: val = 4950; break;
    case 25: val = 4750; break; case 26: val = 4580; break; case 27: val = 4380; break;
    case 28: val = 4210; break; case 29: val = 4020; break; case 30: val = 3840; break;
    case 31: val = 3650; break; case 32: val = 3480; break;
    default: Serial.println("ERR: Invalid slot num"); return false;
  }
  return true;
}

LocationTypeCalib parseLocationCalib(String locStr, long &orbT, long &cartT, long &captT, int &rotT) {
  locStr.trim(); locStr.toLowerCase();
  orbT = stepperOrb.currentPosition(); cartT = stepperCart.currentPosition();
  captT = stepperCapture.currentPosition(); rotT = servoRotation.read();

  if (locStr.startsWith("capt")) {
    if (locStr.length() <= 4) { Serial.println("ERR: Capt num missing"); return LOC_CALIB_INVALID; }
    int slot = locStr.substring(4).toInt();
    if (getTargetForCaptureInternal(slot, captT)) {
      cartT = CART_CAPTURE_POS; rotT = GRIPPER_ROT_CAPTURE; return LOC_CALIB_CAPTURE;
    } else { return LOC_CALIB_INVALID; }
  } else if (locStr.length() == 2) {
    if (getTargetsForSquareInternal(locStr, orbT, cartT)) {
      captT = 0; // Assume capture home for board moves
      rotT = GRIPPER_ROT_BOARD; return LOC_CALIB_BOARD;
    } else { return LOC_CALIB_INVALID; }
  }
  Serial.print("ERR: Invalid loc fmt: "); Serial.println(locStr); return LOC_CALIB_INVALID;
}

// --- END OF FILE calibration_firmware.ino ---