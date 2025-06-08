from flask import Flask, render_template_string, redirect, url_for, jsonify
import subprocess
import os
import signal
import json
import socket
import time
from datetime import datetime

# Firebase setup for logging
import firebase_admin
from firebase_admin import credentials, firestore

cred = credentials.Certificate("firebase_key.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

app = Flask(__name__)

# Flags to keep track of portal and session states
SESSION_CONFIG_FILE = "session_config.json"
TRACKING_STARTED_FLAG = "tracking_started.flag"
FACE_STARTED_FLAG = "face_started.flag"
STOP_RECOGNITION_FLAG = "stop_recognition.flag"

portal_process = None

def get_wlan0_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "Unknown"

CONTROL_TEMPLATE = """<!DOCTYPE html>
<html lang="en"><head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Smart Attendance</title>
  <link href="/static/bootstrap.min.css" rel="stylesheet" />
  <style>
  body {
          background-color: #a8b3dc;
          font-family: 'Segoe UI', sans-serif;
          color: #0b0b0b;
          margin: 0;
          min-height: 100vh;
          display: flex;
          flex-direction: column;
          justify-content: center;
          align-items: center;
          padding: 20px; /* Increased padding for more breathing room */ 
          text-align: center;
          overflow-y: hidden;
      }

      .header {
          margin-bottom: 6px; /* More space below header */
      }

      .header h1 {
          font-size: 4rem; /* Slightly larger heading for prominence */
          font-weight: 700;
          margin-bottom: 6px;
          color: #1a1a1a; /* Slightly darker for contrast */
      }

      .header p {
          font-size: 1.6rem; /* Slightly larger paragraph */
          color: #333;
          margin-bottom: 0px;

      }

    .button-wrapper {
      display: flex;
      gap: 15px; /* Increased gap between buttons */
      align-items: center;
      justify-content: center;
      flex-wrap: wrap;
      margin-bottom: 25px; /* More space below button group */
    }

    .main-btn {
      font-size: 1.6rem !important; /* Larger main button text */
      padding: 15px 25px !important; /* More padding for a bolder button */
      max-width: 350px; /* Wider button */
      border-radius: 12px; /* Slightly more rounded corners */
      margin-bottom: 15px;
      box-shadow: 0 4px 10px rgba(0, 0, 0, 0.15); /* Softer, larger shadow */
      transition: transform 0.2s ease, box-shadow 0.2s ease; /* Smooth animation */
    }

    .main-btn:hover {
      transform: translateY(-3px); /* Lift effect on hover */
      box-shadow: 0 6px 15px rgba(0, 0, 0, 0.2); /* Deeper shadow on hover */
    }

    .side-btn {
      font-size: 1.1rem; /* Slightly larger side button text */
      padding: 10px 20px; /* More padding */
      border-radius: 10px; /* Slightly more rounded corners */
      margin-bottom: 10px;
      transition: transform 0.2s ease, box-shadow 0.2s ease; /* Smooth animation */
      box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
    }

    .side-btn:hover {
      transform: translateY(-2px);
      box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
    }

    .status-msg {
      font-size: 1.1rem; /* Larger status message */
      color: #444;
      margin-top: 5px;
      font-weight: 500; /* Slightly bolder */
    }

    .content-wrapper {
      display: flex;
      gap: 11px;
      align-items: flex-start;
      justify-content: center;
      width: 80%;
      max-width: 800px;
    }
    .video-container {
      flex: 1;
      border-radius: 6px;
      overflow: hidden;
      box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
      max-width: 400px;
    }
    .video-container img {
      width: 100%;
      height: auto;
      max-height: 300px;
      object-fit: cover;
    }
    .recognized-list {
      flex: 1;
      background: white;
      padding: 12px;
      border-radius: 8px;
      min-width: 200px;
      max-width: 300px;
      box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    }
    .recognized-list h3 {
      margin-bottom: 10px;
      color: #333;
      font-size: 1.2rem;
    }
    .recognized-list #students {
      font-size: 1.1rem;
      color: #666;
      max-height: 300px;
      overflow-y: auto;
    }
    .badge {
      display: inline-block;
      padding: 4px 8px;
      margin: 2px;
      border-radius: 4px;
      font-size: 0.9rem;
    }
    
    .badge:hover {
      background-color: #218838; /* Darker green on hover */
      transform: scale(1.02); /* Slight scale up on hover */
    }
  </style>
</head><body>
  <div class="header">
    <h1>{{ course_id }} – Session {{ session_id }}</h1>
    <p>You must attend for <strong>{{ threshold }}</strong> minutes.</p>
  </div>

  {% if not tracking_started %}
    <div class="button-wrapper">
      <form method="POST" action="/start_class">
        <button type="submit" class="btn btn-success main-btn">Start Session</button>
      </form>
      <form method="POST" action="/fetch_config">
        <button type="submit" class="btn btn-info side-btn">Load Info</button>
      </form>
      {% if not portal_started %}
      <form method="POST" action="/start_portal">
        <button type="submit" class="btn btn-secondary side-btn">Start Portal</button>
      </form>
      {% else %}
      <form method="POST" action="/stop_portal">
        <button type="submit" class="btn btn-dark side-btn">Stop Portal</button>
      </form>
      {% endif %}
    </div>
    {% if portal_started %}
    <p class="status-msg">🌐 Portal is live at: <strong>http://{{ portal_ip }}:8080</strong></p>
    {% endif %}

  {% elif tracking_started and not face_started %}
    <div class="content-wrapper" style="
      width: 80%;
      max-width: 600px;
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 20px;
    ">
      <div class="status-info" style="
        background: linear-gradient(145deg, #ffffff, #f0f0f0);
        padding: 20px;
        border-radius: 12px;
        box-shadow: 
          2px 2px 8px rgba(209, 209, 209, 0.2),
          -2px -2px 8px rgba(255, 255, 255, 0.4);
        width: 100%;
        transition: all 0.3s ease;
      ">
        <h3 style="
          color: #2c3e50;
          font-size: 1.5rem;
          font-weight: 600;
          margin-bottom: 15px;
          text-transform: uppercase;
          letter-spacing: 1px;
          text-shadow: 1px 1px 2px rgba(0,0,0,0.1);
          text-align: center;
        ">Session Status</h3>
        
        <div style="
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
          gap: 12px;
          justify-items: center;
        ">
          <div style="
            background: rgba(255,255,255,0.7);
            padding: 12px;
            border-radius: 8px;
            box-shadow: 
              3px 3px 6px #d1d1d1,
              -3px -3px 6px #ffffff;
            width: 100%;
            text-align: center;
          ">
            <p style="
              margin: 0;
              color: #34495e;
              font-size: 1rem;
              font-weight: 500;
            ">
              <strong style="color: #2c3e50;">Connected Students</strong>
              <div id="connectedCount" style="
                color: #27ae60;
                font-weight: 700;
                font-size: 1.8rem;
                margin-top: 5px;
              ">0</div>
            </p>
          </div>

          <div style="
            background: rgba(255,255,255,0.7);
            padding: 12px;
            border-radius: 8px;
            box-shadow: 
              3px 3px 6px #d1d1d1,
              -3px -3px 6px #ffffff;
            width: 100%;
            text-align: center;
          ">
            <p style="
              margin: 0;
              color: #34495e;
              font-size: 1rem;
              font-weight: 500;
            ">
              <strong style="color: #2c3e50;">Time Elapsed</strong>
              <div id="elapsedTime" style="
                color: #2980b9;
                font-weight: 700;
                font-size: 1.8rem;
                margin-top: 5px;
              ">0:00</div>
            </p>
          </div>

          <div style="
            background: rgba(255,255,255,0.7);
            padding: 12px;
            border-radius: 8px;
            box-shadow: 
              3px 3px 6px #d1d1d1,
              -3px -3px 6px #ffffff;
            width: 100%;
            text-align: center;
          ">
            <p style="
              margin: 0;
              color: #34495e;
              font-size: 1rem;
              font-weight: 500;
            ">
              <strong style="color: #2c3e50;">Required Time</strong>
              <div style="
                color: #e74c3c;
                font-weight: 700;
                font-size: 1.8rem;
                margin-top: 5px;
              ">{{ threshold }} min</div>
            </p>
          </div>
        </div>
      </div>

      <form method="POST" action="/start_face_recognition" style="margin-top: 10px;">
        <button type="submit" class="btn btn-primary main-btn" style="
          font-size: 1.4rem !important;
          padding: 12px 25px !important;
          border-radius: 10px;
          box-shadow: 
            0 5px 10px rgba(0,0,0,0.1),
            0 3px 3px rgba(0,0,0,0.1);
          transition: all 0.3s ease;
        ">Start Face Recognition</button>
      </form>
    </div>

    <script>
      // Session start time
      const sessionStartTime = new Date();

      function updateElapsedTime() {
        const now = new Date();
        const elapsed = Math.floor((now - sessionStartTime) / 1000); // elapsed seconds
        const minutes = Math.floor(elapsed / 60);
        const seconds = elapsed % 60;
        document.getElementById('elapsedTime').textContent = 
          `${minutes}:${seconds.toString().padStart(2, '0')}`;
      }

      let lastUpdate = 0;
      const UPDATE_INTERVAL = 2000; // Update every 2 seconds
      
      function updateConnectedStudents() {
        const now = Date.now();
        if (now - lastUpdate < UPDATE_INTERVAL) {
          return;
        }
        lastUpdate = now;
        
        fetch('http://{{ request.host.split(':')[0] }}:5000/connected.json')
          .then(res => res.json())
          .then(data => {
            const connectedCountDiv = document.getElementById('connectedCount');
            connectedCountDiv.textContent = data.connected || 0;
          })
          .catch(err => {
            console.error('Error fetching connected students:', err);
            document.getElementById('connectedCount').textContent = '0';
          });
      }

      // Initial update
      updateConnectedStudents();
      
      // Update every second
      setInterval(updateConnectedStudents, 1000);
      setInterval(updateElapsedTime, 1000);
    </script>

  {% elif tracking_started and face_started %}
    <div class="content-wrapper">
      <div class="video-container" style="
        flex: 1;
        border-radius: 12px;
        overflow: hidden;
        box-shadow: 
          2px 2px 8px rgba(209, 209, 209, 0.2),
          -2px -2px 8px rgba(255, 255, 255, 0.4);
        max-width: 400px;
      ">
        <div id="videoLoading" style="display: none; text-align: center; padding: 20px;">
          <div class="spinner-border text-primary" role="status">
            <span class="visually-hidden">Loading...</span>
          </div>
          <p>Loading video feed...</p>
        </div>
        <img id="videoFeed" style="display: none;" src="http://{{ request.host.split(':')[0] }}:8090/video_feed" alt="Face Recognition Feed" />
      </div>
      
      <div class="recognized-list" style="
        flex: 1;
        background: linear-gradient(145deg, #ffffff, #f0f0f0);
        padding: 20px;
        border-radius: 12px;
        min-width: 200px;
        max-width: 300px;
        box-shadow: 
          2px 2px 8px rgba(209, 209, 209, 0.2),
          -2px -2px 8px rgba(255, 255, 255, 0.4);
      ">
        <h3 style="
          margin-bottom: 15px;
          color: #2c3e50;
          font-size: 1.2rem;
          font-weight: 600;
          text-transform: uppercase;
          letter-spacing: 1px;
          text-shadow: 1px 1px 2px rgba(0,0,0,0.1);
          text-align: center;
        ">Recognized Students</h3>
        <div id="students" style="
          font-size: 1rem;
          color: #34495e;
          max-height: 300px;
          overflow-y: auto;
          padding: 10px;
          background: rgba(255,255,255,0.7);
          border-radius: 8px;
          box-shadow: 
            3px 3px 6px rgba(209, 209, 209, 0.3),
            -3px -3px 6px rgba(255, 255, 255, 0.5);
        ">None</div>
      </div>
    </div>

    <form method="POST" action="/end_class">
      <button type="submit" class="btn btn-danger main-btn" style="
        margin-top: 10px;
        font-size: 1.4rem !important;
        padding: 12px 25px !important;
        border-radius: 10px;
        box-shadow: 
          0 5px 10px rgba(0,0,0,0.1),
          0 3px 3px rgba(0,0,0,0.1);
        transition: all 0.3s ease;
      ">End Session</button>
    </form>

    <script>
      // Ensure video feed is loaded
      const videoFeed = document.getElementById('videoFeed');
      const videoLoading = document.getElementById('videoLoading');
      let retryCount = 0;
      const MAX_RETRIES = 3;
      const RETRY_DELAY = 1000; // 1 second

      function showLoading() {
        videoLoading.style.display = 'block';
        videoFeed.style.display = 'none';
      }

      function showVideo() {
        videoLoading.style.display = 'none';
        videoFeed.style.display = 'block';
      }

      function handleVideoError() {
        console.error('Error loading video feed');
        showLoading();
        
        if (retryCount < MAX_RETRIES) {
          retryCount++;
          console.log(`Retrying video feed (${retryCount}/${MAX_RETRIES})...`);
          setTimeout(() => {
            videoFeed.src = `http://${window.location.hostname}:8090/video_feed?t=${Date.now()}`;
          }, RETRY_DELAY);
        } else {
          console.error('Max retries reached. Please refresh the page.');
          videoLoading.innerHTML = '<p class="text-danger">Failed to load video feed. Please refresh the page.</p>';
        }
      }

      videoFeed.onerror = handleVideoError;
      videoFeed.onload = function() {
        console.log('Video feed loaded successfully');
        showVideo();
        retryCount = 0;
      };

      // Show loading state initially
      showLoading();

      let lastUpdate = 0;
      const UPDATE_INTERVAL = 2000; // Update every 2 seconds
      
      function updateRecognizedStudents() {
        const now = Date.now();
        if (now - lastUpdate < UPDATE_INTERVAL) {
          return;
        }
        lastUpdate = now;
        
        fetch('http://{{ request.host.split(':')[0] }}:8090/recognized.json')
          .then(res => res.json())
          .then(data => {
            const studentsDiv = document.getElementById('students');
            if (data.recognized.length > 0) {
              studentsDiv.innerHTML = data.recognized.map(id => 
                `<span class="badge" style="
                  display: inline-block;
                  padding: 6px 12px;
                  margin: 4px;
                  border-radius: 6px;
                  font-size: 0.9rem;
                  background: linear-gradient(145deg, #27ae60, #2ecc71);
                  color: white;
                  box-shadow: 
                    2px 2px 4px rgba(0,0,0,0.1),
                    -1px -1px 2px rgba(255,255,255,0.5);
                  transition: all 0.2s ease;
                ">${id}</span>`
              ).join('');
            } else {
              studentsDiv.textContent = 'None';
            }
          })
          .catch(err => console.error('Error fetching recognized students:', err));
      }

      // Initial update
      updateRecognizedStudents();
      
      // Update every second, but only fetch if enough time has passed
      setInterval(updateRecognizedStudents, 1000);
    </script>

  {% else %}
    <p class="status-msg">✅ Session completed. You may close this screen.</p>
  {% endif %}
</body></html>"""

@app.route("/")
def home():
    config = {"course_id": "N/A", "session_id": "N/A", "threshold_minutes": "-"}
    if os.path.exists(SESSION_CONFIG_FILE):
        with open(SESSION_CONFIG_FILE) as f:
            config = json.load(f)

    return render_template_string(
        CONTROL_TEMPLATE,
        course_id=config.get("course_id", "N/A"),
        session_id=config.get("session_id", "N/A"),
        threshold=config.get("threshold_minutes", "-"),
        tracking_started=os.path.exists(TRACKING_STARTED_FLAG),
        face_started=os.path.exists(FACE_STARTED_FLAG),
        portal_started=portal_process is not None,
        portal_ip=get_wlan0_ip()
    )

@app.route("/start_portal", methods=["POST"])
def start_portal():
    global portal_process
    if portal_process is None:
        portal_process = subprocess.Popen(["python3", "portal.py"])
        print("[INFO] portal.py started")
    return redirect(url_for("home"))

@app.route("/stop_portal", methods=["POST"])
def stop_portal():
    global portal_process
    if portal_process is not None:
        portal_process.send_signal(signal.SIGINT)
        portal_process.wait()
        portal_process = None
        print("[INFO] portal.py stopped")
    return redirect(url_for("home"))

@app.route("/start_class", methods=["POST"])
def start_class():
    global portal_process

    # Clean previous flags and processes
    for flag in [TRACKING_STARTED_FLAG, FACE_STARTED_FLAG, STOP_RECOGNITION_FLAG]:
        if os.path.exists(flag):
            os.remove(flag)

    if portal_process is not None:
        portal_process.send_signal(signal.SIGINT)
        portal_process.wait()
        portal_process = None
        print("[INFO] portal.py auto-stopped by start_class")

    subprocess.Popen(["python3", "full_log.py"])
    with open(TRACKING_STARTED_FLAG, "w") as f:
        f.write("1")

    print("[INFO] full_log.py started")
    return redirect(url_for("home"))

@app.route("/start_face_recognition", methods=["POST"])
def start_face_recognition():
    os.system("pkill -f full_log.py")

    with open(FACE_STARTED_FLAG, "w") as f:
        f.write("1")

    subprocess.Popen(["python3", "run_recognition_stream.py"])
    print("[INFO] run_recognition_stream.py started")

    return redirect(url_for("home"))

@app.route("/end_class", methods=["POST"])
def end_class():
    # 1: Signal face recognition to stop gracefully
    with open(STOP_RECOGNITION_FLAG, "w") as f:
        f.write("1")
    print("[INFO] Sent stop signal to run_recognition.py")

    # 2: Wait until run_recognition.py exits
    timeout = 3 # seconds
    for _ in range(timeout * 10):  # check every 0.1s
        time.sleep(0.1)
        result = os.system("pgrep -f run_recognition.py > /dev/null")
        if result != 0:
            print("[INFO] run_recognition.py has stopped.")
            break
    else:
        print("⚠️ Timeout waiting for run_recognition.py to stop.")

    # 3: Remove state flags
    for flag in [TRACKING_STARTED_FLAG, FACE_STARTED_FLAG]:
        if os.path.exists(flag):
            os.remove(flag)

    # 4: Upload final log to Firebase
    try:
        with open(SESSION_CONFIG_FILE) as f:
            config = json.load(f)

        course_id = config["course_id"]
        session_id = config["session_id"]
        session_file = f"{course_id}_{session_id}.json"
        session_path = os.path.join("logs", course_id, session_file)

        with open(session_path, "r") as f:
            session_data = json.load(f)

        # Convert students list to map
        student_map = {}
        if isinstance(session_data, list):
            for student in session_data:
                student_id = student.get("student_id", "unknown")
                student_map[student_id] = student
        else:
            student_map = session_data  # if it's already a dict

        # Upload to the 'Test' collection (flat format)
        doc_id = f"{course_id}_{session_id}"
        db.collection("FlatDesign").document(doc_id).set({
            "course_id": course_id,
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            "students": student_map
        })

        print(f"✅ Uploaded session to Test/{doc_id} in Firestore.")

    except Exception as e:
        print(f"❌ Error uploading to Firebase: {e}")

    return redirect(url_for("home"))

@app.route("/fetch_config", methods=["POST"])
def fetch_config():
    try:
        # Fetch config from Firestore
        config_ref = db.collection("Session_config").document("details")
        config_doc = config_ref.get()
        
        if config_doc.exists:
            config_data = config_doc.to_dict()
            # Save to local file
            with open(SESSION_CONFIG_FILE, "w") as f:
                json.dump(config_data, f)
            print("[INFO] Successfully fetched and saved config from Firestore")
        else:
            print("[WARNING] No config found in Firestore")
            
    except Exception as e:
        print(f"[ERROR] Failed to fetch config: {e}")
        
    return redirect(url_for("home"))

@app.route("/status")
def status():
    if os.path.exists(SESSION_CONFIG_FILE):
        with open(SESSION_CONFIG_FILE) as f:
            return json.load(f)
    return {"error": "No session config found"}

@app.route("/connected.json")
def get_connected():
    try:
        # Get current session info
        with open(SESSION_CONFIG_FILE) as f:
            config = json.load(f)
        
        course_id = config["course_id"]
        session_id = config["session_id"]
        session_file = f"{course_id}_{session_id}.json"
        session_path = os.path.join("logs", course_id, session_file)
        
        # Read session data
        with open(session_path, "r") as f:
            session_data = json.load(f)
        
        # Get current connected MACs from iw command
        iw_output = subprocess.check_output(["iw", "dev", "wlan0", "station", "dump"]).decode()
        connected_macs = set()
        
        for line in iw_output.splitlines():
            if line.strip().startswith("Station"):
                mac = line.strip().split()[1].upper()
                connected_macs.add(mac)
        
        # Count students that are currently connected
        connected = 0
        connected_students = []
        
        for student in session_data:
            if student["mac"] in connected_macs:
                connected += 1
                connected_students.append(student["student_id"])
        
        print(f"[DEBUG] Found {connected} currently connected students")
        return jsonify({
            "connected": connected,
            "students": connected_students
        })
    except Exception as e:
        print(f"[ERROR] Failed to get connected students: {e}")
        return jsonify({"connected": 0, "students": []})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
