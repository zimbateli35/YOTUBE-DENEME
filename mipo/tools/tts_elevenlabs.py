#!/usr/bin/env python3
"""ElevenLabs integration for Mipo's Magical World: voices, narration/dialogue and SFX.

Subcommands
  credits                 show plan, credits used/left and reset date (free; spends nothing)
  voices [--search TXT]   list voices in your account to pick IDs for production/voices.json
  tts    <ep>             generate line takes (with word timing) for each speaker's fixed voice
  sfx    <ep>             generate sound-effect takes for the episode's SFX cues
  select <ep> ID TAKE     approve a take: copy it to audio/voice/<ID>.mp3 or audio/sfx/<ID>.mp3

Safety
  * Spends credits ONLY with --yes. Without it you get a dry run with the credit estimate.
  * Checks your remaining credits first and stops before the budget (--max-credits) or your
    remaining credits would be exceeded. It re-checks after every request using the real usage.
  * Never buys credits, never changes your plan, never prints your API key.
  * Never overwrites: takes are numbered; approved files are not replaced (use --replace to
    move the old one into _superseded/ first).

Credentials (mipo/.env, git-ignored)
  ELEVENLABS_API_KEY=...          required
  ELEVENLABS_VOICE_MIPO=...       voice id per character (see production/voices.json)
  ELEVENLABS_BASE_URL=...         optional, for testing against a mock server

Examples (Windows: use "py tools\\tts_elevenlabs.py ...")
  python3 tools/tts_elevenlabs.py credits
  python3 tools/tts_elevenlabs.py tts production/episodes/ep01_missing_rainbow_color --scene 1 --takes 3
  python3 tools/tts_elevenlabs.py tts <ep> --scene 1 --takes 3 --yes
  python3 tools/tts_elevenlabs.py select <ep> L01 2
  python3 tools/tts_elevenlabs.py sfx <ep> --scene 1 --takes 2 --yes
"""
import argparse
import base64
import datetime
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import (ROOT, ApiError, confirm_gate, http, load_env, load_json, mask,  # noqa: E402
                     next_free, save_json, scene_of, secret)

VOICES = os.path.join(ROOT, "production", "voices.json")


def base_url():
    return os.environ.get("ELEVENLABS_BASE_URL", "https://api.elevenlabs.io").rstrip("/")


def headers(key):
    return {"xi-api-key": key, "Accept": "application/json"}


def subscription(key):
    return http("GET", f"{base_url()}/v1/user/subscription", headers(key), secrets=[key])


def remaining(sub):
    return int(sub.get("character_limit", 0)) - int(sub.get("character_count", 0))


def print_sub(sub):
    left = remaining(sub)
    reset = sub.get("next_character_count_reset_unix")
    when = datetime.datetime.fromtimestamp(reset, datetime.timezone.utc).strftime("%Y-%m-%d") if reset else "?"
    print(f"Plan: {sub.get('tier', '?')}   status: {sub.get('status', '?')}")
    print(f"Credits used: {sub.get('character_count')} / {sub.get('character_limit')}   "
          f"left: {left}   resets: {when} (UTC)")
    if sub.get("can_extend_character_limit") or sub.get("allowed_to_extend_character_limit"):
        print("NOTE: usage-based billing may be enabled on this account. This tool never goes past "
              "your remaining credits, so it cannot trigger overage charges.")
    if str(sub.get("tier", "")).lower() == "free":
        print("NOTE: Free plan audio has no commercial license (attribution required). Use it for "
              "tests; generate publishable audio on a plan that includes a commercial license.")


def credit_rate(model_id):
    m = model_id.lower()
    return 0.5 if ("flash" in m or "turbo" in m) else 1.0


def ep_lines(ep, args):
    out = []
    for ln in ep["narration"]:
        if args.line and ln["id"] not in args.line:
            continue
        if args.scene and scene_of(ep, ln["start"])["id"] != args.scene:
            continue
        out.append(ln)
    return out


def voice_for(cast, speaker):
    if speaker not in cast:
        sys.exit(f"speaker '{speaker}' is not in production/voices.json")
    c = cast[speaker]
    vid = os.environ.get(c["voice_id_env"], "").strip()
    if not vid and c.get("legacy_env"):
        vid = os.environ.get(c["legacy_env"], "").strip()
    return c, vid


# ---------------------------------------------------------------------------
def cmd_credits(args):
    key = secret("ELEVENLABS_API_KEY")
    print(f"API key: {mask(key)}")
    print_sub(subscription(key))


def cmd_voices(args):
    key = secret("ELEVENLABS_API_KEY")
    res = http("GET", f"{base_url()}/v1/voices", headers(key), secrets=[key])
    for v in res.get("voices", []):
        line = f"{v.get('voice_id')}  {v.get('name')}  [{v.get('category', '')}]  " + \
               ", ".join(f"{k}={val}" for k, val in (v.get("labels") or {}).items())
        if not args.search or args.search.lower() in line.lower():
            print(line)


