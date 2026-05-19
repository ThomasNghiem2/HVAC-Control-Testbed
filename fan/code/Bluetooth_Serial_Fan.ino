#include <Arduino.h>
#include <BluetoothSerial.h>
#include <ArduinoJson.h>

BluetoothSerial SerialBT;

// GPIO pins connected to fan control (PWM input)
#define INLET_FAN_PIN   18
#define OUTLET_FAN_PIN  19

// LEDC (hardware PWM) config
#define PWM_FREQ       25000   // 25 kHz
#define PWM_RES        8       // 8-bit resolution (0–255)

#define DEVICE_ID "ESP32_FAN_CONTROLLER"

void setup() {
  Serial.begin(115200);
  SerialBT.begin(DEVICE_ID);

  // Setup PWM channels
  ledcAttach(INLET_FAN_PIN, PWM_FREQ, PWM_RES);
  ledcAttach(OUTLET_FAN_PIN, PWM_FREQ, PWM_RES);

  // Start with fans OFF
  ledcWrite(INLET_FAN_PIN, 0);
  ledcWrite(OUTLET_FAN_PIN, 0);

  Serial.println("Fan controller ready (Bluetooth)");
  SerialBT.println("{\"id\":\"" DEVICE_ID "\"}");
}

void loop() {
  if (SerialBT.available()) {
    String msg = SerialBT.readStringUntil('\n');
    Serial.println("Recieved: " + msg);

    StaticJsonDocument<128> doc;
    if (deserializeJson(doc, msg)) return;

    //handshake
    if (doc.containsKey("cmd")) {
      String cmd = doc["cmd"];
      if (cmd == "who") {
        SerialBT.println("{\"id\":\"" DEVICE_ID "\"}");
        return;
      }
    }

    if (doc.containsKey("fan") && doc.containsKey("speed")) {
      String fan = doc["fan"];
      int speed = doc["speed"];   // 0–100

      speed = constrain(speed, 0, 100);
      int duty = map(speed, 0, 100, 0, 255);

      if (fan == "inlet") {
        ledcWrite(INLET_FAN_PIN, duty);
      }
      else if (fan == "outlet") {
        ledcWrite(OUTLET_FAN_PIN, duty);
      }
    }
  }
}