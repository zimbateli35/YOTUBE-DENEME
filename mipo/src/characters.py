"""Locked character models for Mipo's Magical World.

Every shot draws Mipo through draw_mipo() with the single MIPO palette
below, so face, hair, goggles, scarf, jacket, star shirt, jeans, boots,
backpack + bedroll and wand are identical in every frame. Only the pose
(arms, eyes, mouth, legs) changes between shots.

Reference: reference/cover_*.png (the channel banner).
"""
import math

from PIL import ImageDraw

# ---------------------------------------------------------------------------
# LOCKED PALETTE - do not edit per scene.
# ---------------------------------------------------------------------------
MIPO = {
    "outline": "#3b2416",
    "hair": "#5b3520", "hair_hi": "#80522f",
    "skin": "#f9d2b2", "skin_sh": "#efab8c", "cheek": "#f7a99e", "freckle": "#c98a66",
    "iris": "#7a4318", "iris_dark": "#3f220c", "brow": "#4d2c1a",
    "goggle_rim": "#c08640", "goggle_rim_dark": "#7a5022",
    "lens": "#2f9cf0", "lens_hi": "#a6e0ff", "strap": "#6b4423",
    "scarf": "#dc2a22", "scarf_sh": "#a91b16",
    "jacket": "#f2e7d1", "jacket_sh": "#dccbab", "cuff": "#6e4a30",
    "shirt": "#4a2c22", "star": "#ffd23a", "star_edge": "#f0961c",
    "belt": "#6e4424", "buckle": "#e0b24a",
    # Pants follow the channel banner (authoritative): dark brown cargo pants.
    # (The v1 preview MP4 was rendered with blue jeans "#4a78bf" before the
    # banner was declared the single source of truth.)
    "jeans": "#5a4636", "jeans_sh": "#45352a", "jeans_cuff": "#6e5a48",
    "boot": "#9c5c2c", "boot_dark": "#74421f", "sole": "#ead6aa", "lace": "#f0d39a",
    "pack": "#9a6232", "pack_dark": "#76461f", "bedroll": "#cf9049", "bedroll_dark": "#9e6630",
    "wand": "#6b3e1f", "wand_band": "#d9a548",
    "mouth": "#8e2b2b", "tongue": "#f07c84",
}

GLOWS = []  # (x, y, radius, (r,g,b), strength) in canvas pixels


def star_points(cx, cy, ro, ri, rot=0.0, n=5):
    pts = []
    for k in range(2 * n):
        r = ro if k % 2 == 0 else ri
        a = math.radians(rot) - math.pi / 2 + k * math.pi / n
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def ellipse_points(cx, cy, rx, ry, ang=0.0, n=28):
    ca, sa = math.cos(math.radians(ang)), math.sin(math.radians(ang))
    out = []
    for k in range(n):
        t = 2 * math.pi * k / n
        x, y = rx * math.cos(t), ry * math.sin(t)
        out.append((cx + x * ca - y * sa, cy + x * sa + y * ca))
    return out


