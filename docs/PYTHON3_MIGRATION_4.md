# Python 3 Migration Technical Notes - Part 4: Infrastructure, i18n, and Feature Removals

This document is part of the Python 3 migration documentation. See [PYTHON3_MIGRATION_INDEX.md](PYTHON3_MIGRATION_INDEX.md) for the complete index.

**Contents:**
- [Logging Infrastructure](#logging-infrastructure-redirectedoutput--simple-custom-logging)
- [Python 3.12+ Escape Sequence Warning](#python-312-escape-sequence-warning)
- [File Locking: lockfile to fasteners Migration](#file-locking-lockfile--fasteners-migration)
- [App Icon Grouping Across Platforms](#app-icon-grouping-across-platforms)
- [Future Work](#future-work)
- [Internationalization and Locale Issues](#internationalization-and-locale-issues)
- [SyncML Removal](#syncml-removal)

*For additional feature removals, see [Part 5](PYTHON3_MIGRATION_5.md).*

---

## Logging Infrastructure: RedirectedOutput → Simple Custom Logging

**Date Fixed:** December 2025
**Affected Components:** `taskcoachlib/application/application.py`
**Root Cause:** The old `RedirectedOutput` class was a hack that captured stdout/stderr and showed an error popup if anything was written, but couldn't distinguish between debug info and actual errors.

### Problem Overview

Task Coach would show an "Errors have occurred" popup on exit even when there were no errors, because:
1. The `RedirectedOutput` class captured all stdout/stderr output
2. Startup debug logging (version info, GUI environment) wrote to stdout
3. The `summary()` method checked if anything was written and showed the popup

### Previous Workarounds (All Flawed)

| Approach | Problem |
|----------|---------|
| Toggle `error_mode` flag | Not thread-safe - race conditions could miss errors |
| Add `is_error` parameter to `write()` | Can't control what `print()` passes to `write()` |
| Only log when running from TTY | Loses debug info in log file for debugging crashes |
| Python `logging` module + ErrorTracker | Overly complex, still needed separate stderr capture |

### The Simple Solution: Custom log_message/log_error Functions

Replaced the `RedirectedOutput` hack with simple, unified logging:

```python
# Module state
_log_file = None
_has_errors = False
_has_errors_lock = threading.Lock()

def log_message(msg):
    """Log a debug message to file (and stdout if TTY)."""
    _write_log(msg, "DEBUG")

def log_error(msg):
    """Log an error and set the popup flag."""
    _write_log(msg, "ERROR")
    _set_error()

# File descriptor level stderr capture for native C library output
# Uses os.dup2() to redirect fd 2 through a pipe
# Background thread reads pipe, logs to file, echoes to terminal
def _stderr_reader_loop(pipe_read_fd, original_stderr_fd):
    while not _stop_stderr_reader:
        line = pipe_reader.readline()
        # Log to file, echo to original stderr
        if _ERROR_PATTERNS.search(line):
            _set_error()
```

### Usage

```python
log_message("Task Coach version 1.6.1")  # → file only, no popup
log_message("GUI environment info...")    # → file only, no popup
log_error("Something went wrong!")        # → file AND sets _has_errors=True
# Native stderr (GTK-CRITICAL etc)        # → captured, checked for error patterns
```

### Benefits

1. **Simple**: Two functions, one error flag, one stderr capture
2. **Thread-safe**: `_has_errors_lock` protects the error flag
3. **Unified**: Both Python and native library errors go through the same system
4. **True native library support**: File descriptor level capture (os.dup2) catches all C library stderr output
5. **No dependencies**: No `logging` module, just simple file I/O and os.pipe()

### Error Patterns Detected in stderr

The stderr capture checks for these patterns (case-insensitive):
- `CRITICAL`, `ERROR`
- `*** BUG ***`
- `assertion.*failed`
- `Segmentation fault`, `SIGSEGV`, `SIGABRT`
- `core dumped`

### Files Modified

| File | Change |
|------|--------|
| `taskcoachlib/application/application.py` | Removed `RedirectedOutput`, added simple logging functions |

### Key Functions

- `init_logging()` - Opens log file, installs stderr capture, sets up exception hook
- `shutdown_logging()` - Checks `_has_errors` and shows popup if needed, closes file
- `log_message(msg)` - Log debug message (no popup trigger)
- `log_error(msg)` - Log error message (triggers popup)

---

## Python 3.12+ Escape Sequence Warning

**Date Fixed:** December 2025
**Affected Components:** `taskcoachlib/thirdparty/desktop/__init__.py`
**Root Cause:** Python 3.12+ raises SyntaxWarning for invalid escape sequences in regular strings

### Problem Overview

On Debian Trixie (which uses Python 3.12+), installing Task Coach produced a warning:

```
/usr/lib/python3/dist-packages/taskcoachlib/thirdparty/desktop/__init__.py:61: SyntaxWarning: invalid escape sequence '\ '
  DESKTOP_LAUNCH="my\ opener"             Should run the "my opener" program to
```

### Root Cause Analysis

Python 3.12 introduced stricter handling of escape sequences. The module docstring contained example text with `\ ` (backslash-space) which is not a valid escape sequence:

```python
DESKTOP_LAUNCH="my\ opener"             Should run the "my opener" program to
```

In regular strings (not raw strings), `\ ` is interpreted as an escape sequence attempt but `\ ` has no special meaning, triggering the warning.

### The Fix

Converted the module docstring from a regular string to a raw string:

```python
# BEFORE
"""
Simple desktop integration for Python...
"""

# AFTER
r"""
Simple desktop integration for Python...
"""
```

Raw strings treat backslashes as literal characters, avoiding the warning while preserving the documentation's content.

### Files Modified

| File | Change |
|------|--------|
| `taskcoachlib/thirdparty/desktop/__init__.py` | Changed docstring from `"""` to `r"""` |

### Key Learnings

1. **Python 3.12+ is stricter about escape sequences**: What was silently ignored before now produces warnings.

2. **Docstrings are still strings**: Even documentation strings are parsed for escape sequences. Use raw strings (`r"""..."""`) when documentation contains backslashes.

3. **Test on newer Python versions**: Issues like this only appear on newer Python versions (3.12+).

---

## File Locking: lockfile → fasteners Migration

**Date:** December 2025
**Status:** Complete

### Background

The `lockfile` library used for cooperative file locking was deprecated and unmaintained. It has been replaced with `fasteners`, the officially recommended cross-platform file locking library.

### Key Changes

#### Core Implementation

**Before:**
```python
import lockfile

lock = lockfile.FileLock(filename)
lock.acquire(timeout=10)
# ... use file ...
lock.release()
```

**After:**
```python
import fasteners

lock = fasteners.InterProcessLock(filename + ".lock")
acquired = lock.acquire(blocking=True, timeout=0.1)
if not acquired:
    raise LockTimeout(f"File is locked: {filename}")
# ... use file ...
lock.release()
```

#### Custom Exception Classes

Custom exception classes were added to `taskcoachlib/persistence/taskfile.py`:

```python
class LockTimeout(Exception):
    """Raised when file lock cannot be acquired (another process has it)."""
    pass

class LockFailed(Exception):
    """Raised when file locking fails for other reasons."""
    pass
```

These are exported from `taskcoachlib/persistence/__init__.py` and used by `iocontroller.py`.

### Files Modified

| File | Change |
|------|--------|
| `taskcoachlib/persistence/taskfile.py` | Core locking implementation using fasteners |
| `taskcoachlib/persistence/__init__.py` | Export LockTimeout, LockFailed |
| `taskcoachlib/gui/iocontroller.py` | Use persistence.LockTimeout/LockFailed |
| `setup.py` | Replace lockfile with fasteners>=0.19 |
| `debian/control` | Replace python3-lockfile with python3-fasteners |
| `setup_*.sh` | Update pip install commands |
| `tests/unittests/thirdPartySoftwareTests/LockFileTest.py` | Test fasteners instead of lockfile |

### Why Lock File Pattern (Not flock)

The lock file pattern (existence of `.lock` file indicates lock) was preserved because:
- Works reliably on **network drives** (NFS, SMB) where `flock()` may not work
- Cross-platform compatibility
- Safer for document-oriented applications

### References

- [fasteners documentation](https://fasteners.readthedocs.io/)
- [lockfile deprecation notice](https://pypi.org/project/lockfile/)

---

## App Icon Grouping Across Platforms

**Date:** December 2025
**Status:** Complete

### Background

TaskCoach windows were not grouping properly in taskbars/docks across different operating systems. Each platform has its own mechanism for identifying related windows.

### Platform-Specific Solutions

#### Linux: WM_CLASS (X11)

Set at application startup in `taskcoachlib/application/application.py`:

```python
if operating_system.isGTK():
    self.SetClassName("taskcoach")
```

The `WM_CLASS` property tells the X11 window manager which windows belong together.

#### Linux: GLib prgname (Wayland)

**Important:** On Wayland, GNOME Shell uses `app_id` (derived from GLib's `prgname`) instead of X11's `WM_CLASS` to match running applications to their `.desktop` files.

Set at the very start of `taskcoach.py`, **before** any wxPython/GTK imports:

```python
def _set_wayland_app_id():
    """Set GLib prgname for Wayland app_id matching.

    On Wayland, GNOME Shell uses the app_id (derived from GLib's prgname)
    to match running applications to their .desktop files for proper
    icon display. This must be called BEFORE wxPython imports GTK.
    """
    if sys.platform != "linux":
        return

    try:
        import ctypes

        libglib = ctypes.CDLL("libglib-2.0.so.0")
        g_set_prgname = libglib.g_set_prgname
        g_set_prgname.argtypes = [ctypes.c_char_p]
        g_set_prgname.restype = None
        g_set_prgname(b"taskcoach")

        g_set_application_name = libglib.g_set_application_name
        g_set_application_name.argtypes = [ctypes.c_char_p]
        g_set_application_name.restype = None
        g_set_application_name(b"Task Coach")
    except (OSError, AttributeError):
        pass

# Must be called before wx/GTK imports
_set_wayland_app_id()
```

**Why ctypes instead of PyGObject:**
- Using `gi.repository.GLib` can cause segfaults when combined with wxPython
- ctypes directly calls the C function without importing Python GTK bindings
- Avoids potential conflicts with wxPython's GTK initialization

**Why before wxPython imports:**
- GTK reads the prgname during initialization
- wxPython imports GTK when the `wx` module is loaded
- Setting prgname after GTK init has no effect on app_id

#### Linux: StartupWMClass (Desktop Entry)

Added to `build.in/linux_common/taskcoach.desktop`:

```ini
[Desktop Entry]
...
StartupWMClass=taskcoach
```

This links the desktop entry to both WM_CLASS (X11) and app_id (Wayland) for proper dock/taskbar integration.

#### macOS: CFBundleIdentifier

Set in `pymake.py` for app bundle creation:

```python
"CFBundleIdentifier": "org.taskcoach.TaskCoach"
```

#### Windows: AppUserModelID

Set at application startup in `taskcoachlib/application/application.py`:

```python
if operating_system.isWindows():
    import ctypes
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("org.taskcoach.TaskCoach")
```

### Files Modified

| File | Change |
|------|--------|
| `taskcoach.py` | g_set_prgname via ctypes (Wayland) |
| `taskcoachlib/application/application.py` | SetClassName (X11), AppUserModelID (Windows) |
| `build.in/linux_common/taskcoach.desktop` | StartupWMClass=taskcoach |
| `pymake.py` | CFBundleIdentifier for macOS |

### Testing

- **Linux (GNOME/KDE on X11)**: All TaskCoach windows group under single taskbar icon via WM_CLASS
- **Linux (GNOME on Wayland)**: App icon displays correctly in dock via app_id/prgname
- **Windows**: Windows group in taskbar with correct app identity
- **macOS**: Windows group under single Dock icon

### References

- [GTK Wayland app_id documentation](https://docs.gtk.org/gtk3/wayland.html)
- [GNOME Application-Based design](https://wiki.gnome.org/Projects/GnomeShell/ApplicationBased)
- [GTK commit: Use g_get_prgname() for xdg_surface.set_app_id](https://gitlab.gnome.org/GNOME/gtk/-/commit/e1fd87728dd841cf1d71025983107765e395b152)

---

## Future Work

### TODO: Right-Aligned Toolbar Icon Jitter During Sash Drag

**Date Identified:** December 2025
**Status:** Investigation complete, fix deferred to separate branch

#### Root Cause

Right-aligned toolbar icons (after stretch spacer) jitter horizontally during AUI sash drag. Investigation revealed the issue is in the AGW AUI library itself:

- **Tools** are DRAWN by `AuiToolBar.OnPaint()` and undergo `GetToolFitsByIndex()` filtering during resize
- **Controls** (wxWindow children) are POSITIONED by wxWidgets' native layout system and remain stable
- The filtering causes positional mismatch during drag, resulting in visual jitter

This only affects tools added after a stretch spacer. Left-aligned tools and all controls (SearchCtrl, Choice dropdowns) do not jitter.

#### Attempted Workaround (Reverted)

A workaround was attempted using `PlateButton` controls instead of native toolbar tools for icons after the stretch spacer. While this prevented jitter, it introduced new issues:

1. **Toggle buttons (ITEM_CHECK)**: Commands like `ViewerHideTasks_completed`, `ViewerHideTasks_inactive`, and `ResetFilter` are toggle buttons. PlateButton has a `PB_STYLE_TOGGLE` style but:
   - Known wxPython issue: `SetState()` is overridden by mouse actions (see [wxPython discussion](https://discuss.wxpython.org/t/how-to-manually-set-the-toggle-state-of-wxpython-platebutton/28745))
   - `EVT_UPDATE_UI` integration needs work to sync initial toggle state from settings
   - Toggle buttons need proper visual feedback (pressed/unpressed state)

2. **Appearance matching**: PlateButton hover highlight differs from native AuiToolBar tools:
   - Native tools: Light grey square background on hover
   - PlateButton with `PB_STYLE_SQUARE | PB_STYLE_NOBG`: Blue oval highlight

3. **Event forwarding complexity**: PlateButton clicks need to be forwarded as `EVT_MENU` events to maintain compatibility with UICommand binding.

The workaround was reverted - all toolbar buttons now use native AuiToolBar tools.

#### Future Work

- Investigate upstream AGW AUI fix for `GetToolFitsByIndex()` during resize
- Or implement proper PlateButton workaround with:
  - `PB_STYLE_TOGGLE` for visual toggle state
  - `EVT_TOGGLEBUTTON` binding for toggle events
  - Proper `EVT_UPDATE_UI` handling to sync initial state
  - Custom styling to match native toolbar appearance

#### Test Application

A minimal test app exists at `test_aui_toolbar_jitter.py` that reproduces the issue and can be used to test fixes.

---

### Areas for Investigation

1. **AuiNotebook Perspective Management**
   - Consider removing perspective persistence entirely
   - Or implement perspective validation before restoring
   - Current solution: Perspective disabled for editor dialogs

2. **Size Constraint Architecture**
   - Review all uses of `SetSizerAndFit()` in codebase
   - Document where `SetMinSize()` is actually needed vs. harmful
   - Consider creating wrapper methods with safer defaults

3. **Python 3 String Handling**
   - Audit all string/unicode handling
   - Ensure consistent use of str vs bytes
   - Review file I/O encoding

4. **Deprecated wxPython APIs**
   - Review all wx.FONTSTYLE_* usage
   - Check for other deprecated constants/methods

5. **Internationalization Modernization**
   - Migrate from custom `po2dict.py` translation system to standard GNU gettext
   - Replace custom `Translator` class with `wx.GetTranslation`
   - Convert `.po` files to `.mo` using standard `msgfmt`
   - Adopt standard `locale/<lang>/LC_MESSAGES/` directory structure
   - See [Internationalization and Locale Issues](#internationalization-and-locale-issues) for details

---

## Internationalization and Locale Issues

### Problem Overview

**Date Fixed:** January 2026
**Affected Components:** Language detection, translation loading, wx.Locale initialization
**Root Cause:** Deprecated Python APIs, wx.Locale lifecycle issues, missing diagnostic logging

During investigation of a segfault on Ubuntu 24.04 with German locale, several i18n-related issues were discovered:

| Issue | Severity | Status |
|-------|----------|--------|
| `locale.getdefaultlocale()` deprecated since Python 3.11 | High | Fixed |
| wx.Locale object lifecycle can cause segfaults | High | Fixed |
| No diagnostic logging for locale/i18n issues | Medium | Fixed |
| Custom translation system diverges from standard gettext | Low | Future work |

### Root Cause Analysis

#### Issue 1: Deprecated `locale.getdefaultlocale()`

`locale.getdefaultlocale()` was deprecated in Python 3.11 and will be removed in Python 3.15. More importantly, it doesn't reliably read the `LANG` environment variable on Linux, returning incorrect values.

**Example of the problem:**
```
User's environment:  LANG=de_DE.UTF-8
getdefaultlocale():  ('en_US', 'UTF-8')  # Wrong!
```

This caused Task Coach to detect the wrong language for users with non-English locales.

#### Issue 2: wx.Locale Object Lifecycle

According to wxPython documentation, the old C++ wx.Locale object must be explicitly deleted before creating a new one. Failure to do so can cause segfaults:

> "The old C++ object needs to be deleted before the new one is created, and if we just assign a new instance to the old Python variable, the old C++ locale will not be destroyed soon enough, likely causing a crash."

Source: [wxPython Locale Issue Discussion](https://discuss.wxpython.org/t/questions-on-the-locale-issue/36084)

#### Issue 3: No Diagnostic Logging

When locale/translation issues occurred, there was no way to diagnose them from the log file. The user would only see a segfault with no context about what language was being loaded or what locale operations were attempted.

### Fixes Applied

#### Fix 1: Replace Deprecated `locale.getdefaultlocale()` (application.py, i18n/__init__.py)

```python
# BEFORE - Broken (deprecated, unreliable on Linux)
language = locale.getdefaultlocale()[0]

# AFTER - Fixed (reads environment variables directly)
def _get_system_language():
    # Check LANG and LC_ALL environment variables first
    lang = os.environ.get('LANG', os.environ.get('LC_ALL', ''))
    if lang:
        # Strip encoding suffix (e.g., "de_DE.UTF-8" -> "de_DE")
        lang = lang.split('.')[0]
        if lang and lang != "C" and lang != "POSIX":
            return lang

    # Fallback to locale.getlocale()
    try:
        lang = locale.getlocale(locale.LC_MESSAGES)[0]
        if lang and lang != "C" and lang != "POSIX":
            return lang
    except Exception:
        pass

    return "en_US"
```

#### Fix 2: wx.Locale Lifecycle Management (i18n/__init__.py)

```python
# BEFORE - Broken (old locale not deleted)
self.__locale = wx.Locale(languageInfo.Language)

# AFTER - Fixed (explicitly delete old locale first)
# Initialize to None in __init__
self.__locale = None

# In _setLocale():
if self.__locale is not None:
    del self.__locale
    self.__locale = None

self.__locale = wx.Locale(languageInfo.Language)
```

#### Fix 3: Comprehensive Locale Logging (application.py, i18n/__init__.py)

Added `_log_locale_info()` function that logs:
- Environment variables: LANG, LC_ALL, LC_CTYPE, LC_MESSAGES, LC_TIME, LC_NUMERIC, LC_COLLATE, LANGUAGE
- Python locale settings: `locale.getdefaultlocale()`, `locale.getlocale()`, `locale.getpreferredencoding()`
- System encoding: `sys.getdefaultencoding()`, `sys.getfilesystemencoding()`

Added `[i18n]` prefixed logging for:
- Translation module loading attempts and failures
- wx.Locale creation attempts
- Locale setting operations

**Example log output after fix:**
```
Locale/Language Info:
  LANG: de_DE.UTF-8
  LC_CTYPE: de_DE.UTF-8
  locale.getdefaultlocale(): ('de_DE', 'UTF-8')
  locale.getlocale(): ('de_DE', 'UTF-8')
  locale.getpreferredencoding(): UTF-8
  sys.getdefaultencoding(): utf-8
  sys.getfilesystemencoding(): utf-8
...
[i18n] Initializing Translator with language: 'de_DE'
[i18n] Could not load translation module 'de_DE': No module named 'de_DE'
[i18n] Could not load translation module 'de': No module named 'de'
[i18n] No translation module found for language 'de_DE' (tried: ['de_DE', 'de']). Using English.
[i18n] Setting locale for language: 'de_DE'
[i18n] Trying wx.Locale for: 'de_DE'
[i18n] Found wx language info: de_DE (Language=376)
[i18n] Created wx.Locale successfully
```

### Future Work: Modernize Translation System

#### Current Implementation (Custom)

Task Coach uses a custom translation system:

1. **`po2dict.py`** converts `.po` files to Python dict modules (based on `msgfmt.py`)
2. **`Translator` class** looks up translations in these Python dicts
3. Translation modules stored as `.py` files in `taskcoachlib/i18n/`
4. Custom `translate()` function instead of standard `wx.GetTranslation`

**No documented reason exists for this custom approach.** It appears to be legacy from the early Python 2 era.

#### Standard Best Practice (Recommended)

Modern wxPython applications use:

1. **GNU gettext `.mo` files** created with standard `msgfmt` tool
2. **`wx.GetTranslation`** for translation lookup: `_ = wx.GetTranslation`
3. Standard directory structure: `locale/<lang>/LC_MESSAGES/*.mo`
4. **`wx.Locale.AddCatalog()`** to load translation catalogs

#### Benefits of Migration

| Benefit | Description |
|---------|-------------|
| Standard tooling | Poedit, msgfmt, xgettext work directly |
| Familiar workflow | Translators use standard .po/.mo process |
| Native wx strings | wxPython dialogs/buttons auto-translated |
| Less code | Remove custom Translator class and po2dict.py |
| Better compatibility | Works with modern Python/wxPython versions |

#### Migration Steps (Future)

1. Convert `.po` files to `.mo` using standard `msgfmt`
2. Replace custom `Translator` class with `wx.GetTranslation`
3. Set `_ = wx.GetTranslation` in builtins
4. Use `wx.Locale.AddCatalog()` for translation catalogs
5. Adopt standard `locale/<lang>/LC_MESSAGES/` directory structure
6. Remove `po2dict.py` and generated Python translation modules

### References

- [wxPython i18n Wiki](https://wiki.wxpython.org/How%20to%20use%20the%20Internationalization%20-%20i18n%20(Phoenix))
- [Python locale.getdefaultlocale() deprecation](https://github.com/python/cpython/issues/90817)
- [wxPython Locale Questions](https://discuss.wxpython.org/t/questions-on-the-locale-issue/36084)
- [Python gettext documentation](https://docs.python.org/3/library/gettext.html)

---

## SyncML Removal

**Date Completed:** January 2026

### Background

SyncML was a synchronization protocol designed for the pre-smartphone era when syncing between PDAs, desktop apps, and servers was complex. Task Coach used the Funambol C++ API via a Python wrapper (`_pysyncml`).

### Why It Was Removed

**The SyncML project is dead.** This is the primary reason for removal.

| Aspect | Status |
|--------|--------|
| **SyncML Protocol** | Absorbed into OMA (Open Mobile Alliance) in 2009; now only used in enterprise MDM |
| **Funambol** | Company pivoted away from open-source; last meaningful activity ~2007-2012 |
| **pysyncml wrapper** | Source at `svn://www.fraca7.net/fraca7/pysyncml` is gone/inaccessible |
| **Consumer adoption** | All major vendors (Google, Apple, Microsoft) use proprietary cloud sync instead |
| **Task Coach binaries** | Were built for Python 2.6/2.7; cannot be rebuilt |

Modern cloud sync solutions (Dropbox, iCloud, Google Drive, OneDrive) have completely replaced SyncML for consumer use. There is no path forward for this feature.

Additional technical issues:
- Not functional on Linux (used Python 2 style `sys.platform == "linux2"` check)
- ~2600 lines of unmaintainable code with no upstream support

### Removed Files/Directories

```
taskcoachlib/syncml/           # Main SyncML implementation (7 Python files)
├── __init__.py
├── basesource.py
├── config.py
├── core.py
├── notesource.py
├── sync.py
└── tasksource.py

taskcoachlib/widgets/syncmlwarning.py    # SyncML warning dialog
taskcoachlib/gui/dialog/syncpreferences.py  # SyncML preferences dialog
taskcoachlib/bin.in/                     # pysyncml binary modules
├── README.txt
├── macos/IA32/_pysyncml.so
└── windows/py26/_pysyncml.pyd, py27/_pysyncml.pyd
```

### Modified Files

| File | Change |
|------|--------|
| `taskcoachlib/gui/dialog/preferences.py` | Removed SyncML feature toggle |
| `taskcoachlib/gui/menu.py` | Removed SyncML menu items |
| `taskcoachlib/gui/uicommand/uicommand.py` | Removed `FileSynchronize`, `EditSyncPreferences` commands |
| `taskcoachlib/gui/mainwindow.py` | Removed SyncML warning display |
| `taskcoachlib/gui/iocontroller.py` | Removed `synchronize()` method |
| `taskcoachlib/gui/viewer/task.py` | Changed `shadow=False` (was syncml setting) |
| `taskcoachlib/gui/viewer/note.py` | Changed `shadow=False` (was syncml setting) |
| `taskcoachlib/config/defaults.py` | Removed `syncml` settings section |
| `taskcoachlib/persistence/taskfile.py` | Removed SyncML config handling |
| `taskcoachlib/persistence/xml/reader.py` | `__parse_syncml_node()` now returns `None` |
| `taskcoachlib/persistence/xml/writer.py` | Removed `syncMLNode()` method |
| `taskcoachlib/widgets/__init__.py` | Removed `SyncMLWarningDialog` import |
| `taskcoachlib/help/__init__.py` | Removed SyncML help section |

### Backwards Compatibility

Old `.tsk` files with `syncmlconfig` nodes can still be read:

```python
def __parse_syncml_node(self, nodes, guid):
    """Parse the SyncML node from the nodes.

    SyncML has been removed. This method now returns None but is kept
    for backwards compatibility with old task files that contain syncmlconfig.
    """
    return None
```

The XML writer no longer writes `syncmlconfig` nodes to new files.

### Testing

After removal, verify:
- [ ] Application starts without SyncML-related errors
- [ ] Old task files with `syncmlconfig` load correctly
- [ ] New task files save without `syncmlconfig` nodes
- [ ] "Purge deleted items" menu works (was tied to SyncML shadow deletion)
- [ ] No "syncml" references in preferences dialog


---

**Previous:** [Part 3: GTK and AUI Issues](PYTHON3_MIGRATION_3.md)
**Next:** [Part 5: Feature Removals (Continued)](PYTHON3_MIGRATION_5.md)

**Last Updated:** January 2026
