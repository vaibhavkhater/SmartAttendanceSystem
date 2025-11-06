import json, datetime
import azure.functions as func
import shared

def main(req: func.HttpRequest) -> func.HttpResponse:
    qs_date = req.params.get("date")  # YYYY-MM-DD
    if not qs_date:
        return func.HttpResponse("date=YYYY-MM-DD required", status_code=400)

    start_prefix = datetime.date.fromisoformat(qs_date).isoformat()
    q = "SELECT * FROM c WHERE STARTSWITH(c.timestamp, @d)"
    items = list(shared._att.query_items(
        query=q, parameters=[{"name":"@d","value": start_prefix}], enable_cross_partition_query=True))
    return func.HttpResponse(json.dumps(items), status_code=200, mimetype="application/json")
