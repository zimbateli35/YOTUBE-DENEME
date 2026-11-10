"""Render Episode 1 picture frames and mux with the soundtrack.

Usage:
  python3 render.py <audio_dir> <out.mp4>            # full video
  python3 render.py --stills <out_dir> t1 t2 ...    # preview stills
"""
import json
import math
import os
import subprocess
import sys
from multiprocessing import Pool

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageFont

sys.path.insert(0, os.path.dirname(__file__))
import characters as ch  # noqa: E402
from characters import Pen, draw_bird, draw_bunny, draw_deer, draw_mipo, star_points  # noqa: E402
from script import (DURATION, FPS, H, NARRATION, SCENES, TITLE, W, T_BIRD_ARRIVE,  # noqa: E402
                    T_BUNNY_ARRIVE, T_DEER_ARRIVE, T_END_CARD, T_FLOWER_OPEN,
                    T_RESTORE_END, T_RESTORE_START, T_SPARKLE_TRAIL, T_TAP, T_WAND_PICKUP)

SS = 2                       # supersampling
CW, CH = W * SS, H * SS
FONT_BOLD = "/usr/share/fonts/opentype/inter/InterDisplay-Bold.otf"
FONT_XB = "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf"
XFADE = 0.32

RAINBOW = ["#ff6262", "#ffa53f", "#ffe04f", "#72d46b", "#4fb3ff", "#a463ff"]
PURPLE = "#a463ff"
VOICE_DUR = {}


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


def seg(t, a, b):
    return ease((t - a) / (b - a))


def lerp(a, b, u):
    return a + (b - a) * u


def hexrgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def mix(c0, c1, u):
    a, b = hexrgb(c0) if isinstance(c0, str) else c0, hexrgb(c1) if isinstance(c1, str) else c1
    return tuple(int(lerp(a[i], b[i], u)) for i in range(3))


def grey_of(c):
    r, g, b = hexrgb(c)
    y = int(0.3 * r + 0.59 * g + 0.11 * b)
    y = int(lerp(y, 190, 0.35))
    return (y, y, y)


def purple(c, p):
    """Colors that belong to the missing purple: grey when p=0."""
    return mix(grey_of(c), c, p)


def restore_p(t):
    return seg(t, T_RESTORE_START, T_RESTORE_END)


def vgrad(img, box, c0, c1):
    x0, y0, x1, y1 = [int(v * SS) for v in box]
    h = max(1, y1 - y0)
    a, b = np.array(hexrgb(c0), float), np.array(hexrgb(c1), float)
    u = np.linspace(0, 1, h)[:, None]
    col = (a * (1 - u) + b * u).astype(np.uint8)
    arr = np.repeat(col[:, None, :], x1 - x0, axis=1)
    img.paste(Image.fromarray(arr, "RGB"), (x0, y0))


def soft(img, fn, color, alpha):
    """Draw translucent shapes: fn(draw) draws with fill=255 on a mask."""
    mask = Image.new("L", img.size, 0)
    fn(ImageDraw.Draw(mask))
    mask = mask.point(lambda v: int(v * alpha))
    img.paste(color, mask=mask)


def bg_pen(img):
    return Pen(img, 0, 0, SS)


def speaking(t):
    for at, line in NARRATION:
        d = VOICE_DUR.get(line, 1.6)
        if at <= t <= at + d:
            return True
    return False


def talk_mouth(t, base="smile"):
    if speaking(t):
        return "talk" if int(t * 7) % 2 == 0 else "open"
    return base


def blink(t, eyes="open", period=3.1, off=0.0):
    if eyes == "open" and ((t + off) % period) < 0.12:
        return "closed"
    return eyes


# ---------------------------------------------------------------------------
# world pieces (frame units 1080 x 1920)
# ---------------------------------------------------------------------------
def cloud(pen, x, y, s, col="#ffffff"):
    for dx, dy, r in ((-60, 10, 42), (-20, -18, 55), (35, -8, 48), (75, 12, 36), (10, 18, 46)):
        pen.circle(x + dx * s, y + dy * s, r * s, col)


def rainbow(img, cx, cy, R, band, p_purple=0.0, sweep=0.0, hint=0.0, only_purple=False):
    d = ImageDraw.Draw(img)
    for i, c in enumerate(RAINBOW):
        r = (R - i * band) * SS
        box = [cx * SS - r, cy * SS - r, cx * SS + r, cy * SS + r]
        w = int(band * SS) + 2
        if c == PURPLE:
            if sweep > 0:
                d.arc(box, 180, 180 + 180 * sweep, fill=hexrgb(PURPLE), width=w)
            if hint > 0 and sweep < 1:  # dotted "missing" outline
                rr = r - w / 2
                n = 34
                for k in range(n):
                    a = math.pi + math.pi * (k + 0.5) / n
                    if a < math.pi + math.pi * sweep:
                        continue
                    x, y = cx * SS + rr * math.cos(a), cy * SS + rr * math.sin(a)
                    q = 3.5 * SS * hint
                    d.ellipse([x - q, y - q, x + q, y + q], fill=(255, 255, 255))
        elif not only_purple:
            d.arc(box, 180, 360, fill=hexrgb(c), width=w)


def flower(pen, x, y, r, petal, center="#ffd54a", stem=True, n=6):
    if stem:
        pen.line([(x, y + r), (x + 4, y + r * 4)], "#4caf50", max(3, r * 0.22))
    for k in range(n):
        a = 2 * math.pi * k / n
        pen.circle(x + r * 0.75 * math.cos(a), y + r * 0.75 * math.sin(a), r * 0.55, petal)
    pen.circle(x, y, r * 0.42, center)


def crystal(pen, x, y, s, p):
    for dx, h, w, c in ((-26, 120, 26, "#c79bff"), (14, 160, 30, "#b07cff"), (44, 100, 22, "#d6b3ff")):
        col = purple(c, p)
        hi = purple("#efe2ff", p)
        bx = x + dx * s
        pen.poly([(bx - w * s, y), (bx - w * s, y - h * s), (bx, y - (h + 34) * s),
                  (bx + w * s, y - h * s), (bx + w * s, y)], col, "#7a5aa8" if p > 0.5 else "#8a8a8a", 2)
        pen.poly([(bx - w * s * 0.3, y - 10 * s), (bx - w * s * 0.3, y - h * s * 0.9),
                  (bx, y - (h + 20) * s), (bx, y - 10 * s)], hi)


