"""Procedural music bed + transition sounds, synthesised with numpy (no licences, no downloads).

Approach taken from video-studio/studio/pipeline/sound.py: the music is generated, ducked under the voice
with an envelope follower, and mixed onto the finished video.

  festive : tanpura-like drone, santoor-like pentatonic plucks, dholak-like pulse, temple bell
  uplift  : warm major chords, soft arpeggio and a light beat (hiring, launches, news)
"""
import subprocess
from pathlib import Path
from typing import List

import numpy as np
import soundfile as sf
from scipy.signal import lfilter

SR = 44100
_rng = np.random.default_rng(11)


def _t(sec):
    return np.arange(int(sec * SR)) / SR


def _env(n, attack=0.004, decay=0.2):
    x = np.arange(n) / SR
    e = np.exp(-x / max(decay, 1e-4))
    a = int(attack * SR)
    if a > 0:
        e[:a] *= np.linspace(0, 1, a)
    return e


def _lowpass(x, cutoff):
    a = 1 - np.exp(-2 * np.pi * cutoff / SR)
    return lfilter([a], [1, a - 1], x)


def _sweep(f0, f1, sec):
    f = np.geomspace(f0, f1, int(sec * SR))
    return np.sin(2 * np.pi * np.cumsum(f) / SR)


def _add(out, sig, at):
    i = int(at * SR)
    if i >= len(out):
        return
    j = min(len(out), i + len(sig))
    out[i:j] += sig[: j - i]


def _pluck(f, sec=0.6, decay=0.22, bright=0.35):
    x = _t(sec)
    tone = np.sin(2 * np.pi * f * x) + bright * np.sin(4 * np.pi * f * x) + 0.15 * np.sin(6 * np.pi * f * x)
    click = _lowpass(_rng.standard_normal(len(x)), 5000) * _env(len(x), 0.0005, 0.004) * 0.3
    return (tone * _env(len(x), 0.002, decay) + click)


def _festive(seconds: float) -> np.ndarray:
    bpm = 96
    beat = 60 / bpm
    out = np.zeros(int(seconds * SR) + SR)
    x = _t(seconds + 1)
    # drone: Sa and Pa with slow swell (tanpura feel)
    swell = 0.75 + 0.25 * np.sin(2 * np.pi * x / (4 * beat))
    for f, a in ((130.81, 1.0), (196.0, 0.7), (261.63, 0.45)):
        out += 0.035 * a * swell * (np.sin(2 * np.pi * f * x) + 0.35 * np.sin(2 * np.pi * 2 * f * 1.002 * x))
    # santoor-like melody on the major pentatonic (C D E G A)
    scale = [523.25, 587.33, 659.25, 783.99, 880.0, 1046.5]
    phrase = [0, 2, 3, 4, 3, 2, 1, 2, 3, 5, 4, 3, 2, 3, 1, 0]
    n_eighths = int(seconds / (beat / 2))
    for k in range(n_eighths):
        f = scale[phrase[k % len(phrase)]]
        _add(out, 0.05 * _pluck(f, 0.5, 0.2), k * beat / 2)
        if k % 2 == 0:  # tremolo double-strike like a santoor
            _add(out, 0.025 * _pluck(f, 0.3, 0.12), k * beat / 2 + beat / 8)
    # dholak-like: low 'dha' on 1 and 3, high 'na' on the off-beats
    for k in range(int(seconds / beat)):
        at = k * beat
        if k % 2 == 0:
            n = int(0.3 * SR)
            _add(out, 0.16 * _sweep(150, 62, 0.3) * _env(n, 0.001, 0.12), at)
        n = int(0.08 * SR)
        na = (np.sin(2 * np.pi * 420 * _t(0.08)) * 0.6 + _lowpass(_rng.standard_normal(n), 3000) * 0.4) * _env(n, 0.0005, 0.025)
        _add(out, 0.06 * na, at + beat / 2)
    # temple bell every 4 bars
    for k in range(0, int(seconds / (16 * beat)) + 1):
        xb = _t(2.0)
        bell = sum(a * np.sin(2 * np.pi * f * xb) for f, a in ((1318.5, 1), (1975.5, 0.5), (2637, 0.3))) * _env(len(xb), 0.002, 0.7)
        _add(out, 0.03 * bell, k * 16 * beat + 0.1)
    return out[: int(seconds * SR)]


def _uplift(seconds: float) -> np.ndarray:
    bpm = 100
    beat = 60 / bpm
    bar = 4 * beat
    chords = [[130.81, 164.81, 196.0, 246.94], [110.0, 130.81, 164.81, 196.0],
              [87.31, 130.81, 174.61, 220.0], [98.0, 146.83, 196.0, 246.94]]
    out = np.zeros(int(seconds * SR) + SR)
    for b in range(int(np.ceil(seconds / bar))):
        ch = chords[b % 4]
        x = _t(bar)
        pad_env = np.minimum(1, x / 0.6) * np.minimum(1, (bar - x) / 0.5)
        pad = sum(np.sin(2 * np.pi * f * x) + 0.3 * np.sin(2 * np.pi * f * 1.004 * x) for f in ch)
        _add(out, 0.03 * pad * pad_env, b * bar)
        for k in range(16):  # sixteenth-note arpeggio
            f = ch[[0, 1, 2, 3, 2, 1, 3, 2][k % 8]] * 4
            _add(out, 0.022 * _pluck(f, 0.3, 0.1, 0.2), b * bar + k * beat / 4)
        for k in range(4):
            n = int(0.25 * SR)
            _add(out, 0.12 * _sweep(120, 50, 0.25) * _env(n, 0.001, 0.08), b * bar + k * beat)  # soft kick
            m = int(0.05 * SR)
            hat = (_rng.standard_normal(m) - _lowpass(_rng.standard_normal(m), 6000)) * _env(m, 0.0005, 0.012)
            _add(out, 0.025 * hat, b * bar + k * beat + beat / 2)
    return out[: int(seconds * SR)]


