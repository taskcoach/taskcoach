# Issue #64: Segmentation Fault on Ubuntu 24.04

**Status:** ⏳ **PENDING USER CONFIRMATION** - Fix in v2.0.0.101

**GitHub Issue:** https://github.com/taskcoach/taskcoach/issues/64

## Potential Root Cause

An ancient environment variable workaround in `taskcoach.py` may be causing the segfault:

```python
os.environ["XLIB_SKIP_ARGB_VISUALS"] = "1"
```

This was a workaround for an **Ubuntu 10.10 bug from 2010** that has been in the codebase for 14+ years. On modern systems (Ubuntu 24.04 with certain kernel/GPU combinations), this environment variable may cause wxPython/GTK to crash.

## Fix

Removed the `XLIB_SKIP_ARGB_VISUALS=1` workaround in v2.0.0.101. This change resolves some traced segfaults and may resolve Issue #64.

**User testing required to confirm.**

---

## Historical Investigation (Archived)

The following sections document the investigation before the root cause was identified.

### Original Summary

Task Coach crashed with a segmentation fault on startup for users running Ubuntu 24.04. The crash could not be reproduced on developer test systems.

| Version | Crash Location | Code |
|---------|----------------|------|
| 2.0.0.92 | `application.py:493` | `wx.Log.SetActiveTarget(wx.LogStderr())` |
| 2.0.0.96 | `iocontroller.py:213` | `wx.MessageBox()` (file-not-found error) |

The `SetActiveTarget` call was commented out in v2.0.0.96, but the crash moved to the next wx GUI call. This suggested an underlying wxPython/GTK initialization issue.

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

### Version 2.0.0.92 Crash Location

- **File:** `taskcoachlib/application/application.py`
- **Line:** 493
- **Code:** `wx.Log.SetActiveTarget(wx.LogStderr())`

### Version 2.0.0.96 Crash Location (NEW)

- **File:** `taskcoachlib/gui/iocontroller.py`
- **Line:** 213
- **Code:** `showerror(errorMessage, ...)` where `showerror=wx.MessageBox`
- **Context:** Called when file specified on command line doesn't exist

The `SetActiveTarget` call was **commented out** in v2.0.0.96 (lines 522-525 in application.py), causing the crash to move to the next wx GUI operation.

### Sequence Before Crash (v2.0.0.92)
1. TEE initializes - redirects stderr (fd 2) to a pipe
2. wx imports - default log target writes to stderr (works)
3. wx.App created
4. wx.Locale created for en_US
5. i18n initialization completes
6. "Adding duplicate handler" messages appear via default log target (works)
7. `wx.Log.SetActiveTarget(wx.LogStderr())` called - **CRASH**

### Sequence Before Crash (v2.0.0.96)
1. TEE initializes - redirects stderr (fd 2) to a pipe
2. wx imports - default log target writes to stderr (works)
3. wx.App created
4. wx.Locale created for en_US
5. i18n initialization completes
6. "Adding duplicate handler" messages appear (works)
7. MainWindow created (works)
8. `mainwindow.Show()` called (line 527) - **unknown if succeeds**
9. `MainLoop()` starts (line 533)
10. First `wx.CallAfter` event fires → `iocontroller.open()` runs
11. File doesn't exist → `wx.MessageBox()` called - **CRASH**

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

### Developer Test 1: Fresh Ubuntu 24.04 VM (Kernel 6.14)

| Component | Value |
|-----------|-------|
| Task Coach | 2.0.0.92 |
| Python | 3.12.3 |
| wxPython | 4.2.1 gtk3 (phoenix) wxWidgets 3.2.4 |
| Kernel | 6.14.0-37-generic |
| GTK | 3.24.41 |
| Desktop | ubuntu:GNOME (X11) |
| Displays | 1 monitor |
| Hardware | **VM (virt-manager, virtio graphics)** |

**Result: NO CRASH**

