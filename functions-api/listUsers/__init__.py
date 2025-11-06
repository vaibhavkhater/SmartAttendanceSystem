import json
import azure.functions as func
import shared

def main(req: func.HttpRequest) -> func.HttpResponse:
    items = list(shared._users.read_all_items())
    return func.HttpResponse(json.dumps(items), status_code=200, mimetype="application/json")
