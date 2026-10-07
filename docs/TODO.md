# Task Coach TODO

This document tracks planned improvements and known issues to address in future releases.

## Table of Contents

1. [Simultaneous Processes and Locking](#1-simultaneous-processes-and-locking) *(Done)*
2. [Configuration Naming Convention](#2-configuration-naming-convention)
3. [Refactoring Save Patterns](#3-refactoring-save-patterns) *(Dropped)*
4. [Backup Feature Review](#4-backup-feature-review) *(Done)*
5. [Monkeypatches and Workarounds](#5-monkeypatches-and-workarounds)
6. [Text-to-Speech Modernization](#6-text-to-speech-modernization) *(Removed)*
7. [GTK3 Widget Sizing Inconsistency](#7-gtk3-widget-sizing-inconsistency) *(No action)*
8. [BookPage Default Alignment Inconsistency](#8-bookpage-default-alignment-inconsistency) *(Done)*
9. [Preferences Page Alignment Overrides](#9-preferences-page-alignment-overrides) *(Done)*
10. [Preferences Dialog: Dirty-Check and Button State](#10-preferences-dialog-dirty-check-and-button-state) *(Done)*
11. [EVT_TEXT Compatibility Shim in MultiLineTextCtrl](#11-evt_text-compatibility-shim-in-multilinetextctrl) *(Done)*
12. [Thunderbird/IMAP Mail Integration Review](#12-thunderbirdimap-mail-integration-review) *(Closed)*
Signaling system cleanup has moved to
[PUBLISHER_OBSERVER.md](PUBLISHER_OBSERVER.md#signaling-system-cleanup).

---

## 1. Simultaneous Processes and Locking

**Status: Done**

| Resource | Locking |
|----------|---------|
| Task files (`.tsk`) | `resourcelock`, `filename.tsk.lock` ([FILE_LOCKING.md](FILE_LOCKING.md)) |
| INI file (`taskcoach.ini`) | `resourcelock`, `taskcoach.ini.lock` ([FILE_LOCKING.md](FILE_LOCKING.md)) |

Task Coach writes no log file: the log goes to the terminal
([LOGGING_GUIDE.md](LOGGING_GUIDE.md)).

---

## 2. Configuration Naming Convention

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

## 3. Refactoring Save Patterns

**Dropped 2026-10-07**, **ruled by designer** ("completely drop the
whole thing of a save on loss of focus ... we will use auto save,
which saves all the time, or save on demand. There should not be a
third mode"): saving when the window loses focus, instead of after
each change. Added 2025-12-26 to drop autosave's debounce timer,
which is gone: autosave saves milliseconds after each change, with no
timer. Leaving Task Coach already saves the field being typed in:
[PERSISTENCE_XML.md](PERSISTENCE_XML.md#saving).

---

## 4. Backup Feature Review

**Done 2026-10-06** (P94): the questions are answered, and the restore
fixed, in [PERSISTENCE_XML.md](PERSISTENCE_XML.md#backups).

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

## 5. Monkeypatches and Workarounds

**Status:** Review periodically to determine if still needed

The list of bundled, copied and runtime-patched third-party code is
[THIRD_PARTY_CODE.md](THIRD_PARTY_CODE.md); review it every 6 to 12
months and whenever a dependency's version changes.

### HyperTreeList Text Truncation Bug (Standard wxPython Issue)

**Problem:** When column text is too wide and needs truncation, right-aligned and center-aligned columns display incorrectly. The text is truncated with "..." at the end (right side) regardless of alignment, then positioned per alignment, resulting in text being clipped on both sides.

**Closed 2026-10-06, ruled by designer (REFINEMENT_REFACTOR.md To Do 10):** this applies only with `TR_ELLIPSIZE_LONG_ITEMS`, which Task Coach never sets. In Task Coach a right-aligned value wider than its column is drawn from the column's left edge and cut on the right, without "..." (D15), and stays so.

**Expected behavior:**
- LEFT-aligned: Truncate from right, "..." at end (current behavior - correct)
- CENTER-aligned: Truncate from middle, "..." in middle
- RIGHT-aligned: Truncate from left, "..." at start

**Affected columns:** Due Date, completion dates, and other right-aligned date/time columns in task lists.

**Root cause:** `ChopText()` in `customtreectrl` always truncates from the right, and HyperTreeList calls it without the column's alignment. Upstream wxPython has the same bug; Task Coach's copy is the bundled `taskcoachlib/patches/customtreectrl.py`, so it can be fixed there ([BUNDLED_TREE_WIDGET.md](BUNDLED_TREE_WIDGET.md)).

**Fix options:**
1. Report upstream to wxPython/AGW and wait for fix
2. In the bundled `hypertreelist.py`, use `wx.Control.Ellipsize(text, dc, wx.ELLIPSIZE_START, maxWidth)` for RIGHT-aligned columns
3. An alignment-aware `ChopText()` in the bundled `customtreectrl.py`

**References:**
- `wx.Control.Ellipsize()` supports `wx.ELLIPSIZE_START`, `wx.ELLIPSIZE_MIDDLE`, `wx.ELLIPSIZE_END`
- [wx.lib.agw.customtreectrl documentation](https://docs.wxpython.org/wx.lib.agw.customtreectrl.html) - ChopText function
- [wxWidgets/Phoenix GitHub Issues](https://github.com/wxWidgets/Phoenix/issues) - Searched January 2026: no existing issue for alignment-aware truncation
- Related issues found: #1898 (background coloring), #1880 (dark themes), #1901 (column resizing), #1395 (label editing with ellipsize)

**TODO:** Consider filing a new issue at [wxWidgets/Phoenix](https://github.com/wxWidgets/Phoenix/issues/new) with reproduction steps demonstrating the alignment-aware truncation bug.

**Status:** No upstream issue exists - consider filing new issue, or implement local workaround

---

## 6. Text-to-Speech Modernization

**Removed 2026-10-07**, **ruled by designer** (P94): spoken reminders
were removed instead. This plan (pyttsx3), its costs and a smaller way
are in [SPOKEN_REMINDERS.md](SPOKEN_REMINDERS.md#a-better-solution).

---

## 7. GTK3 Widget Sizing Inconsistency

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

## 8. BookPage Default Alignment Inconsistency

**Status: Done** (February 2026)

The old `__defaultFlags()` had inconsistent alignment: column 0 used `ALIGN_LEFT`, all others used `ALIGN_RIGHT | EXPAND`. This was fixed by making all columns use uniform `wx.ALL | wx.ALIGN_TOP | wx.ALIGN_LEFT` in both `BookPage` and `ScrolledBookPage` (`taskcoachlib/widgets/notebook.py`).

Editor pages (e.g. `TaskAppearancePage`) benefit from this fix and have clean, consistent layouts.

---

## 9. Preferences Page Alignment Overrides

**Status: Done** (February 2026)

`ALIGN_TOP` is the correct BookPage default. Simple preferences pages
(WindowBehavior, Features, Icons, DurationPresets) now use clean helpers
(`addBooleanSetting`, `addChoiceSetting`, `addIntegerSetting`,
`_makeInlinePanel`) that handle layout internally — no per-row flag
overrides needed. Complex pages (ThemePage, StatusesPage) retain custom
flags for their multi-column layouts, which is correct.

---

## 10. Preferences Dialog: Dirty-Check and Button State

**Done 2026-10-07**, **ruled by designer**: Apply greyed until a
change, OK and Cancel always enabled
([PREFERENCES.md](PREFERENCES.md#ok-apply-and-cancel)); the first
plan's flaws are in [its History](PREFERENCES.md#history).

---

## 11. EVT_TEXT Compatibility Shim in MultiLineTextCtrl

**Status: Done** (September 2026)

No caller binds `wx.EVT_TEXT` on a `MultiLineTextCtrl` (the text
fields save on `EVT_KILL_FOCUS`), so its remap to `EVT_STC_CHANGE`
was removed.

---

## 12. Thunderbird/IMAP Mail Integration Review

**Status:** closed 2026-10-04: mail stays local, no IMAP, **ruled by
designer** ([EMAIL_ATTACHMENTS.md](EMAIL_ATTACHMENTS.md#decisions) 8).
The IMAP reader, its password dialog and `keyring` were removed, so
OAuth2, NTLM and the Flatpak's network and Secret portal for IMAP are
no longer needed.

---

**Last Updated:** September 2026
