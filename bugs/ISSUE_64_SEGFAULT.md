# Issue #64: Segmentation Fault on Ubuntu 24.04

**Possibly related:** https://github.com/taskcoach/taskcoach/issues/68

## Summary

Task Coach crashes with a segmentation fault on startup for some users running Ubuntu 24.04 with wxPython 4.2.1.

**GitHub Issue:** https://github.com/taskcoach/taskcoach/issues/64

**Status:** NOT REPRODUCED - No fix will be applied until issue can be reproduced

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

---

## Next Steps

1. **Ask user to check files:** Request the user answer the questions in "Files To Check" section above

2. **Ask user to test with fresh config:** Request the user rename `~/.config/Task Coach/` temporarily and test with clean configuration

3. **Ask user to test with Welcome.tsk:**
   ```
   taskcoach.py ~/Documents/Welcome.tsk
   ```
   This tests whether the crash occurs when explicitly loading a known-good task file.

4. **Get more information:** Need user's help to reproduce the issue before any fix can be made

---

## References

- [wx.Log documentation](https://docs.wxpython.org/wx.Log.html)
- [wxLog Wiki](https://wiki.wxwidgets.org/WxLog)
- [Log Classes Overview](https://docs.wxpython.org/log_classes_overview.html)

---

**Last Updated:** January 2, 2026
