# Reels Maker — Full Plan & Architecture

**Goal:** Ekta desktop software jeta long video theke AI diye automatic Shorts/Reels banabe — best clip detect kore, 9:16 vertical kore, proper word-by-word caption boshiye, ready-to-post output dibe. Puro jinis **local / offline**, install er somoy model download hobe.

---

## 1. Target Hardware (eta mathay rekhe design)

| Component | Spec | Impact |
|-----------|------|--------|
| GPU | Intel HD 4600 (no CUDA) | Sob **CPU te** cholbe — heavy model avoid |
| CPU | i7-4770, 4c/8t (2013) | Choto + quantized model lagbe |
| RAM | 16 GB | OK — but ekbar e ekta boro model |

**Design rule:** speed er jonno *choto but smart* model, `int8`/`Q4` quantization, ar processing background e (UI block korbe na).

---

## 2. Pipeline (data flow)

```
Long Video (.mp4)
   │
   ▼
[1] Audio extract ........... FFmpeg  → audio.wav (16kHz mono)
   │
   ▼
[2] Transcribe + timestamps . faster-whisper → words[] {text, start, end}
   │
   ▼
[3] Content understanding ... Local LLM (Ollama) → transcript pore bujhe
   │
   ▼
[4] Segment selection ....... LLM → best clips [{start, end, hook, score}]
   │
   ▼
[5] Cut clips ............... FFmpeg → clip_1.mp4, clip_2.mp4 ...
   │
   ▼
[6] Reframe to 9:16 ......... MediaPipe/OpenCV → speaker track + crop
   │
   ▼
[7] Burn captions ........... ASS subtitle + FFmpeg → word highlight
   │
   ▼
Ready Shorts (output/)
```

---

## 3. Tech Stack

| Layer | Choice | Keno |
|-------|--------|------|
| Core engine | **Python 3.11** | ML/video ecosystem best |
| Transcription | **faster-whisper** (`small`/`base`, int8) | CPU te fast, word-level timestamp dey |
| Mixed Bangla-English | Whisper multilingual | Bangla+English mix handle kore |
| Content AI | **Ollama** + `qwen2.5:3b` ba `llama3.2:3b` | Choto, CPU te chole, JSON output bhalo |
| Video ops | **FFmpeg** (bundled) | Cut, reframe, caption burn |
| Speaker tracking | **MediaPipe Face** / OpenCV | Vertical crop e mukh center rakhe |
| Captions | **ASS** subtitle format | Word-by-word highlight (karaoke) |
| UI | **Tauri** (Rust+web) ba FastAPI+browser | Lightweight desktop app |
| Packaging | **PyInstaller** → `.exe` | Single installer |

> Note: Bangla-English mixed e Whisper kotota accurate hobe seta video quality er upor depend kore. Phase 1-e test kore tune korbo.

---

## 4. Folder Structure

```
Reels Maker/
├── PLAN.md                  # ei file
├── engine/                  # Python core
│   ├── main.py              # entry / orchestrator
│   ├── steps/
│   │   ├── extract_audio.py
│   │   ├── transcribe.py    # faster-whisper wrapper
│   │   ├── analyze.py       # Ollama LLM segment picker
│   │   ├── cut.py           # ffmpeg clip cutter
│   │   ├── reframe.py       # 9:16 speaker-track crop
│   │   └── caption.py       # ASS generate + burn
│   ├── models/              # downloaded whisper models
│   └── config.yaml          # settings (model size, lang, etc.)
├── ui/                      # desktop app (Phase 5)
├── bin/                     # bundled ffmpeg.exe
├── output/                  # generated shorts
└── requirements.txt
```

---

## 5. Phased Roadmap

### Phase 1 — MVP CLI (proof of concept) ✅ DONE
- [x] FFmpeg diye audio extract
- [x] faster-whisper diye transcribe (word timestamps)
- [x] Pause+length rule diye segment cut
- [x] Word-by-word karaoke ASS caption burn
- [x] 9:16 center-crop vertical output
- **Result:** ✅ video in → 9:16 captioned clips out. Tested & working (sample_long.mp4 → 2 shorts).