class Pen:
    """Draws in local 'design units' mapped to canvas pixels."""

    def __init__(self, img, ox, oy, s, flip=False):
        self.img = img
        self.d = ImageDraw.Draw(img)
        self.ox, self.oy, self.s, self.flip = ox, oy, s, flip

    def p(self, x, y):
        return (self.ox + (-x if self.flip else x) * self.s, self.oy + y * self.s)

    def w(self, w):
        return max(1, int(round(w * self.s)))

    def box(self, x0, y0, x1, y1):
        a, b = self.p(x0, y0), self.p(x1, y1)
        return [min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1])]

    def ellipse(self, cx, cy, rx, ry, fill, outline=None, ow=3):
        self.d.ellipse(self.box(cx - rx, cy - ry, cx + rx, cy + ry), fill=fill,
                       outline=outline, width=self.w(ow) if outline else 0)

    def circle(self, cx, cy, r, fill, outline=None, ow=3):
        self.ellipse(cx, cy, r, r, fill, outline, ow)

    def poly(self, pts, fill, outline=None, ow=3):
        P = [self.p(x, y) for x, y in pts]
        self.d.polygon(P, fill=fill)
        if outline:
            self.d.line(P + [P[0]], fill=outline, width=self.w(ow), joint="curve")

    def rot_ellipse(self, cx, cy, rx, ry, ang, fill, outline=None, ow=3):
        if self.flip:
            ang = -ang
        self.poly(ellipse_points(cx, cy, rx, ry, ang), fill, outline, ow)

    def rrect(self, x0, y0, x1, y1, r, fill, outline=None, ow=3):
        self.d.rounded_rectangle(self.box(x0, y0, x1, y1), radius=self.w(r), fill=fill,
                                 outline=outline, width=self.w(ow) if outline else 0)

    def line(self, pts, fill, w, round_ends=True):
        P = [self.p(x, y) for x, y in pts]
        self.d.line(P, fill=fill, width=self.w(w), joint="curve")
        if round_ends:
            r = w * self.s / 2
            for x, y in (P[0], P[-1]):
                self.d.ellipse([x - r, y - r, x + r, y + r], fill=fill)

    def limb(self, pts, fill, w, outline, ow=3):
        self.line(pts, outline, w + 2 * ow)
        self.line(pts, fill, w)

    def glow(self, x, y, r, color, strength=1.0):
        cx, cy = self.p(x, y)
        GLOWS.append((cx, cy, r * self.s, color, strength))


# ---------------------------------------------------------------------------
# MIPO
# ---------------------------------------------------------------------------
DEFAULT_POSE = dict(
    armL=(15, 5), armR=(15, 5),   # (shoulder angle from down, elbow bend), outward +
    wand=True, wand_ang=10,       # absolute angle of wand, 0 = up, + = clockwise
    eyes="open", look=(0.0, 0.0), mouth="smile",
    liftL=0.0, liftR=0.0, scarf=0.0, palmL=False, wand_glow=1.0,
)

UPPER, FORE = 60, 56
SHOULDER_L, SHOULDER_R = (-60, -252), (60, -252)


def _arm_points(side, a1, a2):
    sx, sy = SHOULDER_L if side == "L" else SHOULDER_R
    sg = -1 if side == "L" else 1

    def d(a):
        return (sg * math.sin(math.radians(a)), math.cos(math.radians(a)))

    d1 = d(a1)
    ex, ey = sx + UPPER * d1[0], sy + UPPER * d1[1]
    d2 = d(a1 + a2)
    hx, hy = ex + FORE * d2[0], ey + FORE * d2[1]
    return (sx, sy), (ex, ey), (hx, hy), d2


def wand_tip(ox, oy, s, pose, flip=False):
    """Canvas position of the wand star for a pose (for staging props)."""
    P = dict(DEFAULT_POSE, **pose)
    _, _, (hx, hy), _ = _arm_points("R", *P["armR"])
    a = math.radians(P["wand_ang"])
    tx, ty = hx + 108 * math.sin(a), hy - 108 * math.cos(a)
    return (ox + (-tx if flip else tx) * s, oy + ty * s)


