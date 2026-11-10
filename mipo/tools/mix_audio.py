#!/usr/bin/env python3
"""Build separate audio tracks + a final mix for an episode (or one scene).

Inputs (approved files only, inside the episode folder):
  audio/voice/<LINE>.mp3 (+ .json with word timing from tts_elevenlabs.py)
  audio/sfx/<SFX_ID>.mp3
  audio/music.(wav|mp3)            optional
Speaker -> track comes from production/voices.json ("narration" or "dialogue").

Outputs (regenerated each run; build products, not approved assets):
  audio/build/<scope>/narration.wav, dialogue.wav, music.wav, sfx.wav   (48 kHz stereo, same length)
  audio/build/<scope>/mix.wav       voice-ducked music + SFX, loudness-normalized (-14 LUFS)
  audio/build/<scope>/subtitles.srt captions timed to the real audio
  audio/build/<scope>/report.json   where every line/cue landed + warnings
<scope> is "episode" or "scene_NN".

Sync: a line with a "sync_point" (e.g. L08 "MAGIC" at 22.05 s) is shifted so that word starts
exactly at that time, using the take's word timing. Other lines start at their scripted time.

Usage: python3 tools/mix_audio.py production/episodes/ep01_missing_rainbow_color [--scene 1]
"""
import argparse
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import ROOT, duration, find_media, load_json, need_ffmpeg, save_json, scene_of  # noqa: E402

SR = 48000


