import face_recognition
import os
import pickle

CAPTURE_DIR = "captures"
ENCODING_FILE = "encodings.pkl"

# Load existing encodings if available
if os.path.exists(ENCODING_FILE):
    with open(ENCODING_FILE, "rb") as f:
        known_faces = pickle.load(f)
    print(f"[INFO] Loaded {len(known_faces)} previously encoded students.")
else:
    known_faces = {}

print("[INFO] Scanning for new images to encode...")

new_encodings = 0

for file in os.listdir(CAPTURE_DIR):
    if file.lower().endswith(('.jpg', '.jpeg', '.png')):
        student_id = file.split("_")[0]
        if student_id in known_faces:
            print(f"[SKIP] {student_id} already encoded.")
            continue

        image_path = os.path.join(CAPTURE_DIR, file)
        image = face_recognition.load_image_file(image_path)
        encodings = face_recognition.face_encodings(image)

        if not encodings:
            print(f"[WARNING] No face found in {file}")
            continue

        known_faces[student_id] = encodings[0]
        new_encodings += 1
        print(f"[ENCODED] {student_id} from {file}")

# Save updated encodings
with open(ENCODING_FILE, "wb") as f:
    pickle.dump(known_faces, f)

print(f"[✅ DONE] Encoded {new_encodings} new student(s). Total: {len(known_faces)}")
