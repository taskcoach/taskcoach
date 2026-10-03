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

**Recommendation**: keep.

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
(through `persistence`), so the app does not start without it. Pip
builds also get `six`, which dateutil needs, although Task Coach
dropped its own use of `six` (2026-10-01).

**Size**: 684 KB (`python3-dateutil` 324 KB installed); pip: 844 KB
plus `six` 36 KB.

**Replacing or removing it**: a parser of about 25 lines (regular
expressions and `datetime`) in place of about 6: a prototype read 22 of
27 sample dates as dateutil does (the test values, Task Coach's own
display formats, ISO with a zone). The rest are where dateutil's fuzzy
mode makes a date up ("5", "week 12", "next Monday" become dates);
the prototype leaves them empty. Neither reads non-English month
names. `datetime.fromisoformat` alone rejects 22 of the 26 samples
("2011-6-30" included). Risk: date forms in users' files the
prototype does not know would import empty.

**Recommendation**: keep: one call, 324 KB, and it reads date forms a
small parser would miss.

---

## chardet (To Do 90)

**Why**: guesses the text encoding of the file in File > Import > CSV,
which has no encoding choice. In Task Coach since 2009 (mail
attachments, no longer); the CSV import's since 2011.

**Code**: 1 module, `gui/wizard/csvimport.py`: one call on the whole
file, about 3 lines; no tests. Nothing else Task Coach uses needs it.

**Platforms**: required everywhere; imported unguarded at start-up, so
the app does not start without it. The macOS build pins `<5.2.0`
(py2app could not find 5.2's compiled modules, PACKAGING.md), the
Windows and AppImage builds `>=5.2.0`, which now gets 7.x (inferred).

**Size**: 2.3 MB (`python3-chardet` 1.1 MB installed; 41,288 lines), no
dependencies. Guessing takes 2.1 s for a 0.8 MB file, on the window's
thread when the file is chosen.

**Replacing or removing it**: a guess of about 10 lines: a byte order
mark (UTF-8, UTF-16, UTF-32), else strict UTF-8, else the system's
code page. Tried on samples: the same results for ASCII, UTF-8 with
and without a mark, UTF-16 and Windows-1252; wrong for Mac Roman and
for Cyrillic files on a non-Russian system, where chardet is right; a
Japanese file chardet gives up on reads right only with a Japanese
system code page. An Encoding choice in the wizard (about 10 to 15
lines) would cover the misses.

**Found**: PACKAGING.md's matrix row says "chardet (<5.2)", true of
macOS only.

**Recommendation**: keep: it reads legacy encodings a short guess
misses; the 2 s guess can be limited to the file's start if it
matters.

---

## pyparsing (To Do 91)

**Why**: the date expressions of task templates ("tomorrow", "3pm
tomorrow", "next saturday", "noon"; English only): File > Edit
templates checks them (an invalid one turns red), and New task from
template (menu, toolbar, tray) evaluates them. Save task as template
writes "N minutes from now". Since 1.2.20 (2011); the grammar is the
2024 upstream example, `thirdparty/deltaTime.py`.

**Code**: 1 importing module, `thirdparty/deltaTime.py` (424 lines,
47 of them a self-test), used by `gui/dialog/templates.py` and
`persistence/xml/reader.py`; about 437 lines in all. Tests: the
template reader and writer, the old-format conversion, the templates
dialog.

**Platforms**: required everywhere (`>= 3.0.0`; Ubuntu 22.04 has
3.0.7); imported unguarded at start-up. A template whose expression
does not parse is skipped with a log line.

**Size**: 888 KB (`python3-pyparsing` 472 KB installed), no
dependencies; 50 ms of every start-up to import it and build the
grammar.

**Replacing or removing it**: a hand parser of the same grammar, about
90 to 120 lines for 424: a 75-line prototype matched 44 of 46
expressions (all self-tests, the generated forms, the help examples),
missing compound forms such as "20 seconds before noon tomorrow".
Removing it loses template dates.

**Found**: P170: a partly understood expression is accepted and
evaluated wrong.

**Recommendation**: keep; P170 is fixed in Task Coach's use of it, not
by replacing it.
