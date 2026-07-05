"""Step 5+6: Clip cut + 9:16 vertical crop (center ba speaker-tracking) + caption burn —
ekta single ffmpeg pass e.

`crop_w` + `x_expr` dile dynamic speaker-tracking crop hoy (reframe.py theke), nahole
center-crop. Windows path escaping er jhamela edate ffmpeg ke ass file er folder theke
(cwd) run kori, tate filter e shudhu basename pass kora jay.
"""
import subprocess
from pathlib import Path


def render_clip(video_path, clip, ass_path, out_path, cfg, ffmpeg="ffmpeg",
                crop_filter=None, fade=0.0):
    video_path = Path(video_path).resolve()
    ass_path = Path(ass_path).resolve() if ass_path else None
    out_path = Path(out_path).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    out_cfg = cfg["output"]
    start = clip["start"]
    dur = clip["end"] - clip["start"]

    filters = []
    if out_cfg.get("vertical", True):
        w, h = out_cfg["width"], out_cfg["height"]
        # crop_filter ase = reframe theke (tracking+zoom soho); nahole center-crop
        filters.append(crop_filter or f"crop=ih*9/16:ih,scale={w}:{h}")

    # subtitles filter — ass_path thakle (caption on); cwd = ass folder
    if ass_path:
        filters.append(f"subtitles={ass_path.name}")

    # fade in/out — clip boundary e smooth transition
    if fade and dur > 2 * fade + 0.2:
        filters.append(f"fade=t=in:st=0:d={fade:.2f}")
        filters.append(f"fade=t=out:st={dur - fade:.2f}:d={fade:.2f}")

    vf = ",".join(filters)

    cmd = [
        ffmpeg, "-y",
        "-ss", f"{start:.3f}",
        "-i", str(video_path),
        "-t", f"{dur:.3f}",
        "-vf", vf,
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        "-movflags", "+faststart",
        str(out_path),
    ]
    cwd = str(ass_path.parent) if ass_path else str(out_path.parent)
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"Render failed for clip {clip.get('index')}:\n{proc.stderr[-1800:]}")
    return out_path
