import json, datetime
import azure.functions as func
import shared

def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        b = req.get_json()
        name   = b.get("name")
        roll   = b.get("roll")
        userId = b.get("userId")
        b64    = b.get("base64Image")
        tag    = b.get("classLabel")  # EXACT tag name used in Custom Vision

        if not all([name, roll, userId, b64, tag]):
            return func.HttpResponse("name, roll, userId, classLabel, base64Image required", status_code=400)

        blob_path = shared.save_base64_jpeg(f"enroll/{userId}", b64)

        user_doc = {
            "id": userId,
            "userId": userId,
            "name": name,
            "roll": roll,
            "classLabel": tag,
            "createdAt": datetime.datetime.utcnow().isoformat() + "Z",
            "lastEnrollBlob": blob_path
        }
        shared.upsert_user(user_doc)
        return func.HttpResponse(json.dumps({"ok": True, "user": user_doc}), status_code=200, mimetype="application/json")
    except Exception as e:
        return func.HttpResponse(str(e), status_code=500)
