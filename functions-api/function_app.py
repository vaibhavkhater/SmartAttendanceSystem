import azure.functions as func
import logging
import json, os, datetime, uuid
import os, base64, uuid, datetime, requests
from azure.storage.blob import BlobServiceClient
from azure.cosmos import CosmosClient

CONF_THRESHOLD = float(os.getenv("CONF_THRESHOLD", "0.85"))

# Use ANONYMOUS auth level for local development (no function key required)
# Change to FUNCTION for production deployment
app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

# CORS Headers Helper
def add_cors_headers(response: func.HttpResponse) -> func.HttpResponse:
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    return response


# Blob
_blob = BlobServiceClient.from_connection_string(os.environ["BLOB_CONN_STRING"])
_container = _blob.get_container_client(os.environ["BLOB_CONTAINER"])

def save_base64_jpeg(prefix: str, b64: str) -> str:
    data = base64.b64decode(b64)
    name = f"{prefix}/{datetime.datetime.utcnow().date()}/{uuid.uuid4()}.jpg"
    _container.upload_blob(name, data, overwrite=True, content_type="image/jpeg")
    return name  # blob path only

# Cosmos
_cosmos = CosmosClient(os.environ["COSMOS_URI"], os.environ["COSMOS_KEY"])
_db = _cosmos.get_database_client(os.environ["COSMOS_DB"])
_users = _db.get_container_client(os.environ["COSMOS_USERS_CONTAINER"])
_att  = _db.get_container_client(os.environ["COSMOS_ATTENDANCE_CONTAINER"])

def upsert_user(user):
    _users.upsert_item(user)

def get_user_by_tag(tag_name: str):
    q = "SELECT * FROM c WHERE c.classLabel = @t"
    items = list(_users.query_items(
        query=q, parameters=[{"name": "@t", "value": tag_name}], enable_cross_partition_query=True))
    return items[0] if items else None

def add_attendance(row):
    _att.create_item(row)

# Custom Vision Prediction
def predict_image(b64: str):
    endpoint = os.environ["CV_PREDICTION_ENDPOINT"].rstrip("/")
    project = os.environ["CV_PROJECT_ID"]
    published = os.environ["CV_PUBLISHED_NAME"]
    key = os.environ["CV_PREDICTION_KEY"]
    url = f"{endpoint}/customvision/v3.0/Prediction/{project}/classify/iterations/{published}/image"
    headers = {"Prediction-Key": key, "Content-Type": "application/octet-stream"}
    data = base64.b64decode(b64)
    r = requests.post(url, headers=headers, data=data, timeout=10)
    r.raise_for_status()
    return r.json()


@app.route(route="uploadAndEnroll", methods=["POST", "OPTIONS"])
def uploadAndEnroll(req: func.HttpRequest) -> func.HttpResponse:
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
                "name, roll, userId, classLabel, base64Image required", 
                status_code=400
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
        response = func.HttpResponse(str(e), status_code=500)
        return add_cors_headers(response)

@app.route(route="markAttendance", methods=["POST", "OPTIONS"])
def mark_attendance(req: func.HttpRequest) -> func.HttpResponse:
    # Handle CORS preflight
    if req.method == "OPTIONS":
        response = func.HttpResponse(status_code=200)
        return add_cors_headers(response)
    
    logging.info("Runing markAttendance function")
    # print req
    logging.info(f"Request body: {req.get_body()}")

    try:
        body = req.get_json()
        b64 = body.get("base64Image")
        if not b64:
            response = func.HttpResponse("base64Image required", status_code=400)
            return add_cors_headers(response)

        blob_path = save_base64_jpeg("mark", b64)
        result = predict_image(b64)
        preds = result.get("predictions", [])
        if not preds:
            response = func.HttpResponse(
                json.dumps({"ok": False, "reason": "no-predictions"}),
                status_code=200, mimetype="application/json"
            )
            return add_cors_headers(response)

        top = max(preds, key=lambda p: p["probability"])
        thr = float(os.getenv("CONF_THRESHOLD", "0.85"))

        if top["probability"] >= thr:
            user = get_user_by_tag(top["tagName"])
            if not user:
                response = func.HttpResponse(
                    json.dumps({"ok": False, "reason": "unknown-tag"}),
                    status_code=200, mimetype="application/json"
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
                status_code=200, mimetype="application/json"
            )
            return add_cors_headers(response)
        else:
            response = func.HttpResponse(
                json.dumps({"ok": False, "reason": "low-confidence", "confidence": top["probability"]}),
                status_code=200, mimetype="application/json"
            )
            return add_cors_headers(response)
    except Exception as e:
        # Optional: log stack in App Insights
        response = func.HttpResponse(str(e), status_code=500)
        return add_cors_headers(response)


@app.route(route="getAttendance", methods=["GET", "OPTIONS"])
def getAttendance(req: func.HttpRequest) -> func.HttpResponse:
    # Handle CORS preflight
    if req.method == "OPTIONS":
        response = func.HttpResponse(status_code=200)
        return add_cors_headers(response)
    
    logging.info('getAttendance function triggered')

    try:
        date = req.params.get('date')
        if not date:
            response = func.HttpResponse("date parameter required", status_code=400)
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
        response = func.HttpResponse(str(e), status_code=500)
        return add_cors_headers(response)

@app.route(route="listUsers", methods=["GET", "OPTIONS"])
def listUsers(req: func.HttpRequest) -> func.HttpResponse:
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
        response = func.HttpResponse(str(e), status_code=500)
        return add_cors_headers(response)