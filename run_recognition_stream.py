import face_recognition
import json
import os
import pickle
from datetime import datetime
from picamera2 import Picamera2
import cv2
import numpy as np
import time
from flask import Flask, Response, jsonify
from flask_cors import CORS
import threading
import atexit
import signal
from collections import deque
from queue import Queue

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# === Setup and cleanup
STOP_FLAG = "stop_recognition.flag"
if os.path.exists(STOP_FLAG):
    os.remove(STOP_FLAG)

# === Load encodings
try:
    with open("encodings.pkl", "rb") as f:
        known_faces = pickle.load(f)
except Exception as e:
    print("[ERROR] Could not load encodings.pkl:", e)
    exit()

names = list(known_faces.keys())
encodings = list(known_faces.values())

# === Load session config
try:
    with open("session_config.json") as f:
        session_config = json.load(f)
        course_id = session_config["course_id"]
        session_id = session_config["session_id"]
        threshold = session_config.get("threshold", 60)
except Exception as e:
    print("[ERROR] Could not load session_config.json:", e)
    exit()

# Ensure logs directory exists
log_dir = f"logs/{course_id}"
os.makedirs(log_dir, exist_ok=True)
log_path = f"{log_dir}/{course_id}_{session_id}.json"

# Initialize session data if log file doesn't exist
if not os.path.exists(log_path):
    print(f"[WARNING] Session log not found: {log_path}. Initializing with empty student data.")
    session_data = []
else:
    with open(log_path) as f:
        session_data = json.load(f)

students_by_id = {s["student_id"]: s for s in session_data}

# === Camera Configuration
picam2 = Picamera2()
picam2.preview_configuration.main.size = (640, 480)
picam2.preview_configuration.main.format = "RGB888"
picam2.configure("preview")
picam2.start()
time.sleep(1)

print("[INFO] Camera started. Press Ctrl+C to exit.")

# === Face Recognition Parameters
FACE_DETECTION_DOWNSCALE_FACTOR = 3
FRAME_SKIP_INTERVAL = 2

# Shared state with thread safety
cooldown = {}
COOLDOWN_SECONDS = 5
recognized_students = set()
last_frame_time = time.time()
last_save_time = time.time()
SAVE_INTERVAL = 5

# Thread-safe state management
state_lock = threading.Lock()
current_annotated_frame = None
frame_lock = threading.Lock()
recognition_queue = Queue()  # Queue for recognition updates

def save_logs():
    try:
        with open(log_path, "w") as f:
            json.dump(list(students_by_id.values()), f, indent=2)
        print("[INFO] Logs saved successfully")
    except Exception as e:
        print(f"[ERROR] Failed to save logs: {e}")

def cleanup():
    print("[INFO] Cleaning up resources...")
    try:
        picam2.stop()
        print("[INFO] Camera stopped")
    except Exception as e:
        print(f"[ERROR] Error stopping camera: {e}")
    
    save_logs()
    
    if os.path.exists(STOP_FLAG):
        os.remove(STOP_FLAG)
        print("[INFO] Removed stop flag")

# Register cleanup handlers
atexit.register(cleanup)
signal.signal(signal.SIGINT, lambda s, f: (cleanup(), exit(0)))
signal.signal(signal.SIGTERM, lambda s, f: (cleanup(), exit(0)))

