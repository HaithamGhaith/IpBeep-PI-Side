IpBeep – Smart Attendance System
🚀 Features
•	📸 Face recognition using Picamera2 and dlib
•	🌐 Local Wi-Fi hotspot with captive portal for student check-in
•	🕒 MAC-based presence tracking (start, last seen, total minutes)
•	🔐 Dual validation: connected + recognized
•	☁️ Firebase Firestore sync (FlatDesign model)
•	🧑‍🏫 Instructor dashboard to view courses and sessions (React)
•	🧩 Modular design with individual tracking scripts
📁 Folder Structure
•	captures/ - Face images for encoding
•	logs/ - Per-session logs (JSON format)
•	static/ - Assets for Flask UI
•	venv/ - Virtual environment (gitignored)
•	class_control.py - Main instructor control panel (UI)
•	full_log.py - Tracks MAC/IP presence time
•	run_recognition_stream.py - Face recognition with video feed
•	encode_faces.py - Encodes known faces into encodings.pkl
•	portal.py - Captive portal during registration
•	test_camera.py - Checks Picamera2 functionality
•	sync_to_firebase.py - Uploads session log to Firestore
•	session_config.json - Active session settings
•	registration.json - Student info used for portal
•	requirements.txt - Python dependencies
•	.gitignore - Ignore logs, secrets, etc.
•	README.md - This documentation
🛠️ Setup Instructions
•	Python 3.9+, OpenCV, Flask, dlib, firebase-admin, face_recognition, picamera2
•	Install dependencies: pip install -r requirements.txt
•	Encode face data: python encode_faces.py
🚀 Running the System
•	Start UI: python class_control.py
•	Access UI: http://<your_pi_ip>:5000
•	Start Captive Portal: bash start_hotspot.sh
🔗 Firestore Database Design
•	FlatDesign: Documents with course_id, session_id, timestamp, and students
•	instructors: Maps Firebase UID to instructor info and courses
•	sessionConfigs: Temporary active session config for the Pi
🔐 Security Notes
•	Never upload firebase_key.json
•	Add firebase_key.json to .gitignore
•	Use Firestore rules to restrict instructor access
🧪 Testing
•	test_camera.py – Check Pi camera
•	sync_to_firebase.py – Upload logs manually
•	http://<pi_ip>:8090/video_feed – View video stream
📸 Screenshots (optional)
•	Add screenshots from the Pi UI or dashboard
🤝 Author
•	Developed by Haitham Ghaith
