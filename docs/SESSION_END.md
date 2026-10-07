# Session End

What Task Coach saves, and when, so that quitting, logging out,
shutting down, restarting or a crash loses as little as possible; what
each system tells programs when a session ends; the practices this
follows. **Asked by designer 2026-10-04**: "document and do per modern
best practices".

## Table of Contents

1. [Rules](#rules)
2. [By System](#by-system)
3. [Practices](#practices)
4. [Checked](#checked)
5. [Not Done](#not-done)
6. [History](#history)

---

## Rules

1. **Saved while running, never counting on a warning.**
   - Tasks: autosave, on by default, saves the file milliseconds after
     each change, once what it set off is done; typed text counts when
     the user leaves the field
     ([PERSISTENCE_XML.md](PERSISTENCE_XML.md#saving)).
   - Settings, Preferences included: written 2 s after the last
     change. The main window's viewers, layout, position and size
     change no setting until copied into them, every 30 s once the
     window is placed. The file is written only when its text changed
     (`Application.save_state()`, `Settings.save_if_changed()`;
     [SETTINGS.md](SETTINGS.md)).
   - Each write of the settings and of the task file replaces the file
     in one step once the new text is on disk (a temporary file,
     `fsync`, `os.replace`, the folder's `fsync`;
     `filesystem/ondisk.py`): a crash or power cut leaves the old file
     or the new, never none.
2. **Told to end with nobody to answer: save, do not ask.** SIGTERM
   and SIGHUP (shutdown, restart, `kill`, a closed terminal) take the
   close of a Windows session end: the open file is saved without
   asking, or to a copy beside it when another program changed it
   ([PERSISTENCE_XML.md](PERSISTENCE_XML.md#saving)), then the
   settings, then Task Coach quits (`Application.on_signal()`). Ctrl+C
   in a terminal (SIGINT) asks as File > Quit does. A signal ignored
   when Task Coach started stays ignored: SIGHUP under `nohup`, SIGINT
   in a background job. Ended before the file to open at start was
   read, that file is still the one to open next time. A new file never
   saved has no name to save to: its changes are lost, as before. Not
   handled: a "Save changes?" question already open (autosave off)
   waits for its answer until the system kills Task Coach (P250 in
   [REFINEMENT_REFACTOR.md](REFINEMENT_REFACTOR.md)).
3. **Every step at quit on its own.** A failing step is logged
   (`[SETTINGS]`) and skips no other; the settings lock is released
   (`Application.save_all_settings()`).

## By System

| System | Logout | Shutdown, restart | Task Coach told |
|---|---|---|---|
| LXDE (lxsession) | the X server stops: Task Coach is gone at once | systemd sends SIGTERM, then SIGKILL (90 s by default); the X server stops too | nothing: lxsession has no session protocol |
| GNOME, KDE | the session manager asks the programs that register with it, then the display ends | as LXDE | Task Coach registers with none, so as LXDE |
| Windows | `WM_QUERYENDSESSION`, then `WM_ENDSESSION` | the same | saves without asking (`EVT_QUERY_END_SESSION`) |
| macOS | `applicationShouldTerminate`, as for Quit | the same | asks about unsaved changes, which holds the logout until answered |

On Linux only what is already saved survives a logout: hence rule 1.

## Practices

- **Microsoft:** a program should not block shutdown. At
  `WM_ENDSESSION` it saves the user's data and state automatically,
  without asking; one that must block registers a reason
  (`ShutdownBlockReasonCreate`), and after 5 s Windows lists the
  blocking programs full screen, with "Shut down anyway". Programs
  cannot rely on blocking.
  [Shutdown changes](https://learn.microsoft.com/en-us/windows/win32/shutdown/shutdown-changes-for-windows-vista),
  [Restart Manager guidelines](https://learn.microsoft.com/en-us/windows/win32/rstmgr/guidelines-for-applications).
- **Apple:** at logout, restart or shutdown a program saves its data
  and state; it may ask about unsaved documents (`NSTerminateLater`)
  and answers within 2 minutes.
  [Graceful termination](https://developer.apple.com/library/archive/documentation/Cocoa/Conceptual/AppArchitecture/Tasks/GracefulAppTermination.html).
- **freedesktop:** a program that registers is told the session is
  ending ("Query End", answered within one second) and may hold it
  with a reason the desktop shows beside "Log out anyway"
  ([XDG portal Inhibit](https://flatpak.github.io/xdg-desktop-portal/docs/doc-org.freedesktop.portal.Inhibit.html),
  [GtkApplication](https://docs.gtk.org/gtk3/class.Application.html));
  the others get SIGTERM, then SIGKILL
  ([logind.conf](https://manpages.debian.org/testing/systemd/logind.conf.5.en.html)),
  or lose their display. LXDE's lxsession offers no protocol
  ([LXDE forum](https://forum.lxde.org/viewtopic.php?t=36258)).
- Common to all: keep the user's work saved as it changes; ask only
  through the system's own end-of-session screen; SIGTERM is not a
  question.

## Checked

2026-10-04, on Xvfb, the welcome file's copy and a scratch profile:

- Before: an X server stopped under Task Coach (a logout): gone within
  0.5 s, nothing logged or saved, settings included. SIGTERM with an
  unsaved change: "You have unsaved changes. Save before closing?"
  waited.
- After: a sort changed, the X server stopped 3 s later: the settings
  file has it; the window moved and resized, the X server stopped
  after the next 30 s copy: the file has the new position and size, no
  `[GEOMETRY]` line logged; SIGTERM with an unsaved change: saved,
  quit in 1.5 s, no question.
- Tests: `SettingsWrittenWhileRunningTest` (`ConfigTest.py`),
  `SessionEndTest` (`AppTest.py`).

## Not Done

- GNOME and KDE: asking through the portal's "Query End" when autosave
  is off, holding the logout with a reason. Larger; for later.
- LXDE tells programs nothing; nothing more can be done there.
- No handler for a lost X connection: GTK ends the process from C, and
  rule 1 makes it unneeded.

## History

- January 2026: X session management (XSMP, off by default) removed,
  on the belief that desktops send SIGTERM at logout
  ([PYTHON3_MIGRATION_5.md](PYTHON3_MIGRATION_5.md#x11-session-management-removal));
  LXDE does not.
- 2026-10-04: the settings saved while running, SIGTERM and SIGHUP
  saving without asking, the quit steps logged (P195, P196).