def process_frames():
    global last_frame_time, last_save_time, current_annotated_frame
    frame_count = 0
    
    while True:
        if os.path.exists(STOP_FLAG):
            break

        frame = picam2.capture_array()
        if frame is None:
            time.sleep(0.01)
            continue

        current_time = time.time()
        fps = 1.0 / (current_time - last_frame_time)
        last_frame_time = current_time

        if current_time - last_save_time > SAVE_INTERVAL:
            save_logs()
            last_save_time = current_time

        # Prepare frame for face recognition
        small_frame = cv2.resize(frame, (0, 0), fx=1/FACE_DETECTION_DOWNSCALE_FACTOR, fy=1/FACE_DETECTION_DOWNSCALE_FACTOR)
        rgb_small_frame = np.ascontiguousarray(small_frame[:, :, ::-1], dtype=np.uint8)

        face_locations = []
        face_encs = []

        # Only run face detection on every Nth frame
        frame_count += 1
        if frame_count % FRAME_SKIP_INTERVAL == 0:
            face_locations = face_recognition.face_locations(rgb_small_frame)
            face_encs = face_recognition.face_encodings(rgb_small_frame, face_locations)

        # Annotate the original frame
        annotated_frame = frame.copy()

        # Process faces and update recognition
        with state_lock:
            for i, face_enc in enumerate(face_encs):
                matches = face_recognition.compare_faces(encodings, face_enc)
                name = "Unknown"

                if True in matches:
                    first_match_index = matches.index(True)
                    student_id = names[first_match_index]
                    name = student_id

                    now = time.time()
                    last_seen = cooldown.get(student_id, 0)

                    if now - last_seen > COOLDOWN_SECONDS:
                        cooldown[student_id] = now
                        student = students_by_id.get(student_id)

                        if student:
                            student["face"] = True
                            if student["total_minutes"] >= student["threshold"]:
                                student["attended"] = True
                            print(f"[RECOGNIZED] ✅ {student_id}")
                            recognized_students.add(student_id)
                            # Put recognition update in queue
                            recognition_queue.put({
                                "student_id": student_id,
                                "timestamp": now,
                                "action": "recognized"
                            })
                            save_logs()

                # Scale up coordinates for drawing
                if i < len(face_locations):
                    top, right, bottom, left = face_locations[i]
                    top *= FACE_DETECTION_DOWNSCALE_FACTOR
                    right *= FACE_DETECTION_DOWNSCALE_FACTOR
                    bottom *= FACE_DETECTION_DOWNSCALE_FACTOR
                    left *= FACE_DETECTION_DOWNSCALE_FACTOR

                    # Draw rectangle and name
                    color = (0, 255, 0) if name != "Unknown" else (0, 0, 255)
                    cv2.rectangle(annotated_frame, (left, top), (right, bottom), color, 2)
                    cv2.putText(annotated_frame, name, (left, top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

        # Add FPS counter
        cv2.putText(annotated_frame, f"FPS: {fps:.1f}", (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        # Update the current frame
        with frame_lock:
            current_annotated_frame = annotated_frame

        # Small sleep to prevent CPU overload
        time.sleep(0.01)

    print("[INFO] Frame processing loop stopped.")

def generate_frames_for_stream():
    while True:
        if os.path.exists(STOP_FLAG):
            break
        
        with frame_lock:
            if current_annotated_frame is not None:
                ret, buffer = cv2.imencode('.jpg', current_annotated_frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
                frame_bytes = buffer.tobytes()
                
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            else:
                time.sleep(0.05)

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames_for_stream(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/recognized.json')
def get_recognized():
    updates = []
    # Get all pending updates from the queue
    while not recognition_queue.empty():
        try:
            updates.append(recognition_queue.get_nowait())
        except:
            break
    
    with state_lock:
        return jsonify({
            "recognized": list(recognized_students),
            "updates": updates
        })

@app.route('/stop_face_recognition', methods=['POST'])
def stop_recognition_route():
    with open(STOP_FLAG, 'w') as f:
        f.write('stop')
    print("[INFO] Stop flag created. Recognition thread should terminate soon.")
    return jsonify({"status": "stopping recognition"})

# Start the frame processing thread
frame_processing_thread = threading.Thread(target=process_frames, daemon=True)
frame_processing_thread.start()

if __name__ == '__main__':
    try:
        # Use Flask's built-in threading support
        app.run(host='0.0.0.0', port=8090, debug=False, threaded=True)
    finally:
        cleanup()
        if frame_processing_thread.is_alive():
            print("[INFO] Waiting for frame processing thread to finish...")
            frame_processing_thread.join(timeout=5)
            if frame_processing_thread.is_alive():
                print("[WARNING] Frame processing thread did not terminate gracefully.")
