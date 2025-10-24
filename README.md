# 🔐 Smart Room Monitoring & Intrusion Detection System (IoT + Edge AI)

### 🧠 Solved It! Edge AI Security: Zero-Latency Access Control on Raspberry Pi

This project demonstrates a *Smart Intruder Detection and Lock Control System* — a complete IoT solution built on *Edge Computing, **AI-based facial recognition, and **cloud-integrated automation*.  
It provides *real-time security* through *local face identification, **motion-triggered power optimization, and **remote control* via *MQTT / BLE / Dropbox alerts*.

---

## 🌍 Project Overview

### 🎯 *Purpose*
To design a hybrid IoT system that *detects intruders, **recognizes authorized users, and **controls a smart lock* using *Raspberry Pi (AI processing)* and *Arduino Nano 33 IoT (actuation)*.

### ⚙ *Key Features*
- *Edge-based Facial Recognition* using Dlib + OpenCV  
- *PIR Motion Sensor* for intelligent power control  
- *BLE Communication* between Raspberry Pi and Arduino for lock actuation  
- *Cloud Uploads (Dropbox)* for intruder image storage  
- *Event Logging* (CSV format) for all access events  
- *Instant Email Notifications* for alerts  
- *MQTT Manual Override* for remote unlocks  
- *Fault-tolerant & Low-Latency* system design  

---

## 🧩 *System Architecture*

```plaintext
[ PIR Sensor ] → [ Raspberry Pi ]
                       ↓
             [ Face Recognition (Dlib) ]
                       ↓
     ┌───────────────┬───────────────┐
     │               │               │
 [ BLE ]         [ MQTT ]        [ Dropbox ]
  ↓                 ↓                 ↓
[ Arduino Nano ]  [ Cloud Broker ]  [ Image Logs ]
  ↓
[ Relay + Solenoid Lock ]
