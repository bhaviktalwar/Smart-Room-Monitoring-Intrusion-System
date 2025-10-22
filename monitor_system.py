"""
@file smart_door_security.py
@brief Smart Room Monitoring and Intrusion System for Raspberry Pi.

This script integrates several technologies to provide automated access control
and intrusion alerting:
1. Face Recognition (OpenCV, face_recognition) for known user authentication.
2. PIR Sensor (RPi.GPIO) for motion-based activation.
3. Bluetooth Low Energy (Bleak) to command an Arduino-based door lock.
4. MQTT (Paho) for remote control and status updates.
5. Email (SMTP) and Dropbox integration for intruder notifications and evidence storage.
6. Event logging to a local CSV file.
"""

import cv2
import face_recognition
import pickle
import time
import os
import numpy as np
import asyncio
import threading
import csv
import RPi.GPIO as GPIO
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# --- EXTERNAL LIBRARIES ---
# NOTE: These libraries require specific installation steps on Raspberry Pi OS.
try:
    from bleak import BleakClient # Required for BLE communication
    import dropbox                # Required for cloud storage
    import paho.mqtt.client as mqtt # Required for MQTT
except ImportError as e:
    print(f"CRITICAL: Missing required library: {e}. Please install using pip.")
    exit()

# --- SYSTEM CONFIGURATION ---
# The user MUST replace all placeholder values with their actual credentials/addresses.

# 1. HARDWARE & RECOGNITION CONFIG
ENCODING_FILE = "encodings.pkl"    # Path to the serialized file containing known face encodings.
CAMERA_RESOLUTION = (640, 480)     # Pi Camera resolution for image capture.
RESIZE_FACTOR = 4                  # Factor to scale down frames for faster face detection (e.g., 640/4 = 160).
TOLERANCE = 0.55                   # Face recognition threshold (lower = stricter match).
FRAME_SKIP = 10                    # Process only 1 in every X frames to reduce CPU load.
CONFIRM_FRAMES = 3                 # Number of consecutive frames required for confirmation of a face.

# 2. BLE LOCK INTEGRATION CONFIG
# NOTE: The UUIDs used here are standard, but for a custom service, dedicated UUIDs should be used.
ARDUINO_BLE_ADDRESS = "XX:XX:XX:XX:XX:XX" # Replace with the MAC address of your Arduino BLE device.
CHAR_UUID = "00002A37-0000-1000-8000-00805f9b34fb" # Characteristic UUID for sending commands.

# 3. MOTION SENSOR (PIR) CONFIG
PIR_SENSOR_PIN = 17                # GPIO BCM pin connected to the PIR sensor data line.
PIR_COOLDOWN_TIME = 10             # Seconds the camera stays active after last motion.

# 4. TIMING & COOLDOWNS
COOLDOWN_TIME = 10                 # Seconds to wait after an UNLOCK or ALERT action before triggering another.

# --- STORAGE & LOGGING PATHS ---
INTRUDER_DIR = "/home/pi/intruder_logs" # Local directory to temporarily save captured images.
LOG_CSV = "/home/pi/event_logs/events.csv"   # Path for the main event log file.
os.makedirs(INTRUDER_DIR, exist_ok=True)
os.makedirs(os.path.dirname(LOG_CSV), exist_ok=True)

# --- DROPBOX & EMAIL CONFIG (PLACEHOLDERS) ---
# NOTE: Replace these with your actual credentials for notification services.
DROPBOX_ACCESS_TOKEN = "YOUR_DROPBOX_ACCESS_TOKEN_HERE"
DROPBOX_FOLDER = "/Intruder_Images"
SENDER_EMAIL = "your.sender.email@example.com"
SENDER_PASSWORD = "YOUR_EMAIL_APP_PASSWORD_HERE" # Use an App Password, NOT your main email password.
RECEIVER_EMAIL = "your.receiver.email@example.com"
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

# --- MQTT CONFIGURATION ---
MQTT_BROKER = "your-mqtt-broker.cloud" # Example: 1ab589a6fa704d0c91ca7bf50be25492.s1.eu.hivemq.cloud
MQTT_PORT = 8883                       # Default TLS port for HiveMQ Cloud.
MQTT_USERNAME = "mqtt_user_name"
MQTT_PASSWORD = "mqtt_password"
TOPIC_COMMAND = "bhavik/smartdoor/command"       # Topic to receive remote commands (e.g., UNLOCK).
TOPIC_ALERT_LINK = "bhavik/smartdoor/alert_link" # Topic to publish Dropbox links for alerts.
REMOTE_UNLOCK_CMD = "UNLOCK_REMOTE"

