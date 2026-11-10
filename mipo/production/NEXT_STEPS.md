# Next steps: first professional 3D episode

Follow these in order. Steps 1–3 cost nothing. **Step 4 is the first point where you choose whether
to pay for anything.** Before step 4 you don't need to buy or activate anything.

## 1. Set up the computer (free, about 30 minutes)
Follow `SETUP.md` → "Windows 10/11, step by step", sections 1–4. At the end you have the repo in
`C:\Projects\yotube-deneme`, and `PROMPTS.md` and `NARRATION_SCRIPT.md` open.

## 2. Review the plan (free)
- [ ] Watch `mipo\output\mipo_ep1_missing_rainbow_color_1080x1920.mp4` (the 2D storyboard) for timing.
      Remember: its pants are blue and its voice is a placeholder. The banner and the script win.
- [ ] Read the six scenes in `PROMPTS.md` next to the banner. Change anything you want in `episode.json`,
      then re-run `py tools\build_package.py production\episodes\ep01_missing_rainbow_color`.
- [ ] Print or bookmark `QC_CHECKLIST.md`.
- [ ] Merge the pull request on GitHub when you're happy, then `git checkout main` and `git pull`.

## 3. Test the tools before choosing services (free trials and free tiers only)
Follow **`TEST_01_CHARACTER_LOCK_AND_SCENE1.md`** step by step. It covers the items below with exact files and pass criteria.
- [ ] Use a free tier or trial of one reference-capable image tool. Attach
      `reference\cover_landscape_with_friends.png`, paste `prompts\00_character_sheet.txt`, and compare
      the result with `QC_CHECKLIST.md`. Try two or three tools and keep the one whose Mipo matches the
      banner best.
- [ ] Use a free tier or trial of one or two image-to-video tools. Animate one test frame with
      `scene_01_video.txt` and judge how well Mipo's face and outfit hold through the motion.
- [ ] Listen to free voice previews: ElevenLabs Voice Design (prompt: *"young American boy, 6–7 years
      old, warm, cheerful, calm, clear"*) and/or voice-actor demo reels.
- [ ] Run `py tools\assemble.py production\episodes\ep01_missing_rainbow_color --allow-missing` to
      confirm FFmpeg and the pipeline work on your PC.

## 4. Decide and subscribe (your decision, the first possible cost)
Pick one image tool, one video tool and one voice option based on step 3. Choose plans with commercial
rights. Rough volume for one episode: about 10–20 image generations, about 20–30 video generations
(3–4 takes × 6 scenes, plus retries) and 10 voice lines × 3 takes.

## 5. Produce Episode 1
1. **Character lock:** generate the turnaround sheet, approve it with the QC checklist, and save it as
   `mipo\reference\approved\mipo_turnaround_v1.png`.
2. **Start frames:** for scenes 1–6, attach the banner and the turnaround sheet, paste
   `scene_NN_image.txt` and save the approved frame as `frames\scene_NN_start.png`. Scene 5: the deer must
   be fully visible.
3. **Clips:** animate each frame with `scene_NN_video.txt` (9:16, 5 s), make 3–4 takes and save the best as
   `clips\scene_NN.mp4`.
4. **Voice:** create or select the one Mipo voice, put its ID in `.env`, then run
   `py tools\tts_elevenlabs.py tts production\episodes\ep01_missing_rainbow_color --takes 3 --yes` (check `credits` first).
   Copy the best take of each line to `audio\voice\L01.mp3` … `L10.mp3`. Alternatively, send
   `NARRATION_SCRIPT.md` to a voice actor.
5. **Music/SFX:** save a licensed or commissioned 30 s track as `audio\music.wav` (optional:
   `audio\sfx.wav`).
6. **Assemble:** `py tools\assemble.py production\episodes\ep01_missing_rainbow_color --endcard --subs`
7. **QC:** go through every box in `QC_CHECKLIST.md`. Regenerate anything that fails.
8. **Commit and push** frames, chosen clips, voice files and the final MP4 (see SETUP §7).
9. **Publish:** YouTube Studio → "made for kids", upload `subtitles.srt`, `#Shorts`.

## 6. Episode 2 onward
Copy the episode folder, edit `episode.json`, and reuse the same banner, turnaround sheet and voice ID.
See WORKFLOW.md → "New episode in 5 steps".
