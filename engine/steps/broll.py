"""B-roll + emoji effects planning (LLM) ar Pexels theke stock footage download.

plan_effects()  -> LLM ke clip transcript diye kon somoy ki cutaway/emoji hobe jiggesh kori.
fetch_broll()   -> Pexels API diye keyword er portrait stock video namai (free API key lagbe).

PEXELS_API_KEY na thakle B-roll silently skip hoy (emoji/sfx tobuo chole).
"""
import hashlib
import json
import os
import re
from pathlib import Path

import requests

ENGINE_DIR = Path(__file__).resolve().parent.parent
EMOJI_DIR = ENGINE_DIR / "assets" / "emoji"

EMOJI_NAMES = [p.stem for p in EMOJI_DIR.glob("*.png")] if EMOJI_DIR.exists() else []

PLAN_PROMPT = """You are a short-form video editor adding B-roll cutaways and emoji pops.

Below is the transcript of ONE vertical short clip ({dur:.0f} seconds long), with
timestamps relative to the clip start.

Suggest:
1. "cutaways": 1-{max_broll} stock-footage cutaway moments. Each has:
   - "t": seconds from clip start (between 2 and {t_max:.0f}; keep 4+ seconds apart)
   - "keyword": a concrete, VISUAL English search term for stock video (e.g. "city traffic",
     "typing on laptop", "money falling"). No abstract words.
2. "emojis": 1-4 emoji pop moments. Each has:
   - "t": seconds from clip start
   - "name": one of: {emoji_list}

Pick moments where the visual/emoji genuinely matches what is being said.
Return ONLY valid JSON: {{"cutaways":[...], "emojis":[...]}}

TRANSCRIPT:
{transcript}

JSON:"""


def _fmt_segments(segments, clip_start):
    return "\n".join(
        f"[{max(s['start'] - clip_start, 0):.1f}s] {s['text']}" for s in segments)


def plan_effects(clip, backend, max_broll=3, progress=print):
    """LLM diye cutaway/emoji plan. Return {"cutaways":[{t,keyword}], "emojis":[{t,name}]}."""
    dur = clip["end"] - clip["start"]
    if dur < 8 or not clip.get("segments"):
        return {"cutaways": [], "emojis": []}
    prompt = PLAN_PROMPT.format(
        dur=dur, max_broll=max_broll, t_max=max(dur - 4, 3),
        emoji_list=", ".join(EMOJI_NAMES) or "fire, idea, money",
        transcript=_fmt_segments(clip["segments"], clip["start"]),
    )
    raw = backend.complete(prompt, json_mode=True)
    plan = _extract_json(raw)

    out = {"cutaways": [], "emojis": []}
    for c in (plan.get("cutaways") or [])[:max_broll]:
        try:
            t = float(c["t"])
            kw = str(c["keyword"]).strip()
        except (KeyError, TypeError, ValueError):
            continue
        if kw and 1.0 <= t <= dur - 3:
            out["cutaways"].append({"t": round(t, 2), "keyword": kw})
    for e in (plan.get("emojis") or [])[:4]:
        try:
            t = float(e["t"])
            name = str(e["name"]).strip().lower().replace(" ", "_")
        except (KeyError, TypeError, ValueError):
            continue
        if name in EMOJI_NAMES and 0.5 <= t <= dur - 1.5:
            out["emojis"].append({"t": round(t, 2), "name": name})
    # cutaway gula porjapto fak rakhi (overlap korle kharap dekhay)
    out["cutaways"].sort(key=lambda c: c["t"])
    spaced = []
    for c in out["cutaways"]:
        if not spaced or c["t"] - spaced[-1]["t"] >= 4.0:
            spaced.append(c)
    out["cutaways"] = spaced
    return out


def _extract_json(text):
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?|\n?```$", "", text).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            return json.loads(m.group(0))
    return {}


def fetch_broll(keyword, cache_dir, api_key=None, timeout=60):
    """Pexels theke keyword er portrait stock video namay. Path ba None."""
    api_key = api_key or os.environ.get("PEXELS_API_KEY", "")
    if not api_key:
        return None
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "_", keyword.lower()).strip("_")[:40]
    h = hashlib.md5(keyword.encode()).hexdigest()[:8]
    out = cache_dir / f"{slug}_{h}.mp4"
    if out.exists() and out.stat().st_size > 10000:
        return out

    try:
        r = requests.get(
            "https://api.pexels.com/videos/search",
            params={"query": keyword, "per_page": 3, "orientation": "portrait",
                    "size": "medium"},
            headers={"Authorization": api_key}, timeout=timeout)
        r.raise_for_status()
        videos = r.json().get("videos") or []
    except Exception:
        return None

    best = None
    for v in videos:
        for f in v.get("video_files", []):
            w, hgt = f.get("width") or 0, f.get("height") or 0
            if hgt >= 1000 and hgt >= w:      # portrait-ish, >=1000px
                if best is None or hgt < best[0]:   # sobcheye choto sufficient file (fast dl)
                    best = (hgt, f["link"])
        if best:
            break
    if not best:
        return None
    try:
        with requests.get(best[1], stream=True, timeout=timeout) as resp:
            resp.raise_for_status()
            with open(out, "wb") as fh:
                for chunk in resp.iter_content(1 << 16):
                    fh.write(chunk)
    except Exception:
        out.unlink(missing_ok=True)
        return None
    return out if out.exists() and out.stat().st_size > 10000 else None


def emoji_path(name):
    p = EMOJI_DIR / f"{name}.png"
    return p if p.exists() else None
