#!/usr/bin/env python3
"""End-to-end integration test of the production pipeline against LOCAL MOCK services.

No network, no real API keys, no credits. The test copies the project into a temporary folder,
so your real files are never touched. It then runs the real scripts:

  build_package -> tts_elevenlabs (credits/dry-run/tts/sfx/select/budget guard)
  -> gen_image (turnaround, approve, scene 1, approve) -> gen_video (scene 1, approve)
  -> mix_audio --scene 1 (4 separate tracks + mix + synced subtitles)
  -> assemble --scene 1 --subs     => first 5-second scene MP4 with dialogue + SFX
  plus a full-episode sync check for the "MAGIC" sync point (L08 at 22.05 s).

Run:  python3 tools/tests/test_integration.py        (Windows: py tools\\tests\\test_integration.py)
Needs: Python 3.10+, ffmpeg/ffprobe on PATH.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REAL_ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import mock_services  # noqa: E402

EP_REL = os.path.join("production", "episodes", "ep01_missing_rainbow_color")


def read(path):
    with open(path, encoding="utf-8", errors="ignore") as f:
        return f.read()


def probe(path, entries):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", entries, "-of", "json", path],
                         capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


class Pipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv, cls.state, cls.url = mock_services.start(limit=10000)
        cls.tmp = tempfile.mkdtemp(prefix="mipo_it_")
        root = os.path.join(cls.tmp, "mipo")
        os.makedirs(os.path.join(root, "reference"))
        shutil.copytree(os.path.join(REAL_ROOT, "production"), os.path.join(root, "production"),
                        ignore=shutil.ignore_patterns("audio", "clips", "frames", "final"))
        shutil.copytree(os.path.join(REAL_ROOT, "tools"), os.path.join(root, "tools"),
                        ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copy2(os.path.join(REAL_ROOT, "reference", "cover_landscape_with_friends.png"),
                     os.path.join(root, "reference"))
        cls.root = root
        cls.ep = os.path.join(root, EP_REL)
        k = mock_services.KEYS
        cls.env = dict(os.environ,
                       ELEVENLABS_API_KEY=k["eleven"], ELEVENLABS_VOICE_MIPO="mock_mipo",
                       OPENAI_API_KEY=k["openai"], RUNWAYML_API_SECRET=k["runway"],
                       ELEVENLABS_BASE_URL=cls.url, OPENAI_BASE_URL=cls.url, RUNWAYML_BASE_URL=cls.url,
                       NO_PROXY="127.0.0.1,localhost", no_proxy="127.0.0.1,localhost",
                       PYTHONIOENCODING="utf-8")
        for v in ("HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy", "ALL_PROXY", "all_proxy"):
            cls.env.pop(v, None)
        cls.log = []

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def run_tool(self, *args, ok=True, env=None):
        r = subprocess.run([sys.executable, os.path.join(self.root, "tools", args[0]), *args[1:]],
                           capture_output=True, text=True, env=env or self.env, cwd=self.root)
        out = r.stdout + r.stderr
        self.log.append(out)
        if ok and r.returncode != 0:
            self.fail(f"{args} failed ({r.returncode}):\n{out}")
        if not ok and r.returncode == 0:
            self.fail(f"{args} should have failed:\n{out}")
        return out

    def test_pipeline(self):
        ep = self.ep
        self.run_tool("build_package.py", ep)

        # --- ElevenLabs: credits, dry run, budget guard, generation, selection ---
        out = self.run_tool("tts_elevenlabs.py", "credits")
        self.assertIn("left: 10000", out)
        out = self.run_tool("tts_elevenlabs.py", "tts", ep, "--scene", "1", "--takes", "2")
        self.assertIn("DRY RUN", out)
        self.assertEqual(self.state.used, 0, "dry run must not spend credits")
        out = self.run_tool("tts_elevenlabs.py", "tts", ep, "--scene", "1", "--takes", "2",
                            "--max-credits", "10", "--yes", ok=False)
        self.assertIn("STOP", out)
        self.assertEqual(self.state.used, 0, "budget guard must stop before spending")
        self.run_tool("tts_elevenlabs.py", "tts", ep, "--scene", "1", "--takes", "2", "--yes")
        self.assertEqual(self.state.used, 2 * (len("Good morning! I'm Mipo!") +
                                               len("Oh no! A rainbow color is missing!")))
        self.run_tool("tts_elevenlabs.py", "select", ep, "L01", "1")
        self.run_tool("tts_elevenlabs.py", "select", ep, "L02", "2")
        out = self.run_tool("tts_elevenlabs.py", "select", ep, "L01", "2", ok=False)
        self.assertIn("Not overwriting", out)
        self.run_tool("tts_elevenlabs.py", "sfx", ep, "--scene", "1", "--takes", "1", "--yes")
        for cue in ("SFX01", "SFX02", "SFX03", "SFX04"):
            self.run_tool("tts_elevenlabs.py", "select", ep, cue, "1")
        # placeholder music bed (test tone), 30 s
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "sine=f=220:d=30",
                        os.path.join(ep, "audio", "music.wav")], check=True)

        # --- Images: scene before approved turnaround must be refused ---
        out = self.run_tool("gen_image.py", "scene", ep, "1", "--yes", ok=False)
        self.assertIn("No approved turnaround", out)
        self.run_tool("gen_image.py", "turnaround", ep, "--n", "1", "--yes")
        self.assertIn(("refs", 1), self.state.calls)
        cand = os.path.join(self.root, "reference", "candidates", "mipo_turnaround_cand1.png")
        self.run_tool("gen_image.py", "approve", ep, cand, "--as", "turnaround")
        out = self.run_tool("gen_image.py", "approve", ep, cand, "--as", "turnaround", ok=False)
        self.assertIn("never overwritten", out)
        self.run_tool("gen_image.py", "scene", ep, "1", "--n", "1", "--yes")
        self.assertIn(("refs", 2), self.state.calls, "scene frames must send banner + approved turnaround")
        cand = os.path.join(ep, "frames", "candidates", "scene_01_start_cand1.png")
        self.run_tool("gen_image.py", "approve", ep, cand, "--as", "scene", "--scene", "1")

        # --- Video ---
        self.run_tool("gen_video.py", "scene", ep, "1", "--takes", "1", "--poll", "0.05", "--yes")
        self.run_tool("gen_video.py", "approve", ep, "1", "1")
        self.run_tool("gen_video.py", "approve", ep, "1", "1", ok=False)

        # --- Mix scene 1: separate tracks, sync, subtitles ---
        self.run_tool("mix_audio.py", ep, "--scene", "1")
        b = os.path.join(ep, "audio", "build", "scene_01")
        for stem in ("narration", "dialogue", "music", "sfx", "mix"):
            d = float(probe(os.path.join(b, f"{stem}.wav"), "format=duration")["format"]["duration"])
            self.assertAlmostEqual(d, 5.0, delta=0.05, msg=stem)
        rep = json.loads(read(os.path.join(b, "report.json")))
        self.assertEqual([ln["id"] for ln in rep["lines"]], ["L01", "L02"])
        self.assertAlmostEqual(rep["lines"][0]["start"], 0.30, places=2)
        self.assertEqual({ln["track"] for ln in rep["lines"]}, {"dialogue"})
        self.assertEqual(len(rep["sfx"]), 4)
        srt = read(os.path.join(b, "subtitles.srt"))
        self.assertIn("00:00:00,300 --> ", srt)
        self.assertIn("Good morning! I'm Mipo!", srt)

        # --- Assemble the first 5-second scene ---
        self.run_tool("assemble.py", ep, "--scene", "1", "--subs")
        final = os.path.join(ep, "final", "ep01_missing_rainbow_color_scene01_v1.mp4")
        info = probe(final, "format=duration:stream=codec_type,width,height")
        self.assertAlmostEqual(float(info["format"]["duration"]), 5.0, delta=0.06)
        v = [s for s in info["streams"] if s["codec_type"] == "video"][0]
        self.assertEqual((v["width"], v["height"]), (1080, 1920))
        self.assertTrue(any(s["codec_type"] == "audio" for s in info["streams"]))
        vol = subprocess.run(["ffmpeg", "-i", final, "-af", "volumedetect", "-f", "null", "-"],
                             capture_output=True, text=True).stderr
        mean = float(vol.split("mean_volume:")[1].split("dB")[0])
        self.assertGreater(mean, -50, "scene audio should not be silent")
        self.run_tool("assemble.py", ep, "--scene", "1", "--subs")
        self.assertTrue(os.path.exists(final.replace("_v1.mp4", "_v2.mp4")), "must version, not overwrite")

        # --- Sync point: 'MAGIC' must land on the wand tap at 22.05 s ---
        self.run_tool("tts_elevenlabs.py", "tts", ep, "--line", "L08", "--takes", "1", "--yes")
        self.run_tool("tts_elevenlabs.py", "select", ep, "L08", "1")
        self.run_tool("mix_audio.py", ep)
        rep = json.loads(read(os.path.join(ep, "audio", "build", "episode", "report.json")))
        l08 = next(ln for ln in rep["lines"] if ln["id"] == "L08")
        meta = json.loads(read(os.path.join(ep, "audio", "voice", "L08.json")))
        al = meta["alignment"]
        i = "".join(al["characters"]).upper().find("MAGIC")
        self.assertAlmostEqual(l08["start"] + al["character_start_times_seconds"][i], 22.05, places=2)

        # --- No secret may appear in any output or file we wrote ---
        blob = "\n".join(self.log)
        for k in mock_services.KEYS.values():
            self.assertNotIn(k, blob)
        for dirpath, _, files in os.walk(self.root):
            for fn in files:
                if fn.endswith((".json", ".srt", ".txt", ".md")):
                    txt = read(os.path.join(dirpath, fn))
                    for k in mock_services.KEYS.values():
                        self.assertNotIn(k, txt, fn)

        # keep the scene-1 result for inspection if requested
        keep = os.environ.get("MIPO_TEST_KEEP")
        if keep:
            os.makedirs(keep, exist_ok=True)
            shutil.copy2(final, keep)
            shutil.copytree(b, os.path.join(keep, "scene_01_audio_build"), dirs_exist_ok=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
