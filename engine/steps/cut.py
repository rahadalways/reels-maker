"""Renderer: clip cut + crop/track/zoom + B-roll cutaway + emoji pop + caption burn +
progress bar + fade + SFX mix — sob EKTA ffmpeg pass e (filter_complex).

Windows path escaping er jhamela edate ffmpeg ke ass file er folder theke (cwd) run
kori — subtitles filter e shudhu basename jay.
"""
import subprocess
from pathlib import Path


def render_clip(video_path, clip, ass_path, out_path, cfg, ffmpeg="ffmpeg",
                crop_filter=None, fade=0.0, broll=None, emojis=None, sfx=None,
                progress_bar=False):
    """
    broll  : [{"path": str, "t": float, "dur": float}]  — full-frame cutaway
    emojis : [{"path": str, "t": float, "dur": float}]  — emoji pop overlay
    sfx    : [{"path": str, "t": float, "vol": float}]  — audio mix-in
    """
    video_path = Path(video_path).resolve()
    ass_path = Path(ass_path).resolve() if ass_path else None
    out_path = Path(out_path).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    broll = broll or []
    emojis = emojis or []
    sfx = sfx or []

    out_cfg = cfg["output"]
    w, h = out_cfg["width"], out_cfg["height"]
    start = clip["start"]
    dur = clip["end"] - clip["start"]

    # ---- inputs ----
    cmd = [ffmpeg, "-y", "-ss", f"{start:.3f}", "-i", str(video_path), "-t", f"{dur:.3f}"]
    vin = {}   # overlay-item -> input index
    idx = 1
    for b in broll:
        cmd += ["-i", str(Path(b["path"]).resolve())]
        vin[id(b)] = idx
        idx += 1
    for e in emojis:
        cmd += ["-loop", "1", "-t", f"{e.get('dur', 1.4):.2f}", "-i", str(Path(e["path"]).resolve())]
        vin[id(e)] = idx
        idx += 1
    for s in sfx:
        cmd += ["-i", str(Path(s["path"]).resolve())]
        vin[id(s)] = idx
        idx += 1

    # ---- video chain ----
    fc = []
    if out_cfg.get("vertical", True):
        base = crop_filter or f"crop=ih*9/16:ih,scale={w}:{h}"
    else:
        base = "null"
    fc.append(f"[0:v]{base}[v0]")
    cur = "v0"
    n = 0

    for b in broll:
        i = vin[id(b)]
        t, bdur = b["t"], b.get("dur", 2.5)
        end = min(t + bdur, dur - 0.3)
        fc.append(
            f"[{i}:v]trim=duration={bdur:.2f},"
            f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},setsar=1,"
            f"setpts=PTS-STARTPTS+{t:.2f}/TB[b{n}]")
        fc.append(f"[{cur}][b{n}]overlay=0:0:enable='between(t,{t:.2f},{end:.2f})'[v{n + 1}]")
        cur = f"v{n + 1}"
        n += 1

    for e in emojis:
        i = vin[id(e)]
        t, edur = e["t"], e.get("dur", 1.4)
        end = min(t + edur, dur - 0.1)
        fc.append(
            f"[{i}:v]format=rgba,scale=190:-1,"
            f"fade=t=in:st=0:d=0.15:alpha=1,fade=t=out:st={max(edur - 0.25, 0.1):.2f}:d=0.25:alpha=1,"
            f"setpts=PTS-STARTPTS+{t:.2f}/TB[e{n}]")
        fc.append(
            f"[{cur}][e{n}]overlay=(W-w)/2:H*0.28:enable='between(t,{t:.2f},{end:.2f})'[v{n + 1}]")
        cur = f"v{n + 1}"
        n += 1

    tail = []
    if ass_path:
        tail.append(f"subtitles={ass_path.name}")
    if progress_bar:
        tail.append(f"drawbox=x=0:y=ih-14:w='iw*min(t/{dur:.2f},1)':h=14:color=0x4F46E5@0.9:t=fill")
    if fade and dur > 2 * fade + 0.2:
        tail.append(f"fade=t=in:st=0:d={fade:.2f}")
        tail.append(f"fade=t=out:st={dur - fade:.2f}:d={fade:.2f}")
    fc.append(f"[{cur}]{','.join(tail) if tail else 'null'}[vout]")

    # ---- audio chain ----
    if sfx:
        labels = []
        fc.append("[0:a]anull[a0]")
        for k, s in enumerate(sfx):
            i = vin[id(s)]
            ms = int(max(s["t"], 0) * 1000)
            vol = s.get("vol", 0.85)
            fc.append(f"[{i}:a]adelay={ms}:all=1,volume={vol:.2f}[sx{k}]")
            labels.append(f"[sx{k}]")
        fc.append(f"[a0]{''.join(labels)}amix=inputs={len(sfx) + 1}:duration=first:normalize=0[aout]")

    cmd += ["-filter_complex", ";".join(fc), "-map", "[vout]"]
    cmd += ["-map", "[aout]"] if sfx else ["-map", "0:a?"]
    cmd += [
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        "-movflags", "+faststart",
        "-t", f"{dur:.3f}",
        str(out_path),
    ]
    cwd = str(ass_path.parent) if ass_path else str(out_path.parent)
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"Render failed for clip {clip.get('index')}:\n{proc.stderr[-1800:]}")
    return out_path
