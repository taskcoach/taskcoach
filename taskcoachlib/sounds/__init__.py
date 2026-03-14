"""
Task Coach - Your friendly task manager
Copyright (C) 2004-2016 Task Coach developers <developers@taskcoach.org>

Task Coach is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Task Coach is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import os

import wx
import wx.adv

from taskcoachlib.i18n import _
from taskcoachlib.meta.debug import log_step


_SOUNDS_DIR = os.path.dirname(__file__)

# Lookup table: (key, label, wav filename or None)
# key   - stored in settings
# label - shown in the dropdown
# file  - relative to _SOUNDS_DIR (None = no file)
#
# To regenerate or add sounds, run:
#   python3 taskcoachlib/sounds/generate_sounds.py
SOUNDS = (
    # key              label                        filename
    ("",               _("None"),                   None),
    # Gentle/Subtle
    ("gentle-chime",   _("Gentle Chime"),           "gentle-chime.wav"),
    ("water-drop",     _("Water Drop"),             "water-drop.wav"),
    ("wind-chime",     _("Wind Chime"),             "wind-chime.wav"),
    ("music-box",      _("Music Box"),              "music-box.wav"),
    # Bells/Chimes
    ("bright-bell",    _("Bright Bell"),            "bright-bell.wav"),
    ("bell-classic",   _("Bell Classic"),           "bell-classic.wav"),
    ("temple-bell",    _("Temple Bell"),            "temple-bell.wav"),
    ("sleigh-bell",    _("Sleigh Bell"),            "sleigh-bell.wav"),
    # Alert/Alarm
    ("soft-alarm",     _("Soft Alarm"),             "soft-alarm.wav"),
    ("alarm-clock",    _("Alarm Clock"),            "alarm-clock.wav"),
    ("rising-alert",   _("Rising Alert"),           "rising-alert.wav"),
    ("urgent-beep",    _("Urgent Beep"),            "urgent-beep.wav"),
    # Musical
    ("piano-note",     _("Piano Note"),             "piano-note.wav"),
    ("xylophone",      _("Xylophone"),              "xylophone.wav"),
    ("marimba",        _("Marimba"),                "marimba.wav"),
    ("harp-gliss",     _("Harp Gliss"),             "harp-gliss.wav"),
    # Digital/Modern
    ("two-tone",       _("Two Tone"),               "two-tone.wav"),
    ("electronic-ping", _("Electronic Ping"),       "electronic-ping.wav"),
    ("message-ping",   _("Message Ping"),           "message-ping.wav"),
    ("doorbell",       _("Doorbell"),               "doorbell.wav"),
)


def choices():
    """Return list of (key, label) pairs for addChoiceSetting."""
    return [(key, label) for key, label, _filename in SOUNDS]


def play(key):
    """Play the sound identified by key."""
    if not key:
        return
    for entry_key, _label, filename in SOUNDS:
        if entry_key == key:
            if filename is None:
                return
            path = os.path.join(_SOUNDS_DIR, filename)
            _play_wav(path)
            return
    log_step('Unknown sound key: %s' % key, prefix='SOUND')


def _play_wav(path):
    """Play a WAV file, falling back to system beep on failure.

    wx.adv.Sound uses the OSS backend on Linux, which is absent on
    modern distros (no /dev/dsp).  Play() returns True but produces no
    audio.  Use the platform's native CLI player instead:
    paplay (Linux/PulseAudio), afplay (macOS), wx.adv.Sound (Windows).
    See REMINDERS.md for details.
    """
    import subprocess
    from taskcoachlib import operating_system

    try:
        if operating_system.isGTK():
            subprocess.Popen(
                ['paplay', path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        elif operating_system.isMac():
            subprocess.Popen(
                ['afplay', path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        else:
            # Windows: wx.adv.Sound works natively
            sound = wx.adv.Sound(path)
            if sound.IsOk():
                sound.Play(wx.adv.SOUND_ASYNC)
            else:
                log_step('Sound not playable: %s - falling back to beep'
                         % path, prefix='SOUND')
                wx.Bell()
    except FileNotFoundError as e:
        log_step('Audio player not found: %s - falling back to beep'
                 % e, prefix='SOUND')
        wx.Bell()
    except Exception as e:
        log_step('Sound playback failed: %s - falling back to beep'
                 % e, prefix='SOUND')
        wx.Bell()
