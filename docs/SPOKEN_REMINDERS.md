# Spoken Reminders (removed)

Removed 2026-10-07, **ruled by designer** ("Remove spoken reminders,
but document all your findings so we can make a better solution later
if requested"): the option "Let the computer say the reminder"
(Preferences > Reminders). This page keeps what was found, for a
request to bring it back. Reminders themselves:
[REMINDERS.md](REMINDERS.md).

## What It Was

In Task Coach since at least 2012 (release 1.3). Off by default; shown
on Linux, with "(Needs espeak)", and on macOS; hidden on Windows. When
a reminder window opened, after its sound, the computer said
"Reminder: <task subject>".

- `taskcoachlib/speak/speaker.py`: a `Speaker` singleton that ran
  `say` (macOS) or `espeak` (Linux) as a separate program, one text at
  a time: a text arriving while another was spoken waited, retried
  every second. On Windows a class that did nothing.
- `ReminderDialog.__init__` called `Speaker().say(...)` when
  `feature.sayreminder` was on.
- Packages: Fedora `Recommends: espeak-ng`; Arch `optdepends`
  espeak-ng (and its install message); Debian and Ubuntu nothing; the
  AppImage used the host's program; the Flatpak had none.

The last release with it: 2.0.3.0, tag `v2.0.3.0`, with
`SpeakerTest`, without the fix below.

## Why It Was Removed

Analysed 2026-10-06 and 2026-10-07 (P94 in
[MASTER_SCHEDULER_REFACTOR.md](MASTER_SCHEDULER_REFACTOR.md#pre-existing-issues),
P246 in [REFINEMENT_REFACTOR.md](REFINEMENT_REFACTOR.md)):

- It hid reminders (P246, the same in 2.0.3.0): with the option on and
  no `espeak` command, starting it raised `FileNotFoundError` while
  the reminder window was being made, so the reminder never showed;
  only the log had the error. Debian and Ubuntu install no `espeak`
  command, and their espeak-ng package names its command `espeak-ng`
  (`espeak` comes only from `espeak-ng-espeak` or the old `espeak`
  package). On a Debian 13 LXDE desktop (checked 2026-10-07) neither
  espeak, espeak-ng nor speech-dispatcher is installed. A fix before
  the removal (P246) logged the failure and used `espeak-ng` where
  `espeak` is missing.
- Nothing on Windows.
- A rare feature, off by default, outside the core of tasks,
  categories and efforts.

## A Better Solution

The plan of TODO.md 6 was pyttsx3 (2.99, July 2025). Read from its
package, 2026-10-07:

- Windows: SAPI5 through `comtypes`, plus `pywin32` and `pypiwin32`.
- macOS: `NSSpeechSynthesizer` or `AVSpeechSynthesizer` through the
  whole `pyobjc` (a requirement of `pyobjc>=2.4`, every framework).
- Linux: loads `libespeak-ng.so.1` or `libespeak.so.1`, so it needs
  espeak installed as before; the Flatpak would have to bundle it.
- Its sample (`say()` then `runAndWait()`) waits until the sentence is
  spoken: the window would freeze a few seconds per reminder.

A smaller way, with nothing new to package:

| Platform | How | Notes |
|----------|-----|-------|
| Windows | `win32com.client.Dispatch("SAPI.SpVoice").Speak(text, 1)` | pywin32 is already required ([DEPENDENCIES.md](DEPENDENCIES.md#pywin32-to-do-85)); flag 1 speaks without waiting |
| macOS | `say text` | always installed |
| Linux | `spd-say text` (speech-dispatcher), else `espeak-ng`, else `espeak` | speech-dispatcher is the desktop's speech service (Orca uses it); absent on the Debian 13 LXDE desktop checked |

Rules for it:

- Never speak while the reminder window is being made; start the
  speech after it shows, and only log a failure.
- Show the option only where a speech program is found, or say in
  Preferences what to install; probe there, not at each reminder.
- When many are due at once (a file opening with 134 due reminders
  would talk for minutes), say how many instead of each one.
- The Flatpak: whether its sandbox can reach a speech service is not
  researched.

## To Bring It Back

- `taskcoachlib/speak/` and `SpeakerTest` from `v2.0.3.0`, with the
  fix above, or the smaller way above.
- `config/defaults.py`: `"sayreminder": "False"` in `feature`; take
  `("feature", "sayreminder")` out of `_OBSOLETE_SETTINGS` in
  `config/settings.py` (an old settings file drops the option on load
  until then).
- `TaskReminderPage` in `gui/dialog/preferences.py`: the
  `addBooleanSetting("feature", "sayreminder", ...)` row.
- `ReminderDialog.__init__` in `gui/dialog/reminder.py`: the call after
  `sounds.play(...)`.
- Packages: Fedora's `Recommends`, Arch's `optdepends` and install
  message, the AppStream description's sentence
  (`build.in/debian/taskcoach.appdata.xml`).
- The translations still hold "Let the computer say the reminder" and
  "(Needs espeak)" until the next `msgmerge` marks them obsolete.