# --- GLOBAL STATE MANAGEMENT ---
remote_unlock_flag = False
# Initialize MQTT client with TCP transport as required by some brokers.
mqtt_client = mqtt.Client(transport="tcp")

# --- MQTT CALLBACKS ---
def on_connect(client, userdata, flags, rc):
    """Callback triggered upon connection to the MQTT broker."""
    if rc == 0:
        print("[MQTT] Connected successfully.")
        # Subscribe to the command topic to receive remote instructions.
        client.subscribe(TOPIC_COMMAND)
    else:
        print(f"[MQTT] Connection failed with code {rc}")

def on_message(client, userdata, msg):
    """Callback triggered when a message is received on a subscribed topic."""
    global remote_unlock_flag
    command = msg.payload.decode().strip()

    print(f"[MQTT RECEIVE] Topic: {msg.topic}, Command: {command}")

    if command == REMOTE_UNLOCK_CMD:
        # Set a global flag that will be checked and acted upon in the main loop.
        remote_unlock_flag = True

# --- DROPBOX & NOTIFICATION FUNCTIONS ---

def get_dropbox_client():
    """Initializes and returns the Dropbox client instance."""
    if not DROPBOX_ACCESS_TOKEN or DROPBOX_ACCESS_TOKEN == "YOUR_DROPBOX_ACCESS_TOKEN_HERE":
        print("[CRITICAL] Dropbox token not set. Skipping service initialization.")
        return None

    try:
        dbx = dropbox.Dropbox(DROPBOX_ACCESS_TOKEN)
        # Verify connectivity by checking the current user account.
        dbx.users_get_current_account()
        return dbx
    except Exception as e:
        print(f"[CRITICAL] Dropbox connection failed: {e}")
        return None

def upload_to_dropbox(dbx_client, local_path):
    """Uploads a file to Dropbox and returns a shared link."""
    file_name = os.path.basename(local_path)
    dropbox_path = os.path.join(DROPBOX_FOLDER, file_name)

    try:
        with open(local_path, 'rb') as f:
            # Upload the file, overwriting if it already exists.
            dbx_client.files_upload(f.read(), dropbox_path, mode=dropbox.files.WriteMode('overwrite'))
        # Create a public sharing link for the uploaded image.
        share_link = dbx_client.sharing_create_shared_link(dropbox_path, short_url=True).url
        print(f"[Dropbox] Upload successful. Link: {share_link}")

        # Publish the link via MQTT for immediate access in a remote dashboard
        mqtt_client.publish(TOPIC_ALERT_LINK, share_link, qos=1)
        print(f"[MQTT PUBLISH] Alert link published to {TOPIC_ALERT_LINK}")

        return share_link
    except Exception as e:
        print(f"[Dropbox] Upload failed for {file_name}: {e}")
        return None

def schedule_dropbox_upload(local_path, name, confidence):
    """
    Spawns a background thread to handle Dropbox upload, email notification,
    and local file cleanup to prevent blocking the main recognition loop.
    """
    def worker(path, name, confidence):
        dbx_client = get_dropbox_client()
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

        if dbx_client:
            link = upload_to_dropbox(dbx_client, path)

            # Send notification with the Dropbox link
            if link:
                alert_body = f"!! INTRUDER ALERT! ({name})\nTime: {timestamp}\nConfidence: {confidence:.4f}\nView image securely on Dropbox: {link}"
                # Run the async email function within the thread's event loop.
                asyncio.run(send_notification("🚨 INTRUDER ALERT DETECTED", alert_body))

            # Clean up the local image file after successful cloud upload.
            try:
                os.remove(path)
            except OSError as e:
                print(f"[Cleanup] Failed to delete local file {path}: {e}")

    t = threading.Thread(target=worker, args=(local_path, name, confidence,), daemon=True)
    t.start()

# --- NOTIFICATION FUNCTION ---
async def send_notification(subject, body):
    """Sends a notification email via SMTP."""
    if not SENDER_EMAIL or SENDER_PASSWORD == "YOUR_EMAIL_APP_PASSWORD_HERE":
        print("[EMAIL] Skipping email: Credentials not properly configured.")
        return

    try:
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = RECEIVER_EMAIL
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls() # Secure the connection
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())
        print(f"[EMAIL] Notification sent: {subject}")
    except Exception as e:
        print(f"[EMAIL] Error sending email: {e}. Check server configuration and App Password.")

# --- HELPER & SETUP FUNCTIONS ---
def load_encodings():
    """Loads known face encodings and names from the pickle file."""
    if not os.path.exists(ENCODING_FILE):
        print(f"[ERROR] {ENCODING_FILE} not found! Run encoding script first.")
        return [], []
    with open(ENCODING_FILE, 'rb') as f:
        data = pickle.load(f)
    return data["encodings"], data["names"]

