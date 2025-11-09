from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
import json
import os
import base64
import uuid
import datetime
import requests
from azure.storage.blob import BlobServiceClient
from azure.cosmos import CosmosClient
from dotenv import load_dotenv
from urllib.parse import urlparse

# Load environment variables from local.settings.json
with open('local.settings.json', 'r') as f:
    settings = json.load(f)
    for key, value in settings['Values'].items():
        os.environ[key] = value

# Configuration
CONF_THRESHOLD = float(os.getenv("CONF_THRESHOLD", "0.85"))

# Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Setup logging
logging.basicConfig(level=logging.INFO)

# Blob Storage Client
_blob = BlobServiceClient.from_connection_string(os.environ["BLOB_CONN_STRING"])
_container = _blob.get_container_client(os.environ["BLOB_CONTAINER"])

def save_base64_jpeg(prefix: str, b64: str) -> str:
    """Save base64 encoded image to Azure Blob Storage"""
    data = base64.b64decode(b64)
    name = f"{prefix}/{datetime.datetime.utcnow().date()}/{uuid.uuid4()}.jpg"
    _container.upload_blob(name, data, overwrite=True, content_type="image/jpeg")
    return name

# Cosmos DB Clients
_cosmos = CosmosClient(os.environ["COSMOS_URI"], os.environ["COSMOS_KEY"])
_db = _cosmos.get_database_client(os.environ["COSMOS_DB"])
_users = _db.get_container_client(os.environ["COSMOS_USERS_CONTAINER"])
_att = _db.get_container_client(os.environ["COSMOS_ATTENDANCE_CONTAINER"])

def upsert_user(user):
    """Insert or update user in Cosmos DB"""
    _users.upsert_item(user)

def get_user_by_tag(tag_name: str):
    """Get user by Custom Vision tag name"""
    q = "SELECT * FROM c WHERE c.classLabel = @t"
    items = list(_users.query_items(
        query=q, 
        parameters=[{"name": "@t", "value": tag_name}], 
        enable_cross_partition_query=True
    ))
    return items[0] if items else None

def add_attendance(row):
    """Add attendance record to Cosmos DB"""
    _att.create_item(row)

# Custom Vision Prediction
def predict_image(b64: str):
    """Call Azure Custom Vision to predict image"""
    endpoint = os.environ["CV_PREDICTION_ENDPOINT"].rstrip("/")
    project = os.environ["CV_PROJECT_ID"]
    published = os.environ["CV_PUBLISHED_NAME"]
    key = os.environ["CV_PREDICTION_KEY"]
    
    # Use the /image endpoint (stores prediction results)
    url = f"{endpoint}/customvision/v3.0/Prediction/{project}/classify/iterations/{published}/image"
    headers = {"Prediction-Key": key, "Content-Type": "application/octet-stream"}
    data = base64.b64decode(b64)
    
    logging.info(f"Custom Vision URL: {url}")
    logging.info(f"Using prediction key: {key[:10]}...")
    
    try:
        r = requests.post(url, headers=headers, data=data, timeout=10)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.HTTPError as e:
        logging.error(f"HTTP Error {e.response.status_code}: {e.response.text}")
        # If the endpoint is wrong, you might need to check your Azure Portal
        # Go to customvision.ai -> Settings -> Get Prediction URL
        raise Exception(f"Custom Vision API Error: {e.response.status_code} - {e.response.text}")
    
# Add after predict_image function



from urllib.parse import urlparse
import base64
import os
import logging
import requests

def _normalize_training_endpoint(ep: str) -> str:
    """
    Ensure endpoint is just the resource root (scheme+host), e.g.
    https://<resource>.cognitiveservices.azure.com
    (Strips any accidental /customvision/... suffix.)
    """
    ep = (ep or "").strip()
    if not ep:
        return ep
    u = urlparse(ep)
    if u.scheme and u.netloc:
        return f"{u.scheme}://{u.netloc}"
    return ep.split("/customvision", 1)[0].rstrip("/")