def draw_mipo(img, ox, oy, s, pose=None, flip=False):
    P = dict(DEFAULT_POSE, **(pose or {}))
    C = MIPO
    O = C["outline"]
    pen = Pen(img, ox, oy, s, flip)

    # --- backpack + rolled sleeping mat (behind body, viewer's left) -------
    pen.rrect(-120, -262, -46, -148, 16, C["pack"], O)
    pen.rrect(-114, -214, -74, -158, 9, C["pack_dark"], O, 2.5)
    pen.rrect(-114, -214, -74, -198, 6, C["pack"], O, 2.5)
    pen.rrect(-98, -206, -90, -196, 2, C["buckle"])
    pen.rrect(-124, -302, -38, -256, 22, C["bedroll"], O)
    pen.circle(-112, -279, 22, C["bedroll"], O)
    for r in (16, 10, 4):
        pen.d.arc(pen.box(-112 - r, -279 - r, -112 + r, -279 + r), 200, 520,
                  fill=C["bedroll_dark"], width=pen.w(3))

    # --- legs (blue jeans) + boots ------------------------------------------
    for side, lift in (("L", P["liftL"]), ("R", P["liftR"])):
        sg = -1 if side == "L" else 1
        y = -lift
        x0, x1 = (-52, -8) if side == "L" else (8, 52)
        pen.rrect(x0, -160 + y * 0.3, x1, -50 + y, 10, C["jeans"], O)
        pen.line([(sg * 30, -140 + y * 0.3), (sg * 30, -80 + y)], C["jeans_sh"], 3, False)
        pen.rrect(x0 - 4, -76 + y, x1 + 4, -56 + y, 6, C["jeans_cuff"], O, 2.5)
        bx0, bx1 = (-58, -6) if side == "L" else (6, 58)
        pen.rrect(bx0, -64 + y, bx1, -10 + y, 12, C["boot"], O)
        fx0, fx1 = (-68, -2) if side == "L" else (2, 68)
        pen.ellipse((fx0 + fx1) / 2, -18 + y, 33, 16, C["boot"], O)
        pen.rrect(fx0 - 2, -10 + y, fx1 + 2, 2 + y, 5, C["sole"], O, 2.5)
        pen.rrect(bx0, -66 + y, bx1, -56 + y, 4, C["boot_dark"], O, 2)
        cx = (bx0 + bx1) / 2
        for ly in (-48, -38, -28):
            pen.line([(cx - 10, ly + y), (cx + 10, ly + y + 4)], C["lace"], 3)

    # --- shirt + star + belt --------------------------------------------------
    pen.rrect(-42, -264, 42, -146, 10, C["shirt"], O)
    pen.poly(star_points(0, -208, 31, 14), C["star"], C["star_edge"], 3.5)
    pen.circle(-6, -216, 4, "#fff3b0")
    pen.rrect(-58, -164, 58, -144, 4, C["belt"], O, 2.5)
    pen.rrect(-12, -168, 12, -140, 3, C["belt"], C["buckle"], 4)

    # --- cream explorer jacket (open) ----------------------------------------
    for sg in (-1, 1):
        pts = [(sg * 64, -262), (sg * 34, -272), (sg * 24, -214), (sg * 22, -150),
               (sg * 70, -150), (sg * 72, -205)]
        pen.poly(pts, C["jacket"], O)
        pen.line([(sg * 58, -240), (sg * 62, -170)], C["jacket_sh"], 4, False)
        pen.rrect(min(sg * 22, sg * 72), -158, max(sg * 22, sg * 72), -138, 5, C["cuff"], O, 2.5)
        pen.circle(sg * 32, -232, 3.5, C["cuff"])
        pen.circle(sg * 31, -195, 3.5, C["cuff"])
    pen.line([(24, -212), (23, -142)], C["buckle"], 2.5, False)
    # backpack straps with gold buckles
    for sg in (-1, 1):
        pen.line([(sg * 52, -262), (sg * 44, -170)], C["pack_dark"], 12, False)
        pen.rrect(sg * 48 - 8, -218, sg * 48 + 8, -204, 2, C["pack_dark"], C["buckle"], 2.5)

    # --- scarf (neck wrap + flowing tail with fringe) -------------------------
    f = P["scarf"]
    tail = [(16, -262), (70 + f * 0.5, -250 + f * 0.3), (120 + f, -226 + f * 0.6),
            (126 + f, -196 + f), (114 + f, -190 + f), (104 + f, -200 + f * 0.8),
            (64 + f * 0.4, -226), (20, -244)]
    pen.poly(tail, C["scarf"], O)
    for k in range(5):
        u = k / 4
        x0 = 126 + f - u * 12
        y0 = -196 + f + u * 6
        pen.line([(x0, y0), (x0 + 6, y0 + 14)], C["scarf_sh"], 3)

    # --- arms -----------------------------------------------------------------
    hands = {}
    for side in ("L", "R"):
        a1, a2 = P["armL"] if side == "L" else P["armR"]
        S, E, Hd, d2 = _arm_points(side, a1, a2)
        cuff0 = (Hd[0] - d2[0] * 22, Hd[1] - d2[1] * 22)
        cuff1 = (Hd[0] - d2[0] * 9, Hd[1] - d2[1] * 9)
        pen.limb([S, E, cuff0], C["jacket"], 38, O)
        pen.limb([cuff0, cuff1], C["cuff"], 36, O)
        hands[side] = (Hd, d2)

    # wand behind the gripping hand
    (hR, _) = hands["R"]
    if P["wand"]:
        a = math.radians(P["wand_ang"])
        dx, dy = math.sin(a), -math.cos(a)
        base = (hR[0] - dx * 20, hR[1] - dy * 20)
        tip = (hR[0] + dx * 90, hR[1] + dy * 90)
        pen.limb([base, tip], C["wand"], 10, O, 2.5)
        pen.limb([(hR[0] + dx * 70, hR[1] + dy * 70), (hR[0] + dx * 80, hR[1] + dy * 80)],
                 C["wand_band"], 13, O, 2)

    for side in ("L", "R"):
        (Hd, d2) = hands[side]
        pen.circle(Hd[0], Hd[1], 18, C["skin"], O)
        if side == "L" and P["palmL"]:
            pen.circle(Hd[0] + (-1 if not flip else -1) * d2[1] * 12, Hd[1] - 6, 7, C["skin"], O, 2.5)
            pen.circle(Hd[0] + d2[0] * 14, Hd[1] + d2[1] * 14, 12, C["skin"], O, 2.5)

    if P["wand"]:
        a = math.radians(P["wand_ang"])
        sx, sy = hR[0] + math.sin(a) * 108, hR[1] - math.cos(a) * 108
        g = P["wand_glow"]
        pen.glow(sx, sy, 75, (255, 220, 90), 0.85 * g)
        pen.poly(star_points(sx, sy, 32, 15, P["wand_ang"]), C["star"], C["star_edge"], 4)
        pen.poly(star_points(sx, sy, 15, 7, P["wand_ang"]), "#fff6c4")

    # --- head -----------------------------------------------------------------
    _head(pen, P)
    return pen


