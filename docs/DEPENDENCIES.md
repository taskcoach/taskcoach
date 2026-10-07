# Dependencies

Why each third-party package not yet ruled on is there, the code that
uses it, what it does on each platform, its size, and what replacing
or removing it would take. **Asked by designer 2026-10-03** (To Do 83
to 91 in [MASTER_SCHEDULER_REFACTOR.md](MASTER_SCHEDULER_REFACTOR.md#to-do)).
Where each build gets each package:
[PACKAGING.md](PACKAGING.md#install-overview-by-build-target).

Sizes are installed sizes of the Debian 13 packages this branch is
tested with (`dpkg-query`, `du`); pip builds bundle the same code.
"Inferred" marks what was read but not run.

## Table of Contents

1. [wxPython (To Do 83)](#wxpython-to-do-83)
2. [PyGObject (To Do 84)](#pygobject-to-do-84)
3. [pywin32 (To Do 85)](#pywin32-to-do-85)
4. [keyring (To Do 86)](#keyring-to-do-86)
5. [pyenchant (To Do 87)](#pyenchant-to-do-87)
6. [pywayland (To Do 88)](#pywayland-to-do-88)
7. [python-dateutil (To Do 89)](#python-dateutil-to-do-89)
8. [chardet (To Do 90)](#chardet-to-do-90)
9. [pyparsing (To Do 91)](#pyparsing-to-do-91)
10. [dbus-python (To Do 92)](#dbus-python-to-do-92)

---

## wxPython (To Do 83)

**Why**: the whole user interface: every window, view, dialog and
menu, drag and drop, the tray on Windows and macOS, and the event loop
and timers. There since the first commit (2005).

**Code**: 104 of 258 modules import `wx` (75,212 of 122,453 lines),
with 4,996 `wx.` references to 614 names; 55 of 154 test files.
`gui/`, `widgets/`, the bundled tree widget (`patches/`, 15,938 lines)
and the wx parts of `thirdparty/` hold about 93,000 lines, 76% of the
code. The domain and persistence layers use it too: deferred calls and
timers (`patterns/deferred.py`), idle-time saving
(`persistence/autosaver.py`), colours (`domain/task/task.py`), the
locale (`i18n`), the system font (`persistence/xml/reader.py`).

**Platforms**: required everywhere; the GTK3 port on Linux (4.0.7 on
Ubuntu 22.04 to 4.3.1 in the Flatpak, Windows and macOS builds),
Cocoa on macOS, Win32 on Windows. On native Wayland docking hints and
popup positions are off ([WAYLAND_ISSUES.md](WAYLAND_ISSUES.md)); only
the Flatpak forces X11. Missing, start-up stops with a traceback
(`workarounds/monkeypatches.py` imports it unguarded).

**Size**: 55 MB (`python3-wxgtk4.0` 4.2.3: 44 MB installed) plus 22 MB
of wxWidgets libraries; Debian's package also pulls Pillow (1.9 MB),
which Task Coach never imports.

**Replacing or removing it**: a rewrite of the interface onto another
toolkit (Qt, GTK 4, Tk): about 93,000 lines, every documented
behaviour to verify again. Not a candidate.

**Found**: PACKAGING.md gives 4.2.0 as the minimum ("HyperTreeList
stability"), but the tree views run on the bundled copy on every
version, and Ubuntu 22.04, a supported build, ships 4.0.7.

**Ruling**: keep, **ruled by designer 2026-10-03**.

---

## PyGObject (To Do 84)

**Why**: the Linux tray icon through AppIndicator (StatusNotifierItem):
it works on Wayland and GNOME (with the extension), and its menu keeps
right-click where wx's XEmbed tray loses it (LXDE, KDE on X11)
([SYSTEM_TRAY.md](SYSTEM_TRAY.md)). Added 2026-01 (#235). Also: the GTK
version in the start-up report, the multi-line text boxes' padding,
the Flatpak's tray icon check, the desktop's idle time through Gio,
the X11 Thunderbird drop's files, and the test runner's certified
platform check.

**Code**: 6 files import `gi` (`gui/appindicator.py`, 167 lines;
`application/application.py`; `powermgt/idle.py`; `widgets/textctrl.py`;
`widgets/draganddrop.py`, `x11_drag_files()`; `tests/test.py`), all
guarded; `gui/taskbaricon.py` builds the tray's GTK menu through it
(`AppIndicatorTaskBarIcon`, 624 lines, its menu builder 187). About 40
call sites; about 430 lines call GTK directly, about 870 with the
AppIndicator tray class.

**Platforms**: Linux only, never imported on Windows or macOS. A
dependency of the deb (`python3-gi`, the AppIndicator typelib), rpm
and Arch packages; from the GNOME runtime in the Flatpak; absent from
the AppImage (no AppIndicator tray, P159). Missing: the tray falls
back to wx's XEmbed icon where the desktop has one, else no tray; the
GTK line and the padding fall back quietly. The setup scripts do not
install it (they rely on the distro's).

**Size**: `python3-gi` 780 KB installed, the GLib and GTK typelibs
1.8 MB, the AppIndicator typelib and library 123 KB (Debian 13).
Ubuntu 22.04 has 3.42, Ubuntu 24.04 3.48, Debian 13 3.50.

**Keep or replace**: checked in the app on a desktop whose tray speaks
StatusNotifier only (a stand-in watcher on a private session bus):
with PyGObject the tray icon registers and its menu works (every item
clicked, P169); without it Task Coach logs "No working tray backend
available ... running without a tray icon" and has none.

| Option | The Linux tray | Cost |
|---|---|---|
| Keep | on every desktop with a tray: AppIndicator, StatusNotifier or, where there is none, the X11 tray area | `python3-gi` and typelibs, 2.6 MB |
| Remove | wx's own tray, only where the desktop has an X11 tray area; its right-click menu never opens on LXDE and KDE X11 ([SYSTEM_TRAY.md](SYSTEM_TRAY.md), confirmed there); none on Wayland or GNOME (checked: no icon) | saves 2.6 MB; the start-up report loses its GTK line, the description box its theme padding |
| Replace: ctypes to the AppIndicator and GTK C libraries | the same | the wrapper (167 lines) and menu builder (187) rewritten against C functions, where a wrong argument crashes; the C libraries stay; not prototyped |
| Replace: StatusNotifier and its menu over D-Bus ourselves | the same | two D-Bus protocols written and kept by us; not prototyped |

Since 2026-10-06 it also carries the D-Bus calls dbus-python made (To Do 92).

**Ruling**: keep, **ruled by designer 2026-10-03**. Removing it
loses the tray on Wayland and GNOME and the menu on LXDE and KDE X11;
replacing it saves 2.6 MB for a rewrite of the tray against C or
D-Bus.

---

## pywin32 (To Do 85)

**Why**: Windows calls:
- Outlook (classic) mail dropped on a task: COM (`mailer/outlook.py`).
- The Documents and AppData folders and following `.lnk` shortcuts to
  the templates and data folders (`config/settings.py`).
- Window styles: the editor's own taskbar button
  (`widgets/dialog.py`), double buffering (`gui/mainwindow.py`).
- Monitor geometry (`workarounds/display.py`, which replaces
  `wx.Display`).

**Code**: 6 modules, plus the DLL set-up in `taskcoach.py` and the
version line in the start-up report; about 25 call sites, about 235
lines that exist for it. Tests only mock Outlook.

**Platforms**: Windows only, required: imported unguarded at
start-up (`workarounds/display.py`, through `workarounds/__init__.py`),
so the Windows build does not start without it. Never imported on
Linux or macOS. Nothing here can run it (no Windows): this section is
read from the code and the packages.

**Size**: pywin32 312: a 6.8 MB wheel for Python 3.11 on Windows, about
15 MB installed; the build copies its DLLs next to Python.

**Keep or replace**:

| Option | What changes for Windows users | Cost |
|---|---|---|
| Keep | nothing | 6.8 MB download |
| Remove | the app does not start until `display.py`'s import is guarded; then the Outlook drop, the Documents and AppData folders, `.lnk` shortcuts to the data folders, the editors' own taskbar buttons and monitor changes all go | saves 6.8 MB |
| Replace: comtypes (291 KB, MIT) for the two COM uses (Outlook, shortcuts) and ctypes for the Windows API calls | the same, if the rewrite is right | about 235 lines rewritten, none testable here, the Outlook drop untested even today ([EMAIL_ATTACHMENTS.md](EMAIL_ATTACHMENTS.md)); not prototyped |

**Ruling**: keep, **ruled by designer 2026-10-03**. Removing it
breaks the Windows build's start and six features; replacing it rewrites every Windows call with
nothing here to test them on. 2026-10-04: Thunderbird Portable's
profile lookup (WMI) went with the Thunderbird profile reader
([EMAIL_ATTACHMENTS.md](EMAIL_ATTACHMENTS.md#decisions) 8).

---

## keyring (To Do 86)

**Removed 2026-10-04** with the IMAP reader it served: mail stays
local, **ruled by designer**
([EMAIL_ATTACHMENTS.md](EMAIL_ATTACHMENTS.md#decisions) 8), over the
keep ruling of 2026-10-03. It stored the password of an IMAP account
whose Thunderbird mail was dropped on a task. Its removal takes
SecretStorage, jeepney, jaraco and more-itertools (0.7 MB) off Debian
installs, and 19 MB, mostly cryptography, off the AppImage and
Flatpak.

---|---|---|
| Keep | asked once, stored if ticked | the packages above |
| Remove | asked once per session; about 65 lines and the packaging lines go | saves 0.7 MB on Debian (cryptography stays for other programs), 19 MB in the Linux pip builds |
| Our own store per system: Secret Service over D-Bus, the Windows Credential Manager and the macOS Keychain through ctypes | stored as today | three code paths instead of one library, two of them not testable here; not prototyped |

**Ruling**: keep, **ruled by designer 2026-10-03**. The stored
password works; removing it asks for the password every session, and
replacing it writes three platform paths to save one maintained
library.

**Separate issue**: P177, the drop doing nothing on a desktop with no
keyring service.

---

## pyenchant (To Do 87)

**Why**: spell checking in the Subject and Description fields of the
editors: squiggles (light and dark colours), five suggestions, "Add
to dictionary" and "Ignore" on the right-click menu, and Preferences'
"Enable spell checking" and language ([SPELLCHECKING.md](SPELLCHECKING.md)).
Added 2026-01 (#297).

**Code**: 1 module, `widgets/textctrl.py` (guarded import, 6 functions
at 8 call sites); about 430 lines exist for spell checking (225 in
`textctrl.py`, 197 in Preferences, three settings sections).

**Platforms**: pyenchant 3.x loads the C library libenchant, which
uses Hunspell or Aspell and the installed dictionaries. Ubuntu 22.04
has 3.2.0, Ubuntu 24.04 3.2.2, Debian 13 3.3.0rc1. The deb, rpm and
Arch packages depend on it and recommend an English dictionary.
Windows: pyenchant's Windows wheel (36 MB) carries libenchant, Hunspell
and 61 other DLLs; the build adds an en_US dictionary. macOS and the
Linux pip builds get the plain wheel, with no C library: the macOS
build adds none (P176).

**Size**: `python3-enchant` 180 KB, `libenchant-2-2` 225 KB, plus
Hunspell (856 KB) and a dictionary (an English one 1.6 MB); Windows:
the 36 MB wheel.

**Keep or replace**: checked in the app, a task's Description with
"Teh quik brown fox jumpd":

- With pyenchant: red squiggles under "Teh", "quik" and "jumpd"; a
  right-click on "Teh" offers The, Tech, Te, Th, Eh, Add to dictionary
  and Ignore.
- Without it: no squiggles; the right-click menu has only Undo, Cut,
  Copy, Paste, Delete and Select All; Preferences greys out "Enable
  spell checking" with "Install pyenchant" (read in `preferences.py`).

| Option | Spell checking | Cost |
|---|---|---|
| Keep | as above | 180 KB plus the C library |
| Remove | none; about 430 lines and three settings sections go | saves 180 KB; libenchant stays installed for other programs |
| wx's own spell check | none: the fields are Scintilla (StyledTextCtrl), which has none, and wxPython 4.2.3 has no `TextCtrl.EnableProofCheck` (checked) | the fields rewritten |
| Our own binding to libenchant (ctypes) | the same: a 53-line prototype matched pyenchant on 2,964 words checked and 964 suggestion lists | saves 180 KB on Linux; on Windows the build would have to ship libenchant and its DLLs itself, which pyenchant's wheel does today |

**Ruling**: keep, **ruled by designer 2026-10-03**. Removing it
loses spell checking; our own binding saves 180 KB and takes on the
Windows libraries.

**Separate issue**: P176, the macOS build without libenchant.

---

## pywayland (To Do 88)

**Why**:
- The Idle time notice (off by default) on Wayland desktops that offer
  `ext-idle-notify-v1`: KDE Plasma 6, wlroots desktops (Sway,
  Hyprland, niri) and COSMIC ([IDLE.md](IDLE.md)). Added 2026-05.
- The tray's hide and restore on KDE Plasma Wayland, keeping the
  taskbar entry through `org_kde_plasma_window_management`. Added
  2026-06; deferred by ruling for users of that desktop to test (D5):
  KWin may offer that protocol only to apps that list it in their
  `.desktop` file, which ours does not.

**Code**: 2 modules, imports lazy and guarded (`powermgt/idle.py`,
`gui/toplevelcontroller.py`); about 312 lines of ours (141 for idle
time, 171 for the KDE controller) and 1,363 lines of generated
protocol bindings in `thirdparty/` (279 idle, 1,084 KDE); about 25
calls.

**Platforms**: only on GTK with `WAYLAND_DISPLAY` set; X11 uses the
X screensaver extension, GNOME Mutter over D-Bus ([IDLE.md](IDLE.md)).
Optional everywhere: recommended by the Debian 13 deb and the rpm,
optional on Arch, absent from Debian 12, Ubuntu, the AppImage, the
Flatpak (X11), Windows and macOS.

**Size**: `python3-pywayland` 561 KB installed, plus the cffi backend
(238 KB); the generated bindings in `thirdparty/` 160 KB.

**Keep or replace**: checked in the app on a Wayland compositor
(labwc, wlroots, run headless here) with "Idle time notice" at 1
minute and an effort being tracked, nothing touched:

- With pywayland: `[IDLE] Selected backend: ext_idle_notify`, and after
  the minute `Idle threshold reached while tracking effort`.
- Without it: `[IDLE] WARNING: no backend available; idle-time notice
  will not function`.

| Option | The Idle time notice on KDE Plasma 6 Wayland, wlroots desktops (Sway, Hyprland, labwc, niri) and COSMIC | Cost |
|---|---|---|
| Keep | works | 0.8 MB where installed; optional |
| Remove | none on those desktops; about 312 lines and 1,363 lines of bindings go | saves 0.8 MB where installed |
| Replace: ctypes to libwayland-client | works, if the rewrite is right; a mistake crashes instead of raising | the protocol handling rewritten; not prototyped |

Its other use, the KDE Plasma Wayland window controller, is deferred
by ruling (D5); it does not change this decision.

**Ruling**: keep, **ruled by designer 2026-10-03**. It is optional
and costs nothing where it is not installed; removing it loses the Idle time notice on those
desktops.

---

## python-dateutil (To Do 89)

**Why**: the date columns of File > Import > CSV (planned start, due,
actual start, completion, reminder), with the wizard's day-first or
month-first choice. CSV import since 1.2.11 (2011).

**Code**: 1 module, `persistence/csv/reader.py`: `parse_date_time`
and its reading rules (about 110 lines), reached from 5 fields; 27
date tests in `CSVReaderTest`. Nothing else Task Coach uses needs
it.

**Platforms**: required everywhere; imported unguarded at start-up
(through `persistence`), so the app does not start without it.
Ubuntu 22.04 has 2.8.1, Debian 12 and Ubuntu 24.04 2.8.2, Debian 13
and Arch 2.9.0, Fedora 43 and the pip builds 2.9.0.post0; the call
and its options are the same in all. Pip builds also get `six`, which
dateutil needs. Last releases: 2.8.2 (2021), 2.9.0 (2024).

**Size**: 684 KB (`python3-dateutil` 324 KB installed); pip: 844 KB
plus `six` 36 KB.

**Keep or replace**: the alternative is a reader of our own on the
standard library (a 93-line prototype). Both measured on every date
Task Coach's CSV export writes (every day of 2026, 3 times, 7 date
forms, 12- and 24-hour), exported and imported in 34 system
languages, and on forms other programs write:

| | dateutil | Our own reader |
|---|---|---|
| Languages reading every exported date back | 31 of 34 (Japanese, Korean, Vietnamese need DD/MM chosen) | 23 of 34 |
| Wrong dates | none | none |
| A date among words ("Due: 2026-10-05", "around Oct 5, 2026") | read | empty |
| A date without its year ("5 Oct") | this year | empty |
| Code Task Coach owns | the reading rules in `reader.py` | a date parser, more than 93 lines to match dateutil |
| Package | 324 KB, in every distribution; same results on 2.8.1, 2.8.2, 2.9.0 | none |

**Ruling**: keep, **ruled by designer 2026-10-03**. Replacing it
saves one small package that every build already gets, and costs
reading fewer dates and owning a parser.

**Wrong dates**: fixed 2026-10-03 (P173 in
[MASTER_SCHEDULER_REFACTOR.md](MASTER_SCHEDULER_REFACTOR.md#pre-existing-issues)):
the import reads month names and AM/PM in the system's language too,
gives no date where the text lacks its day or month instead of taking
today's, reads a year-first date as year-month-day anywhere in the
text, and a number too long to be a date no longer stops the import.

---

## chardet (To Do 90)

**Why**: guesses the text encoding of the file in File > Import > CSV,
which has no encoding choice. In Task Coach since 2009 (mail
attachments, no longer); the CSV import's since 2011.

**Code**: 1 module, `gui/wizard/csvimport.py`: one call on the whole
file, about 3 lines; no tests. Nothing else Task Coach uses needs it.

**Platforms**: required everywhere; imported unguarded at start-up, so
the app does not start without it. Each build gets another major
version:

| chardet | Builds |
|---------|--------|
| 4.0.0 | Ubuntu 22.04 |
| 5.1.0 | Debian 12; macOS, pinned `<5.2.0` (py2app cannot find 5.2's compiled modules, PACKAGING.md) |
| 5.2.0 | Debian 13, Ubuntu 24.04, Fedora 43 |
| 6.0.0 | Arch, Fedora 44, openSUSE Tumbleweed |
| 7.x | Windows, AppImage, Flatpak (pip `>=5.2.0`; 7.4.3 in the June Flatpak build) |

7.x is under the 0BSD licence (4.0 to 6.0: LGPL 2.1 or later) and
needs Python 3.10; 17 releases since 2023.

**Size**: `python3-chardet` 5.2: 1.1 MB installed (Debian 13); Arch's
6.0: 36 MB; pip 7.6: 3.2 MB plus an 864 KB compiled module.

**Keep or replace**: the alternatives are charset-normalizer (another
library, in every distribution: Ubuntu 22.04 2.0.6, Debian 12 3.0.1,
Ubuntu 24.04 3.3.2, Debian 13 3.4.2, Fedora 43 3.4.3, Arch 3.5.1, pip
3.5.2; MIT) and a guess of our own (a byte order mark, else UTF-8,
else the system's code page). Measured on 36 CSV files, 13 languages
in their usual encodings (UTF-8 with and without mark, UTF-16,
Windows-1250 to 1255, ISO-8859-1 and 2, Mac Roman, KOI8-R, Shift JIS,
EUC-JP, GBK, Big5), at 5, 100 and 2,000 rows; files read right, of 36,
with the version each build gets:

| Build | chardet | charset-normalizer | Our own guess |
|---|---|---|---|
| Ubuntu 22.04 | 29 (4.0) | 26 to 27 (2.0.6) | 21 |
| Debian 12 | 31 (5.1) | 26 to 27 (3.0.1) | 21 |
| Debian 13, Ubuntu 24.04, Fedora 43 | 31 (5.2) | 27 to 28 (3.3.2, 3.4.2) | 21 |
| Arch | 32 (6.0) | 30 to 31 (3.5) | 21 |
| macOS (pinned to 5.1) | 31 | 30 to 31 (3.5.2) | 21 |
| Windows, AppImage, Flatpak | 36 (7.6) | 30 to 31 (3.5.2) | 21 |

The own guess is right for 21 with a Western system code page, 20
with a Central European one, 17 with a Cyrillic one. charset-normalizer
reads French Windows-1252 files, the usual CSV Excel saves in Western
Europe and the Americas, as Baltic or Central European in every
version (Spanish ones too before 3.5, typographic quotes and dashes
from 3.0 on); chardet reads them right in every version. Time for a 430 KB file:
chardet 4.0 to 6.0 1.3 to 2.8 s, 7.6 under 0.1 s; charset-normalizer
3.0 and 3.4 0.5 to 1.5 s, 3.5 under 0.1 s.

What a replacement loses, file by file (100 rows):

- Our own guess, on every build: Russian (Windows-1251, KOI8-R), Greek,
  Hebrew, Japanese (Shift JIS, EUC-JP) and Chinese (GBK, Big5) files,
  Mac Roman on most builds, Central European and Turkish where chardet
  reads them (Arch, the pip builds). It gains no file anywhere.
- charset-normalizer, on every build: French Windows-1252 and Latin-1
  files; Spanish Windows-1252, Mac Roman, Chinese GBK or Turkish
  depending on the build. It gains one to three Central European
  files on the distribution builds and macOS, none on Windows,
  AppImage and Flatpak.

**Ruling**: keep, **ruled by designer 2026-10-03**. No replacement
reads every file chardet reads on any build.

**Separate issue**: P174, Central European and Turkish files garbled
by chardet 4.0 to 6.0 (every build but Windows, AppImage and
Flatpak), fixed 2026-10-03: the import wizard has an Encoding choice,
set to chardet's guess, which the user changes while looking at the
preview.

---

## pyparsing (To Do 91)

**Why**: the date expressions of task templates ("tomorrow", "3pm
tomorrow", "next saturday", "noon"; English, says the Help): File >
Edit templates checks them (an invalid one turns red), and New task
from template (menu, toolbar, tray) evaluates them. Save task as
template writes "N minutes from now". Since 1.2.20 (2011); the grammar
is the 2024 upstream example, `thirdparty/deltaTime.py`.

**Code**: 1 importing module, `thirdparty/deltaTime.py` (424 lines,
47 of them a self-test), one call each in `gui/dialog/templates.py`
and `persistence/xml/reader.py`. Tests: the template reader and
writer, the old-format conversion, the templates dialog.

**Platforms**: required everywhere (`>= 3.0.0`); imported unguarded
at start-up. Ubuntu 22.04 has 2.4.7, with which the app does not start
(P175); Debian 12 3.0.9, Ubuntu 24.04 3.1.1, Debian 13 and Fedora 43
3.1.2, Arch and the pip builds 3.3.x. 3.3 warns on the old names
2.4.7 has (`PyparsingDeprecationWarning`), so one grammar cannot use
the same names on both.

**Size**: 888 KB (`python3-pyparsing` 472 KB installed); importing it
and building the grammar takes 48 to 132 ms of each start (7 starts,
this machine under load), the prototype below 6 ms.

**Measured**: a parser of the same grammar on the standard library
(prototype of 237 lines, black-formatted), compared with deltaTime on
20,238 expressions (each form with quantities, units, weekdays with
next and last, times, combinations, noise, invalid text) at 5
reference times, as a prefix and as the whole text: the same date or
the same refusal in 171,360 of 202,380. Every other is "N days or
weeks from, before or after [next or last] <weekday>": the prototype
is right in all 23,040 checked against a separate calculation,
deltaTime in 13,455 (P171). deltaTime's 35 self-tests and Task
Coach's own forms ("N minutes from now", the old-format conversions):
the same at 3 reference times.

**Keep or replace**: three issues found in its grammar or its
packaging decide between the two:

- P171: a template due "2 days before sunday" gives the wrong day
  (checked in the app, master the same).
- P172: weekday names follow the system's language, so the Help's own
  "next saturday" is refused on a French system (checked in the app,
  master the same).
- P175: Ubuntu 22.04 has pyparsing 2.4.7, too old: this branch's .deb
  cannot be installed there, master's installs and does not start.

| Option | The three issues | Cost |
|---|---|---|
| Keep | P171 and P172 fixed in the grammar (about 5 lines); P175 needs pyparsing 3 inside the Ubuntu 22.04 .deb, in a folder of its own (about 20 lines in the workflow, `debian/rules` and `taskcoach.py`), checkable only by the CI's Ubuntu 22.04 job | 888 KB; 48 to 132 ms of each start |
| Replace by the parser above | P171 and P172 fixed by it, P175 gone (nothing to bundle) | about 240 lines added, 424 removed; pyparsing out of every build's packaging |
| Remove | template dates gone: a released feature | not proposed |

The replacement read every other expression of the 20,238 as
pyparsing does, at 5 reference times (171,360 comparisons), and Task
Coach's own forms ("N minutes from now", the old-format conversions)
alike. Risk: forms outside the 20,238 reading differently. P170's
choice (a partly read expression) stays its own either way.

**Ruling**: replace, **ruled by designer 2026-10-03**. Done the same
day: `domain/date/timeexpression.py` (about 270 lines) in place of
`thirdparty/deltaTime.py`; pyparsing out of `setup.py` and every
build's packaging and setup script. At the 5 reference times it reads
the 20,238 expressions as deltaTime did, but P171's 17,880, and
deltaTime's 35 self-tests and Task Coach's own forms alike. P171, P172
and P175 fixed; P170 stays its own.

---

## dbus-python (To Do 92)

**Why**: three D-Bus calls: the start-up report's tray check
(`application/application.py`) and two idle readings of the Idle time
notice (`powermgt/idle.py`): GNOME's `org.gnome.Mutter.IdleMonitor`
and `org.freedesktop.ScreenSaver.GetSessionIdleTime`
([IDLE.md](IDLE.md)). Researched 2026-10-06, **asked by designer**:
sources read, both libraries run against stand-in services on a
private bus, the app checked there; no real desktop.

**Platforms**: recommended by the deb and rpm, optional on Arch (not
installed by default), built from source in the Flatpak, absent from
the AppImage. PyGObject, which has Gio, is required by the deb, rpm
and Arch packages and in the Flatpak's runtime: 3.42 (Ubuntu 22.04,
Debian 12) to 3.56 (Arch, GNOME 50 runtime), the calls used the same
in all. **Size**: `python3-dbus` 415 KB (Debian 13).

**Which reading each desktop gets** (sources: Mutter, Muffin,
kscreenlocker, the screensaver daemons, Xwayland):

| Desktop, session | Reading |
|---|---|
| GNOME 42 to 48 X11 | Mutter, else the X11 extension |
| GNOME 42 to 50 Wayland | Mutter only: none without dbus-python (Xwayland disables the X11 extension, so no false reading) |
| Plasma, XFCE, MATE, Cinnamon, LXQt, LXDE on X11 | the X11 extension |
| Plasma 5.27 and 6 Wayland, Sway, Hyprland | `ext-idle-notify-v1` (pywayland) |
| Plasma 5.24 Wayland (Kubuntu 22.04) | ScreenSaver, which answers 0: never idle |
| Cinnamon Wayland | none: Muffin's monitor is `org.cinnamon.Muffin.IdleMonitor` |

The ScreenSaver reading is reached only when the three before it
fail, and there it gives no true reading on any desktop found: 0 on
Plasma 5.24 Wayland, an error on Plasma 5.27 and 6 Wayland, GNOME and
Cinnamon; its unit differs too (KDE X11 answers milliseconds,
light-locker seconds).

**Found, the same on master** (checked in the app on the stand-ins):
the idle readings keep the service's process of the first call
(dbus-python's proxy, `follow_name_owner_changes` off), so after the
service restarts (GNOME Shell restarted on X11) each reading fails, a
warning says idle detection is unavailable, and the notice stays off
until Task Coach restarts. A hung service would hold the window 25 s
at each reading (once a second while tracking): both libraries wait
25 s by default and take a shorter limit.

| Option | Readings | Cost |
|---|---|---|
| Keep, fix the two | as now; GNOME Wayland without the package has none | a new proxy after a failure and a 1 s limit, about 10 lines |
| Gio | as now, with the package's gap gone: GNOME Wayland reads everywhere PyGObject is; a restart followed; 1 s limit | prototyped: 2 files, +68/-36 lines (each reading asked of the name's owner now); dbus-python out of 4 packaging files and 5 docs; the Flatpak builds one C module less |
| jeepney or dasbus (pure Python) | as Gio | a new dependency where PyGObject already serves |

Other projects that moved to Gio report timeouts raised as
`GLib.Error` (caught here, as every probe error is) and a
`Gio.DBusProxy` kept on a dead name (the prototype uses no proxy).
Not settled without a real desktop: the reading after lock and
unlock, Cinnamon on Wayland, and the bus closing at logout (Gio's
shared connection sends SIGTERM, dbus-python's exits at once).

**Ruling**: replace by Gio, and drop the ScreenSaver reading, **ruled
by designer 2026-10-06** ("that is perfect for both of those"). Done
the same day: `powermgt/idle.py` reads GNOME's monitor through Gio
(each reading addressed to the name's owner, at most 1 s; a failed
one counts as not idle, logged once with its end), the start-up
report's tray check too; the ScreenSaver probe and the
Flatpak's `org.freedesktop.ScreenSaver` grant removed; dbus-python
out of the deb, rpm, Arch and Flatpak builds (with the Flatpak's
meson-python and patchelf, needed only for it).
