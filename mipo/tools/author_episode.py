#!/usr/bin/env python3
"""Expand a human-friendly episode outline (outline.json) into the pipeline's episode.json.

outline.json = episode metadata + sequences -> shots. Each shot has a duration (5 or 10 s fits
most image-to-video models), what we see (start_frame / motion / end_frame), the wand state,
Mipo's expression, which friends are in frame, and its lines and SFX with offsets inside the shot.

This tool computes every timestamp, numbers shots (scene ids), lines (L001...) and SFX (SFX001...),
gives each line a `must_end` window, marks whether purple is restored yet, writes YouTube chapters,
and warns when a line is unlikely to fit at a calm, child-friendly pace.

Usage: python3 tools/author_episode.py production/episodes/<ep>      (reads outline.json)
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import load_json, save_json  # noqa: E402

WAND = {
    "bedside": "His star wand is NOT in his hands: it lies glowing on the bedside table.",
    "flying": "The golden star wand floats through the air into Mipo's LEFT hand (viewer's right).",
    "left": "He holds the golden star wand in his LEFT hand (viewer's right when he faces the camera).",
    "tap": "He holds the golden star wand in his LEFT hand and gently taps with its star tip.",
    "none": "",
}
WPS = 2.2          # calm words per second for ages 2-7
PAUSE = 0.45       # extra seconds per "..." or sentence break


def est_seconds(text):
    words = len(re.findall(r"[A-Za-z']+", text))
    breaks = text.count("...") + len(re.findall(r"[.!?](\s|$)", text))
    return words / WPS + breaks * PAUSE * 0.5 + 0.3


def main(ep_dir):
    o = load_json(os.path.join(ep_dir, "outline.json"))
    t = 0.0
    scenes, lines, sfx, chapters, warnings = [], [], [], [], []
    restored = False
    n = 0
    for seq in o["sequences"]:
        chapters.append((t, seq["chapter"]))
        for sh in seq["shots"]:
            n += 1
            start, end = round(t, 3), round(t + sh["dur"], 3)
            purple_now = restored
            wand = WAND[sh.get("wand", "left")]
            scene = {
                "id": n, "start": start, "end": end, "name": sh["name"], "sequence": seq["id"],
                "location": sh.get("location", seq.get("location", "")),
                "camera": sh["camera"], "camera_motion": sh.get("camera_motion", sh["camera"]),
                "mipo_in_frame": sh.get("mipo", True),
                "expression": sh.get("expression", ""),
                "friends": sh.get("friends", []),
                "beats": sh.get("beats", [sh["motion"]]),
                "start_frame": sh["start_frame"], "motion": sh["motion"],
                "end_frame": sh.get("end_frame", ""),
                "continuity": (f"{seq['title']}. Purple is "
                               f"{'RESTORED everywhere (full rainbow with purple stripe, purple castle roofs, crystals and flowers)' if purple_now else 'MISSING (rainbow has no purple stripe; purple things are soft grey; world slightly muted)'}."
                               + (" " + sh["continuity"] if sh.get("continuity") else "")),
                "wand": wand if sh.get("mipo", True) else "",
                "negative_extra": sh.get("negative_extra", "") + ("" if purple_now else ", purple stripe in rainbow, saturated purple"),
            }
            scenes.append(scene)
            for ln in sh.get("lines", []):
                off, spk, text, delivery = ln[:4]
                item = {"speaker": spk, "start": round(start + off, 3), "text": text, "delivery": delivery,
                        "scene": n}
                if len(ln) > 4 and ln[4]:
                    item["sync_point"] = {"word": ln[4], "time": round(start + ln[5], 3)}
                lines.append(item)
            for fx in sh.get("sfx", []):
                off, dur, gain, prompt = fx
                sfx.append({"t": round(start + off, 3), "dur": dur, "gain_db": gain, "prompt": prompt,
                            "cue": prompt, "scene": n})
            if sh.get("restores_purple"):
                restored = True
            t = end
    total = round(t, 3)
    lines.sort(key=lambda x: x["start"])
    for i, ln in enumerate(lines):
        ln["id"] = f"L{i + 1:03d}"
        nxt = lines[i + 1]["start"] if i + 1 < len(lines) else total
        ln["must_end"] = round(min(nxt - 0.1, total - 0.05), 3)
        need = est_seconds(ln["text"])
        if ln["start"] + need > ln["must_end"] + 0.05:
            warnings.append(f"{ln['id']} (scene {ln['scene']}) needs ~{need:.1f}s but has "
                            f"{ln['must_end'] - ln['start']:.1f}s: \"{ln['text']}\"")
    for i, c in enumerate(sorted(sfx, key=lambda x: x["t"])):
        c["id"] = f"SFX{i + 1:03d}"
    ordered = []
    for ln in lines:
        ordered.append({k: ln[k] for k in ("id", "speaker", "start", "must_end", "text", "delivery")
                        if k in ln} | ({"sync_point": ln["sync_point"]} if "sync_point" in ln else {}))
    ep = {k: v for k, v in o.items() if k not in ("sequences",)}
    ep["format"] = dict(o["format"], duration=total)
    ep["chapters"] = [{"t": round(a, 3), "title": b} for a, b in chapters]
    ep["sequences"] = [{k: v for k, v in s.items() if k != "shots"} for s in o["sequences"]]
    ep["scenes"] = scenes
    ep["narration"] = ordered
    ep["sfx"] = sorted(sfx, key=lambda x: x["t"])
    if o.get("end_card"):
        ec = dict(o["end_card"])
        name = ec.pop("shot")
        sc = next((x for x in scenes if x["name"] == name), None)
        if sc is None:
            sys.exit(f"end_card shot '{name}' not found")
        ec["start"] = round(sc["start"] + ec.pop("offset", 0.0), 3)
        ep["end_card"] = ec
    save_json(os.path.join(ep_dir, "episode.json"), ep)
    m, s = divmod(total, 60)
    print(f"episode.json: {len(scenes)} shots, {len(ordered)} lines, {len(sfx)} SFX cues, "
          f"{int(m)}:{s:04.1f} total, {len(chapters)} chapters")
    for w in warnings:
        print("  FIT WARNING:", w)
    return warnings


if __name__ == "__main__":
    main(os.path.abspath(sys.argv[1]))
