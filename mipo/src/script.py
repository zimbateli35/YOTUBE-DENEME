"""Mipo's Magical World - Episode 1: "Mipo and the Missing Rainbow Color".

Single source of truth for timing. render.py (picture) and audio.py
(voice, music, sfx) both import from here so they stay in sync.
"""

W, H = 1080, 1920          # 9:16 YouTube Shorts
FPS = 24
DURATION = 30.0
TITLE = "Mipo and the Missing Rainbow Color"

# (start, end, key, beat)
SCENES = [
    (0.0, 5.0, "bedroom", "Mipo wakes in his treehouse bedroom; purple stripe is missing from the rainbow"),
    (5.0, 10.0, "porch", "Mipo picks up his star wand on the porch; muted valley; sparkles form a trail"),
    (10.0, 15.0, "bridge", "Mipo follows the sparkles across the stone bridge; blue bird joins him"),
    (15.0, 20.0, "meadow", "Bunny and baby deer join; a glowing purple droplet is inside a flower"),
    (20.0, 25.0, "tap", "Mipo taps the droplet; purple sparkles fly up and repaint the rainbow"),
    (25.0, 30.0, "celebrate", "Full rainbow; friends celebrate; Mipo waves at the viewer; end card"),
]

# (start, line) - simple English for ages 2-7.
NARRATION = [
    (0.35, "Good morning, Mipo!"),
    (2.25, "Oh no! A rainbow color is missing!"),
    (5.40, "Where did the purple go?"),
    (7.60, "Let's find it!"),
    (10.50, "Follow those magical sparkles!"),
    (15.50, "Look! Our friends found the missing color!"),
    (20.40, "One little tap..."),
    (21.90, "and MAGIC!"),
    (25.30, "Hooray! We did it!"),
    (27.20, "See you next magic moment!"),
]

# Story events used by both picture and sound.
T_WAND_PICKUP = 6.2     # wand lands in Mipo's hand
T_SPARKLE_TRAIL = 7.4   # trail starts forming
T_BIRD_ARRIVE = 11.2
T_BUNNY_ARRIVE = 15.3
T_DEER_ARRIVE = 15.8
T_FLOWER_OPEN = 16.6
T_TAP = 22.05           # wand touches droplet ("MAGIC!")
T_RESTORE_START = 22.6  # purple stripe begins painting back
T_RESTORE_END = 24.4
T_END_CARD = 27.1
