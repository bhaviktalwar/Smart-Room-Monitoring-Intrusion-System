#include <ArduinoBLE.h>

#define RELAY_PIN 2
#define GREEN_LED 8
#define RED_LED 6

BLEService doorService("180D");
BLEStringCharacteristic commandChar("2A37", BLEWrite | BLERead, 20);

void setup() {
  pinMode(RELAY_PIN, OUTPUT);
  pinMode(GREEN_LED, OUTPUT);
  pinMode(RED_LED, OUTPUT);

  digitalWrite(RELAY_PIN, HIGH);
  digitalWrite(GREEN_LED, LOW);
  digitalWrite(RED_LED, LOW);

  Serial.begin(9600);
  if (!BLE.begin()) {
    Serial.println("BLE start failed");
    while (1);
  }

  BLE.setLocalName("SmartDoorNano");
  BLE.setAdvertisedService(doorService);
  doorService.addCharacteristic(commandChar);
  BLE.addService(doorService);
  commandChar.writeValue("Waiting");
  BLE.advertise();

  Serial.println("BLE Door Lock ready");
}

void loop() {
  BLEDevice central = BLE.central();
  if (central) {
    Serial.print("Connected to ");
    Serial.println(central.address());
    while (central.connected()) {
      if (commandChar.written()) {
        String cmd = commandChar.value();
        Serial.print("Command: ");
        Serial.println(cmd);

        if (cmd == "UNLOCK") {
          digitalWrite(GREEN_LED, HIGH);
          digitalWrite(RELAY_PIN, LOW);
          delay(10000);
          digitalWrite(RELAY_PIN, HIGH);
          digitalWrite(GREEN_LED, LOW);
        } 
        else if (cmd == "ALERT") {
          digitalWrite(RED_LED, HIGH);
          delay(10000);
          digitalWrite(RED_LED, LOW);
        }
      }
    }
    Serial.println("Disconnected");
  }
}