def add_image_to_training(b64: str, tag_name: str):
    """
    Adds a single image to the Azure Custom Vision Training project under the given tag.
    - Creates the tag if missing (POST /tags?name=...)
    - Uploads the image; prefers single-image bytes endpoint, falls back to multipart if needed.
    Returns a dict suitable for surfacing in your API response.
    """
    training_endpoint_raw = os.environ.get("CV_TRAINING_ENDPOINT", "")
    training_endpoint = _normalize_training_endpoint(training_endpoint_raw)
    project_id = os.environ.get("CV_PROJECT_ID", "")
    training_key = os.environ.get("CV_TRAINING_KEY", "")

    # Headers
    headers_json  = {"Training-Key": training_key, "Content-Type": "application/json"}
    headers_octet = {"Training-Key": training_key, "Content-Type": "application/octet-stream"}
    headers_plain = {"Training-Key": training_key}  # no content-type for some POSTs

    # Helper: strip data URI prefix if present
    def _strip_data_uri(s: str) -> str:
        if isinstance(s, str) and s.startswith("data:"):
            parts = s.split(",", 1)
            return parts[1] if len(parts) == 2 else s
        return s

    # Diagnostics scaffold
    diag = {
        "endpoint_raw": training_endpoint_raw,
        "endpoint_normalized": training_endpoint,
        "project_id": project_id,
        "urls": {}
    }

    try:
        # --- 1) List existing tags (verifies endpoint/key/project) ---
        # Use lower-case 'training' in path to avoid case-sensitive setups
        url_tags = f"{training_endpoint}/customvision/v3.3/training/projects/{project_id}/tags"
        diag["urls"]["list_tags"] = url_tags
        logging.info(f"[CV] GET {url_tags}")
        r = requests.get(url_tags, headers=headers_json, timeout=15)
        r.raise_for_status()
        tags = r.json()

        # Resolve tag; create if absent (query param ?name=)
        tag_id = next((t.get("id") for t in tags if t.get("name") == tag_name), None)
        if not tag_id:
            create_url = url_tags
            diag["urls"]["create_tag"] = f"{create_url}?name={tag_name}"
            logging.info(f"[CV] POST {create_url}?name={tag_name}")
            r = requests.post(create_url, headers=headers_plain, params={"name": tag_name}, timeout=20)
            r.raise_for_status()
            tag_id = r.json().get("id")
            if not tag_id:
                return {
                    "ok": False,
                    "step": "create_tag",
                    "error": f"Create tag succeeded but no 'id' in response: {r.text}",
                    **diag
                }

        # Prepare bytes
        raw_b64 = _strip_data_uri(b64)
        data = base64.b64decode(raw_b64)

        # --- 2) Try single-image bytes endpoint first (/images/image, octet-stream) ---
        url_image_single = f"{training_endpoint}/customvision/v3.3/training/projects/{project_id}/images/image"
        diag["urls"]["upload_image_single"] = f"{url_image_single}?tagIds={tag_id}"
        logging.info(f"[CV] POST {url_image_single}?tagIds={tag_id} (octet-stream single)")

        r = requests.post(
            url_image_single,
            headers=headers_octet,
            params={"tagIds": tag_id},
            data=data,
            timeout=60
        )

        # If the environment says 404 for this route, fall back to multipart
        if r.status_code == 404:
            # --- 3) Fallback: multipart to /images ---
            url_image_multipart = f"{training_endpoint}/customvision/v3.3/training/projects/{project_id}/images"
            diag["urls"]["upload_image_multipart"] = f"{url_image_multipart}?tagIds={tag_id}"
            logging.info(f"[CV] POST {url_image_multipart}?tagIds={tag_id} (multipart fallback)")

            files = {
                # field name is 'imageData' per docs; filename arbitrary; content-type can be octet-stream
                "imageData": ("upload.jpg", data, "application/octet-stream")
            }
            # pass tagIds in query (works reliably); some stacks also accept form field 'tagIds'
            r = requests.post(
                url_image_multipart,
                headers={"Training-Key": training_key},  # let requests set multipart boundary
                params={"tagIds": tag_id},
                files=files,
                timeout=60
            )

        # Now enforce success
        if not r.ok:
            return {
                "ok": False,
                "step": "upload_image",
                "status": r.status_code,
                "body": r.text,
                **diag
            }

        resp = r.json()
        return {
            "ok": True,
            "isBatchSuccessful": resp.get("isBatchSuccessful", True),
            "images": resp.get("images", []),
            "usedTag": {"id": tag_id, "name": tag_name},
            **diag
        }

    except requests.exceptions.HTTPError as e:
        status = e.response.status_code if e.response is not None else None
        body = e.response.text if e.response is not None else str(e)
        logging.error(f"[CV] HTTP {status}: {body}")
        return {
            "ok": False,
            "step": "http_error",
            "status": status,
            "body": body,
            **diag
        }
    except Exception as e:
        logging.exception("[CV] add_image_to_training failed")
        return {"ok": False, "error": str(e), **diag}

# ==================== ENDPOINTS ====================

