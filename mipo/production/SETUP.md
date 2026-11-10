# Setup on your computer (Windows first; macOS notes at the end)

Everything here is free to install. **Nothing in this setup buys or activates a paid service.**
Paid plans are only needed later, when you generate final assets (see `NEXT_STEPS.md`).

## Windows 10/11, step by step

Open **PowerShell** (Start menu → type "PowerShell" → Windows PowerShell). Run each block, then
**close and reopen PowerShell** after installing, so the new programs are on your PATH.

### 1. Install the free tools (winget is built into Windows 10/11)
```powershell
winget install --id Git.Git -e
winget install --id Python.Python.3.12 -e
winget install --id Gyan.FFmpeg -e
```
Optional, also free:
```powershell
winget install --id GitHub.GitHubDesktop -e        # point-and-click Git
winget install --id Microsoft.VisualStudioCode -e  # edit JSON / Markdown
```
Video editor (free): **DaVinci Resolve** from blackmagicdesign.com, or **CapCut** from capcut.com.

### 2. Check the install (in a NEW PowerShell window)
```powershell
git --version
py --version
ffmpeg -version
```
All three should print a version. Tips:
- On Windows use **`py`** (the Python launcher). If `python` opens the Microsoft Store, use `py`
  instead, or turn off the "python.exe" app execution alias in Settings → Apps → Advanced app settings.
- If `ffmpeg` is "not recognized", close and reopen PowerShell, or sign out and back in.

### 3. Get the project
Use a short folder **outside OneDrive** (OneDrive syncing large video files gets slow):
```powershell
mkdir C:\Projects -Force
cd C:\Projects
git clone https://github.com/zimbateli35/yotube-deneme.git
cd yotube-deneme
git checkout ccr-bdc662ca-ibq7m0     # until the pull request is merged; afterwards: git checkout main
cd mipo
py tools\build_package.py production\episodes\ep01_missing_rainbow_color
```
You should see `wrote production\episodes\ep01_missing_rainbow_color\generated`.

### 4. Open the package
```powershell
explorer production\episodes\ep01_missing_rainbow_color\generated
```
- `PROMPTS.md`: all six scene prompts (or use the `.txt` files in `prompts\` to copy and paste)
- `NARRATION_SCRIPT.md`: the timed voice script
- `subtitles.srt`: English captions

The character references are in `C:\Projects\yotube-deneme\mipo\reference\`. The MASTER is
`cover_landscape_with_friends.png`.

### 5. API key for the voice script (only when you are ready for ElevenLabs)
```powershell
Copy-Item .env.example .env
notepad .env
```
Fill in `ELEVENLABS_API_KEY=` and `ELEVENLABS_VOICE_ID=`, then save. `.env` is git-ignored, so never
commit it or paste keys into chat. First test without spending credits:
```powershell
py tools\tts_elevenlabs.py production\episodes\ep01_missing_rainbow_color --dry-run
```

### 6. Assemble (after you have clips and voice files)
```powershell
py tools\assemble.py production\episodes\ep01_missing_rainbow_color --endcard --subs
```
The end card uses `C:\Windows\Fonts\arialbd.ttf` automatically. To use another font, pass
`--font C:\Path\To\Font.ttf`. The output goes to `final\ep01_missing_rainbow_color_vN.mp4` and never
overwrites an earlier version.

Timing test with placeholder slates (free, no AI services needed):
```powershell
py tools\assemble.py production\episodes\ep01_missing_rainbow_color --allow-missing
```

### 7. Saving your work back to GitHub
```powershell
cd C:\Projects\yotube-deneme
git add mipo
git commit -m "Ep1: approved start frames"
git push
```
Large media: GitHub rejects single files over 100 MB. If you keep many clips in git, run once:
```powershell
winget install --id GitHub.GitLFS -e
git lfs install
git lfs track "*.mp4" "*.wav"
git add .gitattributes
```
Otherwise keep raw takes in Google Drive or Dropbox. `clips\raw\` and `audio\voice\takes\` are already git-ignored.

## Accounts you will need later (do not buy yet)

| Need | Options (pick one per row) | Web UI enough? | API key needed? |
|---|---|---|---|
| Character sheet + start frames | Midjourney · ChatGPT image generation · Google Gemini · FLUX Kontext | Yes | No |
| 3D image-to-video | Kling · Runway · Google Veo 3 (Flow) · Luma · Hailuo | Yes | No |
| Natural Mipo voice | **ElevenLabs** Voice Design, or a human voice actor | Yes | Only for `tts_elevenlabs.py` |
| Music | Composer · Suno/Udio paid tier · Epidemic Sound · Artlist | Yes | No |
| SFX | ElevenLabs SFX · Epidemic · Freesound (CC0) | Yes | No |
| Lip sync (optional) | Kling lip-sync · Runway Act-Two · Hedra · Sync Labs | Yes | No |

When you do subscribe, choose plans that include **commercial / YouTube monetization rights**, and read
each service's rules on children's content and child-like voices.

## macOS
Same steps with Terminal. Install the tools with Homebrew (`brew install git python ffmpeg`), use
`python3` instead of `py`, `/` instead of `\`, `cp .env.example .env` and `open -e .env`.

## Folder layout per episode
```
production\episodes\<ep>\
  episode.json            <- you edit this, then re-run build_package.py
  generated\              <- prompts, script, SRT (commit)
  frames\                 <- approved start/end frames (commit)
  clips\scene_01.mp4 ...  <- approved AI clips (commit via Git LFS, or keep in cloud storage)
  clips\raw\              <- all other takes (git-ignored)
  audio\voice\L01.mp3 ... <- chosen voice takes (commit)
  audio\voice\takes\      <- all TTS takes (git-ignored)
  audio\music.wav, audio\sfx.wav
  final\<slug>_vN.mp4     <- assembled outputs (never overwritten)
```
