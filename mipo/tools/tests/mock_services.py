"""Local mock of the ElevenLabs, OpenAI Images and Runway endpoints used by the pipeline.

For tests only: returns tones / test patterns made with ffmpeg (no real speech, no real art),
checks auth headers, and tracks a fake credit balance so the budget logic can be tested.
"""
import base64
import json
import os
import subprocess
import tempfile
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

KEYS = {"eleven": "test-eleven-key-123456", "openai": "sk-test-openai-123456", "runway": "key_test_runway_123456"}


def _ff(args, suffix):
    fd, path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    subprocess.run(["ffmpeg", "-v", "error", "-y", *args, path], check=True)
    data = open(path, "rb").read()
    os.remove(path)
    return data


def tone_mp3(seconds, freq=660):
    return _ff(["-f", "lavfi", "-i", f"sine=f={freq}:d={seconds:.3f}", "-af", "volume=0.3",
                "-ac", "1", "-ar", "44100", "-b:a", "128k"], ".mp3")


def png(w, h):
    return _ff(["-f", "lavfi", "-i", f"testsrc2=s={w}x{h}:d=1", "-frames:v", "1"], ".png")


def mp4(w, h, seconds):
    return _ff(["-f", "lavfi", "-i", f"testsrc2=s={w}x{h}:r=24:d={seconds}", "-pix_fmt", "yuv420p",
                "-c:v", "libx264"], ".mp4")


class State:
    def __init__(self, limit=10000):
        self.used = 0
        self.limit = limit
        self.tasks = {}
        self.calls = []


def make_handler(state, port_ref):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _send(self, code, body, ctype="application/json"):
            if isinstance(body, (dict, list)):
                body = json.dumps(body).encode()
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _body(self):
            n = int(self.headers.get("Content-Length") or 0)
            return self.rfile.read(n) if n else b""

        def _auth(self, kind):
            if kind == "eleven":
                ok = self.headers.get("xi-api-key") == KEYS["eleven"]
            else:
                ok = self.headers.get("Authorization") == f"Bearer {KEYS[kind]}"
            if not ok:
                self._send(401, {"detail": "invalid api key"})
            return ok

        def do_GET(self):
            p = self.path.split("?")[0]
            state.calls.append(("GET", p))
            if p == "/v1/user/subscription":
                if self._auth("eleven"):
                    self._send(200, {"tier": "free", "status": "free", "character_count": state.used,
                                     "character_limit": state.limit, "next_character_count_reset_unix": 1893456000,
                                     "can_extend_character_limit": False})
            elif p == "/v1/voices":
                if self._auth("eleven"):
                    self._send(200, {"voices": [{"voice_id": "mock_mipo", "name": "Mock Boy", "category": "generated",
                                                 "labels": {"age": "young"}}]})
            elif p.startswith("/v1/tasks/"):
                if not self._auth("runway"):
                    return
                tid = p.rsplit("/", 1)[1]
                t = state.tasks.get(tid)
                if not t:
                    return self._send(404, {"error": "no task"})
                t["polls"] += 1
                if t["polls"] < 2:
                    return self._send(200, {"id": tid, "status": "RUNNING"})
                self._send(200, {"id": tid, "status": "SUCCEEDED",
                                 "output": [f"http://127.0.0.1:{port_ref[0]}/files/{tid}.mp4"]})
            elif p.startswith("/files/"):
                self._send(200, mp4(720, 1280, 5), "video/mp4")
            else:
                self._send(404, {"error": p})

        def do_POST(self):
            p = self.path.split("?")[0]
            raw = self._body()
            state.calls.append(("POST", p))
            if p.startswith("/v1/text-to-speech/") and p.endswith("/with-timestamps"):
                if not self._auth("eleven"):
                    return
                body = json.loads(raw)
                text = body["text"]
                dur = 0.3 + 0.065 * len(text)
                n = len(text)
                starts = [0.15 + i * (dur - 0.3) / max(1, n) for i in range(n)]
                state.used += len(text)
                self._send(200, {"audio_base64": base64.b64encode(tone_mp3(dur)).decode(),
                                 "alignment": {"characters": list(text),
                                               "character_start_times_seconds": starts,
                                               "character_end_times_seconds": [s + (dur - 0.3) / n for s in starts]}})
            elif p == "/v1/sound-generation":
                if not self._auth("eleven"):
                    return
                body = json.loads(raw)
                d = float(body.get("duration_seconds") or 1.0)
                state.used += int(40 * d)
                self._send(200, tone_mp3(d, 1320), "audio/mpeg")
            elif p == "/v1/images/edits":
                if not self._auth("openai"):
                    return
                n_refs = raw.count(b'name="image[]"')
                if n_refs < 1:
                    return self._send(400, {"error": "no reference image"})
                n = int(raw.split(b'name="n"\r\n\r\n', 1)[1].split(b"\r\n", 1)[0])
                size = raw.split(b'name="size"\r\n\r\n', 1)[1].split(b"\r\n", 1)[0].decode()
                w, h = (int(x) for x in size.split("x"))
                state.calls.append(("refs", n_refs))
                img = base64.b64encode(png(w, h)).decode()
                self._send(200, {"data": [{"b64_json": img} for _ in range(n)]})
            elif p == "/v1/image_to_video":
                if not self._auth("runway"):
                    return
                body = json.loads(raw)
                if not body.get("promptImage", "").startswith("data:image/png;base64,"):
                    return self._send(400, {"error": "promptImage"})
                tid = uuid.uuid4().hex[:12]
                state.tasks[tid] = {"polls": 0}
                self._send(200, {"id": tid})
            else:
                self._send(404, {"error": p})

    return H


def start(limit=10000):
    state = State(limit)
    port_ref = [0]
    srv = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(state, port_ref))
    port_ref[0] = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, state, f"http://127.0.0.1:{port_ref[0]}"