def castle(pen, x, y, s, p):
    """Floating island with castle and waterfall; purple roofs follow p."""
    O = "#8a6a7a"
    pen.poly([(x - 170 * s, y), (x + 170 * s, y), (x + 110 * s, y + 90 * s), (x + 30 * s, y + 150 * s),
              (x - 60 * s, y + 120 * s), (x - 130 * s, y + 70 * s)], "#8a7a6a", "#6a5a4a", 2)
    pen.ellipse(x, y, 175 * s, 30 * s, "#69c25a")
    roof = purple("#8f5cf0", p)
    for dx, w, h in ((-110, 34, 120), (-50, 40, 170), (10, 52, 230), (75, 40, 160), (130, 30, 110)):
        bx = x + dx * s
        top = y - h * s
        pen.rrect(bx - w * s / 2, top, bx + w * s / 2, y, 4, "#fbe3d0", O, 1.5)
        pen.poly([(bx - w * s * 0.65, top), (bx, top - w * 1.5 * s), (bx + w * s * 0.65, top)], roof, O, 1.5)
        pen.line([(bx, top - w * 1.5 * s), (bx, top - w * 1.5 * s - 22 * s)], "#8a6a7a", 2)
        pen.poly([(bx, top - w * 1.5 * s - 22 * s), (bx + 16 * s, top - w * 1.5 * s - 17 * s),
                  (bx, top - w * 1.5 * s - 12 * s)], "#ff4a5a")
        pen.rrect(bx - 6 * s, top + 24 * s, bx + 6 * s, top + 40 * s, 3, "#ffc64a")
    pen.rrect(x - 4 * s, y - 40 * s, x + 24 * s, y, 8, "#ffb04a", O, 1.5)


def waterfall(pen, x, y0, y1, w):
    pen.rrect(x - w / 2, y0, x + w / 2, y1, 6, "#a8e6ff")
    for k in range(4):
        xx = x - w / 2 + (k + 0.5) * w / 4
        pen.line([(xx, y0 + 6), (xx, y1 - 6)], "#e8fbff", 3)


def hills(pen, y, amp, col, phase=0.0, freq=1.6):
    pts = [(0, H)]
    for k in range(0, 41):
        x = k * W / 40
        pts.append((x, y - amp * (0.6 + 0.4 * math.sin(freq * x / W * 2 * math.pi + phase))))
    pts.append((W, H))
    pen.poly(pts, col)


def tree(pen, x, y, s):
    pen.poly([(x - 30 * s, y), (x - 20 * s, y - 160 * s), (x + 20 * s, y - 160 * s), (x + 30 * s, y)], "#8a5a32")
    for dx, dy, r in ((-50, -170, 70), (40, -180, 66), (0, -230, 80)):
        pen.circle(x + dx * s, y + dy * s, r * s, "#5cb85c")
        pen.circle(x + dx * s - 14 * s, y + dy * s - 16 * s, r * s * 0.55, "#7fd17a")


def sky_world(img, p, mute=True, rb=(540, 820, 470, 30), with_castle=(820, 560, 1.0),
              hills_y=(1050, 1150, 1250)):
    """Shared valley backdrop. Returns nothing; draws statics."""
    pen = bg_pen(img)
    vgrad(img, (0, 0, W, 1300), "#3f9bff", "#c3ecff")
    for (x, y, s) in ((170, 240, 0.9), (880, 180, 0.7), (420, 420, 0.6), (980, 620, 0.55)):
        cloud(pen, x, y, s)
    rainbow(img, *rb, p_purple=p, sweep=0.0)
    hills(pen, hills_y[0], 120, "#9ed98a", 0.5, 1.2)
    if with_castle:
        cx, cy, cs = with_castle
        waterfall(pen, cx + 40 * cs, cy + 80 * cs, hills_y[0] + 30, 46 * cs)
        castle(pen, cx, cy, cs, p)
    hills(pen, hills_y[1], 90, "#7fcf6c", 2.0, 1.7)
    for x in (120, 330, 760, 960):
        tree(pen, x, hills_y[1] - 30 + 20 * math.sin(x), 0.5)
    hills(pen, hills_y[2], 70, "#6cc35a", 3.3, 1.1)


def muted(img, amount):
    if amount <= 0:
        return img
    return ImageEnhance.Color(img).enhance(1 - amount)


