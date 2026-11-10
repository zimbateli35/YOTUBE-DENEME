"""Shared helpers for the Mipo pipeline tools (standard library only).

- Secrets come only from environment variables or mipo/.env (git-ignored).
- Keys are never printed: errors are scrubbed and secrets are masked.
- Output paths never overwrite an existing file.
"""
import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
import uuid

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_env():
    """Load mipo/.env into os.environ without overriding real env vars."""
    path = os.path.join(ROOT, ".env")
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                v = v.strip().strip('"').strip("'")
                if v:
                    os.environ.setdefault(k.strip(), v)


def secret(name, required=True):
    val = os.environ.get(name, "").strip()
    if required and not val:
        sys.exit(f"{name} is not set. Put it in mipo/.env (see production/SETUP.md). "
                 f"Never paste keys into chat or commit them.")
    return val


def mask(val):
    return "(not set)" if not val else f"{val[:3]}…{val[-2:]} ({len(val)} chars)"


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def next_free(path_pattern, start=1):
    """path_pattern contains '{n}'. Returns the first path that doesn't exist."""
    n = start
    while os.path.exists(path_pattern.format(n=n)):
        n += 1
    return path_pattern.format(n=n), n


class ApiError(Exception):
    def __init__(self, code, msg):
        super().__init__(f"HTTP {code}: {msg}")
        self.code = code


def _scrub(text, secrets):
    for s in secrets:
        if s:
            text = text.replace(s, "***")
    return text


def http(method, url, headers=None, body=None, secrets=(), timeout=180, raw=False):
    """JSON (or raw bytes) HTTP call with retries on 429/5xx. Never logs secrets."""
    import time
    data = None
    headers = dict(headers or {})
    if isinstance(body, (dict, list)):
        data = json.dumps(body).encode()
        headers.setdefault("Content-Type", "application/json")
    elif isinstance(body, bytes):
        data = body
    for attempt in range(4):
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                payload = r.read()
                if raw:
                    return payload
                return json.loads(payload.decode() or "null")
        except urllib.error.HTTPError as e:
            msg = _scrub(e.read().decode(errors="replace")[:400], secrets)
            if e.code in (429, 500, 502, 503, 504) and attempt < 3:
                time.sleep(2 ** (attempt + 1))
                continue
            raise ApiError(e.code, msg) from None
        except urllib.error.URLError as e:
            raise ApiError(0, _scrub(f"cannot reach {url.split('?')[0]}: {e.reason}", secrets)) from None


def multipart(fields, files):
    """fields: {name: str}; files: [(name, filename, bytes, content_type)] -> (body, content_type)."""
    b = uuid.uuid4().hex
    out = []
    for k, v in fields.items():
        out.append(f"--{b}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode())
    for name, fn, content, ctype in files:
        out.append(f"--{b}\r\nContent-Disposition: form-data; name=\"{name}\"; filename=\"{fn}\"\r\n"
                   f"Content-Type: {ctype}\r\n\r\n".encode() + content + b"\r\n")
    out.append(f"--{b}--\r\n".encode())
    return b"".join(out), f"multipart/form-data; boundary={b}"


def need_ffmpeg():
    for tool in ("ffmpeg", "ffprobe"):
        if not shutil.which(tool):
            sys.exit(f"{tool} not found on PATH (see production/SETUP.md)")


def duration(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "default=nw=1:nk=1", path], capture_output=True, text=True, check=True)
    return float(out.stdout.strip())


def find_media(base, exts=(".wav", ".mp3", ".m4a", ".aac", ".flac")):
    for ext in exts:
        if os.path.exists(base + ext):
            return base + ext
    return None


def scene_of(ep, t):
    for sc in ep["scenes"]:
        if sc["start"] <= t < sc["end"]:
            return sc
    return ep["scenes"][-1]


def confirm_gate(yes, what):
    if not yes:
        print(f"\nDRY RUN: nothing was sent and no credits were used.\n"
              f"Re-run with --yes to {what}.")
        sys.exit(0)
