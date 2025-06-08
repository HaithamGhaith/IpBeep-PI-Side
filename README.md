
# 📡 IpBeep – Smart Attendance System

IpBeep is a real-time attendance tracking system using a Raspberry Pi, facial recognition, and Firebase integration. Designed for university classrooms, it ensures accurate student presence logging via both MAC detection and face verification.

---

## 🚀 Features

- Raspberry Pi as a secure Wi-Fi hotspot (captive portal)
- Student registration via local web interface
- MAC address tracking + Face recognition
- Instructor control panel with Flask GUI
- Real-time logs stored in `JSON` and synced to Firebase Firestore
- Configurable session via the web + Firestore

---

## 📂 Folder Structure

```
.
├── class_control.py          # Flask GUI for instructors (main controller)
├── full_log.py               # Tracks student presence via MAC
├── run_recognition_stream.py # Runs face recognition and updates JSON
├── firebase_key.json         # 🔐 Firebase secret key (not committed)
├── session_config.json       # Holds course_id, session_id, threshold
├── logs/                     # Stores JSON session logs
├── static/                   # Static resources for the Flask app
├── templates/                # (optional if using template files)
└── .gitignore                # Lists ignored files
```

---

## 🔐 .gitignore Highlights

```bash
__pycache__/
*.pyc
venv/
firebase_key.json
logs/
*.log
captures/
*.csv
track_connections.py
run_recognition.py
fast_reup.sh
```

---

## 🧪 How It Works

1. Instructor logs in via website and writes session config (`course_id`, `session_id`, `threshold_minutes`) to Firestore.
2. Instructor presses **“Fetch Config”** on the Pi UI → loads session_config.json from Firestore.
3. Start Session:
   - full_log.py starts tracking connected students.
4. Start Face Recognition:
   - full_log.py stops.
   - run_recognition_stream.py matches faces with pre-encoded data.
5. End Session:
   - face recognition stops gracefully.
   - Final JSON log is uploaded to Firestore `FlatDesign` collection.

---

## 🔥 Firestore Structure

- **Collection: `FlatDesign`**
  ```
  Document ID: <course_id>_<session_id>
  {
    course_id: "CS101",
    session_id: "S1",
    timestamp: "...",
    students: {
      "20201001": {
        student_id: "20201001",
        start: "...",
        total_time: ...,
        recognized: true,
        ...
      },
      ...
    }
  }
  ```

- **Collection: `session_config`**
  ```
  Document ID: latest
  {
    course_id: "CS101",
    session_id: "S1",
    threshold_minutes: 30
  }
  ```

---

## 🛡️ Security Notes

- `firebase_key.json` is **never committed**
- Local network only (Pi IP and hotspot only)
- All sessions are managed by physical button presses to prevent abuse

---

## ✅ To-Do / Future

- Instructor dashboard UI (remote control sessions via web)
- Session analytics charts
- Multi-Pi classroom support
- Sync face encodings from Firebase Storage

---

## 👨‍💻 Author

Made by **HaithamGhaith X Khalid Barham** @ JUST IEEE – 2025 🧠💡

---

## 📜 License

MIT License – use freely with credit.