def whoosh(sec=0.5):
    n = int(sec * SR)
    shape = np.sin(np.linspace(0, np.pi, n)) ** 2
    noise = _rng.standard_normal(n)
    # sweeping band: crossfade between a dark and a bright filtered copy
    dark, bright = _lowpass(noise, 500), _lowpass(noise, 4500) - _lowpass(noise, 900)
    mix = np.linspace(0, 1, n) ** 1.5
    return (dark * (1 - mix) + bright * mix) * shape


def chime():
    x = _t(1.5)
    return sum(a * np.sin(2 * np.pi * f * x) * _env(len(x), 0.002, d) for f, a, d in ((880, 1, .6), (1320, .5, .45), (1760, .35, .3)))


def _quirky(seconds: float) -> np.ndarray:
    bpm = 124
    beat = 60 / bpm
    out = np.zeros(int(seconds * SR) + SR)
    bass = [98.0, 98.0, 130.81, 110.0, 87.31, 87.31, 98.0, 116.54]  # bouncy walking bass (G, C, A, F, Bb)
    mel = [783.99, 880.0, 987.77, 783.99, 659.25, 783.99, 1046.5, 987.77, 880.0, 783.99, 659.25, 587.33]
    for k in range(int(seconds / beat)):
        at = k * beat
        f = bass[k % len(bass)]
        x = _t(0.22)
        _add(out, 0.20 * np.sin(2 * np.pi * f * x) * _env(len(x), 0.002, 0.07), at)          # staccato pizzicato bass
        if k % 2 == 1:                                                                         # clap on the off-beats
            n = int(0.09 * SR)
            _add(out, 0.07 * (_rng.standard_normal(n) - _lowpass(_rng.standard_normal(n), 1500)) * _env(n, 0.0005, 0.02), at)
        if k % 4 in (0, 1, 3):                                                                 # xylophone hops
            g = mel[(k * 5) % len(mel)]
            xx = _t(0.3)
            _add(out, 0.06 * (np.sin(2 * np.pi * g * xx) + 0.5 * np.sin(2 * np.pi * 3.98 * g * xx)) * _env(len(xx), 0.001, 0.06), at + beat / 2)
        if k % 16 == 15:                                                                       # comic 'boing'
            xb = _t(0.5)
            _add(out, 0.05 * np.sin(2 * np.pi * np.cumsum(220 + 160 * np.sin(2 * np.pi * 7 * xb)) / SR) * _env(len(xb), 0.005, 0.25), at)
    return out[: int(seconds * SR)]


def bed(seconds: float, style: str) -> np.ndarray:
    y = _festive(seconds) if style == "festive" else _quirky(seconds) if style == "quirky" else _uplift(seconds)
    y = _lowpass(y, 6000)
    fade_in, fade_out = int(0.8 * SR), int(2.0 * SR)
    y[:fade_in] *= np.linspace(0, 1, fade_in)
    y[-fade_out:] *= np.linspace(1, 0, fade_out)
    return y / (np.max(np.abs(y)) or 1)


def _envelope(x: np.ndarray, win=0.25) -> np.ndarray:
    n = max(1, int(win * SR))
    e = np.sqrt(np.convolve(x ** 2, np.ones(n) / n, mode="same"))
    return np.clip(e / (np.percentile(e, 95) or 1), 0, 1)


def add_to_video(video: Path, style: str, cuts: List[float], end_at: float, work: Path,
                 music_db: float = -17.0, duck_db: float = -9.0) -> None:
    """Mix a ducked music bed, a whoosh at each scene cut and a chime on the end card into `video` (in place)."""
    voice_wav = work / "voice_full.wav"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(video), "-vn", "-ac", "1", "-ar", str(SR), str(voice_wav)], check=True)
    voice, _ = sf.read(voice_wav)
    n = len(voice)
    music = bed(n / SR + 0.05, style)[:n]
    if len(music) < n:
        music = np.pad(music, (0, n - len(music)))
    g = 10 ** (music_db / 20)
    duck = 1 - (1 - 10 ** (duck_db / 20)) * _envelope(voice)
    fx = np.zeros(n)
    w = whoosh()
    for c in cuts:  # whoosh centred on the cut
        _add(fx, 0.12 * w, max(0.0, c - 0.25))
    _add(fx, 0.10 * chime(), end_at + 0.15)
    mix = voice + music * g * duck + fx
    peak = np.max(np.abs(mix)) or 1
    if peak > 0.98:
        mix = mix / peak * 0.98
    mixed = work / "mixed.wav"
    sf.write(mixed, np.stack([mix, mix], axis=1).astype(np.float32), SR)
    tmp = video.with_suffix(".music.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(video), "-i", str(mixed), "-map", "0:v", "-map", "1:a",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-movflags", "+faststart", str(tmp)], check=True)
    tmp.replace(video)
