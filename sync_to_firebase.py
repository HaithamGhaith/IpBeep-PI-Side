import firebase_admin
from firebase_admin import credentials, firestore
import json
import sys
import os

# Load credentials
cred = credentials.Certificate("firebase_key.json")
firebase_admin.initialize_app(cred)

#  Connect to Firestore
db = firestore.client()

#  Get file path from command-line argument
if len(sys.argv) != 2:
    print("Usage: python3 sync_to_firebase.py <path_to_json_file>")
    sys.exit(1)

json_path = sys.argv[1]

if not os.path.exists(json_path):
    print(f"❌ File not found: {json_path}")
    sys.exit(1)

#  Load session JSON
with open(json_path, "r") as f:
    session_data = json.load(f)

#  Extract session name (e.g., CS2_12.json → CS2_12)
session_name = os.path.splitext(os.path.basename(json_path))[0]

#  Upload to Firestore
db.collection("sessions").document(session_name).set(session_data)

print(f"✅ Uploaded session '{session_name}' to Firestore.")