def _head(pen, P):
    C = MIPO
    O = C["outline"]
    # back hair + ragged side tufts
    pen.ellipse(0, -372, 98, 94, C["hair"], O)
    for sg in (-1, 1):
        pen.poly([(sg * 90, -390), (sg * 104, -330), (sg * 88, -344), (sg * 92, -306),
                  (sg * 74, -336)], C["hair"], O)
    # ears
    for sg in (-1, 1):
        pen.circle(sg * 82, -350, 18, C["skin"], O)
        pen.circle(sg * 84, -350, 8, C["skin_sh"])
    # face
    pen.ellipse(0, -350, 82, 80, C["skin"], O)
    # fringe
    fringe = [(-86, -372), (-86, -410), (-62, -440), (-20, -452), (30, -450), (70, -432),
              (90, -398), (86, -366), (72, -390), (60, -372), (46, -404), (26, -382),
              (10, -410), (-12, -386), (-30, -410), (-48, -382), (-62, -404), (-76, -368)]
    pen.poly(fringe, C["hair"], O)
    for a, b in (((-50, -424), (-38, -396)), ((10, -436), (14, -404)), ((50, -420), (58, -396))):
        pen.line([a, b], C["hair_hi"], 5)
    # top tufts
    pen.poly([(-22, -462), (-6, -494), (6, -466), (24, -488), (28, -460), (8, -452)], C["hair"], O)
    # goggle strap
    pen.limb([(-96, -398), (-62, -428), (0, -440), (62, -428), (96, -398)], C["strap"], 15, O, 2.5)
    pen.limb([(-96, -398), (-92, -366)], C["strap"], 13, O, 2.5)
    # goggles (bronze rims, blue lenses)
    for sg in (-1, 1):
        cx, cy = sg * 41, -438
        pen.circle(cx, cy, 38, C["goggle_rim"], O, 3.5)
        pen.circle(cx, cy, 30, C["goggle_rim_dark"])
        pen.circle(cx, cy, 26, C["lens"])
        pen.circle(cx - 6, cy - 6, 13, C["lens_hi"])
        pen.circle(cx - 12, cy - 12, 5, "#ffffff")
        for k in range(6):
            a = math.radians(30 + k * 60)
            pen.circle(cx + 34 * math.cos(a), cy + 34 * math.sin(a), 2.2, C["goggle_rim_dark"])
    pen.rrect(-8, -446, 8, -430, 3, C["goggle_rim"], O, 2.5)
    # brows
    for sg in (-1, 1):
        pen.line([(sg * 54, -390), (sg * 34, -400), (sg * 14, -393)], C["brow"], 7)
    # eyes
    lx, ly = P["look"]
    for sg in (-1, 1):
        ex, ey = sg * 33, -354
        if P["eyes"] == "open":
            pen.ellipse(ex, ey, 23, 27, "#ffffff", O, 3)
            ix, iy = ex + lx * 6, ey + ly * 6 + 2
            pen.circle(ix, iy, 18, C["iris"])
            pen.circle(ix, iy + 2, 11, C["iris_dark"])
            pen.circle(ix - 7, iy - 8, 6.5, "#ffffff")
            pen.circle(ix + 7, iy + 7, 3, "#ffffff")
            pen.line([(ex + sg * 20, ey - 18), (ex + sg * 28, ey - 24)], O, 4)
        elif P["eyes"] == "closed":
            pen.line([(ex - 20, ey - 2), (ex, ey + 8), (ex + 20, ey - 2)], O, 5)
        else:  # happy ^ ^
            pen.line([(ex - 20, ey + 6), (ex, ey - 10), (ex + 20, ey + 6)], O, 6)
    # nose, cheeks, freckles
    pen.ellipse(0, -324, 12, 9, C["skin_sh"])
    for sg in (-1, 1):
        pen.ellipse(sg * 56, -318, 18, 11, C["cheek"])
        for fx, fy in ((44, -328), (54, -334), (62, -326), (50, -320)):
            pen.circle(sg * fx, fy, 2.3, C["freckle"])
    # mouth
    m = P["mouth"]
    if m == "open":
        pen.d.pieslice(pen.box(-28, -320, 28, -270), 0, 180, fill=C["mouth"], outline=O, width=pen.w(3))
        pen.rrect(-20, -297, 20, -290, 2, "#ffffff")
        pen.ellipse(0, -282, 13, 7, C["tongue"])
    elif m == "talk":
        pen.d.pieslice(pen.box(-20, -310, 20, -280), 0, 180, fill=C["mouth"], outline=O, width=pen.w(3))
        pen.ellipse(0, -287, 9, 4, C["tongue"])
    elif m == "o":
        pen.ellipse(0, -296, 11, 13, C["mouth"], O, 3)
    elif m == "yawn":
        pen.ellipse(0, -294, 16, 20, C["mouth"], O, 3)
        pen.ellipse(0, -284, 10, 6, C["tongue"])
    else:  # smile
        pen.line([(-24, -302), (0, -288), (24, -302)], O, 5)


