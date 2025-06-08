import json
import os
import time
import subprocess
import signal
import sys
from datetime import datetime

# Constants
REGISTRATION_FILE = "registration.json"
SESSION_CONFIG_FILE = "session_config.json"
LOGS_FOLDER = "logs"

# Global variables forr the wholee file
students = {}
course_id = ""
session_id = ""
log_path = ""

# Handle session stop nottteee: it was ctrl c now its ui 
def handle_exit(signum, frame):
    print("[INFO] Signal received. Saving session log and exiting...")
    save_and_exit()

def save_and_exit():
    global students, log_path
    # Save final tracking info
    for student in students.values():
        student["total_minutes"] = round(student["total_minutes"])
    with open(log_path, "w") as f:
        json.dump(list(students.values()), f, indent=2)
    print(f"[INFO] Session tracking saved to {log_path}")
    sys.exit(0)

#  Attach signal handlers
signal.signal(signal.SIGINT, handle_exit)
signal.signal(signal.SIGTERM, handle_exit)

#  Load session config
if not os.path.exists(SESSION_CONFIG_FILE):
    print("[ERROR] session_config.json not found!")
    sys.exit(1)

with open(SESSION_CONFIG_FILE) as f:
    session_config = json.load(f)

course_id = session_config['course_id']
session_id = session_config['session_id']
threshold_minutes = session_config['threshold_minutes']

#  Load registered students
if not os.path.exists(REGISTRATION_FILE):
    print("[ERROR] registration.json not found!")
    sys.exit(1)

with open(REGISTRATION_FILE) as f:
    registration_data = json.load(f)
    for student in registration_data:
        mac = student["mac"].upper()
        students[mac] = {
            "student_id": student["student_id"],  # ✅ fixed key
            "name": student["name"],
            "mac": mac,
            "ip": student["ip"],
            "start": None,
            "last_seen": None,
            "total_minutes": 0,
            "threshold": threshold_minutes,
            "face": False,
            "attended": False
        }

#  Prepare log path
log_dir = os.path.join(LOGS_FOLDER, course_id)
os.makedirs(log_dir, exist_ok=True)
log_path = os.path.join(log_dir, f"{course_id}_{session_id}.json")

print(f"[INFO] Session tracking started for {course_id} - Session {session_id}")
print("[INFO] Waiting for student MACs...")

# Loop every 30 seconds
try:
    while True:
        iw_output = subprocess.check_output(["iw", "dev", "wlan0", "station", "dump"]).decode()
        connected_macs = set()

        for line in iw_output.splitlines():
            if line.strip().startswith("Station"):
                mac = line.strip().split()[1].upper()
                connected_macs.add(mac)

        now = datetime.now().strftime("%H:%M:%S")
        changes_made = False

        for mac, student in students.items():
            if mac in connected_macs:
                if student["start"] is None:
                    student["start"] = now
                    changes_made = True
                student["last_seen"] = now
                student["total_minutes"] += 0.5  # Each 30s = 0.5 min
                changes_made = True

        # Save logs if any changes were made
        if changes_made:
            try:
                with open(log_path, "w") as f:
                    json.dump(list(students.values()), f, indent=2)
                print("[INFO] Logs saved after update")
            except Exception as e:
                print(f"[ERROR] Failed to save logs: {e}")

        print(f"[INFO] Cycle completed at {now}. Connected: {len(connected_macs)} students")
        time.sleep(30)

except Exception as e:
    print(f"[ERROR] Unexpected error: {e}")
    save_and_exit()
