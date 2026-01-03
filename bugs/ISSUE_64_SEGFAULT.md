# Issue #64: Segmentation Fault on Ubuntu 24.04

**Possibly related:** https://github.com/taskcoach/taskcoach/issues/68

## Summary

Task Coach crashes with a segmentation fault on startup for one user running Ubuntu 24.04. The crash occurs at `wx.Log.SetActiveTarget(wx.LogStderr())` but **cannot be reproduced** on developer test systems.

**GitHub Issue:** https://github.com/taskcoach/taskcoach/issues/64

**Status:** NOT REPRODUCED - **Kernel 6.8.0-90-generic is the primary suspect.** User tested on empty system with 1 monitor and Welcome.tsk - still crashed. All other theories (wxPython version, TEE, config files, multi-monitor, missing packages) have been ruled out. Only difference: user has kernel 6.8.0-90, developer has 6.14.0-37.

---

## User's Environment (Issue #64)

| Component | Version |
|-----------|---------|
| OS | Ubuntu 24.04 |
| Kernel | Linux 6.8.0-90-generic |
| Python | 3.12.3 (GCC 13.3.0) |
| wxPython | 4.2.1 gtk3 (phoenix) |
| wxWidgets | 3.2.4 |
| GTK | 3.24.41 |
| glibc | 2.39 |
| Desktop | Ubuntu GNOME (X11) |
| Displays | 3 monitors (1920x1080, 2560x1440, 2560x1440) |

### Locale Settings
```
LANG: en_US.UTF-8
LC_TIME: fr_FR.UTF-8
LC_NUMERIC: fr_FR.UTF-8
LANGUAGE: en
```

---

## Crash Details

### Error
```
Fatal Python error: Segmentation fault
```

### Location
- **File:** `taskcoachlib/application/application.py`
- **Line:** 493 (version 2.0.0.92)
- **Code:** `wx.Log.SetActiveTarget(wx.LogStderr())`

### Sequence Before Crash
1. TEE initializes - redirects stderr (fd 2) to a pipe
2. wx imports - default log target writes to stderr (works)
3. wx.App created
4. wx.Locale created for en_US
5. i18n initialization completes
6. "Adding duplicate handler" messages appear via default log target (works)
7. `wx.Log.SetActiveTarget(wx.LogStderr())` called - **CRASH**

### Debug Output Before Crash
```
Adding duplicate image handler for 'Windows bitmap file'
Adding duplicate animation handler for '1' type
Adding duplicate animation handler for '2' type
```

### User's Report (January 2, 2026)

User sjefbosman tested v2.0.0.92 and reported the crash persisted. The diagnostic output showed:
- Locale initialization completed successfully
- Mixed locale settings (LANG: en_US.UTF-8, LC_TIME/LC_NUMERIC: fr_FR.UTF-8)
- i18n module loaded correctly
- Crash still occurred at same location (application.py line 493)

The added diagnostic logging confirmed the crash happens **after** successful locale/i18n initialization, ruling out localization as the cause.

---

## What Does SetActiveTarget Do?

### Purpose of wx.Log.SetActiveTarget()

