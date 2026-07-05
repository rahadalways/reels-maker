"""Step 3 (Phase 1): Rule-based clip selection.

Phase 2 e eta AI (LLM) diye replace hobe. Ekhon natural pause + length diye
clip banai — transcript er sentence gula group kore min/max length er moddhe rakhe.
"""


def select_segments(segments, min_dur=20, max_dur=60, pause_gap=0.6):
    if not segments:
        return []

    clips = []
    cur = []
    cur_start = None

    for i, seg in enumerate(segments):
        if cur_start is None:
            cur_start = seg["start"]
        cur.append(seg)
        dur = seg["end"] - cur_start

        # porer segment er age koto boro pause?
        next_gap = (segments[i + 1]["start"] - seg["end"]) if i + 1 < len(segments) else 999

        reached_min = dur >= min_dur
        natural_break = next_gap >= pause_gap
        too_long = dur >= max_dur

        if (reached_min and natural_break) or too_long:
            clips.append(_make_clip(cur_start, seg["end"], cur))
            cur, cur_start = [], None

    if cur and cur_start is not None:
        clips.append(_make_clip(cur_start, cur[-1]["end"], cur))

    # khub choto last clip (min er ardhek er kom) hole baad
    clips = [c for c in clips if (c["end"] - c["start"]) >= min_dur / 2]
    for idx, c in enumerate(clips, 1):
        c["index"] = idx
    return clips


def _make_clip(start, end, segs):
    return {
        "start": start,
        "end": end,
        "text": " ".join(s["text"] for s in segs).strip(),
        "segments": list(segs),
    }
