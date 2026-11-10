# Test 01: lock Mipo's design and run a 5-second 3D animation test (Scene 1)

**Goal:** prove, before spending money, that an image tool and a video tool can keep Mipo identical to the
banner. You get one approved turnaround sheet, one approved Scene 1 start frame and one 5-second clip.

**Status:** prompts ready; **nothing generated yet.** The build environment has no image/video model and
its network blocks every AI generation service, so this test runs on your computer.

All prompt text lives in `production/episodes/ep01_missing_rainbow_color/generated/`. Paste from the `.txt` files
so you never copy a stale version.

| Step | Prompt file | Attach | Output file |
|---|---|---|---|
| A. Turnaround sheet | `prompts/00_character_sheet.txt` | `reference/cover_landscape_with_friends.png` (MASTER) | `reference/approved/mipo_turnaround_v1.png` |
| B. Scene 1 start frame | `prompts/scene_01_image.txt` (+ `scene_01_negative.txt`) | MASTER banner + approved turnaround | `production/episodes/ep01_missing_rainbow_color/frames/scene_01_start.png` |
| C. 5-second animation | `prompts/scene_01_video.txt` (+ `scene_01_negative.txt`) | the approved start frame | `.../clips/raw/scene_01_takeN.mp4` → best one to `.../clips/scene_01.mp4` |

## Money rules for this test
- Use **free tiers or free daily credits only**. If a tool asks for a card or a subscription, stop and
  try another one, or come back and decide.
- Free tiers change often, so check on the day. Tools whose free tiers have recently included
  reference-image generation and/or image-to-video: ChatGPT (image generation), Google Gemini,
  Leonardo.ai, Kling AI and Hailuo AI. Free-tier output may carry a watermark or limits on
  commercial use. That's fine for a test, but not for publishing.
- Before uploading the banner, read the tool's terms on uploaded images and training. Opt out of
  training where the tool allows it.

## A. Character turnaround (front, side, back)
1. Open the image tool and upload `cover_landscape_with_friends.png` as the **character / omni
   reference** at the highest strength the tool offers. If the tool has no reference slot, attach it
   to the chat.
2. Set the aspect ratio to 16:9 or 3:2 and the highest quality, then paste `00_character_sheet.txt`. If
   there's a negative-prompt field, paste `negative.txt`.
3. Make 4 or more variations. Save candidates to `reference/candidates/` (git-ignored).
4. **Approve only if** every item in `QC_CHECKLIST.md` → "Mipo — every frame" passes **and**:
   - [ ] all three views show the same face, hair, proportions and colors
   - [ ] the side profile shows the goggle strap and scarf correctly, and the backpack depth looks plausible
   - [ ] the back view shows the backpack with its front pocket and buckled straps, the rolled mat with
         its spiral end, and the goggle strap around the back of his head
   - [ ] the wand is in his **left** hand (on the viewer's right in the front view)
   - [ ] the pants are dark brown cargo pants with flap pockets, not jeans
   - [ ] no text, labels or extra characters
5. Save the winner as `reference/approved/mipo_turnaround_v1.png`.

If no variation passes after about 8 tries, write down which items keep failing. That tells us which
tool to try next, or whether a commissioned 3D model is needed.

## B. Scene 1 start frame (9:16)
1. Attach the MASTER banner **and** `mipo_turnaround_v1.png`.
2. Set the aspect ratio to **9:16** and paste `scene_01_image.txt` (+ `scene_01_negative.txt`).
3. **Approve only if:**
   - [ ] it's Mipo, on-model per the checklist (pants and boots may be hidden by the blanket)
   - [ ] he's sitting up in bed with his eyes closed and a sleepy smile; the goggles are on his head, not over his eyes
   - [ ] the **wand lies glowing on the bedside table, not in his hands**
   - [ ] the window rainbow has **no purple stripe**
   - [ ] there's a cozy pastel treehouse room, a lantern and sunbeams; Mipo takes up at least 35% of the frame height
4. Save it as `frames/scene_01_start.png`.

## C. 5-second image-to-video test
1. Use the tool's image-to-video mode with `scene_01_start.png` as the **start frame**, at 9:16,
   **5 seconds**, highest quality the free tier allows.
2. Paste `scene_01_video.txt` as the prompt (and `scene_01_negative.txt` if there's a field).
3. Make 2–3 takes and save them as `clips/raw/scene_01_take1.mp4`, `_take2.mp4` and so on.
4. **Judge character fidelity first, then motion:**
   - [ ] Mipo's face, hair and outfit match the banner in the first, middle and last frame
   - [ ] no melting hands, extra fingers, outfit changes or goggles sliding over his eyes
   - [ ] the wand stays on the bedside table
   - [ ] the motion reads clearly: wake → stretch → hop out → look up and point at the window
   - [ ] the camera is gentle; nothing scary
5. If the model can't fit all four actions into 5 s, test this shorter fallback prompt (it covers the
   first half of the beat; the second half becomes its own clip):
   ```text
   Mipo, sitting up in bed, slowly opens his eyes and stretches both arms up with a cute, happy yawn, then smiles. Golden sunbeam sparkles drift. Gentle slow camera push-in. Keep his face, hair, goggles on his head, red scarf, cream jacket and backpack exactly the same. The star wand stays on the bedside table. Kid-safe, vertical 9:16.
   ```
6. Copy the best take to `clips/scene_01.mp4`.

## D. Test log (fill in)
| Date | Tool + model | Step | Takes | Passed? | What failed | Free credits used |
|---|---|---|---|---|---|---|
| | | A turnaround | | | | |
| | | B start frame | | | | |
| | | C 5 s clip | | | | |

## E. Afterwards
- Commit `reference/approved/mipo_turnaround_v1.png`, `frames/scene_01_start.png`, `clips/scene_01.mp4`
  and this log (see `SETUP.md` §7).
- If you want, share the turnaround, the start frame and the clip in a Claude session. I can check them
  against the banner item by item and pull frames from the clip.
- Choose a paid plan only after a tool passes A–C. That decision is yours.
