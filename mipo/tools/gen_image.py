#!/usr/bin/env python3
"""Generate Mipo reference images through an image API, always with the locked references.

Provider: OpenAI Images "edits" endpoint (accepts several reference images + a prompt).
Any other reference-capable tool (Midjourney, Gemini, Leonardo, Kling...) can be used by hand
with the same prompt files; see production/TEST_01_CHARACTER_LOCK_AND_SCENE1.md.

Steps
  turnaround <ep>            front/side/back sheet   refs: MASTER banner
  scene <ep> N               scene N start frame     refs: MASTER banner + APPROVED turnaround
  approve <ep> FILE --as turnaround | --as scene N   copy a candidate to its approved path

Safety: dry run unless --yes; outputs go to candidates/ folders with new numbers; approved files
are never overwritten. The OpenAI API is billed per image (no free API credits), so --yes
spends money on your OpenAI account.

Credentials (mipo/.env): OPENAI_API_KEY   optional: OPENAI_BASE_URL, OPENAI_IMAGE_MODEL
"""
import argparse
import base64
import datetime
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import (ROOT, ApiError, confirm_gate, http, load_env, load_json, multipart,  # noqa: E402
                     next_free, save_json, secret)

APPROVED_TURNAROUND = os.path.join(ROOT, "reference", "approved", "mipo_turnaround_v1.png")


def master_banner():
    ch = load_json(os.path.join(ROOT, "production", "character", "mipo_character.json"))
    rel = ch["authority"][0].split()[0]
    path = os.path.join(ROOT, rel)
    if not os.path.exists(path):
        sys.exit(f"MASTER reference missing: {rel}")
    return path


def read_prompt(ep_dir, name):
    p = os.path.join(ep_dir, "generated", "prompts", name)
    if not os.path.exists(p):
        sys.exit(f"missing {p}: run tools/build_package.py first")
    return open(p, encoding="utf-8").read().strip()


def generate(ep_dir, step, scene, args):
    refs = [master_banner()]
    if step == "turnaround":
        prompt = read_prompt(ep_dir, "00_character_sheet.txt")
        neg = read_prompt(ep_dir, "negative.txt")
        size = "1536x1024"
        out_pat = os.path.join(ROOT, "reference", "candidates", "mipo_turnaround_cand{n}.png")
    else:
        if not os.path.exists(APPROVED_TURNAROUND):
            sys.exit("No approved turnaround yet (reference/approved/mipo_turnaround_v1.png). "
                     "Every scene must use it: run the 'turnaround' step and approve one first.")
        refs.append(APPROVED_TURNAROUND)
        prompt = read_prompt(ep_dir, f"scene_{scene:02d}_image.txt")
        neg = read_prompt(ep_dir, f"scene_{scene:02d}_negative.txt")
        size = "1024x1536"
        out_pat = os.path.join(ep_dir, "frames", "candidates", f"scene_{scene:02d}_start_cand{{n}}.png")
    full = (f"{prompt}\nUse the attached reference image(s) as the exact character design: same face, "
            f"hair, outfit, colors and proportions. Do NOT redesign him.\nAvoid: {neg}")
    model = os.environ.get("OPENAI_IMAGE_MODEL", args.model)
    print(f"Step: {step}{'' if step == 'turnaround' else ' ' + str(scene)}   model: {model}   size: {size}   "
          f"variations: {args.n}")
    print("References:", *[os.path.relpath(r, ROOT) for r in refs], sep="\n  ")
    print(f"Prompt: {len(full)} chars. Output: {os.path.relpath(os.path.dirname(out_pat), ROOT)}/")
    confirm_gate(args.yes, "call the image API (billed per image on your OpenAI account)")
    key = secret("OPENAI_API_KEY")
    base = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com").rstrip("/")
    files = [("image[]", os.path.basename(r), open(r, "rb").read(), "image/png") for r in refs]
    body, ctype = multipart({"model": model, "prompt": full, "size": size, "n": str(args.n),
                             "quality": args.quality}, files)
    res = http("POST", f"{base}/v1/images/edits",
               {"Authorization": f"Bearer {key}", "Content-Type": ctype}, body, secrets=[key], timeout=600)
    for item in res.get("data", []):
        path, _ = next_free(out_pat)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(base64.b64decode(item["b64_json"]))
        save_json(path[:-4] + ".json", {"step": step, "scene": scene, "model": model, "size": size,
                                        "references": [os.path.relpath(r, ROOT) for r in refs],
                                        "created_utc": datetime.datetime.utcnow().isoformat(timespec="seconds")})
        print("wrote", os.path.relpath(path, ROOT))
    print("Next: check against production/QC_CHECKLIST.md, then approve the best one.")


def approve(ep_dir, src, as_what, scene):
    if not os.path.exists(src):
        sys.exit(f"not found: {src}")
    dst = APPROVED_TURNAROUND if as_what == "turnaround" else \
        os.path.join(ep_dir, "frames", f"scene_{scene:02d}_start.png")
    if os.path.exists(dst):
        sys.exit(f"{os.path.relpath(dst, ROOT)} already exists. Approved assets are never overwritten; "
                 f"rename or move it yourself if you really want to replace it.")
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(src, dst)
    print("approved", os.path.relpath(dst, ROOT))


def main():
    load_env()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("step", choices=["turnaround", "scene", "approve"])
    ap.add_argument("episode_dir")
    ap.add_argument("arg", nargs="?", help="scene number (scene) or candidate file (approve)")
    ap.add_argument("--as", dest="as_what", choices=["turnaround", "scene"])
    ap.add_argument("--scene", type=int, help="scene number for approve --as scene")
    ap.add_argument("--n", type=int, default=2)
    ap.add_argument("--quality", default="high")
    ap.add_argument("--model", default="gpt-image-1")
    ap.add_argument("--yes", action="store_true")
    a = ap.parse_args()
    ep_dir = os.path.abspath(a.episode_dir)
    try:
        if a.step == "approve":
            if not a.arg or not a.as_what or (a.as_what == "scene" and not a.scene):
                sys.exit("usage: approve <ep> FILE --as turnaround | --as scene --scene N")
            approve(ep_dir, os.path.abspath(a.arg), a.as_what, a.scene)
        elif a.step == "turnaround":
            generate(ep_dir, "turnaround", None, a)
        else:
            if not a.arg:
                sys.exit("usage: scene <ep> N")
            generate(ep_dir, "scene", int(a.arg), a)
    except ApiError as e:
        sys.exit(f"Image API error {e}")


if __name__ == "__main__":
    main()
