"""Reels Maker — local web UI (Phase 5).

Browser e drag-drop video -> settings -> Generate -> live progress -> clip preview/download.
Run:  python engine/web/app.py   (tarpor browser e http://localhost:5000)
"""
import os
import sys
import threading
import uuid
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

from flask import (Flask, Response, jsonify, render_template, request,
                   send_from_directory)

ENGINE_DIR = Path(__file__).resolve().parent.parent
ROOT = ENGINE_DIR.parent
sys.path.insert(0, str(ENGINE_DIR))

import yaml  # noqa: E402
from pipeline import run_pipeline  # noqa: E402
from steps.llm import load_env  # noqa: E402

load_env()  # engine/.env -> os.environ (API key, UI password)

# UI password (VPS/public e access hole set koro engine/.env e REELS_UI_PASSWORD)
UI_PASSWORD = os.environ.get("REELS_UI_PASSWORD", "")

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024 * 1024  # 8 GB upload


@app.before_request
def _require_password():
    """REELS_UI_PASSWORD set thakle basic-auth chai (public VPS er jonno)."""
    if not UI_PASSWORD:
        return None
    auth = request.authorization
    if not auth or auth.password != UI_PASSWORD:
        return Response("Login lagbe", 401,
                        {"WWW-Authenticate": 'Basic realm="Reels Maker"'})
    return None

OUT_DIR = ROOT / "output"
UPLOAD_DIR = OUT_DIR / "_uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

JOBS = {}  # job_id -> {state, pct, log, clips, error}


def load_config():
    with open(ENGINE_DIR / "config.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _apply_form(cfg, form):
    if form.get("preset"):
        cfg["caption"]["preset"] = form["preset"]
    cfg["caption"]["enabled"] = form.get("caption", "true") == "true"
    lang = form.get("lang")
    cfg["transcribe"]["language"] = None if lang in (None, "", "auto") else lang
    if form.get("min_dur"):
        cfg["segment"]["min_dur"] = float(form["min_dur"])
    if form.get("max_dur"):
        cfg["segment"]["max_dur"] = float(form["max_dur"])
    cfg["output"]["track_face"] = form.get("track", "true") == "true"
    # zoom off hole 0 kore di (track on thakleo center/face crop, zoom chara)
    if form.get("zoom", "true") != "true":
        cfg["output"]["zoom"] = 0.0
        cfg["output"]["fade"] = 0.0
    cfg["ai"]["enabled"] = form.get("ai", "true") == "true"
    return cfg


def _run_job(job_id, video_path, cfg, work_dir):
    job = JOBS[job_id]

    def progress(msg, pct=None):
        job["log"].append(msg)
        if pct is not None:
            job["pct"] = pct

    try:
        clips = run_pipeline(video_path, cfg, work_dir, progress=progress)
        for c in clips:
            c["url"] = f"/api/file/{job_id}/{c['file']}"
        job["clips"] = clips
        job["state"] = "done"
        job["pct"] = 100
    except Exception as e:
        job["state"] = "error"
        job["error"] = str(e)
        job["log"].append(f"❌ {e}")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/generate", methods=["POST"])
def generate():
    f = request.files.get("video")
    if not f or not f.filename:
        return jsonify({"error": "video file lagbe"}), 400

    job_id = uuid.uuid4().hex[:12]
    safe_name = Path(f.filename).name
    video_path = UPLOAD_DIR / f"{job_id}_{safe_name}"
    f.save(str(video_path))

    cfg = _apply_form(load_config(), request.form)
    work_dir = OUT_DIR / job_id
    JOBS[job_id] = {"state": "running", "pct": 0, "log": [], "clips": [], "error": None}
    threading.Thread(target=_run_job, args=(job_id, video_path, cfg, work_dir),
                     daemon=True).start()
    return jsonify({"job_id": job_id})


@app.route("/api/status/<job_id>")
def status(job_id):
    job = JOBS.get(job_id)
    if not job:
        return jsonify({"error": "job nai"}), 404
    return jsonify(job)


@app.route("/api/file/<job_id>/<path:filename>")
def serve_file(job_id, filename):
    return send_from_directory(OUT_DIR / job_id, filename)


if __name__ == "__main__":
    host = os.environ.get("REELS_HOST", "127.0.0.1")
    port = int(os.environ.get("REELS_PORT", "5000"))
    lock = "🔒 (password on)" if UI_PASSWORD else "⚠️ (no password)"
    print(f"🚀 Reels Maker UI: http://{host}:{port}  {lock}")
    app.run(host=host, port=port, debug=False, threaded=True)
