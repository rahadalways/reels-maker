"""Reels Maker — CLI wrapper. Core logic pipeline.py te.

Usage:
    python main.py path/to/long_video.mp4
    python main.py video.mp4 --caption tiktok --max-dur 45 --no-ai
"""
import argparse
import sys
from pathlib import Path

import yaml

# Windows console e emoji/unicode print korar jonno
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

from pipeline import run_pipeline

ROOT = Path(__file__).resolve().parent


def load_config(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def apply_overrides(cfg, args):
    if args.model:
        cfg["transcribe"]["model_size"] = args.model
    if args.lang:
        cfg["transcribe"]["language"] = args.lang
    if args.min_dur:
        cfg["segment"]["min_dur"] = args.min_dur
    if args.max_dur:
        cfg["segment"]["max_dur"] = args.max_dur
    if args.no_vertical:
        cfg["output"]["vertical"] = False
    if args.no_track:
        cfg["output"]["track_face"] = False
    if args.no_zoom:
        cfg["output"]["zoom"] = 0.0
        cfg["output"]["fade"] = 0.0
    if args.caption:
        cfg["caption"]["preset"] = args.caption
    if args.no_caption:
        cfg["caption"]["enabled"] = False
    if args.no_ai:
        cfg["ai"]["enabled"] = False
    if args.ai_model:
        backend = cfg["ai"].get("backend", "api")
        cfg["ai"][backend]["model"] = args.ai_model
    return cfg


def main():
    ap = argparse.ArgumentParser(description="Reels Maker — long video theke Shorts banao")
    ap.add_argument("video", help="input long video path")
    ap.add_argument("--config", default=str(ROOT / "config.yaml"))
    ap.add_argument("--model", help="whisper model size (tiny/base/small/medium)")
    ap.add_argument("--lang", help="language (e.g. en, bn). default=auto")
    ap.add_argument("--min-dur", type=float, help="min clip length (s)")
    ap.add_argument("--max-dur", type=float, help="max clip length (s)")
    ap.add_argument("--no-vertical", action="store_true", help="9:16 crop off")
    ap.add_argument("--no-track", action="store_true", help="face tracking off, center-crop")
    ap.add_argument("--no-zoom", action="store_true", help="dynamic zoom + fade off")
    ap.add_argument("--caption", help="caption preset: hormozi|impact|neon|tiktok|clean|classic")
    ap.add_argument("--no-caption", action="store_true", help="caption off (sudhu crop/zoom)")
    ap.add_argument("--no-ai", action="store_true", help="AI selection off, rule-based")
    ap.add_argument("--ai-model", help="AI model override (e.g. claude-haiku-4-5)")
    ap.add_argument("--outdir", help="output folder override")
    args = ap.parse_args()

    video = Path(args.video).resolve()
    if not video.exists():
        sys.exit(f"❌ Video pawa jay nai: {video}")

    cfg = apply_overrides(load_config(args.config), args)
    out_dir = Path(args.outdir).resolve() if args.outdir else (ROOT.parent / cfg["output"]["dir"])
    work_dir = out_dir / video.stem

    def progress(msg, pct=None):
        print(f"[{pct:3d}%] {msg}" if pct is not None else f"       {msg}")

    try:
        run_pipeline(video, cfg, work_dir, progress=progress)
    except Exception as e:
        sys.exit(f"❌ {e}")
    print(f"\n📂 Output: {work_dir}")


if __name__ == "__main__":
    main()
