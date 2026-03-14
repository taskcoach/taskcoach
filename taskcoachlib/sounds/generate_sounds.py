#!/usr/bin/env python3
"""Generate notification sound WAV files for Task Coach.

Usage:
    python3 taskcoachlib/sounds/generate_sounds.py

Generates all WAV files in the same directory as this script.
Existing files are overwritten.  Run this after modifying a
generator function or adding a new sound.

Each generator returns a list of 16-bit PCM samples at 22050 Hz.
Sounds use sine waves with harmonics and envelopes to approximate
real instruments.  See REMINDERS.md for the full sound list.
"""

import os
import struct
import math

_DIR = os.path.dirname(os.path.abspath(__file__))
_SAMPLE_RATE = 22050


def _generate_wav(samples_func):
    """Generate a WAV file from a sample generator function."""
    samples = samples_func(_SAMPLE_RATE)
    data = b''.join(
        struct.pack('<h', max(-32767, min(32767, s))) for s in samples
    )
    header = struct.pack(
        '<4sI4s4sIHHIIHH4sI',
        b'RIFF', 36 + len(data), b'WAVE',
        b'fmt ', 16, 1, 1, _SAMPLE_RATE,
        _SAMPLE_RATE * 2, 2, 16,
        b'data', len(data),
    )
    return header + data


def _envelope(t, duration, attack=0.01, release=0.05):
    """Smooth fade in/out to avoid clicks."""
    if t < attack:
        return t / attack
    if t > duration - release:
        return (duration - t) / release
    return 1.0


# --- Gentle/Subtle ---

def _gentle_chime(sr):
    """Soft single-note chime at C6 (1047 Hz)."""
    duration, freq = 0.6, 1047
    samples = []
    for i in range(int(sr * duration)):
        t = i / sr
        env = _envelope(t, duration, attack=0.005, release=0.3)
        decay = math.exp(-t * 4)
        value = env * decay * math.sin(2 * math.pi * freq * t)
        value += 0.3 * env * decay * math.sin(2 * math.pi * freq * 2 * t)
        samples.append(int(32767 * 0.7 * value))
    return samples


def _water_drop(sr):
    """Soft bubble/plop sound."""
    duration, freq = 0.3, 600
    samples = []
    for i in range(int(sr * duration)):
        t = i / sr
        env = _envelope(t, duration, attack=0.001, release=0.15)
        decay = math.exp(-t * 12)
        f = freq * (1.0 + 2.0 * math.exp(-t * 20))
        value = env * decay * math.sin(2 * math.pi * f * t)
        samples.append(int(32767 * 0.6 * value))
    return samples


def _wind_chime(sr):
    """Airy metallic shimmer - two overlapping high tones."""
    duration = 0.8
    freqs = [2093, 2637]  # C7, E7
    samples = []
    for i in range(int(sr * duration)):
        t = i / sr
        env = _envelope(t, duration, attack=0.01, release=0.5)
        value = 0
        for j, freq in enumerate(freqs):
            delay = j * 0.08
            if t > delay:
                td = t - delay
                decay = math.exp(-td * 3)
                value += decay * math.sin(2 * math.pi * freq * td)
                value += 0.3 * decay * math.sin(2 * math.pi * freq * 1.5 * td)
        samples.append(int(32767 * 0.35 * env * value))
    return samples


def _music_box(sr):
    """Delicate single music box note at E6."""
    duration, freq = 0.7, 1319
    samples = []
    for i in range(int(sr * duration)):
        t = i / sr
        env = _envelope(t, duration, attack=0.001, release=0.4)
        decay = math.exp(-t * 3.5)
        value = env * decay * (
            math.sin(2 * math.pi * freq * t)
            + 0.15 * math.sin(2 * math.pi * freq * 2 * t)
            + 0.08 * math.sin(2 * math.pi * freq * 4 * t)
        )
        samples.append(int(32767 * 0.6 * value))
    return samples


# --- Bells/Chimes ---