def srt_time(s):
    ms = int(round(max(0.0, s) * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    sec, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{sec:02d},{ms:03d}"


def word_offset(meta, word):
    al = (meta or {}).get("alignment") or {}
    chars = al.get("characters") or []
    starts = al.get("character_start_times_seconds") or []
    text = "".join(chars).upper()
    i = text.find(word.upper())
    if i < 0 or i >= len(starts):
        return None
    return float(starts[i])


def build_stem(items, length, out):
    """items: [(path, start_s, gain_db, fade_out_s or None)]. Writes a stereo WAV of `length` s."""
    args = ["ffmpeg", "-v", "error", "-y"]
    fc = [f"anullsrc=r={SR}:cl=stereo,atrim=duration={length:.3f}[base]"]
    labels = ["[base]"]
    for k, (path, start, gain, fade) in enumerate(items):
        args += ["-i", path]
        ms = max(0, int(round(start * 1000)))
        chain = f"[{k}:a]aformat=sample_rates={SR}:channel_layouts=stereo,volume={gain}dB"
        if fade:
            chain += f",afade=t=out:st={max(0.0, fade[0]):.3f}:d={fade[1]:.3f}"
        chain += f",adelay={ms}|{ms}[s{k}]"
        fc.append(chain)
        labels.append(f"[s{k}]")
    fc.append(f"{''.join(labels)}amix=inputs={len(labels)}:normalize=0:duration=first,"
              f"atrim=duration={length:.3f}[out]")
    args += ["-filter_complex", ";".join(fc), "-map", "[out]", "-c:a", "pcm_s16le", "-ar", str(SR), out]
    subprocess.run(args, check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("episode_dir")
    ap.add_argument("--scene", type=int)
    ap.add_argument("--tolerance", type=float, default=0.15, help="allowed overrun past must_end (s)")
    args = ap.parse_args()
    need_ffmpeg()
    ep_dir = os.path.abspath(args.episode_dir)
    ep = load_json(os.path.join(ep_dir, "episode.json"))
    cast = load_json(os.path.join(ROOT, "production", "voices.json"))["cast"]
    mixcfg = ep.get("audio_mix", {})
    if args.scene:
        sc = next(s for s in ep["scenes"] if s["id"] == args.scene)
        w0, w1, scope = sc["start"], sc["end"], f"scene_{args.scene:02d}"
    else:
        w0, w1, scope = 0.0, ep["format"]["duration"], "episode"
    length = w1 - w0
    out = os.path.join(ep_dir, "audio", "build", scope)
    os.makedirs(out, exist_ok=True)

    report = {"scope": scope, "window": [w0, w1], "lines": [], "sfx": [], "warnings": []}
    tracks = {"narration": [], "dialogue": []}
    subs = []
    lines = [ln for ln in ep["narration"] if w0 <= ln["start"] < w1]
    for i, ln in enumerate(lines):
        f = find_media(os.path.join(ep_dir, "audio", "voice", ln["id"]))
        if not f:
            report["warnings"].append(f"{ln['id']}: no approved voice file (audio/voice/{ln['id']}.mp3)")
            continue
        meta_path = os.path.splitext(f)[0] + ".json"
        meta = load_json(meta_path) if os.path.exists(meta_path) else None
        d = duration(f)
        start = ln["start"]
        sp = ln.get("sync_point")
        if sp:
            off = word_offset(meta, sp["word"])
            if off is None:
                report["warnings"].append(f"{ln['id']}: no word timing for '{sp['word']}', using scripted start")
            else:
                start = sp["time"] - off
        end = start + d
        if end > ln["must_end"] + args.tolerance:
            report["warnings"].append(f"{ln['id']}: ends at {end:.2f}s, later than must_end {ln['must_end']:.2f}s "
                                      f"(pick a shorter take or raise speed in voices.json)")
        if start < ln["start"] - 0.6:
            report["warnings"].append(f"{ln['id']}: sync shifted start {ln['start'] - start:.2f}s earlier")
        role = cast.get(ln.get("speaker", "mipo"), {}).get("role", "dialogue")
        tracks[role].append((f, start - w0, 0.0, None))
        report["lines"].append({"id": ln["id"], "speaker": ln.get("speaker"), "track": role,
                                "start": round(start, 3), "end": round(end, 3), "file": os.path.relpath(f, ep_dir)})
        subs.append((start - w0, end - w0, ln["text"]))
    for a, b in zip(report["lines"], report["lines"][1:]):
        if a["end"] > b["start"] + 0.02:
            report["warnings"].append(f"{a['id']} overlaps {b['id']} by {a['end'] - b['start']:.2f}s")

    sfx_items = []
    for c in ep.get("sfx", []):
        if not (w0 <= c["t"] < w1):
            continue
        f = find_media(os.path.join(ep_dir, "audio", "sfx", c["id"]))
        if not f:
            report["warnings"].append(f"{c['id']}: no approved SFX file (audio/sfx/{c['id']}.mp3)")
            continue
        d = duration(f)
        keep = min(d, w1 - c["t"])
        fade = (keep - 0.15, 0.15) if keep < d else None
        sfx_items.append((f, c["t"] - w0, c.get("gain_db", -8), fade))
        report["sfx"].append({"id": c["id"], "t": c["t"], "file": os.path.relpath(f, ep_dir)})

    music_items = []
    m = find_media(os.path.join(ep_dir, "audio", "music"))
    if m:
        # trim the music to the window by pre-cutting a temp file
        cut = os.path.join(out, "_music_cut.wav")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{w0:.3f}", "-t", f"{length:.3f}", "-i", m,
                        "-af", f"afade=t=in:d=0.3,afade=t=out:st={max(0, length - 0.6):.3f}:d=0.6",
                        "-ar", str(SR), "-ac", "2", cut], check=True)
        music_items.append((cut, 0.0, mixcfg.get("music_gain_db", -16), None))
    else:
        report["warnings"].append("no audio/music file: music track is silent")

    stems = {}
    for name, items in (("narration", tracks["narration"]), ("dialogue", tracks["dialogue"]),
                        ("music", music_items), ("sfx", sfx_items)):
        stems[name] = os.path.join(out, f"{name}.wav")
        build_stem(items, length, stems[name])

    lufs = mixcfg.get("target_lufs", -14)
    tp = mixcfg.get("true_peak_db", -1.5)
    fc = ("[0:a][1:a]amix=inputs=2:normalize=0[voice];[voice]asplit=2[v1][v2];"
          "[2:a][v2]sidechaincompress=threshold=0.03:ratio=6:attack=20:release=350[duck];"
          f"[v1][duck][3:a]amix=inputs=3:normalize=0,atrim=duration={length:.3f},"
          f"loudnorm=I={lufs}:TP={tp}:LRA=11,aresample={SR}[mix]")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", stems["narration"], "-i", stems["dialogue"],
                    "-i", stems["music"], "-i", stems["sfx"], "-filter_complex", fc, "-map", "[mix]",
                    "-c:a", "pcm_s16le", "-ar", str(SR), "-t", f"{length:.3f}", os.path.join(out, "mix.wav")],
                   check=True)
    if os.path.exists(os.path.join(out, "_music_cut.wav")):
        os.remove(os.path.join(out, "_music_cut.wav"))

    srt = []
    for k, (a, b, txt) in enumerate(subs):
        nxt = subs[k + 1][0] if k + 1 < len(subs) else length
        srt.append(f"{k + 1}\n{srt_time(a)} --> {srt_time(min(b + 0.25, nxt - 0.05, length))}\n{txt}\n")
    with open(os.path.join(out, "subtitles.srt"), "w", encoding="utf-8") as f:
        f.write("\n".join(srt))
    save_json(os.path.join(out, "report.json"), report)

    print(f"wrote {os.path.relpath(out, ep_dir)}/  (narration, dialogue, music, sfx, mix, subtitles, report)")
    for ln in report["lines"]:
        print(f"  {ln['id']:4s} {ln['track']:9s} {ln['start']:6.2f}-{ln['end']:6.2f}s")
    for c in report["sfx"]:
        print(f"  {c['id']:5s} sfx       {c['t']:6.2f}s")
    for w in report["warnings"]:
        print("  WARNING:", w)


if __name__ == "__main__":
    main()
