"""Step 4: Word-by-word caption (ASS subtitle) — Phase 4.6: stable, no-jiggle.

Fix gula:
  • Active word color-highlight (default scale OFF) — scale korle line width palta giye
    text jiggle kore ("ulta palta"). pop=100 hole shudhu color, layout sthir thake.
  • Word boundary monotonic + non-overlapping — overlap hole libass stack kore upore
    (center e) thele dey. Eta abar fix.
  • Bottom-anchored (alignment 2) + WrapStyle 0 — wrap hole upore baare, niche-r baseline
    sthir thake (lower-third e thake, center e bhase na).
"""
from pathlib import Path

# ---- Style presets (ASS color = &HBBGGRR, alpha &HAABBGGRR) ----
# margin_v = niche theke distance (px). 9:16 height 1920. ~520-600 = lower-third.
PRESETS = {
    "hormozi": {
        "font": "Arial Black", "font_size": 86, "bold": True,
        "text_color": "&H00FFFFFF", "highlight_color": "&H0000F0FF",
        "outline_color": "&H00000000", "outline": 6, "shadow": 2,
        "uppercase": True, "mode": "word", "pop": 100, "group_size": 3,
        "position": "bottom", "margin_v": 560,
    },
    "impact": {
        "font": "Impact", "font_size": 92, "bold": False,
        "text_color": "&H00FFFFFF", "highlight_color": "&H003C14DC",
        "outline_color": "&H00000000", "outline": 6, "shadow": 2,
        "uppercase": True, "mode": "word", "pop": 100, "group_size": 3,
        "position": "bottom", "margin_v": 560,
    },
    "neon": {
        "font": "Verdana", "font_size": 78, "bold": True,
        "text_color": "&H00FFFFFF", "highlight_color": "&H00FFFF00",
        "outline_color": "&H00501E00", "outline": 5, "shadow": 1,
        "uppercase": True, "mode": "word", "pop": 100, "group_size": 3,
        "position": "bottom", "margin_v": 600,
    },
    "tiktok": {
        "font": "Arial", "font_size": 74, "bold": True,
        "text_color": "&H00FFFFFF", "highlight_color": "&H0000E000",
        "outline_color": "&H00000000", "outline": 4, "shadow": 1,
        "uppercase": False, "mode": "word", "pop": 100, "group_size": 4,
        "position": "bottom", "margin_v": 520,
    },
    "clean": {
        "font": "Arial", "font_size": 66, "bold": True,
        "text_color": "&H00FFFFFF", "highlight_color": "&H0000FFFF",
        "outline_color": "&H00000000", "outline": 3, "shadow": 1,
        "uppercase": False, "mode": "fill", "pop": 100, "group_size": 4,
        "position": "bottom", "margin_v": 480,
    },
    "classic": {
        "font": "Arial", "font_size": 64, "bold": True,
        "text_color": "&H00FFFFFF", "highlight_color": "&H0000FFFF",
        "outline_color": "&H00000000", "outline": 3, "shadow": 1,
        "uppercase": False, "mode": "fill", "pop": 100, "group_size": 4,
        "position": "bottom", "margin_v": 420,
    },
}

_ALIGN = {"bottom": 2, "center": 5, "top": 8}


def _resolve(cfg):
    base = dict(PRESETS.get(cfg.get("preset", "hormozi"), PRESETS["hormozi"]))
    for k in ("font", "font_size", "bold", "text_color", "highlight_color",
              "outline_color", "outline", "shadow", "uppercase", "mode", "pop",
              "group_size", "position", "margin_v"):
        if cfg.get(k) is not None:
            base[k] = cfg[k]
    return base


def _fmt_time(t):
    if t < 0:
        t = 0
    h = int(t // 3600); m = int((t % 3600) // 60); s = int(t % 60)
    cs = int(round((t - int(t)) * 100))
    if cs == 100:
        cs = 0; s += 1
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def _header(st, width, height):
    align = _ALIGN.get(st["position"], 2)
    bold = -1 if st["bold"] else 0
    if st["mode"] == "fill":
        primary, secondary = st["highlight_color"], st["text_color"]
    else:
        primary, secondary = st["text_color"], st["text_color"]
    return f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{st['font']},{st['font_size']},{primary},{secondary},{st['outline_color']},&H64000000,{bold},0,0,0,100,100,0,0,1,{st['outline']},{st['shadow']},{align},80,80,{st['margin_v']},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def _txt(s, upper):
    s = s.replace("{", "(").replace("}", ")")
    return s.upper() if upper else s


def _clean_timings(ws, clip_start, clip_end):
    """Monotonic, non-overlapping word start/end (clip-relative). Overlap = stack bug."""
    starts, ends = [], []
    prev = 0.0
    n = len(ws)
    for i, w in enumerate(ws):
        s = max(w["start"] - clip_start, prev)
        starts.append(s)
        prev = s
    for i in range(n):
        # event ses = porer word er start (gap e flicker hoy na); shesh word = nijer end
        if i + 1 < n:
            e = starts[i + 1]
        else:
            e = max(ws[i]["end"] - clip_start, starts[i] + 0.1)
        ends.append(max(e, starts[i] + 0.05))
    return starts, ends


def words_to_ass(words, ass_path, clip_start, clip_end, cfg, width=1080, height=1920):
    ass_path = Path(ass_path)
    st = _resolve(cfg)
    upper = st["uppercase"]
    gsize = int(st["group_size"])

    ws = sorted([w for w in words if w["end"] > clip_start and w["start"] < clip_end],
                key=lambda w: w["start"])
    starts, ends = _clean_timings(ws, clip_start, clip_end)

    lines = []
    for i in range(0, len(ws), gsize):
        gi = list(range(i, min(i + gsize, len(ws))))
        if st["mode"] == "fill":
            lines.append(_fill_line(ws, gi, starts, ends, upper))
        else:
            lines.extend(_word_lines(ws, gi, starts, ends, st, upper))

    ass_path.write_text(_header(st, width, height) + "\n".join(lines) + "\n",
                        encoding="utf-8")
    return ass_path


def _fill_line(ws, gi, starts, ends, upper):
    g_start, g_end = starts[gi[0]], ends[gi[-1]]
    parts, prev = [], g_start
    for j in gi:
        cs = max(int(round((ends[j] - prev) * 100)), 1)
        parts.append(f"{{\\k{cs}}}{_txt(ws[j]['text'], upper)} ")
        prev = ends[j]
    return f"Dialogue: 0,{_fmt_time(g_start)},{_fmt_time(g_end)},Default,,0,0,0,,{''.join(parts).strip()}"


def _word_lines(ws, gi, starts, ends, st, upper):
    """Group er protita word — alada event, active word color highlight. Layout sthir."""
    hl, pop = st["highlight_color"], st["pop"]
    scale = pop and pop != 100
    out = []
    for j in gi:
        parts = []
        for k in gi:
            t = _txt(ws[k]["text"], upper)
            if k == j:
                tag = f"\\1c{hl}" + (f"\\fscx{pop}\\fscy{pop}" if scale else "")
                parts.append(f"{{{tag}}}{t}{{\\r}} ")
            else:
                parts.append(f"{t} ")
        out.append(
            f"Dialogue: 0,{_fmt_time(starts[j])},{_fmt_time(ends[j])},Default,,0,0,0,,{''.join(parts).strip()}")
    return out
