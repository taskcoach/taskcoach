# Task Coach TODO

This document tracks planned improvements and known issues to address in future releases.

## Table of Contents

- [Simultaneous Processes and Locking](#simultaneous-processes-and-locking)
- [Configuration Naming Convention](#configuration-naming-convention)
- [Refactoring Save Patterns](#refactoring-save-patterns)
- [Backup Feature Review](#backup-feature-review)
- [Monkeypatches and Workarounds](#monkeypatches-and-workarounds)
- [Text-to-Speech Modernization](#text-to-speech-modernization)
- [GTK3 Widget Sizing Inconsistency](#gtk3-widget-sizing-inconsistency)
- [BookPage Default Alignment Inconsistency](#bookpage-default-alignment-inconsistency) *(Done)*
- [Preferences Page Alignment Overrides](#preferences-page-alignment-overrides)
- [Preferences Dialog: Dirty-Check and Button State](#preferences-dialog-dirty-check-and-button-state)
- [EVT_TEXT Compatibility Shim in MultiLineTextCtrl](#evt_text-compatibility-shim-in-multilinetextctrl)

---

## Simultaneous Processes and Locking

### Current Status

| Resource | Locking | Status |
|----------|---------|--------|
| Task files (`.tsk`) | `fasteners.InterProcessLock` | ✅ Safe - uses `filename.tsk.lock` |
| INI file (`taskcoach.ini`) | `fasteners.InterProcessLock` | ✅ Safe - uses `taskcoach.ini.lock` |
| Log file (`taskcoachlog.txt`) | None | ⚠️ Shared between instances |

### TODO: Per-Process Log Files

Currently, all Task Coach instances write to the same `taskcoachlog.txt` file. While append mode is generally atomic, log entries from multiple instances can interleave, making debugging difficult.

**Proposed Solutions:**

1. **INI file setting** - Allow users to specify a custom log file path in settings:
   ```ini
   [file]
   logfile = /path/to/custom/taskcoachlog.txt
   ```

2. **Auto-numbered log files** - Automatically append instance number to log filename:
   - First instance: `taskcoachlog.txt`
   - Second instance: `taskcoachlog-2.txt`
   - Third instance: `taskcoachlog-3.txt`
   - etc.

**Implementation Notes:**
- Would need to detect if log file is already in use by another instance
- Could use `fasteners.InterProcessLock` on the log file to detect conflicts
- Instance number could be determined by trying locks sequentially

---

## Configuration Naming Convention

### Current Status

The INI file settings use a mix of naming conventions (legacy):
- `effort`, `view` - single lowercase words
- `minidletime`, `showsmwarning` - concatenated lowercase (hard to read)
- `sdtcspans_effort` - some use underscores

### New Convention (PEP 8)

**All new settings should use `snake_case` naming convention:**

```ini
[feature]
my_new_setting = True    # New style (PEP 8 snake_case)
showsmwarning = True     # Old style (avoid for new settings)
```

**Rationale:**
- Python PEP 8 recommends `snake_case` for identifiers
- More readable than concatenated lowercase
- Matches modern Python conventions

**Note:** Existing settings should NOT be renamed to avoid breaking user INI files.
The `defaults.py` file has a comment marking where new snake_case settings begin.

---

## Refactoring Save Patterns

### Current Status

The application currently uses a per-change save pattern with debouncing to avoid excessive disk writes.

### Proposed Change

Refactor from **per-change with debounce** to **per-window active/lost-focus** save pattern.

| Aspect | Current (Debounce) | Proposed (Focus-based) |
|--------|-------------------|------------------------|
| Save trigger | Timer after last change | Window loses focus |
| Complexity | Complex timers, debounce logic | Simpler event-based |
| Multi-screen | Complex interactions | Cleaner handling |

**Pros:**
- No need for debounce timers
- Simpler implementation without complex timer management
- Cleaner multi-screen/multi-window interactions

**Cons:**
- Less precise undo log (changes batched per focus session)
- Less granular save points if crash or power failure occurs mid-session
- User must switch focus to trigger save

**Status:** To be reviewed

---

## Backup Feature Review

### Issues to Investigate

The backup/restore feature needs review - testing showed unexpected restore behavior.

**Questions to answer:**

1. **Where is the backup file stored?**
   - Document the backup file location
   - Is it configurable?

2. **How are backup/restore points decided?**
   - What triggers a backup point creation?
   - How many backup points are retained?
   - What is the rotation/cleanup policy?

3. **Is the backup file safe against corruption?**
   - What happens if save/update is interrupted (crash, power failure)?
   - Is there atomic write protection?
   - Are there checksums or integrity verification?

4. **Restore behavior:**
   - Why might restore not return expected data?
   - Is there a mismatch between what's shown and what's restored?

**Status:** Needs investigation and documentation

---

## Monkeypatches and Workarounds

**Status:** Review periodically to determine if still needed

This section documents workarounds and patches in the codebase that should be regularly reviewed to determine if they are still necessary. As wxPython, GTK, and other dependencies evolve, some of these may become obsolete.

### Active Workarounds

| Location | Workaround | Purpose | Review Notes |
|----------|------------|---------|--------------|
| `taskcoach.py:43-71` | `_set_wayland_app_id()` | Sets GLib program name for Wayland app ID matching | Required for proper Wayland dock integration |
| `taskcoach.py:73-74` | `import workarounds.monkeypatches` | Runtime patches for hypertreelist, inspect.getargspec, Window.SetSize | Required for wxPython compatibility |
| `monkeypatches.py` | `wx.CallAfter` crash guard | Prevents segfaults from callbacks to destroyed C++ objects | Required — see [CRASH_GUARD.md](CRASH_GUARD.md) |
| `application.py` | `OnExceptionInMainLoop` | Catches unhandled exceptions during wx event dispatch | Required — see [CRASH_GUARD.md](CRASH_GUARD.md) |

### Python 3.10 Support (Ubuntu 22.04)

The `inspect.getargspec` shim in `monkeypatches.py` is required for Python 3.10 (Ubuntu 22.04 Jammy). Python 3.11+ removed `getargspec()`.

**Remove after:** April 2027 (Ubuntu 22.04 LTS end of standard support)

Once Ubuntu 22.04 is out of LTS:
- Remove the `getargspec` shim from `monkeypatches.py`
- Update `setup.py` classifiers to remove Python 3.8, 3.9, 3.10
- Update `build.in/fedora/taskcoach.spec` to require Python >= 3.11
- Remove Ubuntu 22.04 .deb from README and CI workflows
| `taskcoach.py:24-30` | TEE module disabled | Stdout/stderr redirection to log file | Disabled pending further testing |
| `application.py:511-516` | `SetActiveTarget` disabled | wx log redirection to stderr | Disabled pending further testing |
| `application.py:21` | `import workarounds` | Imports display, font, encodings | Required |

### Removed Legacy Hacks (January 2026)

The following obsolete workarounds were removed from `taskcoach.py`:

| Workaround | Age | Reason for Removal |
|------------|-----|-------------------|
| `XLIB_SKIP_ARGB_VISUALS=1` | 2010 | Ubuntu 10.10 bug workaround - **may resolve Issue #64 segfault** |
| `mx.DateTime` import | 2012 | Ubuntu 12.04 console message - EOL 2017 |
| `wxversion.select(["2.8-unicode", "3.0"])` | 2008 | Ancient wx 2.8/3.0 selection - obsolete since ~2013 |
| `/usr/share/pyshared` path hack | 2012 | Ubuntu 12.04 Python path - EOL 2017 |

**Note:** Removing `XLIB_SKIP_ARGB_VISUALS=1` may resolve Issue #64 - user testing required to confirm. TEE module remains disabled pending further testing.

### wxPython Patches

| Location | Patch | Purpose |
|----------|-------|---------|
| `apply-wxpython-patch.sh` | `hypertreelist.py` patch | Fixes category row background coloring |

### HyperTreeList Text Truncation Bug (Standard wxPython Issue)

**Problem:** When column text is too wide and needs truncation, right-aligned and center-aligned columns display incorrectly. The text is truncated with "..." at the end (right side) regardless of alignment, then positioned per alignment, resulting in text being clipped on both sides.

**Expected behavior:**
- LEFT-aligned: Truncate from right, "..." at end (current behavior - correct)
- CENTER-aligned: Truncate from middle, "..." in middle
- RIGHT-aligned: Truncate from left, "..." at start

**Affected columns:** Due Date, completion dates, and other right-aligned date/time columns in task lists.

**Root cause:** `ChopText()` function in `wx.lib.agw.customtreectrl` (standard wxPython, not our patch) always truncates from the right. Both standard and patched HyperTreeList use this function without considering column alignment.

**Note:** This is a **standard wxPython bug**, not related to our local background-coloring patch. The local patch (`taskcoachlib/patches/hypertreelist.py`) is for Issue #2081/#1898 (row background colors), which is a separate issue.

**Fix options:**
1. Report upstream to wxPython/AGW and wait for fix
2. Modify local `hypertreelist.py` patch to use `wx.Control.Ellipsize(text, dc, wx.ELLIPSIZE_START, maxWidth)` for RIGHT-aligned columns
3. Create alignment-aware `ChopText` wrapper function in local patch

**References:**
- `wx.Control.Ellipsize()` supports `wx.ELLIPSIZE_START`, `wx.ELLIPSIZE_MIDDLE`, `wx.ELLIPSIZE_END`
- [wx.lib.agw.customtreectrl documentation](https://docs.wxpython.org/wx.lib.agw.customtreectrl.html) - ChopText function
- [wxWidgets/Phoenix GitHub Issues](https://github.com/wxWidgets/Phoenix/issues) - Searched January 2026: no existing issue for alignment-aware truncation
- Related issues found: #1898 (background coloring), #1880 (dark themes), #1901 (column resizing), #1395 (label editing with ellipsize)

**TODO:** Consider filing a new issue at [wxWidgets/Phoenix](https://github.com/wxWidgets/Phoenix/issues/new) with reproduction steps demonstrating the alignment-aware truncation bug.

**Status:** No upstream issue exists - consider filing new issue, or implement local workaround

### Recommendations

1. **Regular review:** Check this section every 6-12 months to clean up obsolete workarounds.

---

## Text-to-Speech Modernization

### Current Status

The "Let the computer say the reminder" feature uses a hand-rolled implementation:
- Mac: subprocess call to `say` command
- Linux: subprocess call to `espeak` command
- Windows: No-op (feature unavailable)

The preference is only shown on Mac/Linux, disabled by default.

### Proposed Change

Replace custom implementation with **pyttsx3** library:

| Aspect | Current | With pyttsx3 |
|--------|---------|--------------|
| Windows | Not supported | SAPI5 (native) |
| macOS | subprocess to `say` | NSSpeechSynthesizer (native) |
| Linux | subprocess to `espeak` | espeak (same) |
| Code lines | ~68 | ~15-20 |
| Dependency | None | pyttsx3 |

### Implementation Details

**Files to change:**

| File | Change |
|------|--------|
| `taskcoachlib/speak/speaker.py` | Replace with pyttsx3 implementation |
| `taskcoachlib/gui/dialog/preferences.py` | Remove OS check, show option on all platforms |
| `taskcoachlib/gui/dialog/reminder.py` | No change - API stays the same |

**New speaker.py implementation:**
```python
import pyttsx3
from taskcoachlib import patterns

class Speaker(metaclass=patterns.Singleton):
    def __init__(self):
        self._engine = pyttsx3.init()

    def say(self, text):
        self._engine.say(text)
        self._engine.runAndWait()
```

**References:**
- [pyttsx3 on PyPI](https://pypi.org/project/pyttsx3/) - Latest version 2.99 (July 2025)
- Supports Python 3.9-3.13
- Works offline, no internet required

**Status:** Ready to implement

---

## GTK3 Widget Sizing Inconsistency

### TODO: Test App

Create a small wxPython test app with buttons, dropdowns, and text inputs. Experiment with:
- Less padding on buttons/dropdowns
- More padding on text entries/spin controls

Test on Linux (GTK3), Windows, and macOS to see if consistent sizing can be achieved.

### The Problem

On Linux/GTK3, there is a noticeable visual inconsistency between widget types:
- **Large widgets:** Buttons, dropdowns (ComboBox), SpinButton arrows - all have consistent large size
- **Small widgets:** Text entries, number input fields - all have consistent small size

The two groups don't match each other, making the UI look incoherent. The obvious fix would be to increase padding on inputs and decrease padding on buttons/dropdowns to meet in the middle.

### Has This Been Addressed?

**Yes, extensively discussed but never successfully fixed:**

1. **[Numix Theme Issue #452](https://github.com/numixproject/numix-gtk-theme/issues/452)** - Explicitly states "The goal should be that entry and button have a similar height." They tried:
   - Remove min-height from buttons → some buttons became too small
   - Remove padding from buttons, add to entries → "changes too much"
   - **Result:** "were not able to get a consistent size of buttons and entries"

2. **[Mozilla Bug #1257811](https://bugzilla.mozilla.org/show_bug.cgi?id=1257811)** - Documents that GTK 3.20 changed to CSS min-height instead of padding. Adwaita theme sets `min-height: 32px` on entries but they remain visually smaller than buttons.

3. **[Inkscape GTK+3 Issues](https://wiki.inkscape.org/wiki/index.php?title=GTK%2B_3_issues)** - Notes "too many ways of creating buttons with icons which leads to inconsistency of behavior"

### Why It's Hard to Fix

- GTK 3.20 moved from pixel-based to CSS-based theming
- Different widgets calculate size differently (some use padding, some use min-height, some use icon size)
- Fixing one widget type often breaks another
- GNOME prioritized touch-friendly button sizes over visual consistency

### Impact on Task Coach

The custom `SpinCtrl` in `taskcoachlib/widgets/spinctrl.py` uses a `TextCtrl` + native `SpinButton` composition. The SpinButton arrows are GTK-sized (large) while the TextCtrl is standard entry-sized (small), creating a visually unbalanced control.

### Possible Solutions

1. **Accept it** - This is "platform native" behavior; GTK users see it everywhere
2. **Custom-drawn spin buttons** - Replace native `SpinButton` with custom arrow images (see [wxPython forum solution](https://discuss.wxpython.org/t/my-personal-crusade-against-gtk-3-spinctrls-size/30506))
3. **GTK CSS override** - Force widget sizes via `~/.config/gtk-3.0/gtk.css` (user-side, not app-side)

**Status:** Known GTK3 limitation. No action planned - accepting platform behavior.

---

## BookPage Default Alignment Inconsistency

**Status: Done** (February 2026)

The old `__defaultFlags()` had inconsistent alignment: column 0 used `ALIGN_LEFT`, all others used `ALIGN_RIGHT | EXPAND`. This was fixed by making all columns use uniform `wx.ALL | wx.ALIGN_TOP | wx.ALIGN_LEFT` in both `BookPage` and `ScrolledBookPage` (`taskcoachlib/widgets/notebook.py`).

Editor pages (e.g. `TaskAppearancePage`) benefit from this fix and have clean, consistent layouts.

---

## Preferences Page Alignment Overrides

### Problem

Preferences pages inherit from `ScrolledBookPage` (via `SettingsPageBase → SettingsPage`) and share the same uniform `__defaultFlags()`. However, most preferences pages **override flags on nearly every `addEntry()` call** with per-row custom values, so the clean defaults are never used.

The most common override is adding `wx.ALIGN_CENTER_VERTICAL` — the BookPage default is `ALIGN_TOP`, but label+control rows look better vertically centered. This forces every preferences page to manually specify flags.

### Inheritance Chain

```
All preferences pages
  → SettingsPage        (overrides addEntry for helpText only, no layout changes)
    → SettingsPageBase  (adds settings tracking lists, no layout changes)
      → ScrolledBookPage (owns __defaultFlags, addEntry, GridBagSizer)
```

No class in the preferences chain overrides `__defaultFlags`.

### Current State by Page

| Page               | Columns | Flag Overrides           |
|--------------------|---------|--------------------------|
| SavePage           | 3       | per-row custom           |
| WindowBehaviorPage | 2       | minimal                  |
| ThemePage          | 7       | every row unique         |
| LanguagePage       | 3       | nested panels + custom   |
| StatusesPage       | 11      | every row unique         |
| FeaturesPage       | 3       | minimal                  |
| TaskDatesPage      | 4       | per-row custom           |
| TaskReminderPage   | 3       | per-row custom           |
| IconsPage          | 2       | minimal                  |
| DurationPresetsPage| 2       | mixed                    |

### Contrast with Editor Pages

Editor pages like `TaskAppearancePage` define one shared `entryFlags` list and reuse it for every row — clean and consistent. Preferences pages specify flags individually per row.

### Possible Approaches

1. **Change BookPage default** from `ALIGN_TOP` to `ALIGN_CENTER_VERTICAL` — this would eliminate the most common override reason across all pages (both preferences and editors)
2. **Standardize simple pages** — pages with 2-3 columns (WindowBehavior, Features, Icons, DurationPresets) could follow the editor pattern: define one `entryFlags` per page, reuse it
3. **Leave complex pages alone** — ThemePage (7-col) and StatusesPage (11-col) have genuine table layouts that need per-row flags

### Files

- `taskcoachlib/widgets/notebook.py` — `BookPage.__defaultFlags()`, `ScrolledBookPage.__defaultFlags()`
- `taskcoachlib/gui/dialog/preferences.py` — all preferences pages
- `taskcoachlib/gui/dialog/editor.py` — editor pages (good example of clean pattern)

---

## Preferences Dialog: Dirty-Check and Button State

### Goal

Grey out Apply and OK buttons until the user has actually changed a setting.

### Approach

Use `EVT_CHILD_FOCUS` on each page to detect when the user leaves a control
(blur = confirmed change, not intermediary keystrokes). On each blur, compare
all tracked controls against the live `Settings` object (the INI file values).
No need to store "original values" — the settings object is the baseline.

**`SettingsPageBase`:**
- Bind `EVT_CHILD_FOCUS` → `_onChildFocus`
- Add `hasChanges()` that iterates `_booleanSettings`, `_choiceSettings`,
  `_integerSettings`, `_pathSettings`, `_textSettings`,
  `_multipleChoiceSettings` and compares each control's current value against
  `self.settings.get(section, setting)`
- Pages with custom controls (Theme, Task Appearance, working hours) override
  `hasChanges()` to add their own comparisons

**Parent dialog:**
- On child focus event (bubbled up or polled), check
  `any(page.hasChanges() for page in self)` and enable/disable Apply/OK
- After Apply saves, button state is re-evaluated (settings now match controls,
  so buttons grey out again automatically)

### Comparison per control type

| Method | Compare |
|--------|---------|
| `addBooleanSetting` | `checkBox.IsChecked() != self.getboolean(section, setting)` |
| `addChoiceSetting` | reconstructed value != `self.gettext(section, setting)` |
| `addIntegerSetting` | `spin.GetValue() != self.getint(section, setting)` |
| `addPathSetting` | `pathChooser.GetPath() != self.gettext(section, setting)` |
| `addTextSetting` | `textCtrl.GetValue() != self.gettext(section, setting)` |
| `addMultipleChoiceSettings` | checked items != `self.getlist(section, setting)` |

### Notes

- One binding per page, one `hasChanges()` scan per blur — no per-control wiring
- Custom pages override `hasChanges()` for non-standard controls
- `EVT_CHILD_FOCUS` fires on focus transfer between any child controls,
  which is the right granularity for confirmed-value checking

**Status:** Planned

---

## EVT_TEXT Compatibility Shim in MultiLineTextCtrl

`MultiLineTextCtrl` (StyledTextCtrl/Scintilla) overrides `Bind()` to remap `wx.EVT_TEXT` to `stc.EVT_STC_CHANGE` for compatibility with code written for `wx.TextCtrl`. If we keep Scintilla long-term, refactor all callers to use `EVT_STC_CHANGE` directly and remove the shim. File: `taskcoachlib/widgets/textctrl.py`.

---

**Last Updated:** February 2026