def _bright_bell(sr):
    """Clear bell ring at E6 (1319 Hz)."""
    duration, freq = 0.5, 1319
    samples = []
    for i in range(int(sr * duration)):
        t = i / sr
        env = _envelope(t, duration, attack=0.002, release=0.2)
        decay = math.exp(-t * 5)
        value = env * decay * math.sin(2 * math.pi * freq * t)
        value += 0.4 * env * decay * math.sin(2 * math.pi * freq * 3 * t)
        samples.append(int(32767 * 0.7 * value))
    return samples


def _bell_classic(sr):
    """Simple clean bell at G5 (784 Hz)."""
    duration, freq = 0.6, 784
    samples = []
    for i in range(int(sr * duration)):
        t = i / sr
        env = _envelope(t, duration, attack=0.001, release=0.3)
        decay = math.exp(-t * 3)
        value = env * decay * (
            math.sin(2 * math.pi * freq * t)
            + 0.5 * math.sin(2 * math.pi * freq * 2.76 * t)
            + 0.25 * math.sin(2 * math.pi * freq * 5.04 * t)
        )
        samples.append(int(32767 * 0.5 * value))
    return samples


def _temple_bell(sr):
    """Deep resonant gong at C4 (262 Hz)."""
    duration, freq = 1.0, 262
    samples = []
    for i in range(int(sr * duration)):
        t = i / sr
        env = _envelope(t, duration, attack=0.005, release=0.6)
        decay = math.exp(-t * 1.8)
        value = env * decay * (
            math.sin(2 * math.pi * freq * t)
            + 0.6 * math.sin(2 * math.pi * freq * 2.4 * t)
            + 0.4 * math.sin(2 * math.pi * freq * 3.8 * t)
            + 0.2 * math.sin(2 * math.pi * freq * 5.1 * t)
        )
        samples.append(int(32767 * 0.4 * value))
    return samples


def _sleigh_bell(sr):
    """Bright jingling - rapid burst of high partials."""
    duration, freq = 0.4, 3000
    samples = []
    for i in range(int(sr * duration)):
        t = i / sr
        env = _envelope(t, duration, attack=0.001, release=0.2)
        decay = math.exp(-t * 6)
        value = env * decay * (
            math.sin(2 * math.pi * freq * t)
            + 0.8 * math.sin(2 * math.pi * (freq * 1.07) * t)
            + 0.6 * math.sin(2 * math.pi * (freq * 1.17) * t)
            + 0.4 * math.sin(2 * math.pi * (freq * 0.93) * t)
        )
        value *= 1.0 + 0.3 * math.sin(2 * math.pi * 25 * t)
        samples.append(int(32767 * 0.3 * value))
    return samples


# --- Alert/Alarm ---

def _soft_alarm(sr):
    """Gentle two-pulse alarm tone at A5 (880 Hz)."""
    pulse_dur, gap, freq = 0.15, 0.1, 880
    samples = []
    for _pulse in range(2):
        for i in range(int(sr * pulse_dur)):
            t = i / sr
            env = _envelope(t, pulse_dur, attack=0.005, release=0.05)
            value = env * math.sin(2 * math.pi * freq * t)
            samples.append(int(32767 * 0.6 * value))
        samples.extend([0] * int(sr * gap))
    return samples


def _alarm_clock(sr):
    """Classic alarm - 4 rapid beeps at B5 (988 Hz)."""
    beep_dur, gap, freq = 0.08, 0.06, 988
    samples = []
    for _beep in range(4):
        for i in range(int(sr * beep_dur)):
            t = i / sr
            env = _envelope(t, beep_dur, attack=0.002, release=0.02)
            value = env * math.sin(2 * math.pi * freq * t)
            samples.append(int(32767 * 0.6 * value))
        samples.extend([0] * int(sr * gap))
    return samples


