#!/usr/bin/env python3
"""Assemble an episode from approved 3D clips + narration + music into a
1080x1920 YouTube Shorts MP4.

Expected layout inside the episode folder:
  clips/scene_01.mp4 ... scene_06.mp4   approved AI-generated clips (any size/fps)
  audio/voice/L01.(wav|mp3) ...         chosen narration takes (one per line id)
  audio/music.(wav|mp3)                 optional background music
  audio/sfx.(wav|mp3)                   optional pre-mixed SFX track (30 s)

Each clip is scaled/cropped to fill 9:16, conformed to the scene's duration
(trimmed, or the last frame held), joined with short crossfades, and each
narration line is placed at its timestamp from episode.json. Music is ducked
under the voice; the mix is normalized to about -14 LUFS for YouTube.

Usage:
  python3 tools/assemble.py production/episodes/ep01_missing_rainbow_color
  python3 tools/assemble.py <ep> --subs --endcard --xfade 0.3
Never overwrites: the output gets a new version number each run (final/<slug>_vN.mp4).
Needs ffmpeg on PATH. Standard library only.
"""
import argparse
import glob
import json
import os
import shutil
import subprocess
import sys

DEFAULT_FONT_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Arial Rounded Bold.ttf",
    "/Library/Fonts/Arial Rounded Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]


def find(base):
    for ext in (".wav", ".mp3", ".m4a", ".aac", ".flac"):
        if os.path.exists(base + ext):
            return base + ext
    return None