### Phase 2 — Smart Selection (AI brain) ✅ DONE
- [x] Dual LLM backend: **API** (OpenCode Zen, OpenAI-compatible) + **local** (llama-cpp GGUF)
- [x] Transcript → LLM prompt → best segments JSON (title hook, start, end, reason, score)
- [x] AI selection replaces rule-based (fail hole auto-fallback)
- [x] clips.json e metadata save
- **Result:** ✅ AI nije clip select korlo — Clip 1 [score 9] "3 ideas...", Clip 2 [score 8].
- **Note:** Ollama er bodole API/llama-cpp newa holo (Ollama CDN ei network e slow chilo).
  API backend e free model `deepseek-v4-flash-free` use hocche.

### Phase 3 — Auto Reframe 9:16 ✅ DONE
- [x] OpenCV Haar diye face detect (bundled — extra download lagena)
- [x] Smooth crop tracking (gap-fill + moving-average, jhakuni kom)
- [x] ffmpeg time-based x-expression — single-pass dynamic crop (audio+caption ek pass e)
- [x] Mukh na pele center-crop fallback
- **Result:** ✅ crop window speaker er mukh follow kore. `output.track_face` config / `--no-track`.
- **Baki:** multi-speaker active-speaker switch (Phase 3.5, optional). MediaPipe er bodole Haar
  newa holo (CPU te fast + zero-download).

### Phase 4 — Caption Polish ✅ DONE
- [x] 4 style presets: **hormozi** (big bold active-word pop), **tiktok**, **clean**, **classic**
- [x] Duito highlight mode: "word" (active word color+scale pop) ar "fill" (karaoke)
- [x] Uppercase, position (bottom/center/top), font/color/size override via config
- **Result:** ✅ Hormozi preset tested — active word holud pop, viral reels look. `--caption <preset>`.

### Phase 4.5 — Edit polish (user feedback) ✅ DONE
- [x] Caption position fix — center er bodole **lower-third** (random majhe boshto)
- [x] Aro caption preset: **impact** (Impact font), **neon** (Verdana cyan) — total 6
- [x] **Dynamic zoom** — proti sentence e zoom alternate (jump-cut energy), face-track soho
- [x] **Fade in/out** transition clip boundary e
- **Config:** `output.zoom`, `output.fade`. UI toggle + `--no-zoom`.

### Phase 5 — Web UI ✅ DONE
- [x] Drag-drop video (Flask + browser)
- [x] Live progress bar + log (background thread + status polling)
- [x] Clip preview (video player) + download
- [x] Settings panel (caption preset, language, clip length, AI/tracking toggle)
- **Result:** ✅ `python engine/web/app.py` → http://localhost:5000. E2E tested (upload→progress→clips).
- **Note:** core pipeline `engine/pipeline.py` e refactored — CLI + web duitoi share kore.

### Phase 6 — Installer
- [ ] PyInstaller `.exe`
- [ ] First-run e Whisper + Ollama model download
- [ ] FFmpeg bundle

---

## 6. Known Challenges & Solutions

| Challenge | Solution |
|-----------|----------|
| CPU te slow processing | Choto model (`base`/`small`), int8, background thread, progress bar |
| Bangla-English mixed accuracy | Whisper multilingual + post-correction; test-driven tuning |
| LLM "best clip" judgment | Good prompt engineering + virality heuristics (hook, emotion, completeness) |
| Vertical crop e mukh kete jawa | MediaPipe tracking + safe-margin padding |
| Long video (1hr+) e RAM/time | Chunk kore process kora, streaming transcribe |

---

## 7. First Run Experience (install flow)
1. User `.exe` install kore
2. App first launch → "Downloading AI models..." (Whisper + Ollama model, ~2-4 GB)
3. Ekbar download → erpor sob **offline**
4. Drag video → "Generate Shorts" → done

---

## Next Step
Phase 1 (MVP CLI) theke shuru kora — eta age working proof dibe, tarpor brick by brick build korbo. Bolo, scaffold kore dei?
