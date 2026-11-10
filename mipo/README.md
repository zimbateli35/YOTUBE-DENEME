# Mipo's Magical World — Episode 1: "Mipo and the Missing Rainbow Color"

**Preview video:** `output/mipo_ep1_missing_rainbow_color_1080x1920.mp4`
(1080×1920, 9:16, 30.0 s, 24 fps, H.264 + AAC, ~15 MB)

## What this preview is (and isn't)

| Requirement | Status |
|---|---|
| 6 scenes, 30 s, 1080×1920 MP4 | ✅ Rendered |
| Mipo on-model in every frame | ✅ One locked model (`src/characters.py`) drawn in every shot; only pose/expression change |
| English narration, synced | ✅ Generated, but with an **offline robotic TTS** (flite), pitched up. Not a natural boy's voice |
| Original music + SFX (sparkles, birds, whooshes) | ✅ Synthesized from code (`src/audio.py`), copyright-safe |
| Subtitles | ✅ `output/audio/subtitles.srt` |
| **Premium 3D animation** | ❌ **Not possible in this environment**. The preview is clean 2D vector animation |

### Why not 3D here
- No video-generation, image-generation or neural-voice service is connected to the
  session. The network blocks OpenAI, ElevenLabs, Runway, Replicate, Luma and Hugging Face.
- Blender is installable as `bpy`, but the machine is CPU-only (4 cores, no GPU), and
  there is no rigged 3D model of Mipo. Building one from primitives would look *less*
  like the banner than the 2D version.

### What's needed for the 3D version
1. **A 3D model of Mipo, consistent with the banner**: a commissioned or rigged Blender model,
   or an image-to-3D service, or a video model with character reference
   (Runway Gen-4 References, Kling Elements, Pika, Luma, Veo/Sora with image refs).
2. **Natural voice**: ElevenLabs / OpenAI TTS / a voice actor, using the lines in `src/script.py`.
3. Either a GPU render machine or API keys for (1) and (2). Once those are available, the
   timings, music and SFX here can be reused unchanged.

## Character notes
Locked palette: brown tousled hair, big brown eyes, freckles and rosy cheeks, bronze goggles
with blue lenses, red scarf, cream jacket with brown cuffs, dark-brown shirt with a gold star,
belt, **blue jeans**, brown boots, brown backpack with a rolled mat, and a gold star wand.

⚠️ The written brief says **blue jeans**, but the banner art shows **dark brown cargo pants**.
The preview follows the written brief. To match the banner, change the three `jeans*` colors
in `src/characters.py` (the values are given in the comment there) and re-render.

The missing color is **purple**. It appears nowhere on Mipo, so his outfit stays identical in
every shot while the rainbow stripe, castle roofs, crystals and flowers lose and regain it.

## Storyboard as rendered
| Time | Scene | Narration |
|---|---|---|
| 0–5 | Treehouse bedroom; wand on the bedside; purple stripe missing in the window rainbow | "Good morning, Mipo! Oh no! A rainbow color is missing!" |
| 5–10 | Porch over the muted valley; wand flies to his hand; sparkle trail forms | "Where did the purple go? Let's find it!" |
| 10–15 | Stone bridge, castle, waterfall, butterflies; blue bird joins and they talk | "Follow those magical sparkles!" |
| 15–20 | Bunny and baby deer arrive; flower opens on a glowing purple droplet | "Look! Our friends found the missing color!" |
| 20–25 | Wand tap; purple sparkles fly up and repaint the stripe; color returns | "One little tap... and MAGIC!" |
| 25–30 | Full rainbow, celebration, Mipo waves; end card | "Hooray! We did it! See you next magic moment!" |

## Rebuild
```bash
python3 src/audio.py output/audio            # voice lines, soundtrack.wav, subtitles.srt, timing.json
python3 src/render.py output/audio output/mipo_ep1_missing_rainbow_color_1080x1920.mp4
python3 src/render.py --stills /tmp/stills 0.5 12 17.8 24   # quick preview frames
```
Needs Python 3 with Pillow and NumPy, plus ffmpeg built with libflite. The full render takes about 75 s on 4 CPU cores.

## Prompt pack for a 3D video/image generator
Attach `reference/cover_*.png` as the character reference to **every** prompt.

**Character lock (prepend to every prompt):** *Mipo, the same human boy as the reference image:
tousled brown hair, large brown eyes, rosy cheeks, freckles, bronze aviator goggles with blue
lenses on his head, bright red scarf, cream explorer jacket with brown cuffs, dark brown shirt
with a large golden star, brown belt, blue jeans, brown explorer boots, brown leather backpack
with a rolled sleeping mat, a wand with a glowing golden star tip. Premium 3D children's
animation, soft lighting, bright colors, kid-safe. No hoodie, no wizard costume, not an animal.*

1. Cozy pastel treehouse bedroom, morning sun through a round window, wand glowing on the
   bedside table. Mipo sits up, stretches and hops out of bed. Through the window, the rainbow
   is missing its purple stripe. Mipo looks surprised.
2. On the treehouse porch over a softly muted valley, Mipo catches his star wand as it flies to
   him and raises it. Tiny glowing sparkles form a trail toward a small stone bridge.
3. Mipo happily walks across an arched stone bridge with orange railings, following the
   sparkles. A friendly round blue bird flies in and chats with him. In the background: a waterfall,
   a castle with purple-grey roofs on a floating island, butterflies.
4. In a flower meadow a white bunny and a spotted baby deer join Mipo and the bird. A big pink
   flower opens to reveal a glowing purple paint droplet. Everyone smiles.
5. Mipo gently taps the droplet with his golden star wand. Purple sparkles swirl up into the sky
   and paint the missing stripe back into the rainbow. Purple returns to the valley.
6. The full rainbow shines. Mipo, the bird, the bunny and the deer celebrate. Mipo waves at the
   camera. Leave clear space at the top for the end-card text "See you next magic moment!"
