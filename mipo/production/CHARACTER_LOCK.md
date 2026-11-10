# MIPO — APPROVED CHARACTER IDENTITY LOCK (v1)

This is the mandatory visual identity policy for the children's 3D animation series **Mipo's Magical World**.

## Canonical source images, in strict priority order

1. `mipo/reference/cover_landscape_with_friends.png` — ORIGINAL MASTER BANNER. This is the approved source of truth for Mipo's appearance and his friends.
2. `mipo/reference/cover_portrait.png` and `mipo/reference/cover_square.png` — supporting images only; use where consistent with the master.
3. `mipo/reference/approved/mipo_turnaround_v1.png` — add ONLY after a human has checked and approved the front, right-side and back character sheet. This file DOES NOT EXIST until an approved image has actually been generated and saved.

Never treat an unapproved generated image as the master. Never substitute earlier failed **robot** generations. The master reference takes precedence over any conflicting written prompt. Always include the master, and once approved the turnaround, as an image reference when the selected generation tool supports it.

## Mipo's fixed visual DNA

- Human boy, about five years old, rounded chibi proportions, large head (~one-third body height)
- Tousled medium-brown wavy hair and bangs, large warm brown eyes, rosy cheeks, freckles, gentle smile
- Bronze aviator goggles with bright blue lenses RESTING ON TOP OF HIS HEAD, brown strap
- Bright red knitted scarf with a fringed end
- Cream explorer jacket with brown cuffs and hem trim; dark brown shirt with ONE large golden star
- Dark brown cargo pants with flap pockets, brown belt/brass buckle, brown lace-up explorer boots
- Brown leather backpack with buckled straps and rolled tan sleeping mat on top
- Wooden magic wand with bronze band and luminous golden star tip
- **Continuity:** in Episode 1 Scene 1, wand lies on bedside table, **not in Mipo's hand**; from Scene 2 onward, wand is in his **left hand**.

## Hard constraints

Same face, hair, proportions, clothing, goggles, accessories and color palette in EVERY front/side/back view and EVERY scene. Do not redesign Mipo, substitute a robot/animal, alter clothing color, add or remove accessories, or use blue jeans. Prevent morphing, extra fingers, missing backpack or inconsistent side/back details. Use the scene-specific wand placement; don't let generic character descriptions override it.

## Production gate (no imaginary results)

1. Create a 3-view turnaround with the existing `generated/prompts/00_character_sheet.txt` and master banner as reference. Save final candidate to `reference/approved/mipo_turnaround_v1.png` **only after approval**.
2. Generate Episode 1 Scene 1 starting frame from `generated/prompts/scene_01_image.txt` with the master banner and approved turnaround references.
3. Animate from starting frame using `generated/prompts/scene_01_video.txt`: 5 seconds, vertical 9:16; maintain the identity throughout.
4. Use existing timed English narration script and audio pipeline; synthesize via ElevenLabs only once access/credits are explicitly available.
5. Before approval, compare front, side, back, start/middle/end of clip against `mipo/production/QC_CHECKLIST.md`. If failed, reject and retry rather than claiming lock succeeded.

All referenced scene prompts are located under `mipo/production/episodes/ep01_missing_rainbow_color/generated/prompts/`.

## Expense and status rules

Never request, purchase, or charge a service; do not publish or merge without explicit permission. If external image-to-video or voice generation tools cannot be accessed, prepare prompts and instructions and report the real constraint. **A prompt or integration is not a rendered image/video/audio asset.**
