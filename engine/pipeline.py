"""Reels Maker — core pipeline (CLI + web duitoi eta use kore).

run_pipeline(video, cfg, work_dir, progress) -> clip metadata list.
progress(msg, pct=None) callback diye stage update jay (web UI progress bar er jonno).
"""
import json
import time
from pathlib import Path

from steps.extract_audio import extract_audio
from steps.transcribe import transcribe
from steps.segment import select_segments
from steps.analyze_ai import select_segments_ai
from steps.llm import make_backend
from steps.caption import words_to_ass
from steps.cut import render_clip
from steps.reframe import make_crop_filter


def run_pipeline(video, cfg, work_dir, progress=None):
    video = Path(video).resolve()
    work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    ffmpeg = cfg.get("ffmpeg", "ffmpeg")

    def say(msg, pct=None):
        if progress:
            progress(msg, pct)

    t0 = time.time()
    say(f"🎬 {video.name}", 2)

    # 1. audio
    say("① Audio extract korchi...", 5)
    audio = extract_audio(video, work_dir / "audio.wav", ffmpeg=ffmpeg)

    # 2. transcribe
    tc = cfg["transcribe"]
    say(f"② Transcribe korchi (model={tc['model_size']}, CPU)...", 10)
    result = transcribe(
        audio,
        model_size=tc["model_size"],
        language=tc.get("language"),
        device=tc.get("device", "cpu"),
        compute_type=tc.get("compute_type", "int8"),
        beam_size=tc.get("beam_size", 1),
        cpu_threads=tc.get("cpu_threads", 0),
    )
    (work_dir / "transcript.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    say(f"   ✓ language: {result['language']}, {len(result['words'])} words", 40)

    # 3. segment select — AI age, fail/off hole rule-based fallback
    sc = cfg["segment"]
    ai = cfg.get("ai", {})
    clips = []
    if ai.get("enabled"):
        say(f"③ AI smart selection (backend={ai.get('backend')})...", 45)
        try:
            backend = make_backend(ai)
            clips = select_segments_ai(
                result["segments"], backend,
                min_dur=sc["min_dur"], max_dur=sc["max_dur"],
                max_clips=ai.get("max_clips", 10),
            )
        except Exception as e:
            say(f"   ⚠️ AI selection fail ({e}). Rule-based fallback.")

    if not clips:
        clips = select_segments(result["segments"], sc["min_dur"], sc["max_dur"], sc["pause_gap"])
        say(f"③ {len(clips)} ta clip (rule-based)", 50)
    else:
        say(f"③ {len(clips)} ta clip (AI):", 50)
        for c in clips:
            sct = f"score {c.get('score')}" if c.get("score") is not None else ""
            say(f"   • Clip {c['index']} [{sct}] {c.get('title','')}")

    if not clips:
        raise RuntimeError("Kono clip banano gelo na (transcript khali?).")

    # user koyta shorts chay — top-N rakho (AI hole score-sorted, tai best gula thake)
    cap = int(ai.get("max_clips") or 0)
    if cap and len(clips) > cap:
        clips = clips[:cap]
        for i, c in enumerate(clips, 1):
            c["index"] = i
        say(f"   (tomar chawa moto top {cap} ta rakha holo)")

    # 4 + 5 + 6. caption + track + render
    oc = cfg["output"]
    made = []
    n = len(clips)
    for k, clip in enumerate(clips):
        idx = clip["index"]
        dur = clip["end"] - clip["start"]
        base_pct = 50 + int(48 * k / n)
        say(f"④ Clip {idx}/{n} ({dur:.0f}s) — {clip.get('title','')}", base_pct)

        ass = None
        if cfg["caption"].get("enabled", True):
            ass = words_to_ass(
                result["words"], work_dir / f"clip_{idx:02d}.ass",
                clip["start"], clip["end"], cfg["caption"],
                oc["width"], oc["height"],
            )

        crop_filter = None
        if oc.get("vertical", True):
            try:
                crop_filter = make_crop_filter(
                    video, clip["start"], clip["end"],
                    oc["width"], oc["height"],
                    sample_fps=oc.get("sample_fps", 3),
                    zoom_amt=oc.get("zoom", 0.0),
                    track=oc.get("track_face", True),   # off holeo center-crop + zoom cholbe
                )
            except Exception as e:
                say(f"     ⚠️ reframe fail ({e}) — plain center-crop")

        out_clip = work_dir / f"short_{idx:02d}.mp4"
        render_clip(video, clip, ass, out_clip, cfg, ffmpeg=ffmpeg,
                    crop_filter=crop_filter, fade=oc.get("fade", 0.0))
        # ass = None hole render_clip cwd out_dir use kore — basename na, full subtitles path lagena
        clip["file"] = out_clip.name
        made.append(clip)
        say(f"   ✓ {out_clip.name}")

    meta = [{key: c.get(key) for key in ("index", "file", "title", "reason", "score", "start", "end")}
            for c in made]
    (work_dir / "clips.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    dt = time.time() - t0
    say(f"✅ Done! {len(made)} ta Shorts ({dt:.0f}s)", 100)
    return meta