def run_budgeted(key, jobs, est_total, max_credits, yes, label):
    """jobs: list of (description, callable). Enforces budget with real usage."""
    sub = subscription(key) if key else None
    if sub:
        print_sub(sub)
        left = remaining(sub)
        print(f"\nPlanned: {len(jobs)} {label} request(s), estimated {est_total:.0f} credits "
              f"(budget --max-credits {max_credits}, left on account {left}).")
        if est_total > min(left, max_credits):
            sys.exit("STOP: the estimate exceeds your budget or remaining credits. Nothing was generated.")
    for desc, _ in jobs:
        print("  -", desc)
    confirm_gate(yes, f"generate these {label} takes")
    start_used = int(sub["character_count"])
    for desc, fn in jobs:
        fn()
        now = subscription(key)
        spent = int(now["character_count"]) - start_used
        print(f"    credits used so far this run: {spent}")
        if spent >= max_credits or remaining(now) <= 0:
            print("Budget reached; stopping early.")
            break


def cmd_tts(args):
    ep_dir = os.path.abspath(args.episode_dir)
    ep = load_json(os.path.join(ep_dir, "episode.json"))
    cfg = load_json(VOICES)
    cast, d = cfg["cast"], cfg["defaults"]
    lines = ep_lines(ep, args)
    if not lines:
        sys.exit("no lines selected")
    key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if args.yes and not key:
        secret("ELEVENLABS_API_KEY")
    out_dir = os.path.join(ep_dir, "audio", "voice", "takes")
    all_lines = ep["narration"]
    jobs, est = [], 0.0
    for ln in lines:
        c, vid = voice_for(cast, ln.get("speaker", "mipo"))
        if not vid and (args.yes or key):
            sys.exit(f"No voice id for '{ln.get('speaker')}': set {c['voice_id_env']} in mipo/.env "
                     f"(find ids with: tts_elevenlabs.py voices)")
        model = args.model or d["model_id"]
        idx = all_lines.index(ln)
        prev_t = all_lines[idx - 1]["text"] if idx > 0 else ""
        next_t = all_lines[idx + 1]["text"] if idx + 1 < len(all_lines) else ""
        for k in range(args.takes):
            est += len(ln["text"]) * credit_rate(model)

            def job(ln=ln, c=c, vid=vid, model=model, prev_t=prev_t, next_t=next_t, k=k):
                path, n = next_free(os.path.join(out_dir, f"{ln['id']}_take{{n}}.mp3"))
                body = {"text": ln["text"], "model_id": model,
                        "voice_settings": c["voice_settings"],
                        "seed": int(c.get("seed", 0)) + k,
                        "previous_text": prev_t, "next_text": next_t}
                if d.get("language_code") and "multilingual" not in model:
                    body["language_code"] = d["language_code"]
                url = (f"{base_url()}/v1/text-to-speech/{vid}/with-timestamps"
                       f"?output_format={d['output_format']}")
                res = http("POST", url, headers(key), body, secrets=[key])
                os.makedirs(out_dir, exist_ok=True)
                with open(path, "wb") as f:
                    f.write(base64.b64decode(res["audio_base64"]))
                save_json(path[:-4] + ".json", {
                    "line": ln["id"], "speaker": ln.get("speaker"), "text": ln["text"],
                    "voice_id": vid, "model_id": model, "voice_settings": c["voice_settings"],
                    "seed": body["seed"], "alignment": res.get("alignment"),
                    "created_utc": datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat(timespec="seconds")})
                print(f"    wrote {os.path.relpath(path, ep_dir)}")

            jobs.append((f"{ln['id']} take {k + 1} [{ln.get('speaker')}] \"{ln['text']}\"", job))
    if not key:
        print("(no ELEVENLABS_API_KEY set: showing the plan only)")
        print(f"Planned: {len(jobs)} TTS request(s), estimated {est:.0f} credits.")
        for desc, _ in jobs:
            print("  -", desc)
        confirm_gate(False, "generate (after setting ELEVENLABS_API_KEY)")
    run_budgeted(key, jobs, est, args.max_credits, args.yes, "TTS")
    print("\nNext: listen to the takes, then approve one per line with:  select <ep> L01 <take>")


