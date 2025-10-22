/**
 * @file SmartDoorLock_BLE.ino
 * @brief Bluetooth Low Energy (BLE) controlled Smart Door Lock System.
 *
 * This sketch uses an Arduino Nano 33 BLE or similar board to act as a
 * peripheral device for receiving commands (e.g., UNLOCK or ALERT)
 * from a central device (e.g., a smartphone application).
 *
 * It controls a door relay and provides status indication via LEDs.
 * The door is kept locked by default using a normally-closed relay configuration.
 */

#include <ArduinoBLE.h>

// --- PIN DEFINITIONS ---
// Define hardware interface pins for clarity and easy modification.
// Digital pin connected to the door lock relay module. LOW = UNLOCK (Active LOW relay), HIGH = LOCK.
#define RELAY_PIN 2
// Digital pin for the Green LED (Status: UNLOCKED/Success).
#define GREEN_LED 8  
 // Digital pin for the Red LED (Status: ALERT/Error).
#define RED_LED 6      

// --- BLE SERVICE AND CHARACTERISTIC DEFINITIONS ---
// Standard 16-bit UUIDs in the custom user range (0xFF00) are used here.
// In a production environment, a unique 128-bit UUID should be registered.
#define DOOR_SERVICE_UUID "FF00"
#define COMMAND_CHAR_UUID "FF01"

// Service definition for the Door Lock application.
BLEService doorService(DOOR_SERVICE_UUID);

// Characteristic for receiving commands.
// Permissions: WRITE (to receive commands) | READ (to check current status/command).
// Max length is 20 bytes (standard BLE characteristic length).
BLEStringCharacteristic commandChar(COMMAND_CHAR_UUID, BLEWrite | BLERead, 20);

// --- SETUP FUNCTION ---
void setup() {
  // Initialize Serial communication for debugging and status logging.
  Serial.begin(9600);
  while (!Serial); // Wait for Serial Monitor to open (optional for Nano 33 BLE)

  // Configure output pins.
  pinMode(RELAY_PIN, OUTPUT);
  pinMode(GREEN_LED, OUTPUT);
  pinMode(RED_LED, OUTPUT);

  // Set initial state: Door Locked (RELAY_PIN HIGH) and all LEDs OFF.
  digitalWrite(RELAY_PIN, HIGH);
  digitalWrite(GREEN_LED, LOW);
  digitalWrite(RED_LED, LOW);

  // Initialize the BLE module.
  if (!BLE.begin()) {
    Serial.println("FATAL ERROR: BLE initialization failed!");
    // Halt execution if BLE cannot start.
    while (1);
  }

  // --- BLE Configuration ---
  // 1. Set the advertised device name.
  BLE.setLocalName("SmartDoorNano");

  // 2. Set the service to be advertised.
  BLE.setAdvertisedService(doorService);

  // 3. Add the characteristic to the service.
  doorService.addCharacteristic(commandChar);

  // 4. Add the service to the BLE server.
  BLE.addService(doorService);

  // 5. Set initial characteristic value.
  commandChar.writeValue("LOCKED");

  // 6. Start advertising the BLE service.
  BLE.advertise();

  Serial.println("BLE Door Lock System initialized and ready. Advertising...");
}

// --- MAIN LOOP FUNCTION ---
void loop() {
  // Wait for a central device (e.g., smartphone) to connect.
  BLEDevice central = BLE.central();

  // Check if a central device is connected.
  if (central) {
    Serial.print("Connected to central device: ");
    Serial.println(central.address());

    // While the central device remains connected:
    while (central.connected()) {
      // Check if the central device has written a new value to the characteristic.
      if (commandChar.written()) {
        // Read the command string.
        String cmd = commandChar.value();
        Serial.print("Received Command: ");
        Serial.println(cmd);

        // --- COMMAND PROCESSING LOGIC ---

        if (cmd.equalsIgnoreCase("UNLOCK")) {
          // Process UNLOCK command.
          Serial.println("Executing UNLOCK sequence...");

          digitalWrite(GREEN_LED, HIGH);   // Indicate successful unlock with green LED.
          digitalWrite(RELAY_PIN, LOW);    // De-energize/switch relay (Active LOW to UNLOCK).
          commandChar.writeValue("UNLOCKED");

          // Keep door unlocked for 10 seconds (configurable security delay).
          delay(10000);

          // Re-lock the door.
          digitalWrite(RELAY_PIN, HIGH);   // Re-energize/switch relay (LOCK state).
          digitalWrite(GREEN_LED, LOW);    // Turn off green LED.
          commandChar.writeValue("LOCKED");
          Serial.println("Door re-locked.");
        }
        else if (cmd.equalsIgnoreCase("ALERT")) {
          // Process ALERT command (e.g., triggered by unauthorized access attempt).
          Serial.println("Executing ALERT sequence...");

          digitalWrite(RED_LED, HIGH);     // Activate red LED for visual alert.
          commandChar.writeValue("ALERT_ACTIVE");

          // Keep alert active for 10 seconds.
          delay(10000);

          // Reset alert status.
          digitalWrite(RED_LED, LOW);      // Turn off red LED.
          commandChar.writeValue("LOCKED");
          Serial.println("Alert sequence finished.");
        }
        else {
          Serial.print("Unknown Command Received: ");
          Serial.println(cmd);
          commandChar.writeValue("ERROR_CMD");
        }
      }
    }

    // This block executes once the device disconnects.
    Serial.print("Disconnected from: ");
    Serial.println(central.address());
  }
}
