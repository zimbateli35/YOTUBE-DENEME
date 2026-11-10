#!/usr/bin/env python3
"""Animate an APPROVED scene start frame into a 9:16 clip through an image-to-video API.

Provider: Runway API (image_to_video). One Runway account reaches several models
(gen4.5, gen4_turbo, veo3.1, veo3.1_fast, kling3.0_*, hailuo3, seedance2 ...). Uses the official
`runwayml` Python SDK when installed (pip install runwayml), else plain HTTPS.
Web apps (Kling, Hailuo, Luma...) work by hand with the same files:
start frame = frames/scene_NN_start.png, prompt = generated/prompts/scene_NN_video.txt.

  scene <ep> N [--takes 2] [--yes]     -> clips/raw/scene_NN_takeK.mp4 (+ .json)
  approve <ep> N TAKE                  -> clips/scene_NN.mp4 (never overwrites)

Safety: dry run unless --yes. The Runway API is billed in credits on your Runway developer
account (no free API credits), so --yes spends money. Approved clips are never overwritten.

Credentials (mipo/.env): RUNWAYML_API_SECRET   optional: RUNWAYML_BASE_URL, RUNWAY_MODEL
Ratio/duration rules per model were taken from runwayml SDK 5.24; for other models pass --ratio
and check the model's allowed durations in the Runway docs.
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

# model -> (ratio for 9:16, ratio for 16:9, allowed durations or None for 2..10)
MODEL_RULES = {
    "gen4.5": ("720:1280", "1280:720", None),
    "gen4_turbo": ("720:1280", "1280:720", (5, 10)),
    "veo3.1": ("1080:1920", "1920:1080", (4, 6, 8)),
    "veo3.1_fast": ("1080:1920", "1920:1080", (4, 6, 8)),
}


def pick_duration(model, seconds):
    allowed = MODEL_RULES.get(model, (None, None, None))[2]
    if allowed is None:
        return max(2, min(10, int(round(seconds))))
    longer = [d for d in allowed if d >= seconds]
    return min(longer) if longer else max(allowed)


def run_sdk(params, timeout):
    from runwayml import RunwayML  # official SDK
    client = RunwayML()  # reads RUNWAYML_API_SECRET / RUNWAYML_BASE_URL
    task = client.image_to_video.create(**params).wait_for_task_output(timeout=timeout)
    return task.id, task.output[0]


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
    model = os.environ.get("RUNWAY_MODEL", args.model)
    dur = pick_duration(model, sc["end"] - sc["start"])
    vertical = ep["format"]["height"] > ep["format"]["width"]
    ratio = args.ratio or MODEL_RULES.get(model, (None, None, None))[0 if vertical else 1]
    if not ratio:
        sys.exit(f"no ratio rule for model {model}: pass --ratio (see the model's allowed ratios)")
    try:
        import runwayml  # noqa: F401
        via = "runwayml SDK"
    except ImportError:
        via = "HTTPS (pip install runwayml to use the official SDK)"
    print(f"Scene {n}: {sc['name']}   model {model}   ratio {ratio}   {dur}s   takes {args.takes}   via {via}")
    print(f"Start frame: {os.path.relpath(frame, ep_dir)}\nPrompt: {len(prompt)} chars")
    confirm_gate(args.yes, "call the video API (spends credits on your Runway account)")
    key = secret("RUNWAYML_API_SECRET")
    base = os.environ.get("RUNWAYML_BASE_URL", os.environ.get("RUNWAY_BASE_URL", "https://api.dev.runwayml.com")).rstrip("/")
    os.environ["RUNWAYML_BASE_URL"] = base
    hdr = {"Authorization": f"Bearer {key}", "X-Runway-Version": API_VERSION}
    raw_img = open(frame, "rb").read()
    if len(raw_img) > 5 * 1024 * 1024:
        sys.exit("start frame is over 5 MB (data URI limit): save it as a smaller PNG/JPEG")
    data_uri = "data:image/png;base64," + base64.b64encode(raw_img).decode()
    for k in range(args.takes):
        seed = args.seed + k
        if via.startswith("runwayml"):
            params = dict(model=model, prompt_image=data_uri, prompt_text=prompt, ratio=ratio,
                          duration=dur, seed=seed)
            try:
                tid, url = run_sdk(params, args.timeout)
            except Exception as e:  # SDK raises TaskFailedError / APIStatusError etc.
                sys.exit(f"  Runway task failed: {type(e).__name__}: {str(e)[:300].replace(key, '***')}")
            print(f"  take {k + 1}: task {tid} done")
        else:
            body = {"model": model, "promptImage": data_uri, "promptText": prompt,
                    "ratio": ratio, "duration": dur, "seed": seed}
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
        save_json(path[:-4] + ".json", {"scene": n, "task": tid, "model": model, "seed": seed, "ratio": ratio,
                                        "duration": dur,
                                        "start_frame": os.path.relpath(frame, ep_dir),
                                        "created_utc": datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat(timespec="seconds")})
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
    ap.add_argument("--model", default="gen4.5")
    ap.add_argument("--ratio", help="override the ratio (required for models without a built-in rule)")
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
