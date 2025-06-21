import firebase_admin
from firebase_admin import credentials, firestore
import os
import json
from datetime import datetime

def initialize_firebase():
    """
    Initializes the Firebase Admin SDK.
    Checks if it's already initialized to prevent errors.
    """
    if not firebase_admin._apps:
        cred = credentials.Certificate("firebase_key.json")
        firebase_admin.initialize_app(cred)
    return firestore.client()

db = initialize_firebase()

def get_db():
    """
    Returns the Firestore client instance.
    """
    return db

def fetch_and_save_session_config(config_file="session_config.json"):
    """
    Fetches the session configuration from Firestore and saves it to a local file.
    """
    try:
        config_ref = db.collection("Session_config").document("details")
        config_doc = config_ref.get()
        
        if config_doc.exists:
            config_data = config_doc.to_dict()
            with open(config_file, "w") as f:
                json.dump(config_data, f)
            print("[INFO] Successfully fetched and saved config from Firestore")
            return True
        else:
            print("[WARNING] No config found in Firestore")
            return False
            
    except Exception as e:
        print(f"[ERROR] Failed to fetch config: {e}")
        return False

def upload_session_log(course_id, session_id):
    """
    Reads a session's log file, formats it, and uploads it to Firestore.
    """
    try:
        session_file = f"{course_id}_{session_id}.json"
        session_path = os.path.join("logs", course_id, session_file)

        with open(session_path, "r") as f:
            session_data = json.load(f)

        student_map = {}
        if isinstance(session_data, list):
            for student in session_data:
                student_id = student.get("student_id", "unknown")
                student_map[student_id] = student
        else:
            student_map = session_data

        doc_id = f"{course_id}_{session_id}"
        db.collection("FlatDesign").document(doc_id).set({
            "course_id": course_id,
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            "students": student_map
        })
        print(f"✅ Uploaded session to FlatDesign/{doc_id} in Firestore.")
        return True

    except Exception as e:
        print(f"❌ Error uploading to Firebase: {e}")
        return False 