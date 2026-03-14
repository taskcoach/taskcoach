# Reminders

## Overview

When a task's reminder datetime is reached, Task Coach shows a popup
dialog (`taskcoachlib/gui/dialog/reminder.py`) that:

1. Brings the window to front (`RequestUserAttention`)
2. Freezes the dialog briefly to prevent accidental dismiss
3. Plays the configured reminder sound
4. Optionally speaks the reminder text via text-to-speech

## Reminder Sound

### Settings

- **Setting**: `feature.reminder_sound` in the INI file
- **Default**: `gentle-chime`
- **Values**: A key from the `SOUNDS` table in `taskcoachlib/sounds/__init__.py`
- **UI**: Preferences > Reminders > "Reminder sound" dropdown with Test button

### Available Sounds

20 bundled notification sounds in `taskcoachlib/sounds/*.wav`:

| Category | Key | Label |
|----------|-----|-------|
| Gentle/Subtle | `gentle-chime` | Gentle Chime |
| | `water-drop` | Water Drop |
| | `wind-chime` | Wind Chime |
| | `music-box` | Music Box |
| Bells/Chimes | `bright-bell` | Bright Bell |
| | `bell-classic` | Bell Classic |
| | `temple-bell` | Temple Bell |
| | `sleigh-bell` | Sleigh Bell |
| Alert/Alarm | `soft-alarm` | Soft Alarm |
| | `alarm-clock` | Alarm Clock |
| | `rising-alert` | Rising Alert |
| | `urgent-beep` | Urgent Beep |
| Musical | `piano-note` | Piano Note |
| | `xylophone` | Xylophone |
| | `marimba` | Marimba |
| | `harp-gliss` | Harp Gliss |
| Digital/Modern | `two-tone` | Two Tone |
| | `electronic-ping` | Electronic Ping |
| | `message-ping` | Message Ping |
| | `doorbell` | Doorbell |

WAV files are mono 16-bit 22050 Hz, ~472 KB total.  Generated
programmatically using sine waves with harmonics and envelopes.

### Adding or Modifying Sounds

1. Edit the generator function in
   `taskcoachlib/sounds/generate_sounds.py`
2. Run: `python3 taskcoachlib/sounds/generate_sounds.py`
3. Add a row to the `SOUNDS` tuple in
   `taskcoachlib/sounds/__init__.py`
4. Commit the new WAV file and updated code

Naming convention: lowercase, hyphen-separated, descriptive.
Example: `soft-marimba.wav`

### Sound Playback Strategy

`wx.adv.Sound` (wxPython's built-in audio) uses the OSS backend on
Linux.  OSS is not present on modern Linux distros - the device nodes
`/dev/dsp` and `/dev/mixer` do not exist.  `wx.adv.Sound.Play()`
returns True but produces no audible output.  `wx.Bell()` has the
same limitation.  This is a known wxWidgets issue
([#18000](https://github.com/wxWidgets/wxWidgets/issues/18000),
[#14899](https://github.com/wxWidgets/wxWidgets/issues/14899)) with
no fix in wxWidgets 3.2.x.

The playback function (`taskcoachlib/sounds/_play_wav`) uses the
platform's native CLI audio player instead:

#### Linux (GTK) - `paplay`

`paplay` is the PulseAudio command-line player.  It ships with
`pulseaudio-utils` which is installed by default on every desktop
Linux distribution.

- **PulseAudio** (Debian 12, Ubuntu 22.04, Mint, etc.): `paplay`
  talks directly to the PulseAudio daemon.
- **PipeWire** (Fedora 39+, Ubuntu 22.10+, Arch): PipeWire provides
  a `paplay` compatibility wrapper via `pipewire-pulse`.  No
  configuration needed.
- **ALSA only** (rare, server installs): `paplay` is not available.
  Falls back to `wx.adv.Sound` which may work if `osspd` is
  installed, otherwise silent.
- **Wayland / X11**: No difference - `paplay` works on both.

`paplay` supports WAV, OGG, FLAC, and other formats natively.

#### macOS - `afplay`

`afplay` is Apple's built-in command-line audio player.  Ships with
every macOS installation since 10.5.  Supports WAV, AIFF, MP3, AAC,
and other Core Audio formats.

#### Windows - `wx.adv.Sound`

On Windows, `wx.adv.Sound` works correctly using the native Windows
multimedia API (`PlaySound`).  No subprocess needed.

#### Fallback Chain

```
_play_wav(path)
    Linux?  -> subprocess.Popen(['paplay', path])
                if FileNotFoundError -> wx.adv.Sound (may be silent)
    macOS?  -> subprocess.Popen(['afplay', path])
                if FileNotFoundError -> wx.adv.Sound
    Windows -> wx.adv.Sound.Play(SOUND_ASYNC)
                if not IsOk() -> wx.Bell()
    Any error -> wx.Bell()
```

All subprocess calls are non-blocking (`Popen` returns immediately).
Errors are logged via `log_step` with the `SOUND` prefix.

## Text-to-Speech

Optional spoken reminder using `espeak` (Linux) or `say` (macOS).
Plays after the sound.  See [TODO.md](TODO.md) for modernization
proposal.

## Snooze

Configurable snooze times in Preferences > Reminders.  See
[DATETIME_PRESETS.md](DATETIME_PRESETS.md) for default reminder
datetime presets.

## Related Documentation

- [SCHEDULERS.md](SCHEDULERS.md) - How reminders are triggered
  (MasterScheduler polls tasks every second, fires
  `task.reminder.trigger`, ReminderController shows the dialog)
- [DATETIME_PRESETS.md](DATETIME_PRESETS.md) - Default reminder
  datetime presets, reminder scheduling on file load
- [TODO.md](TODO.md) - Text-to-speech modernization proposal

## Key Files

| File | Role |
|------|------|
| `taskcoachlib/sounds/__init__.py` | Sound table, playback |
| `taskcoachlib/sounds/generate_sounds.py` | WAV generator script (dev tool) |
| `taskcoachlib/sounds/*.wav` | Bundled sound files (20 WAVs, ~472 KB) |
| `taskcoachlib/gui/dialog/reminder.py` | Reminder popup dialog |
| `taskcoachlib/gui/dialog/preferences.py` | `TaskReminderPage` - preferences UI |
| `taskcoachlib/config/defaults.py` | Default `reminder_sound` value |
| `taskcoachlib/speak/speaker.py` | Text-to-speech |
| `taskcoachlib/gui/remindercontroller.py` | Polling + dialog trigger |

## Known Limitations

1. **wx.adv.Sound silent on Linux** - OSS backend, no /dev/dsp.
   Workaround: `paplay` subprocess.  See wxWidgets
   [#18000](https://github.com/wxWidgets/wxWidgets/issues/18000).

2. **wx.Bell() silent on Linux** - Same OSS issue.  All sounds use
   bundled WAV files played via `paplay` instead.

3. **wx.Button.SetBitmap suppressed on GTK3** - The `gtk-button-images`
   setting is False by default on GNOME.  The Test button uses
   `ThemedGenBitmapTextButton` (same as `IconPicker`) which draws its
   own bitmap and is not affected.  See wxWidgets
   [#18874](https://github.com/wxWidgets/wxWidgets/issues/18874).

4. **espeak not installed by default** - Text-to-speech on Linux
   requires `sudo apt install espeak`.
