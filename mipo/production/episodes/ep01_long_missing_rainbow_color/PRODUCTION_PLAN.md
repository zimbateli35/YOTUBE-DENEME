# Episode 1 long edition: "Mipo and the Missing Rainbow Color" (11:00)

**Status:** script, shot list, all prompts, narration, SFX cues, music cues and chapters are ready.
**No 3D clips, voices, music or final video have been generated yet** (that needs external services).

| What | File |
|---|---|
| Editable story outline (sequences → shots → lines/SFX) | `outline.json` |
| Episode spec built from it (`tools/author_episode.py`) | `episode.json` |
| All image/video prompts for 69 shots | `generated/PROMPTS.md`, `generated/prompts/` |
| Narration and dialogue script with speakers and timing, SFX and music cue sheets | `generated/NARRATION_SCRIPT.md` |
| English captions | `generated/subtitles.srt` |
| YouTube chapters (for the description) | `generated/YOUTUBE_CHAPTERS.txt` |
| Shot list for tracking takes | `generated/shotlist.csv` |

## Story at a glance
Mipo wakes up and sees the rainbow has lost its **purple**, and he feels **sad** (belly breathing helps).
His star wand shows a sparkle trail. With the **Blue Bird**, then the **Bunny** (red garden, counting
strawberries), helping Bunny on **orange** Pumpkin Hill, the **Baby Deer** in the **yellow** sunflowers
(taking turns), being brave together in the **green** forest, and counting stepping stones across the
**blue** river, he finds **Little Purple** in the crystal cave. She felt small and forgotten. Kind words
bring her back. At the top of Rainbow Hill everyone counts 3-2-1, and Mipo taps her with his wand:
**"MAGIC!"** The rainbow is complete. Then come the dance, the color song, the recap and
"See you next magic moment!"

## Volume (for budgeting; do not buy anything without approval)
| Item | Amount |
|---|---|
| Shots | 69 (63 × 10 s, 6 × 5 s), 16:9 |
| Start frames to generate and approve | 69 (+ re-tries) |
| Video generations | about 140–210 (2–3 takes per shot) |
| Voice lines | 84: Mipo 38, narrator 29, Bunny 7, Deer 4, Bird 3, Little Purple 3 |
| TTS characters | 3,269 (≈ 3,300 credits per take; 3 takes ≈ 10,000, about one month of ElevenLabs Free, or about ⅓ of Starter) |
| SFX cues | 75 (≈ 144 s total) |
| Music | theme song (~25 s) + 11:00 underscore by sequence (see the music cue table) |

## Order of work
1. **Character lock first:** approve `reference/approved/mipo_turnaround_v1.png` (see `TEST_01_...md`
   and the open pants question in `reference/submitted/README.md`). Also approve one reference image
   each for **Little Purple** and the friends.
2. **Pilot: chapter "Hi, friends!" (shots 1–2, 20 s)** end to end: frames → clips → voices → SFX →
   `mix_audio.py` → `assemble.py --scene 1` / `--scene 2`. Check quality before scaling up.
3. Produce sequence by sequence (A → L), running QC after each one.
4. Music: commission or license the theme song plus the underscore, then save as `audio/music.wav` (11:00).
5. `py tools\mix_audio.py <ep>` → `py tools\assemble.py <ep> --subs --endcard` → final QC → upload.

## Re-editing the story
Edit `outline.json`, then:
```powershell
py tools\author_episode.py production\episodes\ep01_long_missing_rainbow_color   # warns if a line won't fit
py tools\build_package.py  production\episodes\ep01_long_missing_rainbow_color
```