def setup_gpio():
    """Configures the Raspberry Pi GPIO pins for the PIR sensor."""
    GPIO.setmode(GPIO.BCM)
    # Set the PIR pin as an input
    GPIO.setup(PIR_SENSOR_PIN, GPIO.IN)
    print(f"[PIR] Sensor initialized on GPIO BCM {PIR_SENSOR_PIN}")

def log_event(name, action, confidence, img_path):
    """Writes system events (access/alert) to the local CSV log file."""
    header = ["timestamp", "name", "action", "confidence", "image_path"]
    exists = os.path.exists(LOG_CSV)

    if not exists:
        # Create header if the file does not exist
        try:
            with open(LOG_CSV, "w", newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(header)
        except Exception as e:
            print(f"[LOG ERROR] Failed to write CSV header: {e}")
            return

    # Append the new log entry
    try:
        with open(LOG_CSV, "a", newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                time.strftime("%Y-%m-%d %H:%M:%S"),
                name,
                action,
                f"{confidence:.4f}",
                img_path
            ])
        print(f"[LOG] Logged event: {action} by {name}")
    except Exception as e:
        print(f"[LOG ERROR] Failed to write CSV data row: {e}")

async def send_ble_command(command):
    """
    Asynchronously connects to the Arduino BLE lock and sends a command string.
    This function requires the Bleak library and runs within an asyncio loop.
    """
    if ARDUINO_BLE_ADDRESS == "XX:XX:XX:XX:XX:XX":
        print("[BLE] Skipping command: BLE Address not configured.")
        return

    try:
        # Use BleakClient context manager for reliable connection/disconnection.
        async with BleakClient(ARDUINO_BLE_ADDRESS) as client:
            if not client.is_connected:
                print("[BLE] Connecting...")
                await client.connect()
            # Write the command string to the characteristic.
            await client.write_gatt_char(CHAR_UUID, command.encode('utf-8'), response=False)
            print(f"[BLE] Command sent successfully: {command}")
    except Exception as e:
        print(f"[BLE] Error sending command '{command}'. Check device power/address: {e}")

