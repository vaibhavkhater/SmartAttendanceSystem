import json, os, datetime, uuid
import azure.functions as func
import shared

def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        body = req.get_json()
        b64 = body.get("base64Image")
        if not b64:
            return func.HttpResponse("base64Image required", status_code=400)

        blob_path = shared.save_base64_jpeg("mark", b64)
        result = shared.predict_image(b64)
        preds = result.get("predictions", [])
        if not preds:
            return func.HttpResponse(json.dumps({"ok": False, "reason":"no-predictions"}), status_code=200)

        top = max(preds, key=lambda p: p["probability"])
        thr = float(os.getenv("CONF_THRESHOLD","0.85"))
        if top["probability"] >= thr:
            user = shared.get_user_by_tag(top["tagName"])
            if not user:
                return func.HttpResponse(json.dumps({"ok": False, "reason":"unknown-tag"}), status_code=200)

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
            shared.add_attendance(att)
            return func.HttpResponse(json.dumps({"ok": True, **att}), status_code=200, mimetype="application/json")
        else:
            return func.HttpResponse(json.dumps({"ok": False, "reason":"low-confidence", "confidence": top["probability"]}), status_code=200, mimetype="application/json")
    except Exception as e:
        return func.HttpResponse(str(e), status_code=500)