def cmd_sfx(args):
    ep_dir = os.path.abspath(args.episode_dir)
    ep = load_json(os.path.join(ep_dir, "episode.json"))
    cues = [c for c in ep["sfx"]
            if (not args.cue or c["id"] in args.cue)
            and (not args.scene or scene_of(ep, c["t"])["id"] == args.scene)]
    if not cues:
        sys.exit("no SFX cues selected")
    key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if args.yes and not key:
        secret("ELEVENLABS_API_KEY")
    out_dir = os.path.join(ep_dir, "audio", "sfx", "takes")
    jobs = []
    for c in cues:
        for k in range(args.takes):
            def job(c=c):
                path, _ = next_free(os.path.join(out_dir, f"{c['id']}_take{{n}}.mp3"))
                body = {"text": c["prompt"], "duration_seconds": max(0.5, float(c["dur"])),
                        "prompt_influence": args.prompt_influence}
                audio = http("POST", f"{base_url()}/v1/sound-generation",
                             dict(headers(key), Accept="audio/mpeg"), body, secrets=[key], raw=True)
                os.makedirs(out_dir, exist_ok=True)
                with open(path, "wb") as f:
                    f.write(audio)
                save_json(path[:-4] + ".json", {"cue": c["id"], "prompt": c["prompt"], "dur": c["dur"],
                                                "created_utc": datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat(timespec="seconds")})
                print(f"    wrote {os.path.relpath(path, ep_dir)}")
            jobs.append((f"{c['id']} take {k + 1} @ {c['t']:.2f}s ({c['dur']}s): {c['prompt']}", job))
    est = args.est_per_request * len(jobs)
    if not key:
        print(f"(no ELEVENLABS_API_KEY set: showing the plan only)\nPlanned: {len(jobs)} SFX request(s).")
        for desc, _ in jobs:
            print("  -", desc)
        confirm_gate(False, "generate (after setting ELEVENLABS_API_KEY)")
    print(f"(SFX cost depends on duration; the estimate uses --est-per-request {args.est_per_request}. "
          f"Real usage is re-checked after every request.)")
    run_budgeted(key, jobs, est, args.max_credits, args.yes, "SFX")
    print("\nNext: approve one take per cue with:  select <ep> SFX01 <take>")


def cmd_select(args):
    ep_dir = os.path.abspath(args.episode_dir)
    kind = "sfx" if args.id.upper().startswith("SFX") else "voice"
    src = os.path.join(ep_dir, "audio", kind, "takes", f"{args.id}_take{args.take}.mp3")
    if not os.path.exists(src):
        sys.exit(f"not found: {src}")
    dst = os.path.join(ep_dir, "audio", kind, f"{args.id}.mp3")
    if os.path.exists(dst):
        if not args.replace:
            sys.exit(f"{os.path.relpath(dst, ep_dir)} is already approved. Not overwriting. "
                     f"Use --replace to move it to _superseded/ first.")
        sup, _ = next_free(os.path.join(ep_dir, "audio", kind, "_superseded", f"{args.id}_v{{n}}.mp3"))
        os.makedirs(os.path.dirname(sup), exist_ok=True)
        shutil.move(dst, sup)
        if os.path.exists(dst[:-4] + ".json"):
            shutil.move(dst[:-4] + ".json", sup[:-4] + ".json")
        print("moved previous approval to", os.path.relpath(sup, ep_dir))
    shutil.copy2(src, dst)
    if os.path.exists(src[:-4] + ".json"):
        shutil.copy2(src[:-4] + ".json", dst[:-4] + ".json")
    print("approved", os.path.relpath(dst, ep_dir))


def main():
    load_env()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    sp.add_parser("credits")
    v = sp.add_parser("voices")
    v.add_argument("--search")
    t = sp.add_parser("tts")
    t.add_argument("episode_dir")
    t.add_argument("--scene", type=int)
    t.add_argument("--line", action="append")
    t.add_argument("--takes", type=int, default=3)
    t.add_argument("--model", help="override voices.json default model")
    t.add_argument("--max-credits", type=int, default=1000)
    t.add_argument("--yes", action="store_true", help="actually generate (spends credits)")
    s = sp.add_parser("sfx")
    s.add_argument("episode_dir")
    s.add_argument("--scene", type=int)
    s.add_argument("--cue", action="append")
    s.add_argument("--takes", type=int, default=2)
    s.add_argument("--prompt-influence", type=float, default=0.4)
    s.add_argument("--est-per-request", type=float, default=100.0)
    s.add_argument("--max-credits", type=int, default=1500)
    s.add_argument("--yes", action="store_true", help="actually generate (spends credits)")
    se = sp.add_parser("select")
    se.add_argument("episode_dir")
    se.add_argument("id")
    se.add_argument("take", type=int)
    se.add_argument("--replace", action="store_true")
    args = ap.parse_args()
    try:
        {"credits": cmd_credits, "voices": cmd_voices, "tts": cmd_tts,
         "sfx": cmd_sfx, "select": cmd_select}[args.cmd](args)
    except ApiError as e:
        hint = ""
        if e.code == 401:
            hint = " (check ELEVENLABS_API_KEY)"
        elif e.code == 0:
            hint = " (network: is api.elevenlabs.io reachable from this computer?)"
        sys.exit(f"ElevenLabs error {e}{hint}")


if __name__ == "__main__":
    main()