@app.route('/api/uploadAndEnroll', methods=['POST', 'OPTIONS'])
@app.route('/api/uploadandenroll', methods=['POST', 'OPTIONS'])
def uploadAndEnroll():
    """Endpoint to upload and enroll a new user, and add image to Custom Vision training."""
    if request.method == 'OPTIONS':
        return jsonify({}), 200

    logging.info('uploadAndEnroll function triggered')

    # Helper: strip possible data URI prefix
    def _strip_data_uri(s: str) -> str:
        if isinstance(s, str) and s.startswith("data:"):
            parts = s.split(",", 1)
            return parts[1] if len(parts) == 2 else s
        return s

    try:
        req_body = request.get_json(force=True, silent=False) or {}
        name = req_body.get('name')
        roll = req_body.get('roll')
        userId = req_body.get('userId')
        b64 = req_body.get('base64Image')
        tag = req_body.get('classLabel')

        if not all([name, roll, userId, b64, tag]):
            return jsonify({"error": "name, roll, userId, classLabel, base64Image required"}), 400

        # Normalize base64 (handles data URI)
        raw_b64 = _strip_data_uri(b64)

        # Save to blob storage
        blob_path = save_base64_jpeg(f"enroll/{userId}", raw_b64)

        # Add to Custom Vision training set and capture status for the client
        cv_status = None
        try:
            cv_status = add_image_to_training(raw_b64, tag)
            logging.info(f"Image added to Custom Vision training for tag: {tag}")
        except Exception as cv_error:
            logging.error(f"Failed to add to Custom Vision: {str(cv_error)}")
            cv_status = {"error": str(cv_error)}

        # Save/Upsert user in Cosmos DB
        user_doc = {
            "id": userId,
            "userId": userId,
            "name": name,
            "roll": roll,
            "classLabel": tag,
            "createdAt": datetime.datetime.utcnow().isoformat() + "Z",
            "lastEnrollBlob": blob_path
        }
        upsert_user(user_doc)

        # Return full context so frontend knows if training upload actually succeeded
        return jsonify({
            "ok": True,
            "user": user_doc,
            "customVision": cv_status
        }), 200

    except Exception as e:
        logging.error(f"Error in uploadAndEnroll: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/markAttendance', methods=['POST', 'OPTIONS'])
@app.route('/api/markattendance', methods=['POST', 'OPTIONS'])  # lowercase version
def mark_attendance():
    """Endpoint to mark attendance using face recognition"""
    # Handle CORS preflight
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    logging.info("Running markAttendance function")

    try:
        body = request.get_json()
        b64 = body.get("base64Image")
        if not b64:
            return jsonify({"error": "base64Image required"}), 400

        blob_path = save_base64_jpeg("mark", b64)
        result = predict_image(b64)
        preds = result.get("predictions", [])
        
        if not preds:
            return jsonify({"ok": False, "reason": "no-predictions"}), 200

        top = max(preds, key=lambda p: p['probability'])
        thr = CONF_THRESHOLD
        print(top,thr)

        if top['probability'] >= thr:
            user = get_user_by_tag(top['tagName'])
            if not user:
                return jsonify({"ok": False, "reason": "unknown-tag"}), 200

            att = {
                "id": f"att-{uuid.uuid4()}",
                "userId": user["userId"],
                "name": user["name"],
                "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
                "confidence": round(top['probability'], 4),
                "imageBlobPath": blob_path,
                "device": "web",
                "status": "present"
            }
            add_attendance(att)
            return jsonify({"ok": True, **att}), 200
        else:
            return jsonify({
                "ok": False, 
                "reason": "low-confidence", 
                "confidence": top['probability']
            }), 200
    except Exception as e:
        logging.error(f"Error in markAttendance: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/getAttendance', methods=['GET', 'OPTIONS'])
@app.route('/api/getattendance', methods=['GET', 'OPTIONS'])  # lowercase version
def getAttendance():
    """Endpoint to get attendance records for a specific date"""
    # Handle CORS preflight
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    logging.info('getAttendance function triggered')

    try:
        date = request.args.get('date')
        if not date:
            return jsonify({"error": "date parameter required"}), 400
        
        # Query attendance for the given date
        query = "SELECT * FROM c WHERE STARTSWITH(c.timestamp, @date) ORDER BY c.timestamp DESC"
        items = list(_att.query_items(
            query=query,
            parameters=[{"name": "@date", "value": date}],
            enable_cross_partition_query=True
        ))
        
        return jsonify(items), 200
    except Exception as e:
        logging.error(f"Error in getAttendance: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/listUsers', methods=['GET', 'OPTIONS'])
@app.route('/api/listusers', methods=['GET', 'OPTIONS'])  # lowercase version
def listUsers():
    """Endpoint to list all enrolled users"""
    # Handle CORS preflight
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    logging.info('listUsers function triggered')

    try:
        # Query all users
        query = "SELECT * FROM c"
        items = list(_users.query_items(
            query=query,
            enable_cross_partition_query=True
        ))
        
        return jsonify(items), 200
    except Exception as e:
        logging.error(f"Error in listUsers: {str(e)}")
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    print("Starting local backend server...")
    print("Server running at: http://localhost:7071")
    print("API endpoints:")
    print("  POST http://localhost:7071/api/uploadAndEnroll")
    print("  POST http://localhost:7071/api/markAttendance")
    print("  GET  http://localhost:7071/api/getAttendance?date=YYYY-MM-DD")
    print("  GET  http://localhost:7071/api/listUsers")
    app.run(host='0.0.0.0', port=7071, debug=True)