### Developer Test 2: Same VM with Kernel 6.8.0-90

Installed kernel 6.8.0-90-generic on the same VM to match user's kernel:

| Component | Value |
|-----------|-------|
| Task Coach | 2.0.0.92 |
| Python | 3.12.3 |
| wxPython | 4.2.1 gtk3 (phoenix) wxWidgets 3.2.4 |
| **Kernel** | **6.8.0-90-generic** |
| GTK | 3.24.41 |
| Desktop | ubuntu:GNOME (X11) |
| Displays | 1 monitor |
| Hardware | **VM (virt-manager, virtio graphics)** |

**Result: NO CRASH** - Tested on both Wayland and X11 sessions.

### What This Proves

| Hypothesis | Status |
|------------|--------|
| wxPython 4.2.1 is broken | **RULED OUT** - Works on dev system |
| TEE stderr redirection is broken | **RULED OUT** - Works on dev system |
| Python 3.12 + wxPython combo | **RULED OUT** - Works on dev system |
| 3-monitor setup causes crash | **RULED OUT** - User crashed with 1 monitor |
| Config files cause crash | **RULED OUT** - User crashed on empty system |
| Missing packages cause crash | **RULED OUT** - Installing squaremap didn't help |
| Kernel 6.8.0-90 is the issue | **RULED OUT** - Works in VM with same kernel |
| **Real hardware vs VM** | **PRIMARY SUSPECT** - Only remaining difference |

### Comparison Summary

| Factor | User (CRASH) | Dev VM (OK) | Dev VM (OK) |
|--------|--------------|-------------|-------------|
| Kernel | 6.8.0-90 | 6.14.0-37 | 6.8.0-90 |
| Hardware | **Real PC** | VM | VM |
| Graphics | **Real GPU** | virtio | virtio |
| X11 | Yes | Yes | Yes |
| Result | **CRASH** | OK | OK |

The crash cannot be reproduced in a VM even with the same kernel. The issue appears to be related to **real hardware GPU drivers** interacting with wxPython/GTK.

---

## Investigation (January 3, 2026) - Version 2.0.0.96

### User Test: 3 Monitors with GNOME Extensions

User sjefbosman tested v2.0.0.96 with full desktop configuration:

| Component | Value |
|-----------|-------|
| Task Coach | 2.0.0.96 |
| Python | 3.12.3 |
| wxPython | 4.2.1 gtk3 (phoenix) wxWidgets 3.2.4 |
| **Kernel** | **6.8.0-90-generic** |
| GTK | 3.24.41 |
| glibc | 2.39 |
| Desktop | ubuntu:GNOME (X11) |
| Displays | **3 monitors** (1920x1080, 2560x1440, 2560x1440) |
| GNOME Extensions | Active |
| Task file | `~/Documents/Welcome.tsk` |
| Locale | en_US.UTF-8 (LC_TIME/LC_NUMERIC: en_GB.UTF-8) |

**Result: CRASH** - Segfault at `iocontroller.py:213` (wx.MessageBox)

### Stack Trace (v2.0.0.96)

```
Fatal Python error: Segmentation fault

Thread 0x00007c384c82b6c0 (most recent call first):
  File "taskcoachlib/filesystem/fs_poller.py", line 54 in run
  File "threading.py", line 1073 in _bootstrap_inner

Current thread 0x00007c386724f080 (most recent call first):
  File "taskcoachlib/gui/iocontroller.py", line 213 in open      ← CRASH HERE
  File "wx/core.py", line 3427 in <lambda>
  File "wx/core.py", line 2262 in MainLoop
  File "taskcoachlib/application/application.py", line 533 in start
  File "taskcoach.py", line 139 in start
  File "taskcoach.py", line 143 in <module>
```

### Analysis: Crash Location Changed

The crash moved from `SetActiveTarget` (v2.0.0.92) to `wx.MessageBox` (v2.0.0.96):

