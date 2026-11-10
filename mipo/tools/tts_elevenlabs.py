#!/usr/bin/env python3
"""Generate Mipo's narration lines with the ElevenLabs text-to-speech API.

One file per line and take:  <episode>/audio/voice/takes/L01_take1.mp3 ...
Listen, pick the best take, and copy it to <episode>/audio/voice/L01.mp3
(that's what tools/assemble.py uses).

Setup (see production/SETUP.md):
  export ELEVENLABS_API_KEY=...        # or put it in mipo/.env
  export ELEVENLABS_VOICE_ID=...       # the Mipo voice you designed/selected

Usage:
  python3 tools/tts_elevenlabs.py production/episodes/ep01_missing_rainbow_color --takes 3
  python3 tools/tts_elevenlabs.py <ep> --line L08 --takes 5    # redo one line
  python3 tools/tts_elevenlabs.py <ep> --use-alt L03           # use a line's optional "alt" text
  python3 tools/tts_elevenlabs.py <ep> --dry-run               # show what would be sent

NOTE: written against ElevenLabs' public REST API (POST /v1/text-to-speech/{voice_id}).
It could not be run from the build environment (no network access to ElevenLabs),
so test it with --line L01 --takes 1 first. Standard library only.
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API = "https://api.elevenlabs.io/v1/text-to-speech/{voice}?output_format=mp3_44100_128"


def load_env():
    path = os.path.join(ROOT, ".env")
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def synth(text, voice, key, args):
    body = {
        "text": text,
        "model_id": args.model,
        "voice_settings": {
            "stability": args.stability,
            "similarity_boost": args.similarity,
            "style": args.style,
            "use_speaker_boost": True,
        },
    }
    req = urllib.request.Request(API.format(voice=voice), data=json.dumps(body).encode(),
                                 headers={"xi-api-key": key, "Content-Type": "application/json",
                                          "Accept": "audio/mpeg"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            msg = e.read().decode(errors="replace")[:300]
            if e.code in (429, 500, 502, 503) and attempt < 3:
                time.sleep(2 ** (attempt + 1))
                continue
            sys.exit(f"ElevenLabs error {e.code}: {msg}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("episode_dir")
    ap.add_argument("--takes", type=int, default=3)
    ap.add_argument("--line", action="append", help="only these line ids (repeatable)")
    ap.add_argument("--use-alt", action="append", default=[], help="use the alt text for these ids")
    ap.add_argument("--model", default=os.environ.get("ELEVENLABS_MODEL", "eleven_multilingual_v2"))
    ap.add_argument("--stability", type=float, default=0.45)
    ap.add_argument("--similarity", type=float, default=0.80)
    ap.add_argument("--style", type=float, default=0.30)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    load_env()
    ep = json.load(open(os.path.join(args.episode_dir, "episode.json"), encoding="utf-8"))
    out = os.path.join(args.episode_dir, "audio", "voice", "takes")
    os.makedirs(out, exist_ok=True)
    key = os.environ.get("ELEVENLABS_API_KEY")
    voice = os.environ.get("ELEVENLABS_VOICE_ID")
    if not args.dry_run and (not key or not voice):
        sys.exit("Set ELEVENLABS_API_KEY and ELEVENLABS_VOICE_ID (env or mipo/.env).")

    for ln in ep["narration"]:
        if args.line and ln["id"] not in args.line:
            continue
        text = ln.get("alt", ln["text"]) if ln["id"] in args.use_alt else ln["text"]
        for k in range(1, args.takes + 1):
            path = os.path.join(out, f"{ln['id']}_take{k}.mp3")
            if os.path.exists(path):
                print("skip (exists)", path)
                continue
            if args.dry_run:
                print(f"[dry-run] {ln['id']} take {k}: {text!r} -> {path}")
                continue
            data = synth(text, voice, key, args)
            open(path, "wb").write(data)
            print("wrote", path)
    print("Next: listen, then copy the best take of each line to audio/voice/<ID>.mp3")


if __name__ == "__main__":
    main()
