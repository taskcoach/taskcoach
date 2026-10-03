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
the Flatpak's tray icon check, and the test runner's certified
platform check.

**Code**: 4 files import `gi` (`gui/appindicator.py`, 167 lines;
`application/application.py`; `widgets/textctrl.py`; `tests/test.py`),
all guarded; `gui/taskbaricon.py` builds the tray's GTK menu through it
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

**Size**: `python3-gi` 780 KB, plus the GLib and GTK typelibs (about
2.2 MB) and the AppIndicator libraries (about 650 KB).

**Replacing or removing it**:
- ctypes to libayatana-appindicator and GTK's menu functions (about
  15 C functions): about 150 to 200 lines for `appindicator.py` and a
  rewritten menu builder. Drops `python3-gi` and the typelibs, not the
  C libraries; might give the AppImage a tray (inferred). Risks: wrong
  argument types crash rather than raise, callbacks freed early, two
  library names (Ayatana and the Flatpak's AppIndicator3).
- StatusNotifierItem and dbusmenu over D-Bus ourselves: 400 to 600
  lines (inferred).
- Dropping AppIndicator removes about 870 lines; users lose the tray
  on Wayland and GNOME and the right-click menu on LXDE and KDE X11.
- To Do 92 (dbus-python to Gio) assumes Gio, which is PyGObject.

**Recommendation**: keep.

---

## pywin32 (To Do 85)

**Why**: Windows calls:
- Outlook (classic) mail dropped on a task: COM (`mailer/outlook.py`).
- Thunderbird Portable's profile folder: a WMI process query
  (`mailer/thunderbird.py`).
- The Documents and AppData folders and following `.lnk` shortcuts to
  the templates and data folders (`config/settings.py`).
- Window styles: the editor's own taskbar button
  (`widgets/dialog.py`), double buffering (`gui/mainwindow.py`).
- Monitor geometry (`workarounds/display.py`, which replaces
  `wx.Display`).

**Code**: 7 modules, plus the DLL set-up in `taskcoach.py` and the
version line in the start-up report; about 25 call sites, about 235
lines that exist for it. Tests only mock Outlook.

**Platforms**: Windows only, required: imported unguarded at start-up
(`workarounds/display.py`), so the app does not start without it.
Never imported on Linux or macOS.

**Size**: 6.9 MB download, 15 MB installed (Windows build).

**Replacing or removing it**:
- Window styles, folders, monitors, Thunderbird Portable: ctypes calls
  (Windows API) of 6 to 40 lines each, about 100 to 150 lines for
  about 235 removed. The double-buffering branch looks unreachable on
  Windows 8.1 and later, which Python 3.11 requires (inferred).
- `.lnk` shortcuts: a parser of 50 to 80 lines, or dropping them; no
  doc records the behaviour, so dropping it is a ruling.
- Outlook: COM needs `comtypes` (a new dependency) or about 200 lines
  of raw COM through ctypes; otherwise the Outlook drop goes (marked
  "not tested", [EMAIL_ATTACHMENTS.md](EMAIL_ATTACHMENTS.md)).
- None of it can be checked here (no Windows).

**Found**: the replacement `Display` class lacks `GetPPI` and
`GetScaleFactor`, so the Windows start-up report leaves them out
(inferred).

**Recommendation**: keep: the Outlook drop needs COM, so a partial
replacement keeps the package.

---

## keyring (To Do 86)

**Why**: one use: the password of an IMAP account when a Thunderbird
mail from it is dropped on a task or note; Task Coach logs in to fetch
the mail. The password dialog's "Store in keychain" box saves it under
"server:port" and the user name; a failed login asks again. It also
served SyncML, removed 2026-01.

**Code**: 1 module, `widgets/password.py` (3 lazy imports, 5 call
sites), used by `mailer/thunderbird.py`; about 62 lines exist for it.

**Platforms**: a dependency of every build. keyring picks a backend
when run: the Secret Service (GNOME Keyring, KWallet, KeePassXC) or
KWallet on Linux, the Credential Manager on Windows, the Keychain on
macOS. The Flatpak allows neither the network nor the secret service,
so its IMAP fetch fails before a password is asked. Missing, a "file a
bug report" box shows once, then a plain password prompt cached for
the session. With keyring installed but no backend or a locked
keyring (LXDE without gnome-keyring), its `NoKeyringError` or
`KeyringLocked` is not caught and the drop ends in an error
(inferred).

**Size**: 396 KB, plus SecretStorage, jeepney, jaraco and
more-itertools (about 1.4 MB) and cryptography (4.8 MB): about 6.6 MB
in pip builds.

**Replacing or removing it**:
- Remove: about 65 lines and the packaging lines of 7 setup scripts, 5
  workflows, 3 package specs and the Flatpak; users type the IMAP
  password once per session per server.
- Native stores: libsecret through `gi` on Linux (needs
  `gir1.2-secret-1`), `win32cred` (pywin32) on Windows, the Security
  framework on macOS: about 100 lines for 62; three paths, two of them
  not checkable here.
- A plain file: not acceptable (the password in clear text).

**Recommendation**: keep: storing the password is released
behaviour, and the alternatives trade 6.6 MB for three untested code
paths.

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

**Platforms**: pyenchant loads the C libenchant, which uses hunspell or
aspell and the installed dictionaries. deb, rpm and Arch depend on it
and recommend an English dictionary; the AppImage and Flatpak carry the
pip package and rely on the host's or runtime's libenchant (not
verified for the Flatpak). Windows: the wheel brings its own DLLs and
the build adds `en_US`. macOS: the wheel has no libenchant and the
build adds none, so the DMG checks spelling only with Homebrew's
enchant (inferred). Missing, the Preferences box is greyed out with
"Install pyenchant", also shown when only the C library is missing.

**Size**: 376 KB, no Python dependencies; libenchant 225 KB, hunspell
856 KB, aspell 2.2 MB, an English dictionary 1.6 MB.

**Replacing or removing it**:
- wx's own spell check (`EnableProofCheck`): not in wxPython 4.2.3,
  works on `wx.TextCtrl`, not the styled text fields these are, and
  needs gspell on GTK: the fields would be rewritten.
- Our own ctypes binding to libenchant: about 90 lines to save 180 KB
  of Python.
- Remove: about 430 lines and three settings sections; users lose the
  squiggles, suggestions and their dictionary.

**Recommendation**: keep.

---

## pywayland (To Do 88)

**Why**:
- The Idle time notice (off by default) on Wayland desktops that offer
  `ext-idle-notify-v1`: KDE Plasma 6, wlroots desktops (Sway,
  Hyprland, niri) and COSMIC ([IDLE.md](IDLE.md)). Added 2026-05.
- The tray's hide and restore on KDE Plasma Wayland, keeping the
  taskbar entry through `org_kde_plasma_window_management`. Added
  2026-06; probably inactive: KWin may offer that protocol only to
  apps that list it in their `.desktop` file, and ours do not (D5).

**Code**: 2 modules, imports lazy and guarded (`powermgt/idle.py`,
`gui/toplevelcontroller.py`); about 312 lines of ours (141 for idle
time, 171 for the KDE controller) and 1,363 lines of generated
protocol bindings in `thirdparty/` (279 idle, 1,084 KDE); about 25
calls.

**Platforms**: only on GTK with `WAYLAND_DISPLAY` set; X11 uses the
X screensaver extension, GNOME Wayland Mutter over D-Bus. Optional
everywhere: recommended by the Debian 13 deb and the rpm, optional on
Arch, absent from Debian 12, Ubuntu, the AppImage, the Flatpak (X11),
Windows and macOS. Missing, the idle probe is skipped (no Idle time
notice on those desktops) and the tray hides the window the plain way.

**Size**: 1.2 MB (`python3-pywayland` 561 KB installed), plus the cffi
backend (212 KB); the bindings 160 KB.

**Replacing or removing it**:
- Remove all: -312 lines and -1,363 bindings; users of KDE 6, wlroots
  and COSMIC on Wayland lose the Idle time notice.
- Remove only the KDE controller (-171, -1,084): likely no change,
  given D5 (inferred).
- ctypes to libwayland-client: about 200 to 250 lines; a mistake
  crashes instead of raising, and CI has no compositor to test it.

**Found**: PACKAGING.md and the rpm and Arch packages described it as
for idle time only (corrected 2026-10-03).

**Recommendation**: keep; whether the KDE controller stays is D5's.

---

## python-dateutil (To Do 89)

**Why**: the date columns of File > Import > CSV (planned start, due,
actual start, completion, reminder), with the wizard's day-first or
month-first choice. CSV import since 1.2.11 (2011).

**Code**: 1 module, `persistence/csv/reader.py`: one call
(`parser.parse(..., fuzzy=True)`) reached from 5 fields, about 8
lines; 15 date tests in `CSVReaderTest`. Nothing else Task Coach uses
needs it.

**Platforms**: required everywhere; imported unguarded at start-up
(through `persistence`), so the app does not start without it.
Ubuntu 22.04 has 2.8.1, Debian 12 and Ubuntu 24.04 2.8.2, Debian 13
and Arch 2.9.0, Fedora 43 and the pip builds 2.9.0.post0; the call
and its options are the same in all. Pip builds also get `six`, which
dateutil needs. Last releases: 2.8.2 (2021), 2.9.0 (2024).

**Size**: 684 KB (`python3-dateutil` 324 KB installed); pip: 844 KB
plus `six` 36 KB.

**Measured**: 118 date strings: the 88 Task Coach's CSV export writes
(5 numeric date formats, 12- and 24-hour times, the two display
overrides in English and French, at 4 moments) and 30 that other
programs write (ISO 8601 with and without zone, US, UK, German,
RFC 2822, month names, a time alone, a number, words). Today's call,
on any system:

- 96 as expected.
- 6 wrong dates: French month names with a day of 12 or less,
  "samedi, 07 mars 2026" read as 2026-07-03 (P173).
- 12 empty: other French and German forms ("23 octobre 2026").
- 4 dates where the text has none: "5" (the 5th of this month),
  "2:30 PM" (today), "week 12" (the 12th), "next Monday".

Fuzzy mode also reads a date among words ("Due: 2026-10-05", "around
Oct 5, 2026", "2026-10-05 (approx)"), and fills a missing day, month
or year from today ("Oct 2026" is 2026-10-03).

**Options**:

- A. Keep as is. P173 stays.
- B. Add the system language's month names to dateutil's: a
  `parserinfo` built from `calendar`, about 12 lines in `reader.py`.
  An English system reads all 118 as today. A French system: 109 as
  expected (was 96), no wrong date (was 6); the French
  "2026-oct.-23-ven." form stays empty. Weekday names are left out:
  French "mar" (Tuesday, Spanish and Italian the same) hides English
  "Mar" ("Mar 7, 2026" read as 2026-07-07). Left: a month name in a
  third language, day 12 or less, is still wrong ("7 März 2026" on a
  French system: 2026-07-03).
- C. Drop fuzzy mode: 1 line. No wrong date in any language: all
  French forms import empty, as do dates among words, "week 12" and
  "next Monday".
- D. Replace dateutil with a standard-library reader: a prototype of
  93 lines; dateutil out of every build, `six` out of the pip builds.
  It reads ISO 8601, three numbers in the chosen order (year first is
  year-month-day), month and weekday names in English and the
  system's language, 12- and 24-hour times; any other word gives no
  date. English system: 100 as expected, none wrong or invented (the
  18 empty are French and German names); French system: 117. Unlike
  today, a date among words, a date without its year ("5 Oct") and a
  partial one ("Oct 2026") import empty. Risk: forms outside the 118
  that dateutil reads.

**Recommendation**: B: it ends the wrong dates for the user's own
language and changes nothing on an English system. Effort: the
`parserinfo`, tests giving it French names (no French locale needed),
an app check with a French locale.

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

**Size**: `python3-chardet` 5.2: 1.1 MB installed (2.3 MB with its
files); pip: 4.0 2.1 MB, 6.0 24 MB, 7.6 3.2 MB plus an 864 KB compiled
module.

**Measured**: 36 CSV files, 13 languages in their usual encodings
(UTF-8 with and without mark, UTF-16, Windows-1250 to 1255,
ISO-8859-1 and 2, Mac Roman, KOI8-R, Shift JIS, EUC-JP, GBK, Big5), 5
and 100 rows. Read right, of 36:

| chardet | Right | Wrong |
|---------|:-----:|-------|
| 4.0.0 | 29 | Polish and Czech Windows-1250 and ISO-8859-2, Turkish Windows-1254, French and German Mac Roman (one cannot be decoded: the wizard stops with an error, inferred) |
| 5.1.0, 5.2.0 | 31 | Polish and Czech Windows-1250 and ISO-8859-2, Turkish Windows-1254 (P174) |
| 6.0.0 | 32 | Polish and Czech ISO-8859-2 (read as Windows-1250), French and German Mac Roman |
| 7.6.0 | 36 | |

French text with typographic quotes, dashes and "œ" in Windows-1252:
right on all. A wrong guess shows garbled in the preview and imports
garbled. Guessing runs on the window's thread when the file is
chosen; for a 430 KB file: 4.0 1.4 to 1.6 s, 5.1 2.0 to 2.8 s, 5.2
1.3 s, 6.0 2.0 to 2.3 s, 7.6 under 0.1 s. Guessing from the first
64 KB gave the same answer for all 36 at 8,000 rows, 6 times faster;
a file plain ASCII in its first 64 KB would then be guessed ASCII
(inferred).

A standard-library guess (a byte order mark, else strict UTF-8, else
the system's code page) reads 21 of the 36 right with Windows-1252
(Western), 20 with Windows-1250 (Central European), 17 with
Windows-1251.

**Options**:

- A. Keep as is. P174 stays on every build but Windows, AppImage and
  Flatpak.
- B. Keep chardet and add an Encoding choice to the wizard's first
  page, set to chardet's guess; changing it reloads the preview.
  About 20 lines in `csvimport.py`. Fixes P174 on every build: the
  preview shows the garbling, the user picks the encoding.
- C. Replace chardet by the standard-library guess and the same
  Encoding choice: about 30 lines; chardet out of every build, the
  macOS pin with it. ASCII, UTF-8, UTF-16 and the system code page's
  files read as today; a file in another legacy encoding (Russian,
  Greek, Hebrew, Japanese, Chinese, Central European on a Western
  system) previews garbled until the user picks its encoding, which
  chardet guesses today.
- D. Require chardet 7 on every build: no distribution packages it,
  so each would bundle it (P175's problem).

**Recommendation**: B: it fixes P174 on all builds and loses none of
chardet's guesses. C if fewer packages matter more than the guess for
other languages' legacy files. Effort for B: the choice and its
reload, a test with a Windows-1250 file, an app check.

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

**Found**: P171 (a wrong direction), P172 (weekday names follow the
system's language), P175 (Ubuntu 22.04), besides P170 (a partly read
expression accepted).

**Options**:

- A. Keep pyparsing and repair Ubuntu 22.04's .deb: that package
  carries pyparsing 3 in a folder of its own, added to `sys.path` at
  start, installed after `dh_auto_install` (where `dh_clean` and
  `dh_prep` do not remove it), with no `python3-pyparsing`
  dependency; not in `/usr/lib/python3/dist-packages`, where it would
  hide Ubuntu's `pyparsing.py` from every program (python3-packaging
  depends on it). About 20 lines in the workflow, `debian/rules` and
  `taskcoach.py`; checked only by the CI's Ubuntu 22.04 build, whose
  install test must then start the app (it imports only
  `taskcoachlib`, which does not load the grammar). P171 and P172
  need about 5 lines in the grammar (one `dir` renamed, English
  weekday names).
- B. Replace deltaTime and pyparsing by the parser above, as Task
  Coach's own module: about 240 lines added, 424 removed, the 2 calls
  and their tests (the self-tests, P171, P172); pyparsing out of
  `setup.py`, `debian/control`, the RPM spec, the PKGBUILD, 5 build
  workflows (macOS's py2app list among them), the AppImage and
  Flatpak scripts, 7 setup scripts, the start-up package log and the
  docs. Fixes P171, P172 and P175 (nothing to bundle); every other
  date as today. The prototype follows the grammar rule by rule (the
  first alternative that matches, keywords not inside words), quirks
  included ("10minutes ago" refused, "1230pm" read as 18:00). P170's
  choice (whole text or not) stays its own: the parser offers both.
  Risk: forms outside the 20,238 read differently.
- C. Make the grammar run on 2.4.7 too: it would use the names 3.3
  deprecates. Not proposed.
- D. Drop Ubuntu 22.04 (Launchpad: still supported): the decider's
  call; P171 and P172 stay.

**Recommendation**: B: it fixes three found issues, the Ubuntu 22.04
package among them, removes a package from every build and 50 ms or
more from each start, and reads every other date as today. Effort: the
module, its tests, the packaging and docs, an app check of the
templates dialog and New task from template on master and the branch.
