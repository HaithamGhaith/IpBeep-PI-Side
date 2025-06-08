from flask import Flask, request, render_template_string
import time
import subprocess
import os
import re
import json
from PIL import Image, ExifTags  # For image cleanup

app = Flask(__name__)
UPLOAD_FOLDER = "captures"
JSON_FILE = "registration.json"

# Create folders/files if missing // if the captures folder does not exist, create it
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

if not os.path.exists(JSON_FILE):
    with open(JSON_FILE, "w") as f:
        json.dump([], f)

# Get MAC address via ARP (notte : only works for Linux )
def get_mac_address(ip):
    try:
        subprocess.run(["ping", "-c", "1", ip], stdout=subprocess.DEVNULL)
        arp_output = subprocess.check_output(["arp", "-n", ip]).decode()
        match = re.search(r"(([a-fA-F0-9]{2}:){5}[a-fA-F0-9]{2})", arp_output)
        if match:
            return match.group(0)
        else:
            return "MAC_NOT_FOUND"
    except Exception:
        return "MAC_ERROR"

# Fix EXIF orientation and save clean JPEG // this is the problem i faced regarding the image orientation
# when the user takes a photo with their phone, it may be rotated incorrectly
def clean_image(input_path):
    try:
        img = Image.open(input_path)

        # Handle EXIF rotation
        try:
            for orientation in ExifTags.TAGS.keys():
                if ExifTags.TAGS[orientation] == 'Orientation':
                    break
            exif = img._getexif()
            if exif is not None:
                orientation_value = exif.get(orientation)
                if orientation_value == 3:
                    img = img.rotate(180, expand=True)
                elif orientation_value == 6:
                    img = img.rotate(270, expand=True)
                elif orientation_value == 8:
                    img = img.rotate(90, expand=True)
        except Exception as e:
            print(f"[EXIF] Orientation fix skipped: {e}")

        img = img.convert("RGB")
        img.save(input_path, format="JPEG", quality=95)
        print(f"[INFO] Image cleaned: {input_path}")
    except Exception as e:
        print(f"[ERROR] Image cleaning failed: {e}")

#  NOTES: i can get a better template later
#  but for now this is good enough
FORM_TEMPLATE = """<!DOCTYPE html><html><head><title>Register</title><link href="/static/bootstrap.min.css" rel="stylesheet"></head><body class="bg-light"><div class="container d-flex flex-column align-items-center justify-content-center min-vh-100"><div class="card shadow p-4" style="width:100%; max-width:450px;"><h2 class="mb-4 text-center">📋 IpBeep Registration</h2><form method="POST" action="/register" enctype="multipart/form-data"><div class="form-floating mb-3"><input type="text" name="name" class="form-control" id="name" placeholder="Name" required><label for="name">Name</label></div><div class="form-floating mb-3"><input type="text" name="student_id" class="form-control" id="student_id" placeholder="20201234" required><label for="student_id">Student ID</label></div><div class="mb-3"><label class="form-label">Take Photo</label><input type="file" name="photo" class="form-control" accept="image/*" capture="user" required></div><button type="submit" class="btn btn-primary w-100">Submit</button></form><p class="text-muted text-center mt-3">Connected to portal at <strong>{{SERVER_IP}}</strong></p></div></div></body></html>"""

SUCCESS_TEMPLATE = """<!DOCTYPE html><html><head><title>Success</title><link href="/static/bootstrap.min.css" rel="stylesheet"></head><body class="bg-success text-white d-flex flex-column align-items-center justify-content-center min-vh-100"><div class="text-center p-4"><h1 class="mb-6">✅ Registered Successfully!</h1><p class="lead">You may now close this page.</p></div></body></html>"""

ERROR_TEMPLATE = """<!DOCTYPE html><html><head><title>Already Registered</title><link href="/static/bootstrap.min.css" rel="stylesheet"></head><body class="bg-danger text-white d-flex flex-column align-items-center justify-content-center min-vh-100"><div class="text-center p-3"><h1 class="mb-4">❌ Already Registered!</h1><p class="lead">You have already submitted your attendance.</p></div></body></html>"""

# Serve form
@app.route("/", methods=["GET"])
def form():
    server_ip = request.host.split(":")[0]
    return render_template_string(FORM_TEMPLATE.replace("{{SERVER_IP}}", server_ip))

#  Handle submission (routes POST)
@app.route("/register", methods=["POST"])
def register():
    name = request.form["name"]
    student_id = request.form["student_id"]
    client_ip = request.remote_addr
    mac = get_mac_address(client_ip)

    with open(JSON_FILE) as f:
        existing = json.load(f)

    for record in existing:
        if record["student_id"] == student_id or record["mac"].lower() == mac.lower():
            return render_template_string(ERROR_TEMPLATE), 400

    # Save photo
    photo = request.files["photo"]
    ts = time.strftime("%Y%m%d-%H%M%S")
    filename = f"{student_id}_{ts}.jpg"
    photo_path = os.path.join(UPLOAD_FOLDER, filename)
    photo.save(photo_path)

    #  Clean it! this part where it fixes the image orientation
    clean_image(photo_path)

    # Save registration
    new_entry = {
        "name": name,
        "student_id": student_id,
        "ip": client_ip,
        "mac": mac,
        "photo_path": photo_path,
        "timestamp": ts
    }
    existing.append(new_entry)

    with open(JSON_FILE, "w") as f:
        json.dump(existing, f, indent=2)

    return render_template_string(SUCCESS_TEMPLATE), 200

# Captive portal triggers  NOTES: these routes are used to trigger the popup in captive portals still doesnt work tho
@app.route("/generate_204", methods=["GET", "POST"])
@app.route("/hotspot-detect.html", methods=["GET", "POST"])
@app.route("/library/test/success.html", methods=["GET", "POST"])
@app.route("/connecttest.txt", methods=["GET", "POST"])
@app.route("/ncsi.txt", methods=["GET", "POST"])
@app.route("/chat", methods=["GET", "POST"])
def trigger_popup():
    return '<meta http-equiv="refresh" content="0; url=/" />', 200

# Run server
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
