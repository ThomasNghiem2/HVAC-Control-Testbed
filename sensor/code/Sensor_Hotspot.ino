#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <Adafruit_SCD30.h>

// --------------------
// WIFI SETTINGS
// --------------------
const char* ssid = "Tom laptop";      // your hotspot name
const char* password = "12345678";       // your hotspot password

const char* serverName = "http://192.168.137.1:5000/sensor";

// --------------------
// SENSOR
// --------------------
Adafruit_SCD30 scd30;

#define DEVICE_ID "sensor5"


// --------------------
// SETUP
// --------------------
void setup() {

  Serial.begin(115200);

  // Connect to WiFi
  WiFi.begin(ssid, password);
  Serial.print("Connecting to WiFi");

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("\nConnected!");
  Serial.print("ESP32 IP: ");
  Serial.println(WiFi.localIP());

  //Init SCD30
  if (!scd30.begin()) {
    Serial.println("SCD30 not detected");
    while (1);
  }

  Serial.println("CO2 sensor ready");
}

// --------------------
// LOOP
// --------------------
void loop() {
  if (scd30.dataReady()) {

    if (!scd30.read()) return;

    float co2 = scd30.CO2;
    float temp = scd30.temperature;

    Serial.print("CO2: ");
    Serial.print(co2);
    Serial.print(" ppm | Temp: ");
    Serial.print(temp);

    // --------------------
    // CREATE JSON
    // --------------------
    StaticJsonDocument<128> doc;
    doc["sensor_id"] = DEVICE_ID;
    doc["co2"] = co2;
    doc["temp"] = temp;

    String json;
    serializeJson(doc, json);

    Serial.print("Sending: ");
    Serial.println(json);

    // --------------------
    // SEND TO SERVER
    // --------------------
    if (WiFi.status() == WL_CONNECTED) {

      HTTPClient http;
      http.begin(serverName);
      http.setTimeout(2000);
      http.addHeader("Content-Type", "application/json");

      int httpResponseCode = http.POST(json);

      Serial.print("Response: ");
      Serial.println(httpResponseCode);

      http.end();

    } else {
      Serial.println("Reconnecting WiFi...");
        WiFi.begin(ssid, password);
        delay(2000);
        return;
    }
  }

  delay(100);
}