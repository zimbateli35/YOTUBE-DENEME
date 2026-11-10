"""Build the soundtrack: narrator voice (offline TTS via ffmpeg's flite),
a soft music-box score and gentle magic sound effects, all mixed to 30 s.

Usage: python3 audio.py <out_dir>
Writes voice_XX.wav per line, soundtrack.wav and subtitles.srt.
"""
import os
import subprocess
import sys
import json
import wave

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from script import (DURATION, NARRATION, T_BIRD_ARRIVE, T_BUNNY_ARRIVE,  # noqa: E402
                    T_DEER_ARRIVE, T_FLOWER_OPEN, T_RESTORE_START, T_SPARKLE_TRAIL,
                    T_TAP, T_WAND_PICKUP)

SR = 44100
VOICE = "rms"          # flite voice; pitched up below for a young, warm tone
PITCH = 1.24           # pitch ratio (boy-like)
TEMPO = 0.97           # <1 = slower, calmer delivery
SRC_RATE = 16000       # flite native sample rate


def read_wav(path):
    with wave.open(path) as w:
        data = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
        return data.astype(np.float32) / 32768.0


def write_wav(path, x):
    x = np.clip(x, -1, 1)
    with wave.open(path, "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())


def tts(text, path):
    safe = text.replace("'", "").replace(":", "")
    # flite renders at 16 kHz; raise pitch by resampling, then restore
    # tempo, add a touch of warmth (low shelf) and a soft high cut for calm.
    af = (f"asetrate={SRC_RATE}*{PITCH},aresample={SR},atempo={TEMPO / PITCH:.4f},"
          f"bass=g=3:f=180,lowpass=f=7000,highpass=f=90,"
          f"loudnorm=I=-16:TP=-1.5:LRA=7")
    subprocess.run([
        "ffmpeg", "-v", "error", "-y", "-f", "lavfi",
        "-i", f"flite=text='{safe}':voice={VOICE}",
        "-af", af, "-ac", "1", "-ar", str(SR), path], check=True)
    return read_wav(path)


def env(n, a=0.005, r=0.4):
    t = np.arange(n) / SR
    e = np.minimum(1, t / a) * np.exp(-t / r)
    return e


def tone(freq, dur, amp=0.2, decay=0.6, bell=True):
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = np.sin(2 * np.pi * freq * t)
    if bell:  # music-box partials
        x += 0.35 * np.sin(2 * np.pi * freq * 2.0 * t) * np.exp(-t / 0.15)
        x += 0.15 * np.sin(2 * np.pi * freq * 3.01 * t) * np.exp(-t / 0.08)
    return amp * x * env(n, r=decay)


def add(buf, x, at):
    i = int(at * SR)
    j = min(len(buf), i + len(x))
    if j > i:
        buf[i:j] += x[: j - i]


def midi(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def music(n):
    out = np.zeros(n, np.float32)
    bpm = 96
    beat = 60 / bpm
    # I - vi - IV - V in C, gentle pad + music-box arpeggio
    chords = [[60, 64, 67], [57, 60, 64], [53, 57, 60], [55, 59, 62]]
    melody = [72, 76, 79, 76, 74, 72, 74, 76, 72, 69, 72, 74, 76, 74, 72, 67]
    t = 0.0
    bar = 0
    while t < DURATION:
        ch = chords[bar % 4]
        # pad
        dur = beat * 4
        nn = int(dur * SR)
        tt = np.arange(nn) / SR
        pad = sum(np.sin(2 * np.pi * midi(m - 12) * tt) for m in ch) / 3
        fade = np.minimum(1, tt / 0.6) * np.minimum(1, (dur - tt) / 0.6)
        add(out, 0.05 * pad * fade, t)
        # arpeggio (8ths)
        for k in range(8):
            m = ch[k % 3] + 12 * (k // 3 % 2)
            add(out, tone(midi(m), 1.2, amp=0.035, decay=0.5), t + k * beat / 2)
        # melody (quarters)
        for k in range(4):
            m = melody[(bar * 4 + k) % len(melody)]
            add(out, tone(midi(m), 1.6, amp=0.06, decay=0.7), t + k * beat)
        t += dur
        bar += 1
    return out


def chirp(at, out, base=2600, amp=0.03):
    """Soft cheerful bird tweet: short upward sine sweeps."""
    for k in range(2):
        dur = 0.09
        nn = int(dur * SR)
        tt = np.arange(nn) / SR
        f = base + 1800 * tt / dur
        x = amp * np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * tt / dur)
        add(out, x, at + k * 0.13)


def whoosh(at, out, dur=0.6, amp=0.05, seed=0):
    """Gentle filtered-noise whoosh."""
    rng = np.random.default_rng(seed)
    nn = int(dur * SR)
    x = rng.standard_normal(nn)
    k = 40
    x = np.convolve(x, np.ones(k) / k, mode="same")  # low-pass
    shape = np.sin(np.pi * np.arange(nn) / nn) ** 2
    add(out, amp * 6 * x * shape, at)


def sfx(n):
    out = np.zeros(n, np.float32)
    rng = np.random.default_rng(3)
    # opening sparkle (hook in the first second)
    for i, m in enumerate([84, 88, 91, 96]):
        add(out, tone(midi(m), 1.0, 0.045, 0.45), 0.05 + i * 0.08)
    # hop out of bed
    whoosh(1.55, out, 0.45, 0.035, 1)
    # missing color: soft descending (not scary)
    for i, m in enumerate([79, 76, 72]):
        add(out, tone(midi(m), 1.0, 0.04, 0.5), 2.4 + i * 0.2)
    # morning birds outside the window
    for at in (0.9, 3.6):
        chirp(at, out, 2800, 0.02)
    # wand pickup shimmer
    for i, m in enumerate([88, 91, 93, 96]):
        add(out, tone(midi(m), 0.9, 0.04, 0.4), T_WAND_PICKUP + i * 0.06)
    # sparkle trail twinkles
    for k in range(14):
        add(out, tone(midi(int(rng.choice([88, 91, 93, 96]))), 0.6, 0.022, 0.25),
            T_SPARKLE_TRAIL + k * 0.18)
    # bridge walk: sparkles + bird arrival
    for k in range(8):
        add(out, tone(midi(int(rng.choice([91, 93, 96, 98]))), 0.5, 0.018, 0.2), 10.2 + k * 0.6)
    whoosh(T_BIRD_ARRIVE - 0.4, out, 0.6, 0.04, 2)
    for at in (T_BIRD_ARRIVE + 0.2, 12.6, 13.9):
        chirp(at, out, 2600, 0.035)
    # bunny & deer arrive: soft pops + whoosh
    add(out, tone(midi(84), 0.6, 0.05, 0.18), T_BUNNY_ARRIVE)
    add(out, tone(midi(79), 0.6, 0.05, 0.18), T_DEER_ARRIVE)
    whoosh(T_BUNNY_ARRIVE - 0.2, out, 0.5, 0.03, 3)
    # flower opens: rising harp
    for k, m in enumerate([72, 76, 79, 84, 88]):
        add(out, tone(midi(m), 1.2, 0.035, 0.6), T_FLOWER_OPEN + k * 0.08)
    # wand tap + upward magic glissando + whoosh
    add(out, tone(midi(96), 0.8, 0.08, 0.3), T_TAP)
    whoosh(T_TAP + 0.05, out, 1.0, 0.05, 4)
    for k, m in enumerate([72, 74, 76, 79, 81, 84, 86, 88, 91, 93, 96]):
        add(out, tone(midi(m), 1.2, 0.04, 0.6), T_TAP + 0.08 + k * 0.06)
    # stripe painting shimmer
    for k in range(10):
        add(out, tone(midi(int(rng.choice([91, 93, 96, 98, 100]))), 0.7, 0.022, 0.3),
            T_RESTORE_START + k * 0.18)
    # celebration
    for k, m in enumerate([84, 88, 91, 96, 91, 96]):
        add(out, tone(midi(m), 1.0, 0.04, 0.5), 25.05 + k * 0.15)
    chirp(26.2, out, 2700, 0.03)
    chirp(28.4, out, 2900, 0.025)
    add(out, tone(midi(84), 2.5, 0.05, 1.4), 28.9)
    add(out, tone(midi(91), 2.5, 0.04, 1.4), 28.9)
    return out


def srt_time(s):
    ms = int(round(s * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    sec, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{sec:02d},{ms:03d}"


def main(out_dir):
    os.makedirs(out_dir, exist_ok=True)
    n = int(DURATION * SR)
    voice = np.zeros(n, np.float32)
    srt = []
    timing = {}
    for i, (at, line) in enumerate(NARRATION):
        x = tts(line, os.path.join(out_dir, f"voice_{i:02d}.wav"))
        d = len(x) / SR
        timing[line] = round(d, 3)
        print(f"{at:5.2f}-{at + d:5.2f}  ({d:.2f}s)  {line}")
        nxt = NARRATION[i + 1][0] if i + 1 < len(NARRATION) else DURATION
        if at + d > nxt + 0.01:
            print(f"   WARNING: overlaps next line by {at + d - nxt:.2f}s")
        add(voice, 0.9 * x, at)
        srt.append(f"{i + 1}\n{srt_time(at)} --> {srt_time(min(at + d + 0.3, DURATION))}\n{line}\n")

    mus = music(n)
    # duck music under the voice
    envl = np.abs(voice)
    k = int(0.25 * SR)
    envl = np.convolve(envl, np.ones(k) / k, mode="same")
    duck = 1.0 - 0.55 * np.clip(envl * 12, 0, 1)
    mix = voice + mus * duck + sfx(n)
    # fade in/out
    fi, fo = int(0.4 * SR), int(1.2 * SR)
    mix[:fi] *= np.linspace(0, 1, fi)
    mix[-fo:] *= np.linspace(1, 0, fo)
    mix /= max(1.0, np.max(np.abs(mix)) / 0.95)
    write_wav(os.path.join(out_dir, "soundtrack.wav"), mix)
    with open(os.path.join(out_dir, "timing.json"), "w") as f:
        json.dump(timing, f, indent=1)
    with open(os.path.join(out_dir, "subtitles.srt"), "w") as f:
        f.write("\n".join(srt))


if __name__ == "__main__":
    main(sys.argv[1])
