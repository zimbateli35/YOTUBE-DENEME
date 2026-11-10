#!/usr/bin/env python3
"""Assemble an episode (or a single scene) from approved 3D clips + audio into a
1080x1920 YouTube Shorts MP4.

Inside the episode folder:
  clips/scene_01.mp4 ... scene_06.mp4      approved clips (any size/fps)
  audio/build/<scope>/mix.wav              from tools/mix_audio.py (preferred)
  audio/build/<scope>/subtitles.srt        captions timed to the real audio
Fallback when no mix exists (full episode only): audio/voice/<LINE>.*, audio/music.*, audio/sfx.*

Clips are scaled/cropped to fill 9:16, conformed to the scene duration (trimmed or last
frame held) and joined with short crossfades. The end card is drawn by FFmpeg, not by AI.

Usage:
  python3 tools/assemble.py <ep> --subs --endcard          # full 30 s episode
  python3 tools/assemble.py <ep> --scene 1 --subs           # first 5 s scene only
  python3 tools/assemble.py <ep> --scene 1 --allow-missing  # timing test with a slate
Never overwrites: final/<slug>[_sceneNN]_vN.mp4 gets a new version number each run.
"""
import argparse
import glob
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import find_media, load_json, need_ffmpeg  # noqa: E402

DEFAULT_FONT_CANDIDATES = [
    "C:/Windows/Fonts/arialbd.ttf",
    "/System/Library/Fonts/Supplemental/Arial Rounded Bold.ttf",
    "/Library/Fonts/Arial Rounded Bold.ttf",
    "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]


def esc_path(p):
    return p.replace("\\", "/").replace(":", "\\:").replace("'", "\\'")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("episode_dir")
    ap.add_argument("--scene", type=int, help="assemble only this scene")
    ap.add_argument("--xfade", type=float, default=0.3, help="crossfade seconds between scenes (0 = cut)")
    ap.add_argument("--subs", action="store_true", help="burn in captions")
    ap.add_argument("--endcard", action="store_true", help="draw the end-card text from episode.json")
    ap.add_argument("--font", default=None, help="TTF/OTF for the end card")
    ap.add_argument("--music-db", type=float, default=-16.0, help="fallback mode: music level")
    ap.add_argument("--allow-missing", action="store_true",
                    help="fill missing clips with a placeholder slate (timing tests)")
    args = ap.parse_args()

    need_ffmpeg()
    ep_dir = os.path.abspath(args.episode_dir)
    ep = load_json(os.path.join(ep_dir, "episode.json"))
    W, H, FPS = ep["format"]["width"], ep["format"]["height"], ep["format"]["fps"]
    if args.scene:
        scenes = [s for s in ep["scenes"] if s["id"] == args.scene]
        if not scenes:
            sys.exit(f"no scene {args.scene}")
        scope, X = f"scene_{args.scene:02d}", 0.0
    else:
        scenes, scope, X = ep["scenes"], "episode", max(0.0, args.xfade)
    w0 = scenes[0]["start"]
    total = scenes[-1]["end"] - w0

    inputs, fc, vlabels = [], [], []
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

    build = os.path.join(ep_dir, "audio", "build", scope)
    post = []
    if args.subs:
        srt = os.path.join(build, "subtitles.srt")
        if not os.path.exists(srt):
            srt = os.path.join(ep_dir, "generated", "subtitles.srt") if scope == "episode" else None
        if srt:
            post.append(f"subtitles='{esc_path(srt)}':force_style='Fontsize=13,Bold=1,Outline=2,MarginV=60'")
        else:
            print("WARNING: no subtitles for this scene (run tools/mix_audio.py --scene N first)")
    ec = ep.get("end_card")
    if args.endcard and ec and w0 <= ec["start"] < w0 + total:
        font = args.font or next((f for f in DEFAULT_FONT_CANDIDATES if os.path.exists(f)), None)
        if not font:
            sys.exit("no font found; pass --font /path/to/font.ttf")
        t0 = ec["start"] - w0
        alpha = f"if(lt(t,{t0}),0,min(1,(t-{t0})/0.4))"
        texts = ec["text"] + [ec.get("subtitle", "")]
        for j, txt in enumerate(texts):
            if not txt:
                continue
            main_line = j < len(ec["text"])
            size = 92 if main_line else 44
            color = ["0x7A3FD0", "0xFF5AA5"][j % 2] if main_line else "white"
            y = 300 + j * 115 + (0 if main_line else 40)
            safe = txt.replace("'", "\u2019").replace(":", "\\:")
            post.append(f"drawtext=fontfile='{esc_path(font)}':text='{safe}':"
                        f"fontsize={size}:fontcolor={color}:borderw={8 if main_line else 5}:"
                        f"bordercolor={'white' if main_line else '0x7A3FD0'}:"
                        f"x=(w-text_w)/2:y={y}:alpha='{alpha}'")
    vfinal = cur
    if post:
        fc.append(f"[{cur}]{','.join(post)}[vout]")
        vfinal = "vout"

    idx = len(vlabels)
    mix = os.path.join(build, "mix.wav")
    if os.path.exists(mix):
        inputs += ["-i", mix]
        fc.append(f"[{idx}:a]aformat=sample_rates=48000:channel_layouts=stereo,apad,"
                  f"atrim=duration={total:.3f}[aout]")
        print("audio:", os.path.relpath(mix, ep_dir))
    elif scope != "episode":
        print(f"WARNING: no {os.path.relpath(mix, ep_dir)}; run tools/mix_audio.py --scene {args.scene}. "
              f"Using silence.")
        fc.append(f"anullsrc=r=48000:cl=stereo,atrim=duration={total:.3f}[aout]")
    else:
        fc += legacy_audio(ep, ep_dir, inputs, idx, total, args.music_db)

    os.makedirs(os.path.join(ep_dir, "final"), exist_ok=True)
    stem = ep["slug"] + ("" if scope == "episode" else f"_scene{args.scene:02d}")
    n = 1 + len(glob.glob(os.path.join(ep_dir, "final", f"{stem}_v*.mp4")))
    out = os.path.join(ep_dir, "final", f"{stem}_v{n}.mp4")
    while os.path.exists(out):
        n += 1
        out = os.path.join(ep_dir, "final", f"{stem}_v{n}.mp4")
    cmd = ["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", ";".join(fc),
           "-map", f"[{vfinal}]", "-map", "[aout]", "-t", f"{total:.3f}",
           "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-pix_fmt", "yuv420p", "-r", str(FPS),
           "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", out]
    subprocess.run(cmd, check=True)
    print("wrote", out)


def legacy_audio(ep, ep_dir, inputs, idx, total, music_db):
    """Full-episode fallback when tools/mix_audio.py has not been run."""
    fc, labels, missing = [], [], []
    for ln in ep["narration"]:
        f = find_media(os.path.join(ep_dir, "audio", "voice", ln["id"]))
        if not f:
            missing.append(ln["id"])
            continue
        inputs += ["-i", f]
        ms = int(round(ln["start"] * 1000))
        fc.append(f"[{idx}:a]aformat=sample_rates=48000:channel_layouts=stereo,adelay={ms}|{ms}[n{idx}]")
        labels.append(f"[n{idx}]")
        idx += 1
    if missing:
        print("WARNING: no voice file for", ", ".join(missing))
    if labels:
        fc.append(f"{''.join(labels)}amix=inputs={len(labels)}:normalize=0,apad=whole_dur={total}[voice]")
    else:
        fc.append(f"anullsrc=r=48000:cl=stereo,atrim=duration={total}[voice]")
    fc.append("[voice]asplit=2[voice_a][voice_sc]")
    beds = []
    music = find_media(os.path.join(ep_dir, "audio", "music"))
    if music:
        inputs += ["-i", music]
        fc.append(f"[{idx}:a]aformat=sample_rates=48000:channel_layouts=stereo,volume={music_db}dB,"
                  f"atrim=duration={total},afade=t=out:st={total - 1.2}:d=1.2[mus]")
        fc.append("[mus][voice_sc]sidechaincompress=threshold=0.03:ratio=6:attack=20:release=350[ducked]")
        beds.append("ducked")
        idx += 1
    else:
        fc.append("[voice_sc]anullsink")
    sfx = find_media(os.path.join(ep_dir, "audio", "sfx"))
    if sfx:
        inputs += ["-i", sfx]
        fc.append(f"[{idx}:a]aformat=sample_rates=48000:channel_layouts=stereo,atrim=duration={total}[sfx]")
        beds.append("sfx")
    mixin = "[voice_a]" + "".join(f"[{b}]" for b in beds)
    fc.append(f"{mixin}amix=inputs={1 + len(beds)}:normalize=0,atrim=duration={total},"
              f"loudnorm=I=-14:TP=-1.5:LRA=11[aout]")
    return fc


if __name__ == "__main__":
    main()
