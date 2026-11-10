# Mipo's Magical World: series format

A premium 3D animated series for **children aged 2–7** (still enjoyable up to about 9), in English,
for YouTube. Each episode follows Mipo, a curious and kind human boy, on a new adventure. Every episode
has **its own feeling** and **its own lesson**, and always ends happily.

## 1. Two formats from one production

| | Long episode (main) | Shorts |
|---|---|---|
| Length | **10–12 min** | 30–60 s |
| Frame | 16:9, 1920×1080, 30 fps | 9:16, 1080×1920, 30 fps |
| Purpose | Watch time, learning, chapters | Discovery, channel growth |
| Source | `episode.json` built from `outline.json` | a separate short `episode.json`, or a cut-down of the long one |

## 2. Episode template (about 11 min)

| # | Part | Time | Content |
|---|---|---|---|
| 1 | **Hook** | 0:00–0:20 | Mipo greets the viewer; the problem is shown straight away and the viewer is invited ("Will you help me?") |
| 2 | **Theme song** | 0:20–0:45 | The same opening song every episode (series identity) |
| 3 | **Problem + feeling** | ~1 min | Mipo feels something (sad, scared, angry...); the narrator names the feeling and offers a calming tool |
| 4 | **Call to adventure** | ~1 min | The star wand shows the way; Mipo decides to be brave |
| 5 | **4–5 adventure stops** | 1 min each | Each stop: **1 learning concept** (color, number, shape...) + **1 social skill** (helping, taking turns, asking for help) + **1 interactive question** to the viewer |
| 6 | **Climax** | ~1 min | Solved together, with a 3-2-1 countdown and the "MAGIC!" moment |
| 7 | **Celebration + recap song** | ~1 min | Short song repeating what was learned |
| 8 | **Recap + goodbye** | ~30 s | "Today I felt... I learned..." → **"See you next magic moment!"** |
| 9 | **End screen** | last 20 s | Mipo on the left, empty space on the right for YouTube end-screen elements |

## 3. Rules for ages 2–7
- **Pacing:** one idea per shot, 5–10 s shots, no fast cuts. Speech is calm, about 2.2 words per second
  (`author_episode.py` checks this automatically).
- **Language:** short sentences, repetition, interactive pauses ("Can you say red? ... Red!", leave 1–2 s).
- **Emotions:** negative feelings are never scary. They're named ("Mipo feels sad. That's okay.") and
  given a coping tool (breathing, holding a friend's hand, asking for help).
- **Visuals:** bright, saturated but soft colors, soft lighting, round shapes. No darkness, monsters,
  loud bangs or flashing strobes.
- **Characters:** Mipo is always on-model (`CHARACTER_LOCK.md`); friends always use their locked designs
  (`mipo_character.json` → friends).
- **Voices:** every character always uses the same ElevenLabs voice (`voices.json`).
- **Music:** the same theme and sign-off chime every episode, soft under the voices (ducked automatically).

## 4. Recurring elements (series identity)
- Opening line: **"Hi, friends! I'm Mipo!"** · Theme song · Star-wand "MAGIC!" moment
- Closing line: **"See you next magic moment!"** · Recap song · End screen

## 5. Episode ideas (each with its own feeling and lesson)
| # | Title | Feeling | Lesson |
|---|---|---|---|
| 1 | **Mipo and the Missing Rainbow Color** | sad → brave → happy | Rainbow colors, counting, everyone is important |
| 2 | Mipo and the Lost Little Star | worried → calm | Counting to 10, asking for help |
| 3 | Mipo's Big Shape Parade | frustrated → proud | Shapes, trying again |
| 4 | Mipo and the Sleepy Moon | scared of the dark → safe | Night and day, calming tools |
| 5 | Mipo Shares the Picnic | jealous → generous | Sharing, fruit names |
| 6 | Mipo and the Grumpy Cloud | angry → understanding | Weather, naming anger |

## 6. YouTube publishing checklist
- Audience: **"Yes, it's made for kids"** (COPPA). Comments are turned off automatically.
- Title + `generated/YOUTUBE_CHAPTERS.txt` (paste into the description; the first chapter is 0:00).
- `generated/subtitles.srt` → English captions.
- Altered/synthetic content disclosure: follow YouTube's current guidance (an animated fantasy is
  usually not "realistic", but check).
- Thumbnail: Mipo's face large, bright colors, 2–3 words at most.
- Long-episode end screen: last 20 s (subscribe + next episode).
- Shorts: a 30–60 s vertical cut from the same episode, linking to the long episode.