def _rising_alert(sr):
    """Ascending 3-note scale (C5, E5, G5)."""
    note_dur, gap = 0.15, 0.03
    freqs = [523, 659, 784]  # C5, E5, G5
    samples = []
    for freq in freqs:
        for i in range(int(sr * note_dur)):
            t = i / sr
            env = _envelope(t, note_dur, attack=0.003, release=0.06)
            decay = math.exp(-t * 4)
            value = env * decay * math.sin(2 * math.pi * freq * t)
            value += 0.3 * env * decay * math.sin(2 * math.pi * freq * 2 * t)
            samples.append(int(32767 * 0.65 * value))
        samples.extend([0] * int(sr * gap))
    return samples


def _urgent_beep(sr):
    """Sharp double beep at D6 (1175 Hz)."""
    beep_dur, gap, freq = 0.1, 0.08, 1175
    samples = []
    for _beep in range(2):
        for i in range(int(sr * beep_dur)):
            t = i / sr
            env = _envelope(t, beep_dur, attack=0.001, release=0.03)
            value = env * math.sin(2 * math.pi * freq * t)
            value += 0.5 * env * math.sin(2 * math.pi * freq * 2 * t)
            samples.append(int(32767 * 0.7 * value))
        samples.extend([0] * int(sr * gap))
    return samples


# --- Musical ---

def _piano_note(sr):
    """Single piano-like note at A4 (440 Hz)."""
    duration, freq = 0.8, 440
    samples = []
    for i in range(int(sr * duration)):
        t = i / sr
        env = _envelope(t, duration, attack=0.005, release=0.4)
        decay = math.exp(-t * 2.5)
        value = env * decay * (
            math.sin(2 * math.pi * freq * t)
            + 0.5 * math.sin(2 * math.pi * freq * 2 * t)
            + 0.25 * math.sin(2 * math.pi * freq * 3 * t)
            + 0.12 * math.sin(2 * math.pi * freq * 4 * t)
        )
        samples.append(int(32767 * 0.5 * value))
    return samples


def _xylophone(sr):
    """Bright wooden mallet hit at G5 (784 Hz)."""
    duration, freq = 0.4, 784
    samples = []
    for i in range(int(sr * duration)):
        t = i / sr
        env = _envelope(t, duration, attack=0.001, release=0.2)
        decay = math.exp(-t * 7)
        value = env * decay * (
            math.sin(2 * math.pi * freq * t)
            + 0.4 * math.sin(2 * math.pi * freq * 3 * t)
            + 0.15 * math.sin(2 * math.pi * freq * 6 * t)
        )
        samples.append(int(32767 * 0.6 * value))
    return samples


def _marimba(sr):
    """Warm deep wooden mallet at C4 (262 Hz)."""
    duration, freq = 0.5, 262
    samples = []
    for i in range(int(sr * duration)):
        t = i / sr
        env = _envelope(t, duration, attack=0.002, release=0.25)
        decay = math.exp(-t * 4)
        value = env * decay * (
            math.sin(2 * math.pi * freq * t)
            + 0.3 * math.sin(2 * math.pi * freq * 4 * t)
            + 0.1 * math.sin(2 * math.pi * freq * 10 * t)
        )
        samples.append(int(32767 * 0.6 * value))
    return samples


def _harp_gliss(sr):
    """Quick ascending harp sweep (C5, E5, G5, C6)."""
    note_dur, overlap = 0.12, 0.08
    freqs = [523, 659, 784, 1047]  # C5, E5, G5, C6
    total = note_dur + (len(freqs) - 1) * (note_dur - overlap) + 0.3
    n = int(sr * total)
    samples = [0] * n
    for idx, freq in enumerate(freqs):
        start = int(sr * idx * (note_dur - overlap))
        note_n = int(sr * (note_dur + 0.3))
        for i in range(min(note_n, n - start)):
            t = i / sr
            env = _envelope(t, note_dur + 0.3, attack=0.002, release=0.2)
            decay = math.exp(-t * 4)
            value = env * decay * math.sin(2 * math.pi * freq * t)
            value += 0.3 * env * decay * math.sin(2 * math.pi * freq * 2 * t)
            if start + i < n:
                samples[start + i] += int(32767 * 0.35 * value)
    return samples


