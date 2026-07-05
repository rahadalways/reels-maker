"""Step 3 (Phase 2): AI-powered clip selection — LLM diye.

Transcript ta LLM ke dei, oi bujhe kon part gula standalone "viral" short hote pare
seta start/end + hook title + score soho JSON e ferot dey. Phase 1 er pause-rule er
bodole eta use hoy. Backend: API (OpenAI-compatible) ba local (llama-cpp) — llm.py.
"""
import json
import re

PROMPT_TMPL = """You are an expert short-form video editor (YouTube Shorts, Reels, TikTok).
You are given a timestamped transcript of a long video. Pick the BEST segments that
would work as standalone short clips.

Rules for a great clip:
- Self-contained: makes sense on its own, a complete thought (don't cut mid-idea).
- Strong hook in the first seconds (question, bold claim, emotion, surprising fact).
- Length between {min_dur} and {max_dur} seconds.
- Pick the most engaging / valuable / emotional / shareable moments.

Return ONLY valid JSON, no extra text, exactly this shape:
{{
  "clips": [
    {{"start_index": <int>, "end_index": <int>, "title": "<catchy hook>", "reason": "<why it works>", "score": <1-10>}}
  ]
}}
Use the [index] numbers from the transcript for start_index and end_index (inclusive).
Pick at most {max_clips} clips, ordered best first.

TRANSCRIPT:
{transcript}

JSON:"""


def _format_transcript(segments):
    return "\n".join(
        f"[{i}] ({s['start']:.1f}-{s['end']:.1f}s) {s['text']}"
        for i, s in enumerate(segments)
    )


def _extract_json(text):
    text = text.strip()
    # markdown fence soriye fela
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?|\n?```$", "", text).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    m = re.search(r"\{.*\}", text, re.DOTALL)  # prothom { theke shesh }
    if m:
        return json.loads(m.group(0))
    raise ValueError("LLM theke valid JSON pawa gelo na")


def select_segments_ai(segments, backend, min_dur=20, max_dur=60,
                       max_clips=10, progress=print):
    """LLM (backend) diye clip select. Success hole Phase 1 format e clip list, nahole raise."""
    if not segments:
        return []

    prompt = PROMPT_TMPL.format(
        min_dur=int(min_dur), max_dur=int(max_dur), max_clips=max_clips,
        transcript=_format_transcript(segments),
    )
    progress("   🤖 LLM transcript analyze korche...")
    raw = backend.complete(prompt, json_mode=True)
    parsed = _extract_json(raw)

    picks = parsed.get("clips", []) if isinstance(parsed, dict) else []
    n = len(segments)
    clips = []
    for p in picks:
        try:
            si = int(p["start_index"])
            ei = int(p["end_index"])
        except (KeyError, ValueError, TypeError):
            continue
        si = max(0, min(si, n - 1))
        ei = max(si, min(ei, n - 1))
        segs = segments[si:ei + 1]
        if not segs:
            continue
        clips.append({
            "start": segs[0]["start"],
            "end": segs[-1]["end"],
            "text": " ".join(s["text"] for s in segs).strip(),
            "segments": segs,
            "title": str(p.get("title", "")).strip(),
            "reason": str(p.get("reason", "")).strip(),
            "score": p.get("score"),
        })

    clips.sort(key=lambda c: (c.get("score") or 0), reverse=True)
    for idx, c in enumerate(clips, 1):
        c["index"] = idx
    return clips
