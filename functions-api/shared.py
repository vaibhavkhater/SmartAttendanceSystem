import os, base64, uuid, datetime, requests
from azure.storage.blob import BlobServiceClient
from azure.cosmos import CosmosClient

CONF_THRESHOLD = float(os.getenv("CONF_THRESHOLD", "0.85"))

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
