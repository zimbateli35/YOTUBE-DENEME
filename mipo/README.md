# Mipo's Magical World

A kids' YouTube Shorts series (ages 2–7). Episode 1: **"Mipo and the Missing Rainbow Color"**.

| Folder | Contents |
|---|---|
| [`production/`](production/README.md) | **3D production package**: workflow, setup, QC checklist, locked character file, Episode 1 spec, six-scene 3D prompts, timed narration script, subtitles |
| Long episode | [`production/episodes/ep01_long_missing_rainbow_color/`](production/episodes/ep01_long_missing_rainbow_color/PRODUCTION_PLAN.md): 11-minute Episode 1 (script, 69 shot prompts, narration, SFX, chapters) |
| [`reference/`](reference/README.md) | Channel banner (**MASTER character reference**) and supporting covers |
| [`tools/`](tools) | Pipeline scripts: `build_package.py`, `tts_elevenlabs.py` (voices + SFX), `mix_audio.py` (4 tracks + sync), `gen_image.py`, `gen_video.py`, `assemble.py`, `tests/test_integration.py` |
| `output/` | **v1 2D storyboard animatic** (kept unchanged) |
| `src/` | Code for the 2D storyboard animatic |

**Start here:** [`production/NEXT_STEPS.md`](production/NEXT_STEPS.md) (uses [`production/SETUP.md`](production/SETUP.md) for Windows setup).

## Status
| Item | Status |
|---|---|
| 2D storyboard animatic (timing and blocking reference) | ✅ `output/mipo_ep1_missing_rainbow_color_1080x1920.mp4` |
| Six-scene 3D prompt package | ✅ `production/episodes/ep01_missing_rainbow_color/generated/PROMPTS.md` |
| Timed English narration script + SRT | ✅ `.../generated/NARRATION_SCRIPT.md`, `.../generated/subtitles.srt` |
| Assembly pipeline (clips + voice + music → 1080×1920 MP4) | ✅ `tools/assemble.py` (tested with placeholder clips) |
| **Premium 3D scene clips** | ⏳ Not generated. Needs an external image-to-video service (see SETUP) |
| **Natural neural/actor narration** | ⏳ Not generated. Needs ElevenLabs or a voice actor (see SETUP) |
| Final 3D episode MP4 | ⏳ Built with `tools/assemble.py` once the above exist |

## v1 2D storyboard animatic (reference only)
`output/mipo_ep1_missing_rainbow_color_1080x1920.mp4`: 1080×1920, 30.0 s, 24 fps, H.264/AAC.
Use it **for timing, staging and story beats only**. Known differences from the current spec:
- Mipo's pants are **blue** in the animatic. The banner (now authoritative) shows **dark brown cargo pants**.
- The baby deer is partly cut off in the 20–22 s close-up. The spec now requires it to be fully visible.
- The narration in `output/audio/` is a robotic offline placeholder voice, **not** the final voice.
- Its first line is "Good morning, Mipo!". The final script uses **"Good morning! I'm Mipo!"**, with one Mipo voice throughout.

Both visual issues are already fixed in the 2D source (`src/characters.py`, `src/render.py`),
but the animatic was **not** re-rendered on purpose, so the delivered MP4 stays unchanged. If you
ever need a 2D v2, render it to a **new** file name:
```bash
python3 src/render.py output/audio output/mipo_ep1_storyboard_v2.mp4
```
