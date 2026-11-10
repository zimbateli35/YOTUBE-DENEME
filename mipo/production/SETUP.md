# Setup on your computer (macOS or Windows)

## 1. Software

| Tool | Why | Install |
|---|---|---|
| **Git** (+ optional GitHub Desktop) | Get and update this repo | git-scm.com / desktop.github.com |
| **Python 3.10+** | Runs `tools/*.py` (standard library only, no `pip install` needed) | python.org, or `brew install python` |
| **FFmpeg** | Used by `tools/assemble.py` | macOS: `brew install ffmpeg` · Windows: `winget install Gyan.FFmpeg` |
| **DaVinci Resolve** (free) or **CapCut** | Final edit, color matching, SFX placement | blackmagicdesign.com / capcut.com |
| VS Code (optional) | Edit `episode.json` and the prompts | code.visualstudio.com |
| Claude Code (optional) | Keep working on this pipeline with an assistant | claude.ai/code |
| Blender (optional) | Only if you commission a rigged 3D Mipo | blender.org |

Check the install:
```bash
git --version && python3 --version && ffmpeg -version | head -1
```

## 2. Get the project
```bash
git clone https://github.com/zimbateli35/yotube-deneme.git
cd yotube-deneme
git checkout ccr-bdc662ca-ibq7m0        # until it is merged into main
cd mipo
python3 tools/build_package.py production/episodes/ep01_missing_rainbow_color
```
Open `production/episodes/ep01_missing_rainbow_color/generated/PROMPTS.md`; everything you need to paste is in there.

## 3. Accounts and API access

| Need | Service (pick one per row) | Web UI enough? | API key needed for |
|---|---|---|---|
| Character sheet + start frames | Midjourney · ChatGPT (GPT-image) · Google Gemini · FLUX Kontext (BFL/fal/Replicate) | Yes | Only for automation |
| 3D image-to-video | Kling · Runway · Google Veo 3 (Flow / Gemini API / Vertex AI) · Luma · Hailuo | Yes | Only for automation |
| Natural voice | **ElevenLabs** (Voice Design) · or a human voice actor | Yes | `tools/tts_elevenlabs.py` |
| Music | Composer · Suno/Udio paid tier · Epidemic Sound · Artlist | Yes | – |
| SFX | ElevenLabs SFX · Epidemic · Freesound (CC0) | Yes | – |
| Lip sync (optional) | Kling lip-sync · Runway Act-Two · Hedra · Sync Labs | Yes | – |

Use **paid plans that grant commercial/YouTube monetization rights**, and read each service's
rules on children's content.

### API keys (only the ElevenLabs script needs one today)
```bash
cp .env.example .env      # inside mipo/
# edit .env:
# ELEVENLABS_API_KEY=...
# ELEVENLABS_VOICE_ID=...   (from ElevenLabs > Voices > your "Mipo" voice > ID)
```
`.env` is git-ignored. Never commit keys or paste them into chat.

Test with a single line first:
```bash
python3 tools/tts_elevenlabs.py production/episodes/ep01_missing_rainbow_color --line L01 --takes 1
```
> `tts_elevenlabs.py` was written against ElevenLabs' public REST API but could not be run in the
> build environment (no network access). `--dry-run` was tested, and so was `assemble.py` (end to
> end, with test clips).

## 4. Where files go (per episode)
```
production/episodes/<ep>/
  episode.json            <- you edit this
  generated/              <- build_package.py output (commit it)
  frames/                 <- approved start/end frames (commit)
  clips/scene_NN.mp4      <- approved AI clips (commit via Git LFS or keep in cloud storage)
  clips/raw/              <- all other takes (git-ignored; keep in Drive/Dropbox)
  audio/voice/LNN.mp3     <- chosen takes (commit)
  audio/voice/takes/      <- every TTS take (git-ignored)
  audio/music.wav, sfx.wav
  final/<slug>_vN.mp4     <- assembled outputs (never overwritten)
```
Large media: GitHub rejects files over 100 MB. For many clips, enable Git LFS
(`git lfs install && git lfs track "*.mp4" "*.wav"`) or keep the raw files in cloud storage.
