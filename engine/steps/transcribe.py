"""Step 2: faster-whisper diye transcribe — word-level timestamp soho.

Bangla-English mixed handle korar jonno language=None (auto-detect) rakha bhalo.
"""
from faster_whisper import WhisperModel

_MODEL_CACHE = {}


def _get_model(model_size, device, compute_type, cpu_threads):
    key = (model_size, device, compute_type, cpu_threads)
    if key not in _MODEL_CACHE:
        _MODEL_CACHE[key] = WhisperModel(
            model_size, device=device, compute_type=compute_type,
            cpu_threads=cpu_threads)   # 0 = auto (sob core)
    return _MODEL_CACHE[key]


def transcribe(audio_path, model_size="small", language=None,
               device="cpu", compute_type="int8", beam_size=1,
               cpu_threads=0, progress=print):
    model = _get_model(model_size, device, compute_type, cpu_threads)
    segments, info = model.transcribe(
        str(audio_path),
        language=language,
        word_timestamps=True,
        beam_size=beam_size,             # 1 = greedy (fast); 5 = accurate (slow)
        vad_filter=True,                 # silence/noise baad dey
        vad_parameters={"min_silence_duration_ms": 500},
    )

    seg_list, words = [], []
    for seg in segments:
        text = seg.text.strip()
        if not text:
            continue
        seg_list.append({"start": seg.start, "end": seg.end, "text": text})
        for w in (seg.words or []):
            wt = w.word.strip()
            if wt:
                words.append({"start": w.start, "end": w.end, "text": wt})
        progress(f"   [{seg.end:6.1f}s] {text}")

    return {
        "language": info.language,
        "duration": info.duration,
        "segments": seg_list,
        "words": words,
    }
