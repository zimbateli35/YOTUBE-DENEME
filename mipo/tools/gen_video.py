#!/usr/bin/env python3
"""Animate an APPROVED scene start frame into a 9:16 clip through an image-to-video API.

Provider: Runway API (image_to_video). Kling, Veo, Luma or Hailuo can be used by hand with the
same files: start frame = frames/scene_NN_start.png, prompt = generated/prompts/scene_NN_video.txt.

  scene <ep> N [--takes 2] [--yes]     -> clips/raw/scene_NN_takeK.mp4 (+ .json)
  approve <ep> N TAKE                  -> clips/scene_NN.mp4 (never overwrites)

Safety: dry run unless --yes. The Runway API is billed in credits on your Runway developer
account (no free API credits), so --yes spends money. Approved clips are never overwritten.

Credentials (mipo/.env): RUNWAYML_API_SECRET   optional: RUNWAY_BASE_URL, RUNWAY_MODEL
"""
import argparse
import base64
import datetime
import os
import shutil
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import (ApiError, confirm_gate, http, load_env, load_json, next_free,  # noqa: E402
                     save_json, secret)

API_VERSION = "2024-11-06"


def scene_job(ep_dir, n, args):
    ep = load_json(os.path.join(ep_dir, "episode.json"))
    sc = next((s for s in ep["scenes"] if s["id"] == n), None)
    if not sc:
        sys.exit(f"no scene {n}")
    frame = os.path.join(ep_dir, "frames", f"scene_{n:02d}_start.png")
    if not os.path.exists(frame):
        sys.exit(f"No approved start frame {os.path.relpath(frame, ep_dir)}. Generate and approve one with "
                 f"tools/gen_image.py first (it always uses the approved Mipo references).")
    prompt = open(os.path.join(ep_dir, "generated", "prompts", f"scene_{n:02d}_video.txt"),
                  encoding="utf-8").read().strip()
    if len(prompt) > 1000:
        sys.exit(f"video prompt is {len(prompt)} chars; Runway accepts 1000. Shorten it in episode.json.")
    dur = 5 if sc["end"] - sc["start"] <= 5 else 10
    model = os.environ.get("RUNWAY_MODEL", args.model)
    print(f"Scene {n}: {sc['name']}   model {model}   ratio 720:1280   {dur}s   takes {args.takes}")
    print(f"Start frame: {os.path.relpath(frame, ep_dir)}\nPrompt: {len(prompt)} chars")
    confirm_gate(args.yes, "call the video API (spends credits on your Runway account)")
    key = secret("RUNWAYML_API_SECRET")
    base = os.environ.get("RUNWAY_BASE_URL", "https://api.dev.runwayml.com").rstrip("/")
    hdr = {"Authorization": f"Bearer {key}", "X-Runway-Version": API_VERSION}
    data_uri = "data:image/png;base64," + base64.b64encode(open(frame, "rb").read()).decode()
    for k in range(args.takes):
        body = {"model": model, "promptImage": data_uri, "promptText": prompt,
                "ratio": "720:1280", "duration": dur, "seed": args.seed + k}
        task = http("POST", f"{base}/v1/image_to_video", hdr, body, secrets=[key])
        tid = task["id"]
        print(f"  take {k + 1}: task {tid} submitted")
        t0 = time.time()
        while True:
            st = http("GET", f"{base}/v1/tasks/{tid}", hdr, secrets=[key])
            if st.get("status") == "SUCCEEDED":
                break
            if st.get("status") in ("FAILED", "CANCELLED"):
                sys.exit(f"  task {tid} {st.get('status')}: {st.get('failure', '')}")
            if time.time() - t0 > args.timeout:
                sys.exit(f"  task {tid} still running after {args.timeout}s; check the Runway dashboard")
            time.sleep(args.poll)
        url = st["output"][0]
        path, _ = next_free(os.path.join(ep_dir, "clips", "raw", f"scene_{n:02d}_take{{n}}.mp4"))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(http("GET", url, raw=True, timeout=600))
        save_json(path[:-4] + ".json", {"scene": n, "task": tid, "model": model, "seed": body["seed"],
                                        "start_frame": os.path.relpath(frame, ep_dir),
                                        "created_utc": datetime.datetime.utcnow().isoformat(timespec="seconds")})
        print("  wrote", os.path.relpath(path, ep_dir))
    print("Next: QC each take (character first, then motion), then: approve <ep> N TAKE")


def approve(ep_dir, n, take):
    src = os.path.join(ep_dir, "clips", "raw", f"scene_{n:02d}_take{take}.mp4")
    dst = os.path.join(ep_dir, "clips", f"scene_{n:02d}.mp4")
    if not os.path.exists(src):
        sys.exit(f"not found: {src}")
    if os.path.exists(dst):
        sys.exit(f"{os.path.relpath(dst, ep_dir)} already exists. Approved clips are never overwritten.")
    shutil.copy2(src, dst)
    print("approved", os.path.relpath(dst, ep_dir))


def main():
    load_env()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("step", choices=["scene", "approve"])
    ap.add_argument("episode_dir")
    ap.add_argument("scene_no", type=int)
    ap.add_argument("take", type=int, nargs="?")
    ap.add_argument("--takes", type=int, default=2)
    ap.add_argument("--model", default="gen4_turbo")
    ap.add_argument("--seed", type=int, default=7001)
    ap.add_argument("--poll", type=float, default=5.0)
    ap.add_argument("--timeout", type=float, default=900.0)
    ap.add_argument("--yes", action="store_true")
    a = ap.parse_args()
    ep_dir = os.path.abspath(a.episode_dir)
    try:
        if a.step == "approve":
            if a.take is None:
                sys.exit("usage: approve <ep> N TAKE")
            approve(ep_dir, a.scene_no, a.take)
        else:
            scene_job(ep_dir, a.scene_no, a)
    except ApiError as e:
        sys.exit(f"Video API error {e}")


if __name__ == "__main__":
    main()