# ---------------------------------------------------------------------------
# glow / particles / text
# ---------------------------------------------------------------------------
def apply_glows(img):
    if not ch.GLOWS:
        return img
    f = 8
    layer = Image.new("RGB", (CW // f, CH // f), (0, 0, 0))
    d = ImageDraw.Draw(layer)
    for x, y, r, col, st in ch.GLOWS:
        x, y, r = x / f, y / f, max(1.5, r / f)
        c = tuple(int(v * clamp(st, 0, 1.5) * 0.75) for v in col)
        d.ellipse([x - r, y - r, x + r, y + r], fill=c)
    layer = layer.filter(ImageFilter.GaussianBlur(7)).resize(img.size, Image.BILINEAR)
    ch.GLOWS.clear()
    return ImageChops.screen(img, layer)


def sparkle(img, x, y, r, col=(255, 240, 160), rot=0.0, glow=True):
    pen = bg_pen(img)
    pen.poly(star_points(x, y, r, r * 0.38, rot, 4), col)
    pen.circle(x, y, r * 0.25, "#ffffff")
    if glow:
        pen.glow(x, y, r * 2.4, col, 0.8)


def text_center(img, txt, y, size, fill, stroke, sw=10, font=FONT_XB, scale=1.0, alpha=1.0):
    if alpha <= 0:
        return
    fnt = ImageFont.truetype(font, int(size * SS * scale))
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    bb = d.textbbox((0, 0), txt, font=fnt, stroke_width=int(sw * SS * scale))
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    d.text((CW / 2 - tw / 2 - bb[0], y * SS - th / 2 - bb[1]), txt, font=fnt, fill=fill,
           stroke_width=int(sw * SS * scale), stroke_fill=stroke)
    if alpha < 1:
        layer.putalpha(layer.getchannel("A").point(lambda v: int(v * alpha)))
    img.paste(layer, (0, 0), layer)


# ---------------------------------------------------------------------------
# backgrounds (cached per process)
# ---------------------------------------------------------------------------
_BG = {}


def bg(key, p=0.0):
    k = (key, round(p, 3))
    if k in _BG:
        return _BG[k]
    img = Image.new("RGB", (CW, CH))
    globals()["bg_" + key](img, p)
    keep = ch.GLOWS[:]
    ch.GLOWS.clear()
    _BG[k] = (img, keep)
    return _BG[k]


def bg_blend(key, p):
    """Blend the grey (p=0) and restored (p=1) versions of a backdrop."""
    if p <= 0.001:
        return bg(key, 0.0)
    if p >= 0.999:
        return bg(key, 1.0)
    a, ga = bg(key, 0.0)
    b, _ = bg(key, 1.0)
    return Image.blend(a, b, p), ga


def bg_bedroom(img, p):
    pen = bg_pen(img)
    vgrad(img, (0, 0, W, 1500), "#f9dfbd", "#ecbf91")
    for x in range(45, W, 90):
        pen.line([(x, 0), (x, 1500)], "#e2b182", 4, False)
    vgrad(img, (0, 1500, W, H), "#c48650", "#a96d3c")
    for y in (1560, 1650, 1760, 1880):
        pen.line([(0, y), (W, y)], "#9a6236", 4, False)
    pen.ellipse(600, 1700, 420, 105, "#f6a9bd")
    pen.ellipse(600, 1700, 330, 76, "#ffd3de")
    # round window with valley + rainbow missing purple
    wx, wy, wr = 690, 560, 280
    view = Image.new("RGB", (CW, CH))
    vp = bg_pen(view)
    vgrad(view, (wx - wr, wy - wr, wx + wr, wy + wr), "#4aa6ff", "#bfeaff")
    cloud(vp, wx - 120, wy - 170, 0.55)
    cloud(vp, wx + 150, wy - 90, 0.45)
    rainbow(view, wx, wy + 230, 250, 24)
    hills(vp, wy + 230, 60, "#8fd67c", 1.0, 3.0)
    hills(vp, wy + 280, 50, "#6cc35a", 2.4, 2.2)
    m = Image.new("L", (CW, CH), 0)
    ImageDraw.Draw(m).ellipse([(wx - wr) * SS, (wy - wr) * SS, (wx + wr) * SS, (wy + wr) * SS], fill=255)
    img.paste(view, (0, 0), m)
    pen.d.ellipse([(wx - wr - 26) * SS, (wy - wr - 26) * SS, (wx + wr + 26) * SS, (wy + wr + 26) * SS],
                  outline=hexrgb("#8a5a32"), width=34 * SS)
    pen.line([(wx - wr, wy), (wx + wr, wy)], "#8a5a32", 14, False)
    pen.line([(wx, wy - wr), (wx, wy + wr)], "#8a5a32", 14, False)
    # sun beams
    soft(img, lambda d: [d.polygon([((wx - 200) * SS, (wy - 120) * SS), ((wx - 60) * SS, (wy - 250) * SS),
                                    ((wx - 330 + k * 60) * SS, 1900 * SS), ((wx - 620 + k * 60) * SS, 1900 * SS)],
                                   fill=255) for k in (0, 3)], (255, 244, 200), 0.18)
    # shelf with books + star toy
    pen.rrect(40, 700, 330, 722, 6, "#9a6236", "#6e4424", 2)
    for i, (c, h) in enumerate((("#ff7b7b", 90), ("#6fb7ff", 110), ("#ffd166", 80), ("#7ed67a", 100))):
        pen.rrect(60 + i * 40, 700 - h, 92 + i * 40, 700, 4, c, "#6e4424", 2)
    pen.poly(star_points(270, 660, 34, 15), "#ffd23a", "#f0961c", 3)
    # lantern
    pen.line([(190, 0), (190, 260)], "#6e4424", 4, False)
    pen.rrect(150, 260, 230, 370, 14, "#ffcf5a", "#7a4a22", 6)
    pen.rrect(140, 250, 240, 272, 6, "#7a4a22")
    pen.glow(190, 315, 140, (255, 200, 90), 1.0)
    # bed (back parts)
    pen.rrect(30, 1120, 510, 1460, 40, "#b8773f", "#7a4a22", 4)
    pen.rrect(60, 1150, 480, 1300, 30, "#cf9258")
    pen.rrect(30, 1330, 640, 1500, 22, "#ffffff", "#bba", 3)
    pen.ellipse(170, 1300, 120, 55, "#ffffff", "#c9c0b8", 3)
    # nightstand (far right)
    pen.rrect(880, 1440, 1100, 1700, 14, "#b5763f", "#7a4a22", 4)
    pen.rrect(900, 1520, 1080, 1600, 8, "#c98a50", "#7a4a22", 2)
    pen.circle(990, 1560, 9, "#e0b24a")


def bed_front(img, wand_on_stand=True, t=0.0):
    pen = bg_pen(img)
    pen.rrect(40, 1340, 660, 1530, 30, "#7ccfd6", "#4a9aa3", 4)
    pen.line([(60, 1395), (640, 1395)], "#a8e4e8", 8, False)
    for x, y in ((150, 1450), (300, 1480), (450, 1440), (580, 1490)):
        pen.poly(star_points(x, y, 22, 10), "#ffe27a")
    pen.rrect(20, 1470, 660, 1590, 20, "#b8773f", "#7a4a22", 4)


def wand_prop(img, x, y, ang, s=1.0, glow=1.0):
    """Wand lying/flying on its own (same model as in Mipo's hand)."""
    pen = Pen(img, x * SS, y * SS, SS * s)
    a = math.radians(ang)
    dx, dy = math.sin(a), -math.cos(a)
    C = ch.MIPO
    pen.limb([(-dx * 110, -dy * 110), (0, 0)], C["wand"], 10, C["outline"], 2.5)
    pen.limb([(-dx * 38, -dy * 38), (-dx * 28, -dy * 28)], C["wand_band"], 13, C["outline"], 2)
    pen.glow(0, 0, 75, (255, 220, 90), 0.9 * glow)
    pen.poly(star_points(0, 0, 32, 15, ang), C["star"], C["star_edge"], 4)
    pen.poly(star_points(0, 0, 15, 7, ang), "#fff6c4")


def bg_porch(img, p):
    sky_world(img, p, rb=(540, 900, 520, 30), with_castle=(800, 600, 0.9), hills_y=(1080, 1180, 1260))
    pen = bg_pen(img)
    # river + small bridge in the distance
    pen.poly([(0, 1230), (300, 1210), (520, 1240), (760, 1215), (1080, 1235), (1080, 1300), (0, 1300)], "#59c3f2")
    pen.d.arc([380 * SS, 1150 * SS, 640 * SS, 1300 * SS], 180, 360, fill=hexrgb("#c9b29a"), width=26 * SS)
    # treehouse trunk at left edge with door
    pen.poly([(0, 0), (150, 0), (170, 1500), (0, 1500)], "#8a5a32", "#6a4224", 3)
    pen.rrect(20, 1060, 140, 1380, 50, "#6e4424", "#4a2e1c", 4)
    pen.circle(118, 1230, 8, "#e0b24a")
    for y in (300, 620, 900):
        pen.line([(20, y), (130, y + 30)], "#6e4424", 6, False)
    # lantern
    pen.rrect(200, 880, 260, 960, 12, "#ffcf5a", "#7a4a22", 5)
    pen.glow(230, 920, 100, (255, 200, 90), 1.0)
    # porch railing + deck
    for x in range(180, W + 1, 110):
        pen.rrect(x - 12, 1330, x + 12, 1560, 6, "#c48650", "#7a4a22", 3)
    pen.rrect(150, 1320, W + 20, 1350, 10, "#d39760", "#7a4a22", 3)
    pen.rrect(150, 1430, W + 20, 1452, 8, "#d39760", "#7a4a22", 3)
    vgrad(img, (0, 1540, W, H), "#c98a50", "#a86d3a")
    for y in (1600, 1690, 1800):
        pen.line([(0, y), (W, y)], "#93592e", 4, False)
    for x, c in ((260, "#ff8fc8"), (980, "#ffd54a")):
        pen.rrect(x - 40, 1500, x + 40, 1580, 10, "#d07a4a", "#7a4a22", 3)
        flower(pen, x, 1470, 26, c, stem=False)


def deck_y(x):
    return 1260 - 110 * math.sin(math.pi * clamp((x - 40) / 1000))


def bg_bridge(img, p):
    sky_world(img, p, rb=(540, 760, 470, 28), with_castle=(820, 470, 0.85), hills_y=(950, 1060, 1150))
    pen = bg_pen(img)
    # river
    pen.poly([(0, 1180), (W, 1170), (W, 1620), (0, 1640)], "#4fbdf0")
    for k in range(10):
        y = 1230 + k * 38
        pen.line([(60 + (k * 97) % 300, y), (200 + (k * 97) % 300, y)], "#a8e6ff", 5)
        pen.line([(620 - (k * 53) % 260, y + 12), (760 - (k * 53) % 260, y + 12)], "#a8e6ff", 5)
    # stone bridge
    top = [(x, deck_y(x)) for x in range(0, W + 1, 20)]
    body = top + [(W, 1600), (0, 1600)]
    pen.poly(body, "#c9ad8e", "#8a7058", 4)
    for row in range(5):
        y0 = 1300 + row * 60
        for k in range(12):
            x = (k * 100 + (row % 2) * 50)
            if y0 < deck_y(x) + 30:
                continue
            pen.rrect(x + 4, y0 + 4, x + 96, y0 + 56, 10, "#d8bea0")
    pen.d.ellipse([260 * SS, 1300 * SS, 820 * SS, 1800 * SS], fill=hexrgb("#3d8fc2"))
    pen.d.arc([260 * SS, 1300 * SS, 820 * SS, 1800 * SS], 180, 360, fill=hexrgb("#8a7058"), width=8 * SS)
    pen.poly([(x, y) for x, y in top] + [(W, deck_y(W) + 30)] + [(x, y + 30) for x, y in reversed(top)][1:],
             "#b8987a", "#8a7058", 3)
    # back railing (orange wood like banner)
    for x in range(30, W, 70):
        pen.rrect(x - 7, deck_y(x) - 95, x + 7, deck_y(x), 4, "#e39b4a", "#9a5a22", 2)
    pen.line([(x, deck_y(x) - 92) for x in range(0, W + 1, 20)], "#f0ad5a", 12, False)
    # foreground meadow with flowers
    vgrad(img, (0, 1640, W, H), "#7fd36a", "#4fae4a")
    rng = np.random.default_rng(7)
    for k in range(26):
        x, y = rng.uniform(0, W), rng.uniform(1680, 1900)
        c = rng.choice(["#ff8fc8", "#ffd54a", "#ffffff", "#ff6b6b", "PURPLE"])
        flower(pen, x, y, rng.uniform(14, 26), purple("#a463ff", p) if c == "PURPLE" else c)
    crystal(pen, 990, 1900, 0.9, p)


def bg_meadow(img, p):
    sky_world(img, p, rb=(540, 840, 500, 30), with_castle=(840, 520, 0.75), hills_y=(980, 1080, 1170))
    pen = bg_pen(img)
    vgrad(img, (0, 1200, W, H), "#86d870", "#4fae4a")
    pen.poly([(0, 1250), (300, 1235), (520, 1260), (760, 1240), (1080, 1255), (1080, 1300), (0, 1310)], "#59c3f2")
    rng = np.random.default_rng(11)
    for k in range(34):
        x, y = rng.uniform(0, W), rng.uniform(1330, 1900)
        c = rng.choice(["#ff8fc8", "#ffd54a", "#ffffff", "#ff6b6b", "PURPLE", "PURPLE"])
        flower(pen, x, y, rng.uniform(12, 24) * (0.6 + 0.6 * (y - 1300) / 600),
               purple("#a463ff", p) if c == "PURPLE" else c)
    crystal(pen, 70, 1560, 1.0, p)
    crystal(pen, 1020, 1480, 0.8, p)
    # treehouse tree at left, like the banner
    pen.poly([(0, 1200), (0, 300), (90, 320), (120, 1220)], "#8a5a32", "#6a4224", 3)
    for dx, dy, r in ((20, 260, 140), (130, 200, 110), (-20, 120, 120)):
        pen.circle(dx, dy, r, "#5cb85c")
        pen.circle(dx - 30, dy - 30, r * 0.5, "#7fd17a")
    pen.rrect(10, 560, 120, 660, 14, "#ffcf5a", "#7a4a22", 5)
    pen.glow(65, 610, 110, (255, 200, 90), 0.9)


def bg_celebrate(img, p):
    sky_world(img, 1.0, rb=(540, 900, 520, 34), with_castle=(820, 640, 0.8), hills_y=(1080, 1170, 1250))
    pen = bg_pen(img)
    vgrad(img, (0, 1270, W, H), "#86d870", "#4fae4a")
    rng = np.random.default_rng(21)
    for k in range(40):
        x, y = rng.uniform(0, W), rng.uniform(1300, 1900)
        c = rng.choice(["#ff8fc8", "#ffd54a", "#ffffff", "#ff6b6b", "#a463ff", "#a463ff"])
        flower(pen, x, y, rng.uniform(12, 26) * (0.6 + 0.6 * (y - 1300) / 600), c)
    crystal(pen, 60, 1560, 1.0, 1.0)
    crystal(pen, 1030, 1520, 0.85, 1.0)


# ---------------------------------------------------------------------------
# scenes: each returns (canvas_img, zoom, cx, cy) in frame units
# ---------------------------------------------------------------------------
def scene_bedroom(t):
    base, gl = bg("bedroom")
    img = base.copy()
    ch.GLOWS.extend(gl)
    # missing purple hint in window rainbow
    hint = 0.5 + 0.5 * math.sin(t * 6)
    rainbow_hint(img, 690, 790, 250, 24, hint * seg(t, 1.9, 2.4))
    # dust sparkles in the sunbeam (instant hook)
    for k in range(10):
        ph = (t * 0.25 + k * 0.137) % 1
        x = 420 + 260 * math.sin(k * 1.7) - 140 * ph
        y = 500 + 1000 * ph
        sparkle(img, x, y, 8 + 4 * math.sin(t * 5 + k), (255, 236, 170), t * 40)
    # wand resting on the nightstand
    wand_prop(img, 1000, 1420, -78, 0.95, 0.8 + 0.3 * math.sin(t * 4))

    s = 1.9 * SS
    in_bed = t < 1.45
    if t < 1.45:
        x, fy = 290, 1580
    elif t < 2.15:
        u = (t - 1.45) / 0.7
        x = lerp(290, 620, ease(u))
        fy = lerp(1580, 1790, u) - 330 * math.sin(math.pi * u)
    else:
        x, fy = 620, 1790
    bob = 6 * math.sin(t * 3)
    pose = dict(wand=False, scarf=8 * math.sin(t * 2.4))
    if t < 0.7:
        pose.update(eyes="closed", mouth="smile")
    elif t < 1.45:
        u = seg(t, 0.7, 1.25)
        pose.update(eyes="closed" if t < 0.85 else "open", mouth="yawn" if t < 1.2 else "open",
                    armL=(lerp(15, 160, u), lerp(5, 10, u)), armR=(lerp(15, 160, u), lerp(5, 10, u)))
    elif t < 2.15:
        pose.update(eyes="happy", mouth="open", armL=(110, 20), armR=(110, 20),
                    liftL=20, liftR=10)
    else:
        u = seg(t, 2.15, 2.6)
        pose.update(eyes=blink(t), look=(0.7, -0.9), mouth="o" if t < 3.4 else talk_mouth(t, "o"),
                    armR=(lerp(20, 152, u), lerp(5, 8, u)), armL=(lerp(20, 30, u), lerp(5, 120, u)))
    if in_bed:
        pose["eyes"] = blink(t, pose["eyes"]) if pose["eyes"] == "open" else pose["eyes"]
    draw_mipo(img, x * SS, (fy + (bob if not in_bed else 0)) * SS, s, pose)
    if t < 1.62:
        bed_front(img)
    else:
        # blanket stays on bed, drawn behind Mipo would need re-ordering; redraw only frame
        pass
    if t < 0.95:  # z z z
        for k in range(3):
            ph = (t * 0.9 + k * 0.33) % 1
            text_at(img, "z", 420 + 50 * k + 30 * ph, 860 - 160 * ph, 46 + 18 * k, alpha=1 - ph)
    z = lerp(1.2, 1.0, seg(t, 1.2, 2.3)) + 0.04 * seg(t, 2.6, 5.0)
    cx = lerp(330, 560, seg(t, 1.2, 2.3)) + 60 * seg(t, 2.6, 5.0)
    cy = lerp(1150, 960, seg(t, 1.2, 2.3)) - 60 * seg(t, 2.6, 5.0)
    return img, z, cx, cy


def bed_front_after(img):
    bed_front(img)


def rainbow_hint(img, cx, cy, R, band, hint):
    if hint <= 0:
        return
    rainbow_only_purple_hint(img, cx, cy, R, band, hint)


def rainbow_only_purple_hint(img, cx, cy, R, band, hint):
    d = ImageDraw.Draw(img)
    i = len(RAINBOW) - 1
    r = (R - i * band) * SS
    n = 30
    for k in range(n):
        a = math.pi + math.pi * (k + 0.5) / n
        x, y = cx * SS + r * math.cos(a), cy * SS + r * math.sin(a)
        q = 3.2 * SS * (0.4 + 0.6 * hint)
        d.ellipse([x - q, y - q, x + q, y + q], fill=(255, 255, 255))


def text_at(img, txt, x, y, size, alpha=1.0):
    fnt = ImageFont.truetype(FONT_XB, int(size * SS))
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(layer).text((x * SS, y * SS), txt, font=fnt, fill=(120, 150, 255, int(255 * alpha)),
                               stroke_width=3 * SS, stroke_fill=(255, 255, 255, int(255 * alpha)))
    img.paste(layer, (0, 0), layer)


def bezier(p0, p1, p2, u):
    return ((1 - u) ** 2 * p0[0] + 2 * (1 - u) * u * p1[0] + u * u * p2[0],
            (1 - u) ** 2 * p0[1] + 2 * (1 - u) * u * p1[1] + u * u * p2[1])


def scene_porch(t):
    lt = t - 5.0
    base, gl = bg("porch")
    img = muted(base, 0.38).copy()
    ch.GLOWS.extend(gl)
    rainbow_only_purple_hint(img, 540, 900, 520, 30, 0.5 + 0.5 * math.sin(t * 5))
    s = 1.85 * SS
    X, FY = 600, 1800
    pose = dict(scarf=10 * math.sin(t * 2.2), eyes=blink(t), mouth=talk_mouth(t, "smile"))
    tp = T_WAND_PICKUP
    if t < tp:
        u = seg(t, tp - 0.6, tp)
        pose.update(wand=False, look=(-0.8, 0.2) if t < 5.6 else (-0.6, 0.0), mouth=talk_mouth(t, "o"),
                    armR=(lerp(20, 70, u), lerp(5, 20, u)), armL=(30, 120))
        # wand flies in from the treehouse door
        hx, hy = ch.wand_tip(X * SS, FY * SS, s, dict(armR=(70, 20), wand_ang=20))
        k = seg(t, 5.25, tp)
        p0, p1, p2 = (90, 1230), (250, 700), (hx / SS, hy / SS)
        wx, wy = bezier(p0, p1, p2, k)
        for j in range(8):
            q = max(0, k - j * 0.04)
            sx, sy = bezier(p0, p1, p2, q)
            sparkle(img, sx, sy, 10 - j, (255, 230, 140), t * 90 + j * 20)
        if t > 5.25:
            wand_prop(img, wx, wy, lerp(-90, 20, k) + 360 * k, 1.0)
    else:
        u = seg(t, tp, tp + 0.6)
        pose.update(armR=(lerp(70, 112, u), lerp(20, 48, u)), wand_ang=lerp(20, -10, u),
                    armL=(lerp(30, 95, seg(t, 7.4, 7.8)), lerp(120, 15, seg(t, 7.4, 7.8))),
                    palmL=t > 7.6, look=(0.0, -0.3) if t < 7.4 else (-0.5, 0.4),
                    mouth=talk_mouth(t, "open"), wand_glow=1.0 + 0.5 * math.sin(t * 6))
        if t < tp + 0.4:
            pen = bg_pen(img)
            hx, hy = ch.wand_tip(X * SS, FY * SS, s, dict(armR=pose["armR"], wand_ang=pose["wand_ang"]))
            pen.glow(hx / SS, hy / SS, 220 * (1 - (t - tp) / 0.4), (255, 230, 140), 1.2)
    bob = 7 * math.sin(t * 3.2)
    draw_mipo(img, X * SS, (FY + bob) * SS, s, pose)
    # sparkle trail from the porch to the distant bridge
    if t > T_SPARKLE_TRAIL:
        sx, sy = ch.wand_tip(X * SS, (FY + bob) * SS, s, dict(armR=pose["armR"], wand_ang=pose["wand_ang"]))
        p0, p1, p2 = (sx / SS, sy / SS), (380, 900), (510, 1170)
        n = 20
        grown = seg(t, T_SPARKLE_TRAIL, T_SPARKLE_TRAIL + 1.4)
        for j in range(n):
            u = j / (n - 1)
            if u > grown:
                break
            x, y = bezier(p0, p1, p2, u)
            r = (14 - 8 * u) * (0.7 + 0.3 * math.sin(t * 8 + j))
            sparkle(img, x, y, r, (255, 236, 150) if j % 3 else (200, 170, 255), t * 60 + j * 30)
    z = 1.0 + 0.07 * seg(t, 5.0, 10.0)
    return img, z, 560, 1080


def scene_bridge(t):
    base, gl = bg("bridge")
    img = muted(base, 0.32).copy()
    ch.GLOWS.extend(gl)
    rainbow_only_purple_hint(img, 540, 760, 470, 28, 0.5 + 0.5 * math.sin(t * 5))
    # walk path; pause to talk with the bird
    if t < 12.6:
        x = lerp(150, 520, (t - 10.0) / 2.6)
        walking = True
    elif t < 13.9:
        x = 520
        walking = False
    else:
        x = lerp(520, 700, (t - 13.9) / 1.1)
        walking = True
    fy = deck_y(x) + 6
    ph = t * 2 * math.pi * 1.6
    s = 1.3 * SS
    bob = (-6 * abs(math.sin(ph))) if walking else 3 * math.sin(t * 3)
    # sparkles ahead along the deck
    for j in range(9):
        xx = x + 140 + j * 70 + 10 * math.sin(t * 3 + j)
        if xx > W + 40:
            break
        yy = deck_y(xx) - 120 - 50 * math.sin(t * 2 + j * 0.8)
        sparkle(img, xx, yy, 13 - j * 0.6, (255, 236, 150) if j % 2 else (210, 180, 255), t * 70 + j * 40)
    # butterflies
    for k, (bx, by, c) in enumerate(((180, 1500, "#ffd54a"), (860, 1450, "#ff8fc8"), (720, 1700, "#ffd54a"))):
        fx = bx + 60 * math.sin(t * 0.9 + k)
        fyb = by + 30 * math.sin(t * 1.7 + k * 2)
        wingw = 18 * abs(math.sin(t * 12 + k))
        pen = bg_pen(img)
        pen.ellipse(fx - wingw, fyb, wingw, 16, c, "#9a6a20", 1.5)
        pen.ellipse(fx + wingw, fyb, wingw, 16, c, "#9a6a20", 1.5)
        pen.line([(fx, fyb - 10), (fx, fyb + 10)], "#5a3a20", 3)
    talking_to_bird = 12.4 < t < 14.0
    pose = dict(scarf=10 * math.sin(t * 3), eyes=blink(t, off=1.0),
                mouth=talk_mouth(t, "smile") if not talking_to_bird else ("talk" if int(t * 6) % 2 else "smile"),
                liftL=max(0, math.sin(ph)) * 22 if walking else 0,
                liftR=max(0, -math.sin(ph)) * 22 if walking else 0,
                armL=(20 + (12 * math.sin(ph) if walking else 0), 8),
                armR=(25 - (12 * math.sin(ph) if walking else 0), 30), wand_ang=25,
                look=(0.8, -0.6) if talking_to_bird or t > T_BIRD_ARRIVE else (0.6, 0.0))
    if talking_to_bird:
        pose.update(armL=(70, 60), palmL=True, eyes=blink(t, "open"))
    draw_mipo(img, x * SS, (fy + bob) * SS, s, pose)
    # blue bird joins
    if t > T_BIRD_ARRIVE - 0.9:
        u = seg(t, T_BIRD_ARRIVE - 0.9, T_BIRD_ARRIVE + 0.3)
        tx, ty = x + 190, fy - 560 + 14 * math.sin(t * 4)
        bx = lerp(W + 120, tx, u)
        byy = lerp(380, ty, u)
        nod = 10 * math.sin(t * 10) if 13.2 < t < 13.8 else 0
        draw_bird(img, bx * SS, byy * SS, 1.15 * SS, flap=t * 16, flip=False,
                  happy=12.9 < t < 13.6, nod=nod)
    z = 1.12
    cx = clamp(x + 120, 480, 600)
    return img, z, cx, 1250


def flower_head():
    """Flower/droplet position = Mipo's wand tip at the tap pose (staging)."""
    X, FY, s = 360, 1810, 1.75 * SS
    tx, ty = ch.wand_tip(X * SS, FY * SS, s, TAP_POSE)
    return X, FY, s, tx / SS + 34, ty / SS + 18


TAP_POSE = dict(armR=(78, 4), wand_ang=118)


def big_flower(img, x, y, open_u, droplet=1.0, t=0.0, p=0.0):
    pen = bg_pen(img)
    pen.line([(x, y + 40), (x - 20, y + 260), (x - 10, 1900)], "#3f9f45", 16)
    pen.rot_ellipse(x - 70, y + 220, 60, 20, -25, "#5cbf55", "#3f8f45", 2)
    pen.rot_ellipse(x + 50, y + 300, 60, 20, 25, "#5cbf55", "#3f8f45", 2)
    spread = lerp(18, 62, open_u)
    if droplet > 0 and open_u > 0.05:
        dy = 6 * math.sin(t * 3)
        r = 30 * droplet
        dc = purple("#a463ff", 1.0)
        pen.glow(x, y - 10 + dy, 120 * droplet * open_u, (190, 120, 255), 1.2 * open_u)
        pen.poly([(x, y - 10 + dy - r * 1.7), (x + r * 0.9, y - 10 + dy - r * 0.2),
                  (x, y - 10 + dy + r), (x - r * 0.9, y - 10 + dy - r * 0.2)], dc)
        pen.circle(x, y - 10 + dy, r, dc, "#6a3ac0", 2.5)
        pen.circle(x - r * 0.35, y - 10 + dy - r * 0.35, r * 0.3, "#efe0ff")
    for k in range(7):
        a = math.radians(-90 + (k - 3) * spread * 0.55)
        px, py = x + 70 * math.cos(a), y + 30 + 70 * math.sin(a)
        ang = math.degrees(a) + 90
        pen.rot_ellipse(px, py, 34, 66, ang, "#ff8fc8" if k % 2 else "#ff74b8", "#d0508f", 2.5)
    pen.ellipse(x, y + 60, 60, 26, "#ff74b8", "#d0508f", 2.5)


def scene_meadow(t):
    base, gl = bg("meadow")
    img = muted(base, 0.32).copy()
    ch.GLOWS.extend(gl)
    rainbow_only_purple_hint(img, 540, 840, 500, 30, 0.5 + 0.5 * math.sin(t * 5))
    X, FY, s, fx, fy = flower_head()
    ou = seg(t, T_FLOWER_OPEN, T_FLOWER_OPEN + 0.8)
    # deer (back), walks in from right
    du = seg(t, T_DEER_ARRIVE - 1.2, T_DEER_ARRIVE + 0.6)
    dx = lerp(W + 220, 985, du)
    draw_deer(img, dx * SS, 1560 * SS, 1.05 * SS, step=t * 8 if du < 1 else 0,
              happy=t > T_FLOWER_OPEN + 0.6, nod=6 * math.sin(t * 3) if du >= 1 else 0)
    big_flower(img, fx, fy, ou, 1.0, t)
    # bunny hops in
    bu = seg(t, T_BUNNY_ARRIVE - 1.0, T_BUNNY_ARRIVE + 0.4)
    bx = lerp(W + 140, 930, bu)
    hop = abs(math.sin(t * 9)) * 60 * (1 - bu) + (abs(math.sin(t * 4)) * 10 if bu >= 1 else 0)
    draw_bunny(img, bx * SS, (1860 - hop) * SS, 1.05 * SS, happy=t > T_FLOWER_OPEN + 0.5,
               ear=8 * math.sin(t * 5))
    # bird already with Mipo, hovering above the flower
    draw_bird(img, (fx + 80 + 20 * math.sin(t * 1.3)) * SS, (fy - 330 + 15 * math.sin(t * 4)) * SS,
              1.05 * SS, flap=t * 16, happy=t > T_FLOWER_OPEN + 0.4)
    pose = dict(scarf=9 * math.sin(t * 2.5), eyes=blink(t, off=0.5), look=(0.9, 0.2),
                mouth=talk_mouth(t, "open" if t > T_FLOWER_OPEN else "smile"),
                armL=(lerp(20, 60, seg(t, 15.3, 15.8)), 100) if t < T_FLOWER_OPEN else (150, 20),
                armR=(lerp(20, 70, seg(t, 15.4, 16.0)), 30), wand_ang=50, palmL=t > T_FLOWER_OPEN)
    if t > T_FLOWER_OPEN + 1.6:
        pose["eyes"] = "happy" if int(t * 2) % 3 == 0 else blink(t)
    bob = 6 * math.sin(t * 3)
    draw_mipo(img, X * SS, (FY + bob) * SS, s, pose)
    if ou > 0:
        for j in range(6):
            a = t * 2 + j * math.pi / 3
            sparkle(img, fx + 110 * math.cos(a) * ou, fy - 10 + 70 * math.sin(a) * ou, 9,
                    (220, 180, 255), t * 80)
    z = 1.0 + 0.1 * seg(t, 15.5, 19.5)
    return img, z, lerp(540, 600, seg(t, 15.5, 19.5)), lerp(1200, 1350, seg(t, 15.5, 19.5))


def scene_tap(t):
    p = restore_p(t)
    base, gl = bg_blend("meadow", p)
    img = muted(base, 0.32 * (1 - p)).copy()
    ch.GLOWS.extend(gl)
    sweep = seg(t, T_RESTORE_START, T_RESTORE_END)
    rainbow(img, 540, 840, 500, 30, sweep=sweep, hint=1 - sweep, only_purple=True)
    X, FY, s, fx, fy = flower_head()
    draw_deer(img, 985 * SS, 1560 * SS, 1.05 * SS, happy=t > T_TAP + 0.3,
              nod=-14 * seg(t, T_TAP + 0.6, T_TAP + 1.4))
    dropu = 1 - seg(t, T_TAP, T_TAP + 0.35)
    big_flower(img, fx, fy, 1.0, dropu, t)
    draw_bunny(img, 930 * SS, (1860 - (abs(math.sin(t * 6)) * 30 if t > T_TAP + 0.4 else 0)) * SS,
               1.05 * SS, happy=t > T_TAP + 0.3, ear=8 * math.sin(t * 5))
    draw_bird(img, (fx + 80) * SS, (fy - 330 + 15 * math.sin(t * 4)) * SS, 1.05 * SS,
              flap=t * 16, happy=t > T_TAP + 0.3)
    # tap animation
    if t < 21.2:
        u = seg(t, 20.0, 20.6)
        armR, wa = (lerp(70, 112, u), lerp(30, 50, u)), lerp(50, -5, u)
    else:
        u = seg(t, 21.2, T_TAP)
        armR = (lerp(112, TAP_POSE["armR"][0], u), lerp(50, TAP_POSE["armR"][1], u))
        wa = lerp(-5, TAP_POSE["wand_ang"], u)
    pose = dict(scarf=9 * math.sin(t * 2.5), eyes=blink(t) if t < T_TAP else "happy",
                look=(0.9, 0.3), mouth=talk_mouth(t, "open"), armR=armR, wand_ang=wa,
                armL=(40, 30) if t < T_TAP else (150, 20), palmL=t >= T_TAP,
                wand_glow=1.0 + 1.5 * seg(t, 21.6, T_TAP) * (1 - seg(t, T_TAP, T_TAP + 0.8)))
    draw_mipo(img, X * SS, FY * SS, s, pose)
    # flash at tap
    if T_TAP <= t < T_TAP + 0.6:
        k = (t - T_TAP) / 0.6
        pen = bg_pen(img)
        pen.glow(fx, fy, 260 * (0.4 + k), (230, 190, 255), 1.6 * (1 - k))
        for j in range(12):
            a = j * math.pi / 6
            sparkle(img, fx + 200 * k * math.cos(a), fy + 200 * k * math.sin(a), 14 * (1 - k) + 4,
                    (220, 170, 255) if j % 2 else (255, 236, 150), t * 120)
    # purple sparkles fly up into the sky to repaint the stripe
    if t > T_TAP:
        R = (500 - 5 * 30)
        for j in range(28):
            st = T_TAP + j * 0.06
            u = (t - st) / 1.1
            if u <= 0:
                continue
            a = math.pi + math.pi * ((j * 0.37) % 1)
            tx, ty = 540 + R * math.cos(a), 840 + R * math.sin(a)
            if u >= 1:
                continue
            ctrl = (fx + 200 * math.sin(j), fy - 500)
            x, y = bezier((fx, fy), ctrl, (tx, ty), ease(u))
            sparkle(img, x, y, 12, (200, 140, 255) if j % 3 else (255, 236, 150), t * 90 + j * 20)
    # sparkles riding the stripe front
    if 0 < sweep < 1:
        a = math.pi + math.pi * sweep
        R = 500 - 5 * 30
        sparkle(img, 540 + R * math.cos(a), 840 + R * math.sin(a), 26, (230, 200, 255), t * 100)
    zu = seg(t, 22.2, 23.4)
    z = lerp(1.32, 1.0, zu)
    cx = lerp(560, 540, zu)
    cy = lerp(1380, 960, zu)
    return img, z, cx, cy


def scene_celebrate(t):
    base, gl = bg("celebrate", 1.0)
    img = base.copy()
    ch.GLOWS.extend(gl)
    rainbow(img, 540, 900, 520, 34, sweep=1.0, only_purple=True)
    pen = bg_pen(img)
    pen.glow(540, 700, 380, (255, 250, 220), 0.25 + 0.1 * math.sin(t * 3))
    jump = lambda f, ph: abs(math.sin(t * f + ph))  # noqa: E731
    draw_deer(img, 900 * SS, (1690 - 18 * jump(4.0, 1.0)) * SS, 0.95 * SS, happy=True, nod=6 * math.sin(t * 4))
    draw_bunny(img, 180 * SS, (1860 - 50 * jump(4.4, 0.3)) * SS, 1.0 * SS, flip=True, happy=True,
               ear=10 * math.sin(t * 6))
    draw_bird(img, (540 + 300 * math.cos(t * 1.4)) * SS, (1020 + 60 * math.sin(t * 2.8)) * SS, 1.0 * SS,
              flap=t * 16, flip=math.sin(t * 1.4) > 0, happy=True)
    wave = math.sin(t * 7)
    pose = dict(scarf=12 * math.sin(t * 3), eyes="happy" if (t < 26.3 or (t % 2.2) < 0.5) else blink(t),
                look=(0, 0.2), mouth=talk_mouth(t, "open"),
                armL=(150, 15 + 25 * wave), palmL=True,
                armR=(105, 55), wand_ang=-15 + 10 * math.sin(t * 3), wand_glow=1.3 + 0.4 * math.sin(t * 5))
    hop = 22 * jump(3.6, 0.0) if t < 26.8 else 6 * math.sin(t * 3)
    draw_mipo(img, 540 * SS, (1800 - hop) * SS, 1.75 * SS, pose)
    # confetti stars
    rng = np.random.default_rng(5)
    for j in range(36):
        x0 = rng.uniform(0, W)
        sp = rng.uniform(120, 260)
        y = (rng.uniform(-400, 1900) + (t - 25) * sp) % 2100 - 120
        x = x0 + 40 * math.sin(t * 2 + j)
        col = [hexrgb(c) for c in RAINBOW][j % 6]
        sparkle(img, x, y, rng.uniform(8, 16), col, t * 100 + j * 30, glow=j % 3 == 0)
    if t > T_END_CARD:
        u = seg(t, T_END_CARD, T_END_CARD + 0.45)
        sc = 0.6 + 0.4 * u + 0.06 * math.sin(clamp((t - T_END_CARD) / 0.45) * math.pi)
        pen = bg_pen(img)
        a = u
        if a > 0:
            soft(img, lambda d: d.rounded_rectangle([90 * SS, 260 * SS, 990 * SS, 520 * SS], 60 * SS,
                                                    fill=255), (255, 255, 255), 0.82 * a)
            pen.d.rounded_rectangle([90 * SS, 260 * SS, 990 * SS, 520 * SS], 60 * SS,
                                    outline=hexrgb("#a463ff"), width=int(8 * SS * a) or 1)
        text_center(img, "See you next", 340, 76, "#7a3fd0", "#ffffff", 6, FONT_XB, sc, a)
        text_center(img, "magic moment!", 440, 76, "#ff5aa5", "#ffffff", 6, FONT_XB, sc, a)
        text_center(img, "Mipo's Magical World", 590, 40, "#ffffff", "#7a3fd0", 7, FONT_BOLD, 1.0,
                    seg(t, T_END_CARD + 0.4, T_END_CARD + 0.9))
    z = lerp(1.06, 1.0, seg(t, 25.0, 27.0))
    return img, z, 540, 960


SCENE_FN = dict(bedroom=scene_bedroom, porch=scene_porch, bridge=scene_bridge,
                meadow=scene_meadow, tap=scene_tap, celebrate=scene_celebrate)


def render_scene(key, t):
    ch.GLOWS.clear()
    img, z, cx, cy = SCENE_FN[key](t)
    img = apply_glows(img)
    vw, vh = W / z, H / z
    x0 = clamp(cx - vw / 2, 0, W - vw)
    y0 = clamp(cy - vh / 2, 0, H - vh)
    box = tuple(int(v * SS) for v in (x0, y0, x0 + vw, y0 + vh))
    return img.resize((W, H), Image.LANCZOS, box=box)


def frame(t):
    for i, (a, b, key, _) in enumerate(SCENES):
        if a <= t < b or (i == len(SCENES) - 1 and t >= a):
            out = render_scene(key, t)
            # crossfade into the next scene
            if i + 1 < len(SCENES) and t > b - XFADE / 2:
                nxt = render_scene(SCENES[i + 1][2], t)
                out = Image.blend(out, nxt, ease((t - (b - XFADE / 2)) / XFADE) * 0.5)
            if i > 0 and t < a + XFADE / 2:
                prv = render_scene(SCENES[i - 1][2], t)
                out = Image.blend(prv, out, 0.5 + 0.5 * ease((t - a) / (XFADE / 2)))
            if t < 2.6:  # title hook, drawn after the camera move so it never crops
                a = seg(t, 0.0, 0.3) * (1 - seg(t, 2.2, 2.6))
                overlay_title(out, a, 0.85 + 0.15 * ease(t / 0.3))
            return out
    raise ValueError(t)


def overlay_title(img, a, sc):
    if a <= 0:
        return
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for txt, y, size, fill, stroke, sw, font in (
            ("Mipo's Magical World", 150, 66, "#ffffff", "#7a3fd0", 9, FONT_XB),
            (TITLE, 240, 40, "#fff6c4", "#3b2416", 7, FONT_BOLD)):
        fnt = ImageFont.truetype(font, int(size * sc))
        bb = d.textbbox((0, 0), txt, font=fnt, stroke_width=sw)
        tw, th = bb[2] - bb[0], bb[3] - bb[1]
        d.text((W / 2 - tw / 2 - bb[0], y - th / 2 - bb[1]), txt, font=fnt, fill=fill,
               stroke_width=sw, stroke_fill=stroke)
    layer.putalpha(layer.getchannel("A").point(lambda v: int(v * a)))
    img.paste(layer, (0, 0), layer)


def _init(voice):
    VOICE_DUR.update(voice)


def _render_bytes(i):
    return frame(i / FPS).tobytes()


def load_voice(audio_dir):
    pth = os.path.join(audio_dir, "timing.json")
    if os.path.exists(pth):
        return json.load(open(pth))
    return {}


def main():
    if sys.argv[1] == "--stills":
        out = sys.argv[2]
        os.makedirs(out, exist_ok=True)
        VOICE_DUR.update(load_voice(os.environ.get("AUDIO_DIR", "")))
        for ts in sys.argv[3:]:
            frame(float(ts)).save(os.path.join(out, f"still_{float(ts):05.2f}.png"))
        return
    audio_dir, out = sys.argv[1], sys.argv[2]
    voice = load_voice(audio_dir)
    n = int(DURATION * FPS)
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-", "-i", os.path.join(audio_dir, "soundtrack.wav"),
           "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-shortest", out]
    ff = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    with Pool(os.cpu_count(), initializer=_init, initargs=(voice,)) as pool:
        for i, buf in enumerate(pool.imap(_render_bytes, range(n), chunksize=4)):
            ff.stdin.write(buf)
            if i % 48 == 0:
                print(f"frame {i}/{n}", flush=True)
    ff.stdin.close()
    ff.wait()
    print("wrote", out)


if __name__ == "__main__":
    main()