def esc_path(p):
    return p.replace("\\", "/").replace(":", "\\:").replace("'", "\\'")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("episode_dir")
    ap.add_argument("--xfade", type=float, default=0.3, help="crossfade seconds between scenes (0 = cut)")
    ap.add_argument("--subs", action="store_true", help="burn in generated/subtitles.srt")
    ap.add_argument("--endcard", action="store_true", help="draw the end-card text from episode.json")
    ap.add_argument("--font", default=None, help="TTF/OTF for the end card")
    ap.add_argument("--music-db", type=float, default=-16.0, help="music level before ducking")
    ap.add_argument("--allow-missing", action="store_true",
                    help="fill missing clips with a placeholder slate (for timing tests)")
    args = ap.parse_args()

    if not shutil.which("ffmpeg"):
        sys.exit("ffmpeg not found on PATH (see production/SETUP.md)")
    ep_dir = os.path.abspath(args.episode_dir)
    ep = json.load(open(os.path.join(ep_dir, "episode.json"), encoding="utf-8"))
    W, H, FPS = ep["format"]["width"], ep["format"]["height"], ep["format"]["fps"]
    total = ep["format"]["duration"]
    X = max(0.0, args.xfade)

    inputs, fc = [], []
    vlabels = []
    scenes = ep["scenes"]
    for i, sc in enumerate(scenes):
        clip = os.path.join(ep_dir, "clips", f"scene_{sc['id']:02d}.mp4")
        dur = sc["end"] - sc["start"] + (X if i < len(scenes) - 1 else 0)
        if os.path.exists(clip):
            inputs += ["-i", clip]
        elif args.allow_missing:
            inputs += ["-f", "lavfi", "-i", f"color=c=0x334455:s={W}x{H}:r={FPS}:d={dur}"]
        else:
            sys.exit(f"missing {clip} (use --allow-missing for a timing test)")
        k = len(vlabels)
        fc.append(f"[{k}:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
                  f"fps={FPS},setsar=1,format=yuv420p,tpad=stop_mode=clone:stop_duration={dur},"
                  f"trim=duration={dur},setpts=PTS-STARTPTS[v{k}]")
        vlabels.append(f"v{k}")

    cur, acc = vlabels[0], scenes[0]["end"] - scenes[0]["start"]
    for k in range(1, len(vlabels)):
        if X > 0:
            fc.append(f"[{cur}][{vlabels[k]}]xfade=transition=fade:duration={X}:offset={acc:.3f}[x{k}]")
        else:
            fc.append(f"[{cur}][{vlabels[k]}]concat=n=2:v=1:a=0[x{k}]")
        cur = f"x{k}"
        acc += scenes[k]["end"] - scenes[k]["start"]

    post = []
    if args.subs:
        srt = os.path.join(ep_dir, "generated", "subtitles.srt")
        post.append(f"subtitles='{esc_path(srt)}':force_style='Fontsize=13,Bold=1,Outline=2,MarginV=60'")
    if args.endcard:
        font = args.font or next((f for f in DEFAULT_FONT_CANDIDATES if os.path.exists(f)), None)
        if not font:
            sys.exit("no font found; pass --font /path/to/font.ttf")
        ec = ep["end_card"]
        t0 = ec["start"]
        alpha = f"if(lt(t,{t0}),0,min(1,(t-{t0})/0.4))"
        lines = ec["text"] + [ec.get("subtitle", "")]
        for j, txt in enumerate(lines):
            if not txt:
                continue
            size = 92 if j < len(ec["text"]) else 44
            color = ["0x7A3FD0", "0xFF5AA5"][j % 2] if j < len(ec["text"]) else "white"
            y = 300 + j * 115 + (40 if j >= len(ec["text"]) else 0)
            safe = txt.replace("'", "\u2019").replace(":", "\\:")
            post.append(f"drawtext=fontfile='{esc_path(font)}':text='{safe}':"
                        f"fontsize={size}:fontcolor={color}:borderw={8 if size > 50 else 5}:"
                        f"bordercolor={'white' if size > 50 else '0x7A3FD0'}:"
                        f"x=(w-text_w)/2:y={y}:alpha='{alpha}'")
    vfinal = cur
    if post:
        fc.append(f"[{cur}]{','.join(post)}[vout]")
        vfinal = "vout"

    # ---- audio ----
    alabels = []
    nvid = len(vlabels)
    idx = nvid
    voice_dir = os.path.join(ep_dir, "audio", "voice")
    missing = []
    for ln in ep["narration"]:
        f = find(os.path.join(voice_dir, ln["id"]))
        if not f:
            missing.append(ln["id"])
            continue
        inputs += ["-i", f]
        ms = int(round(ln["start"] * 1000))
        fc.append(f"[{idx}:a]aformat=sample_rates=48000:channel_layouts=stereo,adelay={ms}|{ms}[n{idx}]")
        alabels.append(f"n{idx}")
        idx += 1
    if missing:
        print("WARNING: no narration file for", ", ".join(missing))
    if alabels:
        fc.append(f"{''.join('[' + a + ']' for a in alabels)}amix=inputs={len(alabels)}:normalize=0,"
                  f"apad=whole_dur={total}[voice]")
    else:
        fc.append(f"anullsrc=r=48000:cl=stereo,atrim=duration={total}[voice]")
    fc.append("[voice]asplit=2[voice_a][voice_sc]")
    beds = []
    music = find(os.path.join(ep_dir, "audio", "music"))
    if music:
        inputs += ["-i", music]
        fc.append(f"[{idx}:a]aformat=sample_rates=48000:channel_layouts=stereo,volume={args.music_db}dB,"
                  f"atrim=duration={total},afade=t=out:st={total - 1.2}:d=1.2[mus]")
        fc.append("[mus][voice_sc]sidechaincompress=threshold=0.03:ratio=6:attack=20:release=350[ducked]")
        beds.append("ducked")
        idx += 1
    else:
        fc.append("[voice_sc]anullsink")
    sfx = find(os.path.join(ep_dir, "audio", "sfx"))
    if sfx:
        inputs += ["-i", sfx]
        fc.append(f"[{idx}:a]aformat=sample_rates=48000:channel_layouts=stereo,atrim=duration={total}[sfx]")
        beds.append("sfx")
        idx += 1
    mixin = "[voice_a]" + "".join(f"[{b}]" for b in beds)
    fc.append(f"{mixin}amix=inputs={1 + len(beds)}:normalize=0,atrim=duration={total},"
              f"loudnorm=I=-14:TP=-1.5:LRA=11[aout]")

    os.makedirs(os.path.join(ep_dir, "final"), exist_ok=True)
    n = 1 + len(glob.glob(os.path.join(ep_dir, "final", f"{ep['slug']}_v*.mp4")))
    out = os.path.join(ep_dir, "final", f"{ep['slug']}_v{n}.mp4")
    while os.path.exists(out):
        n += 1
        out = os.path.join(ep_dir, "final", f"{ep['slug']}_v{n}.mp4")
    cmd = ["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", ";".join(fc),
           "-map", f"[{vfinal}]", "-map", "[aout]", "-t", str(total),
           "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-pix_fmt", "yuv420p", "-r", str(FPS),
           "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", out]
    subprocess.run(cmd, check=True)
    print("wrote", out)


if __name__ == "__main__":
    main()
