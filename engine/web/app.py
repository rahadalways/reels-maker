"""Reels Maker — local web UI (Phase 5+).

Features: drag-drop / YouTube link -> settings -> Generate -> live progress ->
clip preview/download -> caption edit + single-clip re-render.
Run:  python engine/web/app.py   (browser: http://localhost:5000)
"""
import copy
import json
import os
import re
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
from steps.caption import words_to_ass  # noqa: E402
from steps.cut import render_clip  # noqa: E402
from steps.reframe import make_crop_filter  # noqa: E402

try:
    from unidecode import unidecode
except ImportError:
    unidecode = None

load_env()  # engine/.env -> os.environ (API key, UI password)

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
OUT_DIR.mkdir(parents=True, exist_ok=True)

JOBS = {}  # job_id -> {state,pct,log,clips,error, _cfg,_video,_work_dir}
_JOB_ID_RE = re.compile(r"^[0-9a-f]{12}$")  # path-traversal thekay
_PUBLIC_KEYS = ("state", "pct", "log", "clips", "error")


def load_config():
    with open(ENGINE_DIR / "config.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _apply_form(cfg, form):
    if form.get("preset"):
        cfg["caption"]["preset"] = form["preset"]
    cfg["caption"]["enabled"] = form.get("caption", "true") == "true"
    cfg["caption"]["romanize"] = form.get("romanize", "true") == "true"
    lang = form.get("lang")
    cfg["transcribe"]["language"] = None if lang in (None, "", "auto") else lang
    if form.get("min_dur"):
        cfg["segment"]["min_dur"] = float(form["min_dur"])
    if form.get("max_dur"):
        cfg["segment"]["max_dur"] = float(form["max_dur"])
    try:
        n = int(form.get("max_clips") or 0)
    except ValueError:
        n = 0
    if n > 0:
        cfg["ai"]["max_clips"] = n     # AI ke o bola hoy, render o top-N e cap hoy
    cfg["output"]["track_face"] = form.get("track", "true") == "true"
    if form.get("zoom", "true") != "true":
        cfg["output"]["zoom"] = 0.0
        cfg["output"]["fade"] = 0.0
    cfg["ai"]["enabled"] = form.get("ai", "true") == "true"
    return cfg


def _download_youtube(url, work_dir, progress):
    """YouTube (ba onno site) theke video namay — yt-dlp diye. Path ferot dey."""
    import yt_dlp
    progress("⬇️ YouTube theke video namacchi...", 3)
    opts = {
        "outtmpl": str(work_dir / "source.%(ext)s"),
        "format": "bv*[height<=1080][ext=mp4]+ba[ext=m4a]/b[ext=mp4]/b",
        "merge_output_format": "mp4",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.extract_info(url, download=True)
    vids = sorted(work_dir.glob("source.*"), key=lambda p: p.stat().st_size, reverse=True)
    if not vids:
        raise RuntimeError("YouTube download hoyni — link thik ache to?")
    progress(f"   ✓ namano sesh: {vids[0].name}")
    return vids[0]


def _run_job(job_id, video_path, yt_url, cfg, work_dir):
    job = JOBS[job_id]

    def progress(msg, pct=None):
        job["log"].append(msg)
        if pct is not None:
            job["pct"] = pct

    try:
        if yt_url:
            video_path = _download_youtube(yt_url, work_dir, progress)
        job["_video"] = str(video_path)
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
        # error hole source rekhe labh nai — muchhe di
        try:
            if video_path:
                Path(video_path).unlink(missing_ok=True)
        except OSError:
            pass
    # NOTE: success hole source video work_dir e thake — caption edit + re-render er jonno lagbe।
    # (Purano job folder gula majhe majhe muchho: output/ er bhitor।)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/generate", methods=["POST"])
def generate():
    f = request.files.get("video")
    yt_url = (request.form.get("yt_url") or "").strip()
    if (not f or not f.filename) and not yt_url:
        return jsonify({"error": "video file ba YouTube link lagbe"}), 400

    job_id = uuid.uuid4().hex[:12]
    work_dir = OUT_DIR / job_id
    work_dir.mkdir(parents=True, exist_ok=True)

    video_path = None
    if f and f.filename:
        ext = Path(f.filename).suffix or ".mp4"
        video_path = work_dir / f"source{ext}"
        f.save(str(video_path))
        yt_url = ""

    cfg = _apply_form(load_config(), request.form)
    JOBS[job_id] = {
        "state": "running", "pct": 0, "log": [], "clips": [], "error": None,
        "_cfg": cfg, "_video": str(video_path or ""), "_work_dir": str(work_dir),
    }
    threading.Thread(target=_run_job, args=(job_id, video_path, yt_url, cfg, work_dir),
                     daemon=True).start()
    return jsonify({"job_id": job_id})


@app.route("/api/status/<job_id>")
def status(job_id):
    job = JOBS.get(job_id)
    if not job:
        return jsonify({"error": "job nai"}), 404
    return jsonify({k: job[k] for k in _PUBLIC_KEYS})


@app.route("/api/captions/<job_id>/<int:idx>")
def get_captions(job_id, idx):
    """Clip er word list (timing soho) — edit panel er jonno."""
    job = JOBS.get(job_id)
    if not job:
        return jsonify({"error": "job nai (server restart hole purano job edit kora jay na)"}), 404
    clip = next((c for c in job["clips"] if c["index"] == idx), None)
    if not clip:
        return jsonify({"error": "clip nai"}), 404
    tr_path = Path(job["_work_dir"]) / "transcript.json"
    tr = json.loads(tr_path.read_text(encoding="utf-8"))
    ws = [w for w in tr["words"] if w["end"] > clip["start"] and w["start"] < clip["end"]]
    if job["_cfg"]["caption"].get("romanize", True) and unidecode is not None:
        ws = [{**w, "text": unidecode(w["text"]) or w["text"]} for w in ws]
    return jsonify({"words": ws})


@app.route("/api/rerender/<job_id>/<int:idx>", methods=["POST"])
def rerender(job_id, idx):
    """Edited words diye oi clip ta abar render (synchronous — 1-2 min lagte pare)."""
    job = JOBS.get(job_id)
    if not job:
        return jsonify({"error": "job nai"}), 404
    clip = next((c for c in job["clips"] if c["index"] == idx), None)
    if not clip:
        return jsonify({"error": "clip nai"}), 404
    video = Path(job["_video"])
    if not video.exists():
        return jsonify({"error": "source video ar nai — abar generate koro"}), 410

    data = request.get_json(force=True, silent=True) or {}
    words = [w for w in (data.get("words") or [])
             if str(w.get("text", "")).strip()]
    if not words:
        return jsonify({"error": "kono word nai"}), 400

    cfg = copy.deepcopy(job["_cfg"])
    cfg["caption"]["romanize"] = False   # user er edited text-i final
    work_dir = Path(job["_work_dir"])
    oc = cfg["output"]

    ass = None
    if cfg["caption"].get("enabled", True):
        ass = words_to_ass(words, work_dir / f"clip_{idx:02d}.ass",
                           clip["start"], clip["end"], cfg["caption"],
                           oc["width"], oc["height"])
    crop_filter = None
    if oc.get("vertical", True):
        try:
            crop_filter = make_crop_filter(
                video, clip["start"], clip["end"], oc["width"], oc["height"],
                sample_fps=oc.get("sample_fps", 3), zoom_amt=oc.get("zoom", 0.0),
                track=oc.get("track_face", True))
        except Exception:
            pass
    out_clip = work_dir / f"short_{idx:02d}.mp4"
    try:
        render_clip(video, {"start": clip["start"], "end": clip["end"], "index": idx},
                    ass, out_clip, cfg, ffmpeg=cfg.get("ffmpeg", "ffmpeg"),
                    crop_filter=crop_filter, fade=oc.get("fade", 0.0))
    except Exception as e:
        return jsonify({"error": f"re-render fail: {e}"}), 500
    return jsonify({"ok": True, "url": f"/api/file/{job_id}/{out_clip.name}"})


@app.route("/api/file/<job_id>/<path:filename>")
def serve_file(job_id, filename):
    if not _JOB_ID_RE.match(job_id):
        return jsonify({"error": "invalid job id"}), 400
    return send_from_directory(OUT_DIR / job_id, filename)


if __name__ == "__main__":
    host = os.environ.get("REELS_HOST", "127.0.0.1")
    port = int(os.environ.get("REELS_PORT", "5000"))
    lock = "🔒 (password on)" if UI_PASSWORD else "⚠️ (no password)"
    print(f"🚀 Reels Maker UI: http://{host}:{port}  {lock}")
    app.run(host=host, port=port, debug=False, threaded=True)