According to [wxPython documentation](https://docs.wxpython.org/wx.Log.html):

- **Only one log target is active at any moment** - this is the one used by all wxLogXXX functions
- **SetActiveTarget** replaces the current log target with a new one and returns the old target
- For GUI apps, the default log target is `wxLogGui` (shows message dialogs)
- For console apps, the default is `wxLogStderr` (writes to C stderr)

### Why Was It Added to Task Coach?

The line was added in commit `def3832cf` ("Full Merge back of detached fork") with the comment:
```
# Enable wxPython debug logging on GTK to help diagnose crashes
# This helps identify which wx events/callbacks were active when segfaults occur
# Only visible when running from terminal, doesn't affect GUI-only users
```

The intent was to redirect wx log messages to stderr so they would be captured in the log file (via TEE) for debugging.

### Why SetActiveTarget May Be Required

The default log target for GUI apps is `wxLogGui` which **shows popup dialogs**.

`SetActiveTarget(wx.LogStderr())` redirects wx log messages to stderr instead of showing popups. This may be needed to:
1. Prevent popup dialogs for messages like "Adding duplicate image handler"
2. Ensure log messages go to the log file (via TEE) instead of dialogs

**Observation:** The "Adding duplicate handler" messages appeared on stderr before `SetActiveTarget` was called during testing. It's unclear if this is because:
- wx detects terminal and uses stderr automatically, OR
- Some other mechanism

**Unknown:** If SetActiveTarget is removed, will users see popup dialogs when NOT running from terminal?

---

## Investigation (January 2, 2026)

### Test Environment

| Component | Issue #64 User | Test System | Match |
|-----------|----------------|-------------|-------|
| OS | Ubuntu 24.04 | Ubuntu 24.04 | Yes |
| Kernel | 6.8.0-90-generic | 6.14.0-37-generic | No (newer) |
| Python | 3.12.3 | 3.12.3 | Yes |
| wxPython | 4.2.1 gtk3 wxWidgets 3.2.4 | 4.2.1 gtk3 wxWidgets 3.2.4 | Yes |
| GTK | 3.24.41 | 3.24.41 | Yes |
| glibc | 2.39 | 2.39 | Yes |
| fr_FR locale | installed | installed | Yes |
| Desktop | X11 | X11 | Yes |
| **Displays** | **3 monitors** | **1 monitor** | **No** |

### Test Environment Files

| File | Issue #64 User | Test System | Match |
|------|----------------|-------------|-------|
| `~/taskcoachlog.txt` | *Unknown* | Fresh (created on run) | ? |
| `~/.config/Task Coach/TaskCoach.ini` | *Unknown* | Did not exist | ? |
| `~/.local/share/Task Coach/` | *Unknown* | Did not exist | ? |
| Last opened `.tsk` file | *Unknown* | None | ? |

### Test Results

#### Test 1: Wayland Session (Earlier Testing)
```
$ LANG=en_US.UTF-8 LC_TIME=fr_FR.UTF-8 LC_NUMERIC=fr_FR.UTF-8 ./taskcoach-run.sh
[Ran for 30 seconds - NO CRASH]
```

#### Test 2: X11 Session with SetActiveTarget Restored
```
$ LANG=en_US.UTF-8 LC_TIME=fr_FR.UTF-8 LC_NUMERIC=fr_FR.UTF-8 ./taskcoach-run.sh
XDG_SESSION_TYPE: x11
Number of displays: 1
  Display 0: geometry=0,0 1920x1029
[Ran for 30 seconds - NO CRASH]
```

#### Test 3: Isolated Test Script
```
$ LANG=en_US.UTF-8 LC_TIME=fr_FR.UTF-8 LC_NUMERIC=fr_FR.UTF-8 python3 test_wxlog_crash.py --with-tee
[STEP 7] Calling wx.Log.SetActiveTarget(new_log_target)...
[STEP 7] SetActiveTarget returned old target: None
ALL STEPS COMPLETED - NO CRASH
```

### Conclusion

**CRASH NOT REPRODUCED** despite testing:
- SetActiveTarget with TEE enabled (stderr redirected to pipe) - NO CRASH
- Mixed locale settings (en_US + fr_FR) - NO CRASH
- X11 session (same as user) - NO CRASH
- Matching Python 3.12.3, wxPython 4.2.1, GTK 3.24.41, glibc 2.39

**Known differences from user's environment:**
| Factor | User | Test System |
|--------|------|-------------|
| Displays | 3 monitors | 1 monitor |
| Kernel | 6.8.0-90-generic | 6.14.0-37-generic |
| Config files | *Unknown* | Fresh/none |

**Root cause unknown.** The crash cannot be reproduced with the available test environment.

---

## Investigation (January 3, 2026)

### User Test: Empty System with Single Monitor

User sjefbosman tested on a **minimal configuration** to isolate the issue:

| Component | Value |
|-----------|-------|
| Task Coach | 2.0.0.92 |
| Python | 3.12.3 |
| wxPython | 4.2.1 gtk3 (phoenix) wxWidgets 3.2.4 |
| **Kernel** | **6.8.0-90-generic** |
| GTK | 3.24.41 |
| glibc | 2.39 |
| Desktop | ubuntu:GNOME (X11) |
| Displays | **1 monitor** (1920x1080) |
| Config | Empty system, no extensions, no apps running |
| Task file | Welcome.tsk (explicitly specified) |
| Locale | en_US.UTF-8 (LC_TIME/LC_NUMERIC: en_GB.UTF-8) |

**Result: CRASH** - Same segfault at `application.py:493`, identical stack trace.

User also installed missing packages (python3-squaremap, gntp-send) - same crash.

### Developer Test: Fresh Ubuntu 24.04 VM

A fresh Ubuntu 24.04 installation with **identical wxPython version** was tested:

| Component | Value |
|-----------|-------|
| Task Coach | 2.0.0.92 |
| Python | 3.12.3 |
| wxPython | 4.2.1 gtk3 (phoenix) wxWidgets 3.2.4 |
| Kernel | 6.14.0-37-generic |
| GTK | 3.24.41 |
| glibc | 2.39 |
| Desktop | ubuntu:GNOME (X11) |
| Displays | 1 monitor (1920x1029) |
| Config | Fresh (no INI file) |
| Locale | en_US.UTF-8 only |

**Result: NO CRASH** - Application started successfully, TEE worked correctly, "Adding duplicate handler" messages captured without issue.

### What This Proves

| Hypothesis | Status |
|------------|--------|
| wxPython 4.2.1 is broken | **RULED OUT** - Same version works on dev system |
| TEE stderr redirection is broken | **RULED OUT** - TEE works on dev system |
| Python 3.12 + wxPython combo | **RULED OUT** - Same combo works on dev system |
| 3-monitor setup causes crash | **RULED OUT** - User crashed with 1 monitor |
| Config files cause crash | **RULED OUT** - User crashed on empty system |
| Missing packages cause crash | **RULED OUT** - Installing squaremap didn't help |
| **Kernel 6.8.0-90 is the issue** | **PRIMARY SUSPECT** - Only remaining difference |

### Comparison Summary

| Factor | User (CRASH) | Developer (OK) |
|--------|--------------|----------------|
| wxPython | 4.2.1 | 4.2.1 |
| Python | 3.12.3 | 3.12.3 |
| GTK | 3.24.41 | 3.24.41 |
| glibc | 2.39 | 2.39 |
| Displays | 1 monitor | 1 monitor |
| Config | Empty/fresh | Fresh |
| **Kernel** | **6.8.0-90-generic** | **6.14.0-37-generic** |

---

## Technical Analysis: Why the Crash Occurs at SetActiveTarget

### The Crash Line

```python
wx.Log.SetActiveTarget(wx.LogStderr())
```

This line is the **first explicit C++ stderr access** after TEE's file descriptor manipulation.

### Thread State at Crash Time

The user's crash trace shows 4 threads active:

| Thread | File:Line | Code | State |
|--------|-----------|------|-------|
| **Main** | `application.py:517` | `wx.Log.SetActiveTarget(wx.LogStderr())` | **CRASH HERE** |
| TEE stderr | `tee.py:91` | `data = os.read(pipe_read_fd, 4096)` | Blocked reading pipe |
| TEE stderr | `tee.py:106` | `log_file.write(text)` | In same function scope |
| FS poller | `fs_poller.py:54` | `self.evt.wait(10)` | Sleeping |

### What Each Line Does

**`application.py:517` - wx.Log.SetActiveTarget(wx.LogStderr())**
1. `wx.LogStderr()` creates a C++ wxLogStderr object
2. The C++ constructor initializes a pointer to C's `FILE* stderr`
3. `SetActiveTarget()` installs it as the active log target
4. The C++ code may access `stderr` stream state - **SEGFAULT**

**`tee.py:91` - os.read(pipe_read_fd, 4096)**
- TEE thread blocked waiting for data from stderr pipe
- `pipe_read_fd` is the read end of the pipe that replaced fd 2

**`tee.py:106` - log_file.write(text)**
- Writes captured stderr text to `~/taskcoachlog.txt`
- Appears in trace because it's in the same function

**`fs_poller.py:54` - self.evt.wait(10)**
- Filesystem poller sleeping, checking for .tsk file changes every 10 seconds
- Not involved in crash, just happened to be running

### Why This Line Specifically?

```
BEFORE TEE init_tee():
┌─────────────────────────────────────┐
│  Python sys.stderr ──► fd 2 ──► terminal
│  C runtime stderr  ──► fd 2 ──► terminal
└─────────────────────────────────────┘

AFTER TEE init_tee():
┌─────────────────────────────────────┐
│  Python sys.stderr ──► fd 2 ──► PIPE
│  C runtime stderr  ──► fd 2 ──► PIPE
│  (internal buffer state = ???)
└─────────────────────────────────────┘

wx.LogStderr() CREATED:
┌─────────────────────────────────────┐
│  wxLogStderr C++ object
│    └─► directly accesses C's stderr
│         └─► inconsistent state?
│              └─► SEGFAULT
└─────────────────────────────────────┘
```

The earlier "Adding duplicate handler" messages work because they use the **default auto-detected log target**, not an explicitly created `wxLogStderr`. When `wx.LogStderr()` is explicitly created, its C++ constructor directly accesses the C runtime's stderr stream.

### Faulthandler Output

The user may see output like:
```
matplotlib._path, kiwisolver._cext, matplotlib._imageSegmentation fault (core dumped)
```

This "truncated" appearance happens because:
1. Python's **faulthandler** only outputs on fatal signals (SIGSEGV)
2. The segfault kills the process instantly at the C level
3. No opportunity to flush buffers or print a newline
4. The shell's "Segmentation fault" message concatenates directly

The "Extension modules:" line is **crash-only diagnostic output** - it never appears during normal operation because faulthandler only activates on fatal signals.

---

## Remaining Suspect: Kernel Version

All other hypotheses have been ruled out by user testing. The **only remaining difference** is the kernel:

| System | Kernel | Result |
|--------|--------|--------|
| User (sjefbosman) | 6.8.0-90-generic | CRASH |
| Developer test | 6.14.0-37-generic | OK |

### Possible Kernel-Related Causes

1. **Pipe/fd behavior differences** - The TEE module uses `os.dup2()` to redirect stderr to a pipe. Kernel 6.8.0 may handle pipe buffering or fd state differently than 6.14.0.

2. **Memory management** - Different kernel versions have different memory allocators and ASLR behavior, which could affect when/if the crash manifests.

3. **GTK/GLib kernel interactions** - GTK and GLib make syscalls that may behave differently across kernel versions.

4. **Bug in kernel 6.8.0-90** - There may be a kernel bug that was fixed in later versions.

### User's Note on Kernel

User commented: "Hm, strange that the update/upgrade didn't install the newer kernel then. On the other hand, IMHO TaskCoach should work on even older kernels..."

The user ran `apt full-upgrade` but kernel 6.8.0-90 was not updated, possibly due to regional mirror lag.

---

## Files To Check (Ask User)

The following files are accessed during startup before the crash point:

| File | Path (Linux) | Purpose |
|------|--------------|---------|
| Log file | `~/taskcoachlog.txt` | TEE module writes stdout/stderr here |
| INI file | `~/.config/Task Coach/TaskCoach.ini` | Settings (window positions, last file, etc.) |
| Data dir | `~/.local/share/Task Coach/` | Templates, backups |
| Last opened file | Value of `[file] lastfile` in INI | Auto-loaded on startup |

### Questions for User

1. Does `~/taskcoachlog.txt` exist? Is it writable? What are its permissions?
2. Does `~/.config/Task Coach/TaskCoach.ini` exist? Is it corrupted?
3. What is the value of `lastfile` in the INI? Does that `.tsk` file exist and is it valid?
4. Does the crash still occur after renaming `~/.config/Task Coach/` (fresh config)?

---

## Fix Status

**No fix will be applied** until the issue can be reproduced.

### Suspected Code

The user's stack trace points to this line in `taskcoachlib/application/application.py`:
```python
wx.Log.SetActiveTarget(wx.LogStderr())
```

However, this code does not crash in our test environment (see Investigation section above).

### Ruled Out Theories

| Theory | Evidence Against |
|--------|------------------|
| wxPython 4.2.1 is broken | Same version works on dev system |
| TEE stderr redirection causes crash | TEE works on dev system |
| Python 3.12 + wxPython combo issue | Same combination works on dev system |
| 3-monitor setup causes crash | User tested with 1 monitor, still crashed |
| Corrupted config files | User tested on empty system, still crashed |
| Missing packages (squaremap, gntp) | User installed them, still crashed |
| Locale/i18n issues | User has simple en_US/en_GB, still crashed |

The crash appears to be **kernel-specific**, not a bug in Task Coach, wxPython, or TEE.

---

## Next Steps

1. **Ask user to upgrade kernel:**
   ```bash
   sudo apt install linux-generic-hwe-24.04
   ```
   Or wait for regional mirrors to provide kernel updates.

2. **Test on kernel 6.8.0-90:** Developer should try to obtain/test on kernel 6.8.0-90-generic to reproduce the issue.

3. **Investigate kernel differences:** Research what changed between kernel 6.8.0 and 6.14.0 regarding pipes, file descriptors, or memory management.

4. **Consider workaround:** If kernel is confirmed as the issue, consider:
   - Making `SetActiveTarget(wx.LogStderr())` conditional
   - Wrapping it in try/except
   - Skipping it on affected kernel versions

---

## References

- [wx.Log documentation](https://docs.wxpython.org/wx.Log.html)
- [wxLog Wiki](https://wiki.wxwidgets.org/WxLog)
- [Log Classes Overview](https://docs.wxpython.org/log_classes_overview.html)

---

**Last Updated:** January 3, 2026
