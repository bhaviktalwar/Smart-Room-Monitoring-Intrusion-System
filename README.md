# 🔐 Smart Intrusion Detection System (IoT + Cloud)

This project is a **Smart Intrusion Detection and Door Security System** built using **IoT, Cloud, AI, and Embedded Systems**.

It uses **face recognition, sensors, cloud services, and Bluetooth** to automatically detect people, verify identity, and control a smart door lock.

This is a **full-stack IoT project** combining:

* Raspberry Pi
* Python
* Arduino
* Cloud services
* AI (Face Recognition)
* Networking (MQTT, BLE)

---

## 🧠 What This System Does

✔ Detects motion using PIR sensor
✔ Activates camera only when motion is detected
✔ Recognizes faces using AI
✔ Differentiates between known users and intruders
✔ Unlocks door for known users
✔ Triggers alert for unknown users
✔ Captures intruder image
✔ Uploads evidence to cloud (Dropbox)
✔ Sends email alerts
✔ Publishes alert links via MQTT
✔ Allows remote door unlock using MQTT
✔ Controls door lock via Bluetooth (BLE)
✔ Logs all events in CSV file

---

## 🧩 Project Architecture

```
Camera + PIR Sensor (Raspberry Pi)
        |
        v
Python AI System (Face Recognition + Logic)
        |
        |---- Email Alerts (SMTP)
        |---- Cloud Storage (Dropbox)
        |---- MQTT Cloud Broker
        |---- Local CSV Logs
        |
        v
Bluetooth BLE Communication
        |
        v
Arduino Smart Door Lock System
        |
        v
Relay + LEDs + Door Lock
```

---

## 📂 Project Files

```
Smart_Intrusion_System/
│
├── monitor_system.py        # Main AI + IoT + Cloud system
├── encode_faces.py          # Face encoding generator
├── SmartDoorLock_BLE.ino    # Arduino BLE door lock code
├── training_images/         # Face training images
├── encodings.pkl            # Generated face encodings
└── README.md                # Project documentation
```

---

## 🧠 Technologies Used

### 🖥️ Hardware

* Raspberry Pi
* Pi Camera
* PIR Motion Sensor
* Arduino Nano 33 BLE
* Relay Module
* LEDs
* Smart Door Lock

### 🧑‍💻 Software

* Python
* Arduino IDE
* OpenCV
* face_recognition
* MQTT (Paho)
* BLE (Bleak)
* Dropbox API
* SMTP Email

### ☁️ Cloud

* MQTT Cloud Broker (HiveMQ)
* Dropbox Cloud Storage
* Email Server (SMTP)

---

## ⚙️ How the System Works (Simple Flow)

1. PIR sensor detects motion
2. Camera turns ON
3. Face is detected
4. Face is recognized
5. If face is known → Door UNLOCK
6. If face is unknown → ALERT
7. Intruder image captured
8. Image uploaded to cloud
9. Email alert sent
10. MQTT alert link published
11. Arduino receives BLE command
12. Door relay activates

---

## 🛠️ Setup Flow

### Step 1: Train Faces

```bash
python encode_faces.py
```

### Step 2: Run Main System

```bash
python monitor_system.py
```

### Step 3: Upload Arduino Code

Upload `SmartDoorLock_BLE.ino` to Arduino Nano 33 BLE

---

## 🎯 Learning Outcomes

* IoT system design
* AI integration
* Edge computing
* Cloud integration
* Embedded systems
* Real-time systems
* Sensor integration
* BLE communication
* MQTT networking
* Security system design
* Event-driven programming

---

## 🚀 Future Improvements

* Mobile app integration
* Web dashboard
* Live camera streaming
* Database integration
* Cloud AI models
* Multi-door support
* Role-based access
* Face mask detection
* Anti-spoofing system
* Voice authentication

---

## 👨‍💻 Developer

Bhavik Talwar
IoT Developer | AI Enthusiast | Software Engineering Student

---

## ❤️ Project Vision

"This project represents the future of smart security — where AI, IoT, and cloud work together to protect real-world spaces." 🚀
