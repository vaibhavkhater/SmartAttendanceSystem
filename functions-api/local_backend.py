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


# ==================== ENDPOINTS ====================

@app.route('/api/uploadAndEnroll', methods=['POST', 'OPTIONS'])
@app.route('/api/uploadandenroll', methods=['POST', 'OPTIONS'])  # lowercase version
def uploadAndEnroll():
    """Endpoint to upload and enroll a new user"""
    # Handle CORS preflight
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    logging.info('uploadAndEnroll function triggered')

    try:
        req_body = request.get_json()
        name = req_body.get('name')
        roll = req_body.get('roll')
        userId = req_body.get('userId')
        b64 = req_body.get('base64Image')
        tag = req_body.get('classLabel')
        
        if not all([name, roll, userId, b64, tag]):
            return jsonify({"error": "name, roll, userId, classLabel, base64Image required"}), 400
        
        blob_path = save_base64_jpeg(f"enroll/{userId}", b64)
        
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
        
        return jsonify({"ok": True, "user": user_doc}), 200
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

        top = max(preds, key=lambda p: p["probability"])
        thr = CONF_THRESHOLD

        if top["probability"] >= thr:
            user = get_user_by_tag(top["tagName"])
            if not user:
                return jsonify({"ok": False, "reason": "unknown-tag"}), 200

            att = {
                "id": f"att-{uuid.uuid4()}",
                "userId": user["userId"],
                "name": user["name"],
                "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
                "confidence": round(top["probability"], 4),
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
                "confidence": top["probability"]
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