# ---------- MAIN EXECUTION FUNCTION ----------
def main():
    """Main application loop controlling the system's logic flow."""
    global remote_unlock_flag

    # --- 1. MQTT Initialization ---
    try:
        mqtt_client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
        mqtt_client.tls_set()
        mqtt_client.on_connect = on_connect
        mqtt_client.on_message = on_message
        mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
        # Start the network loop in a non-blocking thread to handle callbacks continuously.
        mqtt_client.loop_start()
    except Exception as e:
        print(f"[MQTT ERROR] Failed to initialize MQTT: {e}. Remote control unavailable.")

    picam2 = None

    try:
        # --- 2. System Setup ---
        setup_gpio()
        known_face_encodings, known_face_names = load_encodings()

        # Initialize PiCamera2
        picam2 = Picamera2()
        config = picam2.create_preview_configuration(main={"format": 'XRGB8888', "size": CAMERA_RESOLUTION})
        picam2.configure(config)

        get_dropbox_client() # Initial connection check

        print("[SYSTEM] Initialization complete. Monitoring PIR sensor for motion.")

        last_action_time = 0
        # Start motion time far enough in the past to ensure initial camera state is OFF.
        last_motion_time = time.time() - PIR_COOLDOWN_TIME - 1
        same_face_count = 0
        last_recognized_name = None
        frame_count = 0

        # --- 3. Main Monitoring Loop ---
        while True:
            current_time = time.time()

            # --- 3.0 REMOTE OVERRIDE CHECK (MQTT) ---
            if remote_unlock_flag:
                print("--- MQTT Remote Override Initiated ---")
                asyncio.run(send_ble_command("UNLOCK"))

                # Log the override event
                log_event("Owner", "MANUAL_MQTT_UNLOCK", 1.0, "N/A")

                remote_unlock_flag = False # Reset the flag
                last_action_time = current_time # Reset cooldown
                continue

            # --- 3.1 MOTION CONTROL LOGIC (Camera ON/OFF) ---
            motion = GPIO.input(PIR_SENSOR_PIN)

            if motion:
                last_motion_time = current_time
                if not picam2.started:
                    picam2.start()
                    print("[PIR] Motion detected. Camera starting...")
                    time.sleep(0.6) # Wait for camera sensor to stabilize
            elif picam2.started and (current_time - last_motion_time > PIR_COOLDOWN_TIME):
                # Turn off camera to save resources if no motion for cooldown duration.
                picam2.stop()
                print("[PIR] Motion timeout. Camera stopped.")

            if not picam2.started:
                # Allow exit even if camera is off
                if cv2.waitKey(100) & 0xFF == ord('q'):
                    break
                continue

            # --- 3.2 FACE RECOGNITION THROTTLING ---
            frame_count += 1
            if frame_count % FRAME_SKIP != 0:
                # Display frame and check for exit, but skip processing
                cv2.imshow("Smart Door Lock", cv_frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
                continue

            # --- 3.3 CAPTURE AND PROCESS FRAME ---
            frame = picam2.capture_array()
            cv_frame = cv2.cvtColor(frame, cv2.COLOR_RGBA2BGR)
            # Resize for speed
            small_frame = cv2.resize(cv_frame, (0,0), fx=1/RESIZE_FACTOR, fy=1/RESIZE_FACTOR)
            rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

            # Find all faces in the current frame
            face_locations = face_recognition.face_locations(rgb_small_frame)
            face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)

            # Process each detected face
            for face_encoding, face_location in zip(face_encodings, face_locations):
                name = "Unknown Intruder"
                color = (0,0,255) # Red for Unknown
                confidence = 0.0

                if known_face_encodings:
                    # Compare face to known faces
                    distances = face_recognition.face_distance(known_face_encodings, face_encoding)
                    best_idx = np.argmin(distances)
                    confidence = float(distances[best_idx]) # Note: This is a distance score (lower is better)

                    if distances[best_idx] < TOLERANCE:
                        name = known_face_names[best_idx]
                        color = (0,255,0) # Green for Known

                # Scale coordinates back up for drawing on the full-size frame
                top, right, bottom, left = [v * RESIZE_FACTOR for v in face_location]
                cv2.rectangle(cv_frame, (left,top),(right,bottom), color, 2)
                cv2.putText(cv_frame, name, (left, top-10), cv2.FONT_HERSHEY_DUPLEX, 0.7, color, 2)

                # --- 3.4 CONSECUTIVE FRAME CONFIRMATION ---
                if name == last_recognized_name:
                    same_face_count += 1
                else:
                    same_face_count = 1
                    last_recognized_name = name

                # Trigger action only after confirmation and cooldown period
                if same_face_count >= CONFIRM_FRAMES and (current_time - last_action_time > COOLDOWN_TIME):
                    # --- ACTION TRIGGER ---
                    if name == "Unknown Intruder":
                        print("!! INTRUSION: Unknown person detected. Activating alert procedures.")

                        # 1. Save Image Locally
                        timestamp = time.strftime("%Y%m%d_%H%M%S")
                        fname = f"intruder_{timestamp}.jpg"
                        local_path = os.path.join(INTRUDER_DIR, fname)
                        cv2.imwrite(local_path, cv_frame)

                        # 2. Log locally
                        log_event(name, "ALERT", confidence, local_path)

                        # 3. Upload in background (handles Dropbox, MQTT link publish, and email)
                        schedule_dropbox_upload(local_path, name, confidence)

                        # 4. Send BLE Command to Arduino lock
                        asyncio.run(send_ble_command("ALERT"))

                    else: # Known User
                        print(f"[ACCESS] Recognized known user: {name}. Granting access.")
                        asyncio.run(send_ble_command("UNLOCK"))

                        # Log successful access
                        timestamp = time.strftime("%Y%m%d_%H%M%S")
                        fname = f"access_{name}_{timestamp}.jpg"
                        local_path = os.path.join(INTRUDER_DIR, fname)
                        cv2.imwrite(local_path, cv_frame) # Capture image for audit trail
                        log_event(name, "UNLOCK", confidence, local_path)

                        # Send access notification (without image link)
                        alert_body = f"{name} was granted access at {time.ctime()}."
                        asyncio.run(send_notification(f"✅ Access Granted: {name}", alert_body))

                    # Reset action timer to enforce cooldown
                    last_action_time = current_time

            # Display the result frame
            cv2.imshow("Smart Door Lock", cv_frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    except Exception as e:
        print(f"[CRITICAL ERROR] A major error occurred in the main loop: {e}")
    finally:
        # --- CLEANUP AND RESOURCE RELEASE ---
        if picam2 and picam2.started:
            picam2.stop()
        cv2.destroyAllWindows()
        GPIO.cleanup() # Release RPi GPIO resources
        mqtt_client.loop_stop() # Stop MQTT thread
        print("[SYSTEM] Safe shutdown complete.")

if __name__ == "__main__":
    main()
