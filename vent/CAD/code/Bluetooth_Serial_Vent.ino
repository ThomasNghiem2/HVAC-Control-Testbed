#include <Arduino.h>
#include <BluetoothSerial.h>
#include <ArduinoJson.h>

#include <ezButton.h>
#include <AccelStepper.h>
#include <Adafruit_MotorShield.h>

#define DEVICE_ID "ESP32_VENT_CONTROLLER"
BluetoothSerial SerialBT;

// =====================
// MECHANICAL CONSTANTS
// =====================
const float degPerStep = 1.8;
const float maxAngle = 70.0;   // safety soft limit

// =====================
// LIMIT SWITCHES
// =====================
ezButton switchA(26);
ezButton switchB(25);

// =====================
// MOTOR SHIELD
// =====================
Adafruit_MotorShield AFMStop(0x60);

// Steppers: 200 steps/rev, ports 1 & 2
Adafruit_StepperMotor *motorA = AFMStop.getStepper(200, 1);
Adafruit_StepperMotor *motorB = AFMStop.getStepper(200, 2);

void forwardA() { motorA->onestep(FORWARD, SINGLE); }
void backwardA() { motorA->onestep(BACKWARD, SINGLE); }
void forwardB() { motorB->onestep(FORWARD, SINGLE); }
void backwardB() { motorB->onestep(BACKWARD, SINGLE); }

AccelStepper stepperA(forwardA, backwardA);
AccelStepper stepperB(forwardB, backwardB);

// =====================
// HOMING FUNCTION
// =====================
void homeStepper(AccelStepper &stepper, ezButton &limitSwitch) {
  stepper.setMaxSpeed(100);
  stepper.setSpeed(-25);

  while (true) {
    limitSwitch.loop();
    stepper.runSpeed();
    if (limitSwitch.isPressed()) break;
  }

  // Move forward slightly to release switch
  stepper.setSpeed(10);
  while (true) {
    limitSwitch.loop();
    stepper.runSpeed();
    if(limitSwitch.isReleased()) { break; }
  }

  stepper.setCurrentPosition(0);
}

// =====================
// MOVE TO ANGLE
// =====================
void moveToAngle(AccelStepper &stepper, float angle) {
  angle = constrain(angle, 0, maxAngle);
  long targetSteps = lround(angle / degPerStep);
  stepper.moveTo(targetSteps);
}

// =====================
// BLUETOOTH HANDLER
// =====================
void handleBluetooth() {
  if (!SerialBT.available()) return;

  String msg = SerialBT.readStringUntil('\n');

  StaticJsonDocument<200> doc;
  if (deserializeJson(doc, msg)) return;

  //handshake
  if (doc.containsKey("cmd")) {
    String cmd = doc["cmd"];
    if (cmd == "who") {
      SerialBT.println("{\"id\":\"" DEVICE_ID "\"}");
      return;
    }
  }

  // ---- VENT COMMAND ----
  if (doc.containsKey("vent") && doc.containsKey("angle")) {
    String vent = doc["vent"];
    float angle = doc["angle"];

    if (vent == "inlet") {
      moveToAngle(stepperA, angle);
    }
    else if (vent == "outlet") {
      moveToAngle(stepperB, angle);
    }
  }
}


// =====================
// SETUP
// =====================
void setup() {
  Serial.begin(115200);
  SerialBT.begin(DEVICE_ID);
  Serial.println("Bluetooth vent controller started");

  switchA.setDebounceTime(50);
  switchB.setDebounceTime(50);

  AFMStop.begin();

  stepperA.setMaxSpeed(100);
  stepperA.setAcceleration(100);
  stepperB.setMaxSpeed(100);
  stepperB.setAcceleration(100);

  Serial.println("Homing Stepper A...");
  homeStepper(stepperA, switchA);

  Serial.println("Homing Stepper B...");
  homeStepper(stepperB, switchB);

  Serial.println("Homing complete.");
}

// =====================
// LOOP
// =====================
void loop() {
  handleBluetooth();
  stepperA.run();
  stepperB.run();
}
