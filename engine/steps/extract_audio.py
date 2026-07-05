"""Step 1: Video theke audio extract kora (16kHz mono WAV — Whisper er jonno ideal)."""
import subprocess
from pathlib import Path


def extract_audio(video_path, out_path, ffmpeg="ffmpeg"):
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        ffmpeg, "-y",
        "-i", str(video_path),
        "-vn",                # no video
        "-ac", "1",           # mono
        "-ar", "16000",       # 16kHz
        "-c:a", "pcm_s16le",  # WAV
        str(out_path),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"Audio extract failed:\n{proc.stderr[-1500:]}")
    return out_path
