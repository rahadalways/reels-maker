# Reels Maker

Long video theke automatic Shorts/Reels banano — **100% local / offline**.
Full architecture + roadmap er jonno [PLAN.md](PLAN.md) dekho.

## Status
- ✅ **Phase 1 — MVP CLI** (working): audio → transcribe → segment → caption → render
- ✅ **Phase 2 — AI smart clip selection** (working): LLM transcript bujhe best clip + title + score
- ✅ **Phase 3 — Auto 9:16 speaker tracking** (working): face detect kore crop window mukh follow kore
- ✅ **Phase 4 — Caption styling polish** (working): hormozi/tiktok/clean/classic presets, active-word pop
- ✅ **Phase 5 — Web UI** (working): drag-drop browser app, live progress, clip preview/download
- ⬜ Phase 6 — Installer (.exe)

## Setup (ekbar)
```powershell
# venv banao + dependencies
C:\Users\rahad\AppData\Local\Programs\Python\Python312\python.exe -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r engine\requirements.txt
```
> FFmpeg PATH e thaka lagbe (already ache). First run e Whisper model auto-download hobe.

## Use

### Option A — Web UI (sohoj, drag-drop)
```powershell
.\.venv\Scripts\python.exe engine\web\app.py
```
Browser e **http://localhost:5000** kholo → video drag-drop → settings → **Generate**.
Live progress dekhbe, ses e clip preview + download.

### Option B — CLI
```powershell
.\.venv\Scripts\python.exe engine\main.py "path\to\long_video.mp4"
```
Output `output\<job-id ba video-name>\short_01.mp4`, `short_02.mp4` ... e jabe.

### Useful flags
| Flag | Ki kore |
|------|---------|
| `--model base` | Choto/fast model (`tiny`/`base`/`small`/`medium`) |
| `--lang en` | Language fix (default = auto-detect) |
| `--max-dur 45` | Clip er max length (second) |
| `--min-dur 25` | Clip er min length |
| `--no-vertical` | 9:16 crop off (original aspect rakhe) |
| `--no-track` | Face tracking off, center-crop use kore |
| `--caption <preset>` | Caption style: `hormozi`/`impact`/`neon`/`tiktok`/`clean`/`classic` |
| `--no-caption` | Caption off (sudhu crop/zoom) |
| `--no-zoom` | Dynamic zoom + fade off |
| `--outdir D:\shorts` | Output folder change |

## Kivabe kaj kore
1. **Audio extract** — FFmpeg diye 16kHz mono WAV
2. **Transcribe** — faster-whisper, word-level timestamp soho (CPU, int8)
3. **Segment (AI)** — LLM transcript bujhe best clip select kore (title + reason + score).
   Fail/off hole natural-pause rule-based e fallback.
4. **Caption** — word-by-word karaoke ASS subtitle
5. **Reframe (track)** — OpenCV face detect kore smooth crop trajectory; mukh na pele center-crop
6. **Render** — cut + 9:16 crop (tracked/center) + caption burn, single FFmpeg pass

## AI backend (Phase 2)
`engine/config.yaml` → `ai.backend`:
- **`api`** (default) — OpenCode Zen (OpenAI-compatible). Key `engine/.env` e (`REELS_LLM_API_KEY`).
  - Free model: `deepseek-v4-flash-free`. Paid (credit lagbe): `claude-haiku-4-5`, `gpt-5.5`, etc.
- **`local`** — llama-cpp-python + GGUF model (fully offline). `ai.local.model_path` e GGUF rakho.

> ⚠️ `engine/.env` e API key ache — gitignored, kawkey share koro na.

### AI flags
| Flag | Ki kore |
|------|---------|
| `--no-ai` | AI off, rule-based use koro |
| `--ai-model <name>` | Model override (e.g. `claude-haiku-4-5`) |

## Caption presets (Phase 4)
`engine\config.yaml` → `caption.preset` (ba `--caption <preset>`):

| Preset | Look |
|--------|------|
| `hormozi` | Boro bold UPPERCASE, active word holud **pop** (viral reels) |
| `impact` | Impact font, lal active word pop |
| `neon` | Verdana, cyan active word |
| `tiktok` | White text, sobuj active word |
| `clean` | Simple white, soft yellow karaoke fill |
| `classic` | Phase 1 er karaoke style |

Sob preset ekhon **lower-third** e boshe (center e bhase na). Override: config e `font`, `font_size`,
`uppercase`, `text_color`, `highlight_color`, `position` (bottom/center/top), `margin_v` — `null` na korle override hoy.

## Dynamic zoom + transitions
`engine\config.yaml` → `output`:
- `zoom: 0.06` — proti sentence/segment e zoom level alternate hoy (jump-cut energy). `0` = off.
- `fade: 0.25` — clip shuru/ses e fade in/out (second). `0` = off.

Web UI te "Dynamic zoom + transitions" checkbox, ba CLI te `--no-zoom`.

## Settings
Sob default `engine\config.yaml` te — model size, caption preset/style, clip length, tracking, output resolution edit kora jay.