| Version | Crash Point | wx Call | When |
|---------|-------------|---------|------|
| 2.0.0.92 | `application.py:493` | `wx.Log.SetActiveTarget()` | Before MainLoop |
| 2.0.0.96 | `iocontroller.py:213` | `wx.MessageBox()` | During MainLoop (first event) |

**Key insight:** The `SetActiveTarget` line was commented out in v2.0.0.96, so the crash simply moved to the **next wx GUI call**. This confirms the issue is NOT specific to `SetActiveTarget` - it's a general wxPython/GTK problem on this system.

### The Crashing Code Path (v2.0.0.96)

```python
# iocontroller.py lines 203-214
def open(self, filename=None, showerror=wx.MessageBox, ...):
    ...
    if fileExists(filename):
        # Load file...
    else:
        errorMessage = _("Cannot open %s because it doesn't exist") % filename
        if operating_system.isMac():
            wx.CallAfter(showerror, errorMessage, ...)
        else:
            showerror(errorMessage, ...)  # ← LINE 213: CRASH
```

The user ran:
```bash
taskcoach.py ~/Documents/Welcome.tsk
```

If `~/Documents/Welcome.tsk` doesn't exist, the code attempts to show an error dialog via `wx.MessageBox`, which crashes.

### Key Diagnostic Question

**Did `mainwindow.Show()` succeed before the crash?**

The startup sequence is:
```
init():
  ├─ MainWindow created
  ├─ openAfterStart() schedules wx.CallAfter(self.open, filename)

start():
  ├─ mainwindow.Show()     ← Did this work? Any window flash?
  └─ MainLoop() starts
       └─ CallAfter fires → open() → wx.MessageBox → CRASH
```

If `mainwindow.Show()` succeeded (window appeared even briefly), then some wx GUI operations work. The crash may be specific to dialogs during early MainLoop.

If no window appeared at all, then wx GUI is fundamentally broken on this system.

### Questions Asked to User

1. **Did any GUI elements show up or flash quickly before the crash?**
2. **Does the file exist?** `ls -la ~/Documents/Welcome.tsk`
3. **Test with AppImage** (uses wxPython 4.2.4, wxWidgets 3.2.8):
   ```bash
   wget https://github.com/taskcoach/taskcoach/releases/download/v2.0.0.96/TaskCoach-2.0.0.96-x86_64.AppImage
   chmod +x TaskCoach-2.0.0.96-x86_64.AppImage
   ./TaskCoach-2.0.0.96-x86_64.AppImage
   ```
4. **Test both v2.0.0.96 .deb and AppImage on minimal system** (empty system, no extensions, single monitor)

### Pattern: Three Users on Kernel 6.8.0-90

So far, **three users** have reported segfaults, all on `Linux-6.8.0-90-generic`:

| User | Kernel | Hardware | Result |
|------|--------|----------|--------|
| sjefbosman | 6.8.0-90 | Real PC | CRASH |
| User 2 | 6.8.0-90 | Real PC | CRASH |
| User 3 | 6.8.0-90 | Real PC | CRASH |
| Developer VM | 6.8.0-90 | VM (virtio) | OK |
| Other users | Various | Various | OK |

This strongly suggests a kernel-specific issue, possibly related to:
- GA kernel CONFIG settings (preemption, timer rate)
- Interaction with real GPU drivers
- Security settings specific to GA kernel track

---

## Technical Analysis: Why wx GUI Calls Crash

### Original Theory: SetActiveTarget and stderr

The original crash line in v2.0.0.92:
```python
wx.Log.SetActiveTarget(wx.LogStderr())
```

This was theorized to be the **first explicit C++ stderr access** after TEE's file descriptor manipulation. However, since commenting out this line just moved the crash to `wx.MessageBox`, the theory is **partially invalidated** - the issue is broader than just stderr access.

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

## Remaining Suspect: Real Hardware GPU Drivers