# ---------------------------------------------------------------------------
# FRIENDS (match banner: blue bird, white bunny, spotted baby deer)
# ---------------------------------------------------------------------------
def _eye(pen, x, y, rx, ry, look=(0, 0), happy=False, outline="#2b1a10"):
    if happy:
        pen.line([(x - rx, y + 4), (x, y - ry * 0.6), (x + rx, y + 4)], outline, 5)
        return
    pen.ellipse(x, y, rx, ry, "#3a2412")
    pen.circle(x - rx * 0.3 + look[0] * 2, y - ry * 0.35, rx * 0.38, "#ffffff")
    pen.circle(x + rx * 0.35, y + ry * 0.35, rx * 0.16, "#ffffff")


def draw_bird(img, ox, oy, s, flap=0.0, flip=False, happy=False, nod=0.0):
    """Round blue bird, center at (ox, oy). flap in radians phase."""
    pen = Pen(img, ox, oy + nod * s, s, flip)
    O = "#24527f"
    wing = 25 + 35 * math.sin(flap)
    for sg in (-1, 1):
        pen.rot_ellipse(sg * 50, -6, 38, 17, sg * wing, "#3b8ad6", O, 3)
        pen.rot_ellipse(sg * 60, -10, 22, 10, sg * wing, "#7cc4ff")
    pen.poly([(-14, 30), (0, 58), (14, 30)], "#3b8ad6", O, 3)
    pen.ellipse(0, 0, 48, 44, "#4fa7ee", O, 3)
    pen.ellipse(0, 16, 32, 25, "#f4f8ff")
    for k, (x, y, r) in enumerate(((-6, -50, 8), (4, -54, 9), (12, -48, 7))):
        pen.ellipse(x, y, r * 0.7, r * 1.3, "#4fa7ee", O, 2)
    _eye(pen, -17, -8, 10, 13, happy=happy)
    _eye(pen, 17, -8, 10, 13, happy=happy)
    pen.poly([(-9, 4), (9, 4), (0, 17)], "#ffa63a", "#c86a10", 2)
    for sg in (-1, 1):
        pen.ellipse(sg * 30, 6, 8, 5, "#ffb0b8")