# --- Digital/Modern ---

def _two_tone(sr):
    """Ascending two-note alert (C5 then E5)."""
    note_dur, gap = 0.25, 0.05
    freqs = [523, 659]  # C5, E5
    samples = []
    for freq in freqs:
        for i in range(int(sr * note_dur)):
            t = i / sr
            env = _envelope(t, note_dur, attack=0.005, release=0.08)
            decay = math.exp(-t * 3)
            value = env * decay * math.sin(2 * math.pi * freq * t)
            samples.append(int(32767 * 0.7 * value))
        samples.extend([0] * int(sr * gap))
    return samples


def _electronic_ping(sr):
    """Clean digital ping at A5 (880 Hz)."""
    duration, freq = 0.25, 880
    samples = []
    for i in range(int(sr * duration)):
        t = i / sr
        env = _envelope(t, duration, attack=0.001, release=0.12)
        decay = math.exp(-t * 10)
        value = env * decay * (
            math.sin(2 * math.pi * freq * t)
            + 0.1 * math.sin(2 * math.pi * freq * 2 * t)
        )
        samples.append(int(32767 * 0.7 * value))
    return samples


def _message_ping(sr):
    """IM notification - quick ascending pair (E5, B5)."""
    note_dur, gap = 0.1, 0.04
    freqs = [659, 988]  # E5, B5
    samples = []
    for freq in freqs:
        for i in range(int(sr * note_dur)):
            t = i / sr
            env = _envelope(t, note_dur, attack=0.001, release=0.05)
            decay = math.exp(-t * 8)
            value = env * decay * math.sin(2 * math.pi * freq * t)
            samples.append(int(32767 * 0.65 * value))
        samples.extend([0] * int(sr * gap))
    return samples


def _doorbell(sr):
    """Classic ding-dong (E5 then C5)."""
    note_dur, gap = 0.3, 0.05
    freqs = [659, 523]  # E5, C5 (descending)
    samples = []
    for freq in freqs:
        for i in range(int(sr * note_dur)):
            t = i / sr
            env = _envelope(t, note_dur, attack=0.003, release=0.15)
            decay = math.exp(-t * 3)
            value = env * decay * (
                math.sin(2 * math.pi * freq * t)
                + 0.4 * math.sin(2 * math.pi * freq * 2 * t)
                + 0.15 * math.sin(2 * math.pi * freq * 3 * t)
            )
            samples.append(int(32767 * 0.55 * value))
        samples.extend([0] * int(sr * gap))
    return samples


# --- Generator table ---

SOUNDS = {
    "gentle-chime.wav": _gentle_chime,
    "water-drop.wav": _water_drop,
    "wind-chime.wav": _wind_chime,
    "music-box.wav": _music_box,
    "bright-bell.wav": _bright_bell,
    "bell-classic.wav": _bell_classic,
    "temple-bell.wav": _temple_bell,
    "sleigh-bell.wav": _sleigh_bell,
    "soft-alarm.wav": _soft_alarm,
    "alarm-clock.wav": _alarm_clock,
    "rising-alert.wav": _rising_alert,
    "urgent-beep.wav": _urgent_beep,
    "piano-note.wav": _piano_note,
    "xylophone.wav": _xylophone,
    "marimba.wav": _marimba,
    "harp-gliss.wav": _harp_gliss,
    "two-tone.wav": _two_tone,
    "electronic-ping.wav": _electronic_ping,
    "message-ping.wav": _message_ping,
    "doorbell.wav": _doorbell,
}


if __name__ == "__main__":
    total = 0
    for filename, generator in sorted(SOUNDS.items()):
        path = os.path.join(_DIR, filename)
        wav_data = _generate_wav(generator)
        with open(path, 'wb') as f:
            f.write(wav_data)
        size = len(wav_data)
        total += size
        print(f"  {size:6d}  {filename}")
    print(f"  {total:6d}  TOTAL ({len(SOUNDS)} files)")
