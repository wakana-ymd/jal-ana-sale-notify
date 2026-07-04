from flask import Flask, jsonify, request

from watcher.config import load_settings
from watcher.service import WatchService


app = Flask(__name__)


def build_service() -> WatchService:
    settings = load_settings()
    return WatchService.from_settings(settings)


@app.get("/")
def healthcheck():
    return jsonify({"status": "ok"})


@app.route("/run", methods=["GET", "POST"])
def run_watch():
    if request.method == "POST":
        payload = request.get_json(silent=True) or {}
    else:
        payload = request.args.to_dict()

    dry_run = str(payload.get("dry_run", "")).lower() in {"1", "true", "yes"}
    service = build_service()
    result = service.run(dry_run=dry_run)
    status_code = 200 if result["ok"] else 500
    return jsonify(result), status_code


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
