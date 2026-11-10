# Production workflow: premium 3D Shorts with a consistent Mipo

The goal is the **same Mipo in every shot of every episode**. AI video models drift
when you give them text alone, so this workflow fixes Mipo's look in still images
first, approves them, and only then animates them.

```
 banner (MASTER)                    episode.json  ──► tools/build_package.py ──► prompts + script + SRT
      │                                                          │
      ▼                                                          ▼
 1. Character sheet ──► 2. Six start frames ──► 3. Image-to-video clips ──► clips/scene_NN.mp4
      (approve once)       (approve each)          (3-4 takes, pick best)
                                                                 │
 4. Voice (ElevenLabs / voice actor) ──► audio/voice/L01..L10 ───┤
 5. Music + SFX (licensed/original)  ──► audio/music, audio/sfx ─┤
                                                                 ▼
                                   6. tools/assemble.py ──► final/ep01_..._vN.mp4 ──► 7. QC ──► 8. Publish
```

> Product names, features and limits below are as of the time of writing and change
> often. Check each service's current docs, pricing and **commercial-use and
> children's-content terms** before you commit to one.

## 1. Character lock (once per series)
1. Attach `reference/cover_landscape_with_friends.png` (the MASTER banner). You can also add the two
   full-body covers as extra references.
2. Generate a **turnaround sheet** from `generated/prompts/00_character_sheet.txt` using an image model
   that accepts a character reference image. Good options:
   - **Midjourney** (Omni Reference / character reference)
   - **ChatGPT image generation** (GPT-image) with the banner attached
   - **Google Gemini image editing**
   - **FLUX.1 Kontext** (BFL, fal.ai or Replicate)
3. Compare the sheet to the banner item by item using `QC_CHECKLIST.md`. Regenerate until every item
   matches, then save the approved sheet as `reference/approved/mipo_turnaround_v1.png`. Attach both the
   banner **and** this sheet to every later generation.
4. *Long-term option (best consistency across many episodes):* have a 3D character artist build
   and rig Mipo in Blender from the banner and the sheet. Alternatively, train a LoRA on 20–40 approved
   images (ComfyUI with FLUX/SDXL). Either way, the character can no longer drift.

## 2. Start frames (per scene)
- For each scene, paste `generated/prompts/scene_NN_image.txt` and attach the banner and the approved
  sheet. Generate at 9:16 (1080×1920 or larger).
- Pick the best frame and QC it. Save it as `episodes/<ep>/frames/scene_NN_start.png`. Where it
  helps, also make an `_end.png` (scene 5's sky reveal, for example).
- **Scene 5 staging:** the baby deer must be fully in frame, behind and between Mipo and the flower,
  with nothing covering it. Reject any frame where the flower, the bird or the frame edge hides it.

## 3. Animate (image-to-video)
- Use an image-to-video model with **start-frame** (and ideally **end-frame**) support:
  **Kling** (start/end frames, Elements multi-reference), **Runway Gen-4 / References**,
  **Google Veo 3** (via Flow, the Gemini API or Vertex AI), **Luma Ray**, **Hailuo/MiniMax**.
  Settings: 9:16, the scene's duration (5 s), highest quality tier.
- Paste `scene_NN_video.txt` as the motion prompt and `scene_NN_negative.txt` if the tool takes one.
  Generate 3–4 takes and keep the one with the best character fidelity, not just the best motion.
- If a scene needs two moves (scene 5: tap, then sky), generate two clips and join them in the
  editor, or chain them by using clip A's last frame as clip B's start frame.
- Do **not** ask the video model to render text. The end card is added in step 6.
- Save the approved clips as `episodes/<ep>/clips/scene_01.mp4` … `scene_06.mp4`.
- Lip sync is optional: the narration works as a voice-over. If you want on-screen lip sync, run the
  chosen clip and voice line through a lip-sync tool (Kling lip-sync, Runway Act-Two, Hedra or
  Sync Labs) and QC the face afterwards.

## 4. Narration (natural boy voice)
- **Fastest:** use **ElevenLabs Voice Design** to create a "young American boy, 6–7, warm, cheerful,
  calm, clear" voice. Name it *Mipo* and reuse the same Voice ID for every episode. Then run
  `python3 tools/tts_elevenlabs.py production/episodes/<ep> --takes 3`
  (add `--use-alt L01` if Mipo should say "Good morning! I'm Mipo!").
- **Most natural, long-term:** hire a voice actor who specializes in kid voices (usually an adult)
  through Voices.com, Voice123 or Fiverr. Send them `generated/NARRATION_SCRIPT.md`, which has the
  timings and delivery notes. Ask for a separate 48 kHz WAV per line, with 3 takes each, and get a written
  license for use across the series.
- Never clone a real child's voice without the guardian's written consent, and check the TTS
  provider's policy on child-like voices.
- Put the chosen takes in `audio/voice/L01.mp3` … `L10.mp3`. Line L08 must land "MAGIC" on the wand tap
  at 22.05 s. Nudge that line's start time in `episode.json` if needed.

## 5. Music and SFX
- Music: commission it, or use a service whose plan grants commercial and YouTube rights (Suno/Udio
  paid tiers, Epidemic Sound, Artlist). The brief is in `NARRATION_SCRIPT.md`. Export exactly 30 s to
  `audio/music.wav`.
- SFX: ElevenLabs Sound Effects, Epidemic or Freesound (CC0 only). Pre-mix them on the cue sheet into
  `audio/sfx.wav`. The v1 storyboard's synthesized `output/audio/soundtrack.wav` can stand in as a
  temporary bed.
- Keep license receipts in `production/licenses/`.

## 6. Assemble
```bash
python3 tools/assemble.py production/episodes/ep01_missing_rainbow_color --endcard --subs
```
This conforms every clip to 1080×1920 at 30 fps, applies 0.3 s crossfades, places each line at its
timestamp, ducks the music under the voice, normalizes to about −14 LUFS and adds the end card.
It writes `final/<slug>_vN.mp4` and never overwrites a previous version. For the final polish
(color matching, extra SFX, timing tweaks), open the parts in **DaVinci Resolve** (free) or **CapCut**.

## 7. QC
Go through `QC_CHECKLIST.md` frame by frame. Character fidelity is the release gate.

## 8. Publish (YouTube Studio)
- Set **Audience: "Yes, it's made for kids"** (required under COPPA for kids' content).
- Upload `generated/subtitles.srt` as English captions.
- Answer the **altered or synthetic content** question honestly. YouTube's current rules focus on
  realistic content; follow the latest guidance.
- Use a title, a short description and `#Shorts`. The video must be vertical and 60 s or shorter.

## New episode in 5 steps
1. `cp -r production/episodes/ep01_missing_rainbow_color production/episodes/ep02_<slug>`, then delete
   the copy's `generated/`, `clips/`, `audio/`, `final/` and `frames/`.
2. Edit `episode.json`: title, slug, scenes, narration and timings. Leave the character file alone.
3. `python3 tools/build_package.py production/episodes/ep02_<slug>`
4. Run steps 2–7 above with the same banner, approved sheet and Voice ID.
5. Commit `episode.json`, `generated/`, approved frames and the final MP4.