All software hypotheses have been ruled out. Kernel 6.8.0-90 works fine in a VM. The crash only occurs on **real hardware**.

| System | Kernel | Hardware | Result |
|--------|--------|----------|--------|
| User (sjefbosman) | 6.8.0-90 | Real PC + real GPU | **CRASH** |
| Developer VM | 6.8.0-90 | VM + virtio graphics | OK |
| Developer VM | 6.14.0-37 | VM + virtio graphics | OK |

### Possible Hardware-Related Causes

1. **GPU driver interaction with stderr** - Real GPU drivers (NVIDIA, AMD, Intel) may interact differently with GTK/wxWidgets logging and file descriptors than VM virtual graphics.

2. **Driver-specific GTK initialization** - Real GPU drivers perform additional initialization during GTK startup that may conflict with TEE's stderr redirection.

3. **Proprietary vs open-source drivers** - NVIDIA proprietary drivers or specific Mesa versions may have bugs when stderr is redirected to a pipe.

4. **Known wxPython/GTK issues** - There are documented cases of wxPython segfaults related to GTK initialization order and logging ([wxWidgets #15898](https://github.com/wxWidgets/wxWidgets/issues/15898)).

### Server vs Desktop Kernel CONFIG Differences

The GA kernel (server default) has different compile-time settings than desktop kernels:

| Setting | Server (GA 6.8) | Desktop (HWE 6.14) | Impact |
|---------|-----------------|---------------------|--------|
| **Preemption** | `CONFIG_PREEMPT_NONE` (off) | `CONFIG_PREEMPT_VOLUNTARY` (on) | Race condition timing |
| **Timer rate** | 100 Hz | 250 Hz | Interrupt frequency |
| **I/O scheduler** | Deadline | CFQ | I/O ordering |
| **Mesa** | Older | 25.0 (backported) | Graphics stack |

**The preemption and timer differences could cause race conditions to manifest differently.**

If there's a timing-sensitive race between TEE's `dup2()` and wxWidgets' stderr access:
- Server kernel (100Hz, no preemption) → race condition triggers → CRASH
- Desktop kernel (250Hz, preemptive) → race condition doesn't trigger → OK
- VM (different timing characteristics) → race condition doesn't trigger → OK

### AppArmor (Both Have It)

Both server and desktop have AppArmor enabled by default, so this is unlikely to be the difference. However, it's still worth checking for denials:
```bash
sudo aa-status
sudo dmesg | grep -i apparmor
```

### Questions for User

To investigate security-related causes:
```bash
# Check AppArmor status
sudo aa-status

# Check for AppArmor denials
sudo dmesg | grep -i apparmor

# Check audit log
sudo ausearch -m avc -ts recent

# Check if running in confined mode
cat /proc/self/attr/current
```

### Ubuntu 24.04 Kernel Tracks

Ubuntu 24.04 LTS has **two separate kernel tracks** that do not cross-update:

| Track | Name | Kernel | Default For | Updates |
|-------|------|--------|-------------|---------|
| **GA** | General Availability | 6.8.0-xx | Server installs | Security patches only, stays on 6.8.x forever |
| **HWE** | Hardware Enablement | 6.14.0-xx | Desktop installs | Rolling updates to newer kernels |

**Key points:**
- Running `apt upgrade` does **NOT** switch tracks - GA stays on 6.8.x
- The user (sjefbosman) is on the GA track, likely from a server-style install
- GA kernel may have different security configurations than HWE
- To switch to HWE kernel:
  ```bash
  sudo apt install linux-generic-hwe-24.04
  sudo reboot
  ```

### Recommended Workaround for User

Ask user to switch to the HWE kernel track:
```bash
sudo apt install linux-generic-hwe-24.04
sudo reboot
```

This provides kernel 6.14.x which may resolve the GPU driver interaction issue.

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

**No fix will be applied** until the issue can be reproduced or root cause identified.

### What We Know

1. **Crash location is not fixed** - it moves to the next wx GUI call when the previous one is removed
2. **Three users affected**, all on kernel 6.8.0-90-generic (GA track)
3. **Cannot reproduce in VM** even with identical kernel
4. **Real hardware + GA kernel** appears to be the common factor

### Suspected Code (Historical)

| Version | Crash Location | Status |
|---------|----------------|--------|
| 2.0.0.92 | `wx.Log.SetActiveTarget(wx.LogStderr())` | Commented out in v2.0.0.96 |
| 2.0.0.96 | `wx.MessageBox()` in `iocontroller.py:213` | **Current crash point** |

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
| Kernel 6.8.0-90 is broken | Works in VM with same kernel |
| SetActiveTarget specifically | Commenting it out moved crash elsewhere |

### Current Theory

The crash appears to be caused by a **timing-sensitive race condition** or **hardware-specific wxPython/GTK issue** that only manifests on:
- Real hardware (not VMs)
- GA kernel track (6.8.0-xx with CONFIG_PREEMPT_NONE)
- Specific GPU driver configurations

The issue is **not a bug in Task Coach code** - it's an environmental incompatibility that we cannot reproduce.

---

## Next Steps

### Immediate Testing (Ask User)

1. **Confirm file existence:**
   ```bash
   ls -la ~/Documents/Welcome.tsk
   ```
   If file doesn't exist, test with a file that does exist to isolate the issue.

2. **Observe startup carefully:**
   - Does any window appear, even briefly, before the crash?
   - This determines if `mainwindow.Show()` succeeds

3. **Test AppImage** (uses newer wxPython 4.2.4, wxWidgets 3.2.8):
   ```bash
   wget https://github.com/taskcoach/taskcoach/releases/download/v2.0.0.96/TaskCoach-2.0.0.96-x86_64.AppImage
   chmod +x TaskCoach-2.0.0.96-x86_64.AppImage
   ./TaskCoach-2.0.0.96-x86_64.AppImage
   ```
   The AppImage bundles its own wxPython, which may behave differently.

4. **Test on minimal system:**
   - Empty system, no GNOME extensions, no other apps running
   - Single monitor
   - Test both .deb package and AppImage

### If Testing Confirms Broader wx Issue

5. **Ask user to switch to HWE kernel:**
   ```bash
   sudo apt install linux-generic-hwe-24.04
   sudo reboot
   ```
   This switches from GA (server) kernel 6.8.x to HWE (desktop) kernel 6.14.x.

6. **Ask user to check security configurations:**
   ```bash
   sudo aa-status                          # AppArmor status
   sudo dmesg | grep -i apparmor          # AppArmor denials
   sudo ausearch -m avc -ts recent        # Audit log
   cat /proc/self/attr/current            # Confinement status
   ```

7. **Ask user for GPU/driver info:**
   ```bash
   lspci | grep -i vga
   glxinfo | grep "OpenGL renderer"
   dpkg -l | grep -i nvidia
   ```

### Potential Code Workarounds

If the issue cannot be resolved at the system level:

1. **Delay file opening until window is ready:**
   - Use `wx.CallLater(100, self.open, filename)` instead of `wx.CallAfter`
   - Or wait for `EVT_ACTIVATE` on main window before opening file

2. **Avoid dialogs during early startup:**
   - Check file existence in `openAfterStart()` before scheduling `wx.CallAfter`
   - Log errors to console instead of showing dialogs during startup

3. **Skip SetActiveTarget entirely:**
   - Already done in v2.0.0.96, but crash moved elsewhere
   - Confirms the issue is broader than just this call

---

## References

- [wx.Log documentation](https://docs.wxpython.org/wx.Log.html)
- [wxLog Wiki](https://wiki.wxwidgets.org/WxLog)
- [Log Classes Overview](https://docs.wxpython.org/log_classes_overview.html)

---

**Last Updated:** January 3, 2026 (v2.0.0.96 crash analysis added)