def draw_bunny(img, ox, oy, s, flip=False, happy=False, ear=0.0):
    pen = Pen(img, ox, oy, s, flip)
    O = "#a99c94"
    W = "#fdfaf6"
    pen.circle(46, -40, 18, W, O)                 # tail
    for sg, a in ((-1, -12 + ear), (1, 14 - ear)):  # ears
        pen.rot_ellipse(sg * 22, -232, 17, 52, a, W, O)
        pen.rot_ellipse(sg * 22, -228, 8, 38, a, "#f6b2c2")
    pen.ellipse(0, -62, 52, 62, W, O)
    for sg in (-1, 1):
        pen.ellipse(sg * 30, -8, 25, 12, W, O)
        pen.ellipse(sg * 20, -96, 14, 12, W, O)
    pen.circle(0, -152, 50, W, O)
    _eye(pen, -19, -158, 10, 13, happy=happy)
    _eye(pen, 19, -158, 10, 13, happy=happy)
    pen.ellipse(0, -138, 7, 5, "#f58aa0")
    pen.line([(-10, -128), (0, -124), (10, -128)], "#8a6a62", 3)
    for sg in (-1, 1):
        pen.ellipse(sg * 34, -134, 10, 6, "#ffc2cc")


def draw_deer(img, ox, oy, s, flip=False, happy=False, step=0.0, nod=0.0):
    """Baby deer facing LEFT by default (flip=True faces right)."""
    pen = Pen(img, ox, oy, s, flip)
    O = "#7d4a20"
    B = "#da8b3e"
    L = "#c47a35"
    for k, x in enumerate((-56, -34, 38, 60)):
        lift = max(0, math.sin(step + k * math.pi / 2)) * 8
        pen.rrect(x - 7, -134, x + 7, -12 - lift, 6, L, O, 2.5)
        pen.rrect(x - 8, -16 - lift, x + 8, 0 - lift, 4, "#4a2e1c")
    pen.ellipse(82, -176, 14, 18, "#fff2dc", O, 2.5)
    pen.ellipse(0, -150, 84, 46, B, O)
    pen.ellipse(-6, -128, 60, 18, "#f2c891")
    for x, y in ((-10, -170), (14, -176), (36, -164), (-30, -160), (52, -178), (4, -156)):
        pen.circle(x, y, 5, "#fff6e8")
    hy = nod
    pen.limb([(-48, -168), (-70, -230 + hy)], B, 36, O)
    # ears + antlers
    pen.rot_ellipse(-122, -296 + hy, 32, 14, -35, B, O)
    pen.rot_ellipse(-118, -296 + hy, 20, 7, -35, "#f6b2bc")
    pen.rot_ellipse(-34, -300 + hy, 32, 14, 35, B, O)
    pen.rot_ellipse(-38, -300 + hy, 20, 7, 35, "#f6b2bc")
    for pts in (((-92, -306), (-100, -346)), ((-97, -330), (-112, -340)),
                ((-62, -308), (-56, -348)), ((-58, -330), (-42, -340))):
        pen.line([(x, y + hy) for x, y in pts], "#6b4423", 7)
    pen.ellipse(-78, -268 + hy, 48, 44, B, O)
    pen.ellipse(-100, -250 + hy, 26, 19, "#f7ddb6", O, 2.5)
    pen.ellipse(-116, -256 + hy, 8, 6, "#2b1a10")
    _eye(pen, -92, -278 + hy, 11, 14, happy=happy)
    _eye(pen, -58, -280 + hy, 11, 14, happy=happy)
    pen.line([(-108, -240 + hy), (-98, -236 + hy), (-90, -240 + hy)], "#6b3a20", 3)
    pen.ellipse(-46, -258 + hy, 9, 6, "#ffb4a8")
