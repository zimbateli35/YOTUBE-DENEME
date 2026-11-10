# Mipo's Magical World: 3D production package

**Status:** pre-production is ready; the premium 3D clips and the natural voice **have not been generated
yet**, because that needs external services (see `SETUP.md`). Nothing in this folder is an AI-generated
3D or neural-voice file.

| Document | What it is |
|---|---|
| [`CHARACTER_LOCK.md`](CHARACTER_LOCK.md) | **Mandatory identity policy** (reference priority, visual DNA, hard constraints, production gate) |
| [`TEST_01_CHARACTER_LOCK_AND_SCENE1.md`](TEST_01_CHARACTER_LOCK_AND_SCENE1.md) | **Current task:** front/side/back turnaround + Scene 1 start frame + 5 s animation test (free tiers only) |
| [`AUDIO_AND_API_INTEGRATION.md`](AUDIO_AND_API_INTEGRATION.md) | ElevenLabs voices/SFX (pricing, credit safety), 4-track mix and sync, image/video API tools, first 5-second scene recipe, integration test |
| [`NEXT_STEPS.md`](NEXT_STEPS.md) | **Start here:** exact next steps for the first 3D episode (free steps first) |
| [`WORKFLOW.md`](WORKFLOW.md) | The step-by-step pipeline: character lock → start frames → image-to-video → voice → music → assemble → QC → publish |
| [`SETUP.md`](SETUP.md) | Windows-first setup: software, project, API keys, saving to GitHub |
| [`QC_CHECKLIST.md`](QC_CHECKLIST.md) | Character-fidelity and technical release gate |
| [`character/mipo_character.json`](character/mipo_character.json) | Locked character definition (identity prompt, negative prompt, friends, world) |
| [`episodes/ep01_missing_rainbow_color/episode.json`](episodes/ep01_missing_rainbow_color/episode.json) | Episode 1 spec: six scenes, staging, beats, narration timestamps, SFX cues, music brief |
| [`episodes/ep01_missing_rainbow_color/generated/PROMPTS.md`](episodes/ep01_missing_rainbow_color/generated/PROMPTS.md) | **Six-scene 3D prompt package** (start-frame and motion prompts, ready to paste) |
| [`episodes/ep01_missing_rainbow_color/generated/NARRATION_SCRIPT.md`](episodes/ep01_missing_rainbow_color/generated/NARRATION_SCRIPT.md) | **Timed English narration script** with delivery notes, SFX cue sheet and music brief |
| `episodes/ep01_.../generated/subtitles.srt` | English captions for YouTube |
| `episodes/ep01_.../generated/prompts/*.txt` | One file per prompt, for copy and paste |
| `episodes/ep01_.../generated/shotlist.csv` | Shot list for tracking takes |

Tools (in `../tools/`):
- `build_package.py`: regenerates everything in `generated/` from the JSON files
- `tts_elevenlabs.py`: generates the narration takes through the ElevenLabs API
- `assemble.py`: turns the approved clips, voice and music into the final 1080×1920 MP4

## Rules
1. The **banner** (`../reference/cover_landscape_with_friends.png`) is the only authority on how Mipo looks.
2. Edit the JSON files, never `generated/`, and re-run `build_package.py`.
3. Never overwrite a delivered MP4: `assemble.py` writes a new version number each time.
