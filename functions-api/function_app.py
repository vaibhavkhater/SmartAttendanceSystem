import azure.functions as func
import logging
import json
import os
import base64
import uuid
import datetime
import requests
from azure.storage.blob import BlobServiceClient
from azure.cosmos import CosmosClient

# Configuration
CONF_THRESHOLD = float(os.getenv("CONF_THRESHOLD", "0.85"))

# Azure Functions app
app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

# CORS Headers Helper
def add_cors_headers(response: func.HttpResponse) -> func.HttpResponse:
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    return response

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
    
    try:
        r = requests.post(url, headers=headers, data=data, timeout=10)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.HTTPError as e:
        logging.error(f"HTTP Error {e.response.status_code}: {e.response.text}")
        raise Exception(f"Custom Vision API Error: {e.response.status_code} - {e.response.text}")


# ==================== ENDPOINTS ====================

@app.route(route="uploadAndEnroll", methods=["POST", "OPTIONS"])
def uploadAndEnroll(req: func.HttpRequest) -> func.HttpResponse:
    """Endpoint to upload and enroll a new user"""
    # Handle CORS preflight
    if req.method == "OPTIONS":
        response = func.HttpResponse(status_code=200)
        return add_cors_headers(response)
    
    logging.info('uploadAndEnroll function triggered')

    try:
        req_body = req.get_json()
        name = req_body.get('name')
        roll = req_body.get('roll')
        userId = req_body.get('userId')
        b64 = req_body.get('base64Image')
        tag = req_body.get('classLabel')
        
        if not all([name, roll, userId, b64, tag]):
            response = func.HttpResponse(
                json.dumps({"error": "name, roll, userId, classLabel, base64Image required"}),
                status_code=400,
                mimetype="application/json"
            )
            return add_cors_headers(response)
        
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
        
        response = func.HttpResponse(
            json.dumps({"ok": True, "user": user_doc}),
            status_code=200,
            mimetype="application/json"
        )
        return add_cors_headers(response)
    except Exception as e:
        logging.error(f"Error in uploadAndEnroll: {str(e)}")
        response = func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )
        return add_cors_headers(response)


@app.route(route="markAttendance", methods=["POST", "OPTIONS"])
def mark_attendance(req: func.HttpRequest) -> func.HttpResponse:
    """Endpoint to mark attendance using face recognition"""
    # Handle CORS preflight
    if req.method == "OPTIONS":
        response = func.HttpResponse(status_code=200)
        return add_cors_headers(response)
    
    logging.info("Running markAttendance function")

    try:
        body = req.get_json()
        b64 = body.get("base64Image")
        if not b64:
            response = func.HttpResponse(
                json.dumps({"error": "base64Image required"}),
                status_code=400,
                mimetype="application/json"
            )
            return add_cors_headers(response)

        blob_path = save_base64_jpeg("mark", b64)
        result = predict_image(b64)
        preds = result.get("predictions", [])
        
        if not preds:
            response = func.HttpResponse(
                json.dumps({"ok": False, "reason": "no-predictions"}),
                status_code=200,
                mimetype="application/json"
            )
            return add_cors_headers(response)

        top = max(preds, key=lambda p: p["probability"])
        thr = CONF_THRESHOLD

        if top["probability"] >= thr:
            user = get_user_by_tag(top["tagName"])
            if not user:
                response = func.HttpResponse(
                    json.dumps({"ok": False, "reason": "unknown-tag"}),
                    status_code=200,
                    mimetype="application/json"
                )
                return add_cors_headers(response)

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
            response = func.HttpResponse(
                json.dumps({"ok": True, **att}),
                status_code=200,
                mimetype="application/json"
            )
            return add_cors_headers(response)
        else:
            response = func.HttpResponse(
                json.dumps({
                    "ok": False, 
                    "reason": "low-confidence", 
                    "confidence": top["probability"]
                }),
                status_code=200,
                mimetype="application/json"
            )
            return add_cors_headers(response)
    except Exception as e:
        logging.error(f"Error in markAttendance: {str(e)}")
        response = func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )
        return add_cors_headers(response)


@app.route(route="getAttendance", methods=["GET", "OPTIONS"])
def getAttendance(req: func.HttpRequest) -> func.HttpResponse:
    """Endpoint to get attendance records for a specific date"""
    # Handle CORS preflight
    if req.method == "OPTIONS":
        response = func.HttpResponse(status_code=200)
        return add_cors_headers(response)
    
    logging.info('getAttendance function triggered')

    try:
        date = req.params.get('date')
        if not date:
            response = func.HttpResponse(
                json.dumps({"error": "date parameter required"}),
                status_code=400,
                mimetype="application/json"
            )
            return add_cors_headers(response)
        
        # Query attendance for the given date
        query = "SELECT * FROM c WHERE STARTSWITH(c.timestamp, @date) ORDER BY c.timestamp DESC"
        items = list(_att.query_items(
            query=query,
            parameters=[{"name": "@date", "value": date}],
            enable_cross_partition_query=True
        ))
        
        response = func.HttpResponse(
            json.dumps(items),
            status_code=200,
            mimetype="application/json"
        )
        return add_cors_headers(response)
    except Exception as e:
        logging.error(f"Error in getAttendance: {str(e)}")
        response = func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )
        return add_cors_headers(response)


@app.route(route="listUsers", methods=["GET", "OPTIONS"])
def listUsers(req: func.HttpRequest) -> func.HttpResponse:
    """Endpoint to list all enrolled users"""
    # Handle CORS preflight
    if req.method == "OPTIONS":
        response = func.HttpResponse(status_code=200)
        return add_cors_headers(response)
    
    logging.info('listUsers function triggered')

    try:
        # Query all users
        query = "SELECT * FROM c"
        items = list(_users.query_items(
            query=query,
            enable_cross_partition_query=True
        ))
        
        response = func.HttpResponse(
            json.dumps(items),
            status_code=200,
            mimetype="application/json"
        )
        return add_cors_headers(response)
    except Exception as e:
        logging.error(f"Error in listUsers: {str(e)}")
        response = func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )
        return add_cors_headers(response)
