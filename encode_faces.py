"""
@file encode_faces.py
@brief Generates and serializes 128-D face encodings from a set of labeled training images.

This script processes images stored in structured subdirectories (where each subdirectory
name is the name of a known person) and saves the resulting face encodings and names
to a serialized pickle file for fast loading by the main security application.
"""
import face_recognition
import cv2
import os
import pickle

# --- CONFIGURATION ---
DATA_DIR = "./training_images"  # Path to the root directory containing subfolders of training images.
ENCODING_FILE = "encodings.pkl" # Filename for the output serialized file.

print("[INFO] Starting face encoding generation process...")

# Initialize lists to hold the generated data
known_face_encodings = []
known_face_names = []

# --- 1. Iterate Through Training Data Structure ---
# Loop through every person's folder (each folder name is the person's identity)
for name in os.listdir(DATA_DIR):
    person_dir = os.path.join(DATA_DIR, name)

    # Skip any file that is not a directory (e.g., .DS_Store, stray files)
    if not os.path.isdir(person_dir):
        continue

    print(f"[INFO] Processing identity: {name}...")

    # Loop through every image file within the person's dedicated folder
    for filename in os.listdir(person_dir):
        # Only process common image formats
        if filename.lower().endswith((".jpg", ".jpeg", ".png")):
            image_path = os.path.join(person_dir, filename)

            try:
                # Load image file for face processing
                image = face_recognition.load_image_file(image_path)
            except Exception as e:
                print(f"    [ERROR] Failed to load image {filename}: {e}. Skipping.")
                continue

            # Find the location (bounding box) of the face in the image
            face_locations = face_recognition.face_locations(image)

            # --- 2. Face Detection and Encoding ---
            # Enforce strict policy: only encode if exactly one face is detected.
            if len(face_locations) == 1:
                # Generate the 128-D face encoding vector for the detected face
                encoding = face_recognition.face_encodings(image, face_locations)[0]
                
                # Store the encoding and the corresponding name
                known_face_encodings.append(encoding)
                known_face_names.append(name)

            elif len(face_locations) > 1:
                # Warning if multiple faces could confuse the training model
                print(f"    [WARN] Skipping {filename}: Found too many faces ({len(face_locations)}).")
            else:
                # Warning if no face was found
                print(f"    [WARN] Skipping {filename}: No face found. Check image quality/cropping.")

# --- 3. Save the Data ---
print(f"--- Encoding Summary ---")
print(f"[INFO] Successfully generated {len(known_face_encodings)} total face encodings.")
print(f"[INFO] These encodings represent {len(set(known_face_names))} unique identities.")

# Bundle the final data into a dictionary for clean storage
data = {"encodings": known_face_encodings, "names": known_face_names}

# Write the bundled data to the pickle file (serialization)
try:
    with open(ENCODING_FILE, 'wb') as f:
        f.write(pickle.dumps(data))
    print(f"[SUCCESS] Face encodings and names saved to {ENCODING_FILE}")
except Exception as e:
    print(f"[CRITICAL] Failed to write encodings file: {e}")
