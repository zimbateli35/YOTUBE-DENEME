# Audio and API integrations (ElevenLabs, image, video)

**Status:** the integrations are built and pass an end-to-end test against **local mock services**
(`tools/tests/test_integration.py`). They have **not** been run against the real ElevenLabs, OpenAI or
Runway APIs yet, because those hosts are blocked in the build environment and no keys were used. No real
narration, SFX, images or clips exist yet.

## 1. ElevenLabs: costs and credits (check before generating)

Taken from web search while the ElevenLabs site was unreachable from the build environment.
**Confirm on elevenlabs.io/pricing before you subscribe.**

| Plan | Price / month | Credits / month | Commercial use |
|---|---|---|---|
| Free | $0 | 10,000 | **No.** Non-commercial with attribution: fine for tests, not for a monetized channel |
| Starter | about $6 (some sources say $5) | 30,000 | Yes |
| Pro | $99 | 600,000 | Yes |

- Text-to-speech uses about **1 credit per character** on the standard models (Multilingual v2), and
  about half that on the Flash/Turbo models. Episode 1's ten lines are **241 characters**, so
  3 takes of every line ≈ 725 credits. SFX cost depends on length; the tool measures the real usage.
- `tts_elevenlabs.py credits` shows your plan, credits used and left, and the reset date. It's free.
- **Commercial use:** generate the audio you'll publish on a plan that includes a commercial license.

Sources: [ElevenLabs pricing](https://www.elevenlabs.io/pricing), [ElevenLabs API pricing](https://elevenlabs.io/hi/pricing/api),
[bigvu.tv 2026 guide](https://bigvu.tv/blog/elevenlabs-pricing-2026-plans-credits-commercial-rights-api-costs/),
[smallest.ai 2026 guide](https://smallest.ai/blog/elevenlabs-pricing-plans-cost-what-you-get-in-2026).

### Safety built into `tools/tts_elevenlabs.py`
- **Spends nothing without `--yes`.** Without it you get a dry run with the plan and a credit estimate.
- Reads your **remaining credits first** and refuses to start if the estimate exceeds them or your
  `--max-credits` budget. It re-checks the **real** usage after every request and stops at the budget.
  It never goes past your remaining credits, so it can't trigger overage billing.
- Never buys credits, changes plans or prints the key. Error messages are scrubbed of secrets.
- Never overwrites: takes are numbered, and approved files are protected (`--replace` moves the old one
  to `_superseded/`, it never deletes).

## 2. Voices: one fixed voice per character
`production/voices.json` defines the cast. Each character points to an environment variable holding its
ElevenLabs Voice ID, plus fixed voice settings and a seed, so the same character always sounds the same:

| Character | Env var | Ep1 | Track |
|---|---|---|---|
| Mipo | `ELEVENLABS_VOICE_MIPO` | all 10 lines | dialogue |
| Storyteller | `ELEVENLABS_VOICE_NARRATOR` | not used (decided: one Mipo voice) | narration |
| Bird / Bunny / Deer | `ELEVENLABS_VOICE_BIRD` / `_BUNNY` / `_DEER` | non-speaking (their sounds are SFX) | dialogue |

**Creating Mipo's voice (once):** in ElevenLabs, go to Voices → Voice Design and paste `voice_design_prompt`
from `voices.json`. Generate the previews, pick the warmest and clearest, save it as "Mipo", and copy its
Voice ID into `.env`. Never clone a real child's voice.
To audition library voices instead: `py tools\tts_elevenlabs.py voices --search boy`.

Each episode line has a `speaker`. To add a storyteller line in a future episode, set
`"speaker": "narrator"` and it goes to the narration track automatically.

## 3. Separate tracks and sync
`tools/mix_audio.py <ep> [--scene N]` builds four aligned tracks plus a final mix:
`narration.wav`, `dialogue.wav`, `music.wav`, `sfx.wav`, `mix.wav` (music ducked under voices, −14 LUFS),
`subtitles.srt` (timed to the real audio) and `report.json` (where everything landed, plus warnings).
They go in `audio/build/episode/` or `audio/build/scene_NN/`.

- Lines start at their scripted times. **L08 is auto-aligned** so the word "MAGIC" starts exactly at
  22.05 s, using the word timings ElevenLabs returns with each take.
- You get a warning if a take runs past its latest allowed end time (`must_end`) or overlaps the next line.
  Pick a shorter take, or lower `speed` slightly in `voices.json` and regenerate.
- SFX cues (`episode.json` → `sfx`) have IDs, prompts, durations and gains, and are placed at their times.
- Music: any licensed 30 s track saved as `audio/music.wav`.

## 4. Image and video integrations (always with the approved references)
- `tools/gen_image.py`: OpenAI Images (edits endpoint, accepts reference images).
  - `turnaround`: sends the **MASTER banner**.
  - `scene N`: refuses to run until `reference/approved/mipo_turnaround_v1.png` exists, then sends the
    **banner and the approved turnaround** with the scene prompt.
  - Output goes to `candidates/`; `approve` copies a candidate to its approved path and never overwrites.
- `tools/gen_video.py`: Runway image-to-video at 720:1280 for 5 s. It refuses to run without an
  **approved** `frames/scene_NN_start.png`. Output goes to `clips/raw/`; `approve` copies to `clips/scene_NN.mp4`.
- **Both are paid APIs with no free API credits.** Each one is a dry run unless you add `--yes`. The free
  route is still the tools' **web apps** (see `TEST_01_...md`). Save results under the same file names,
  and the rest of the pipeline works the same.

## 5. Your first complete 5-second scene (Scene 1)
Windows PowerShell, from `C:\Projects\yotube-deneme\mipo`, with `.env` filled in:
```powershell
$EP = "production\episodes\ep01_missing_rainbow_color"
py tools\build_package.py $EP
py tools\tts_elevenlabs.py credits                                 # free: plan + credits left
py tools\tts_elevenlabs.py tts $EP --scene 1 --takes 3            # dry run: shows the cost
py tools\tts_elevenlabs.py tts $EP --scene 1 --takes 3 --max-credits 300 --yes
py tools\tts_elevenlabs.py select $EP L01 2                        # pick takes after listening
py tools\tts_elevenlabs.py select $EP L02 1
py tools\tts_elevenlabs.py sfx $EP --scene 1 --takes 2 --max-credits 1500 --yes
py tools\tts_elevenlabs.py select $EP SFX01 1                      # ...and SFX02, SFX03, SFX04
#   video: approved frames\scene_01_start.png -> clips\scene_01.mp4 (web app per TEST_01, or gen_video.py)
#   music: save a licensed track as audio\music.wav (optional for the test)
py tools\mix_audio.py $EP --scene 1
py tools\assemble.py $EP --scene 1 --subs
```
The result is `final\ep01_missing_rainbow_color_scene01_v1.mp4`: 1080×1920, 5.0 s, with Mipo's lines, SFX,
music and captions.

## 6. Integration test (no keys, no network, no cost)
```powershell
py tools\tests\test_integration.py
```
It copies the project to a temporary folder and runs every script against a local mock of ElevenLabs,
OpenAI and Runway. It checks dry runs, the budget stop, take/approve/no-overwrite, required references,
the 4 tracks plus mix and subtitles, the 5-second 1080×1920 scene with audio, the "MAGIC" sync at 22.05 s,
and that no key appears in any output. The mock audio is test tones, not speech.
