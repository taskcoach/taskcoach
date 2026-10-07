# Preferences

The Preferences dialog (Edit > Preferences, Alt+P): its pages, and OK,
Apply and Cancel. The settings themselves and the settings file:
[SETTINGS.md](SETTINGS.md).

## Table of Contents

1. [The Dialog](#the-dialog)
2. [The Pages](#the-pages)
3. [OK, Apply and Cancel](#ok-apply-and-cancel)
4. [Layout](#layout)
5. [History](#history)
6. [Key Files](#key-files)

---

## The Dialog

- `Preferences` (`gui/dialog/preferences.py`), a `NotebookDialog`
  (`widgets/dialog.py`) with one tab per page, opened by
  `EditPreferences` (`wx.ID_PREFERENCES`, which macOS puts in the
  application menu).
- Not modal: the main window stays usable while it is open.
- Each page reads the settings when the dialog opens.
- The first size fits the pages, at most 80% of the screen; the pages
  scroll ([WINDOW_GEOMETRY.md](WINDOW_GEOMETRY.md#decisions) 10).

## The Pages

In the dialog's order. Every change waits for OK or Apply
([below](#ok-apply-and-cancel)); some apply only after a restart.

| Page | Settings | More |
|------|----------|------|
| Windows | Tips at startup; check for a new version at startup; tray clock ticking while tracking effort | [PACKAGING.md](PACKAGING.md#version-check) |
| Files | Autosave after every change (on by default since 1.3.21, 2012); the settings file beside the program, for a removable drive; the attachment base folder | [PERSISTENCE_XML.md](PERSISTENCE_XML.md#saving), [ATTACHMENTS.md](ATTACHMENTS.md) |
| Regional | Language; date format and its display override; time format; decimal separator; currency decimal places; spell checking and its language. The language and formats apply after a restart, as the page says (in red once changed) | [LOCALE.md](LOCALE.md), [TRANSLATIONS.md](TRANSLATIONS.md), [SPELLCHECKING.md](SPELLCHECKING.md) |
| Task dates | Mark a parent completed with its last child; hours a task is due soon; what the planned start and due dates do when the other changes; default planned start, due, actual start, completion and reminder dates | [DATETIME_PRESETS.md](DATETIME_PRESETS.md) |
| Reminders | Reminder sound, with Test; default snooze time; snooze times offered | [REMINDERS.md](REMINDERS.md) |
| Durations | Duration presets of tasks and of efforts: Add, Delete | [DURATION_CALCULATIONS.md](DURATION_CALCULATIONS.md#preset-dropdown-sync) |
| Theme | Mode (light, dark, automatic; on Windows after a restart); calendar colours, light and dark: weekday header, days of other months, weekend days, today's border; spell-check underline colour; hover outline width | [SETTINGS.md](SETTINGS.md#system-theme-changes), [WINDOWS.md](WINDOWS.md#dark-mode) |
| Statuses | Per status: sort priority, and colours, font and icon, light and dark; legacy status icons | [TASK_STATUS.md](TASK_STATUS.md), [TASK_STATUS_SORT.md](TASK_STATUS_SORT.md), [APPEARANCE_STYLES.md](APPEARANCE_STYLES.md) |
| Features | Start of the work week; working hours (after a restart); calendar gradients; minutes and seconds between suggested times; idle time notice; decimal effort times; hover popups; editing cells in place, and by a slow double click | [IDLE.md](IDLE.md), [LIST_MANAGEMENT.md](LIST_MANAGEMENT.md#in-place-editing) |
| Icons | Icon sets in the icon picker; theme name and context in icon search; icon size (read nowhere yet: kept for larger icons on high-DPI screens, P49 in [MASTER_SCHEDULER_REFACTOR.md](MASTER_SCHEDULER_REFACTOR.md#pre-existing-issues)) | [ICON_PICKER_REFACTORING.md](ICON_PICKER_REFACTORING.md) |

## OK, Apply and Cancel

**Ruled by designer 2026-10-07** ("proceed with holding all changes
and having the apply/cancel options, and having them
grey/disabled/enabled as relevant, following modern best practices"),
as Windows' property sheets
([Property Sheets: Design Guidelines](https://learn.microsoft.com/en-us/previous-versions/windows/desktop/bb226808(v=vs.85)),
[About Property Sheets](https://learn.microsoft.com/en-us/windows/win32/controls/property-sheets)):

- **OK** saves every page's changes and closes. **Apply** saves them
  and stays open. **Cancel** closes and drops what was not saved; it
  does not undo an Apply. Escape and the window's close button are
  Cancel (wx sends Cancel for both).
- **Apply is greyed** until a page differs from what it showed: at
  open, after Apply, and when a change is undone by hand. OK and
  Cancel are always enabled.
- Changes show in Task Coach once saved: a calendar colour after
  Apply or OK, not while picking.
- The settings file is written 2 s after the last change
  ([SESSION_END.md](SESSION_END.md#rules) 1).

How:

- Each page's `values()` lists what OK and Apply save: (section,
  option, value) for each control the `add*Setting` helpers made
  (`_booleanSettings`, `_choiceSettings`, `_multipleChoiceSettings`,
  `_integerSettings`, `_colorSettings`, `_fontSettings`,
  `_iconSettings`, `_pathSettings`), and the page's own controls:
  Regional's six choices and `view.language`, Statuses' priorities,
  Features' working hours, Theme's "Other Months Days Background",
  Durations' presets. `ok()` saves that list, so Apply's state and
  what is saved cannot disagree.
- Apply is enabled while the lists differ from those taken at open or
  at the last Apply. Compared with what the page showed, not with the
  settings file, so an older file's way of writing a value does not
  count as a change.
- Event-driven, no polling at idle
  ([LIST_MANAGEMENT.md](LIST_MANAGEMENT.md#vampire-cpu-usage)): once
  the pages are built, the dialog binds each control's change event
  (checkbox, choice, text, button, colour, font, icon, folder, number,
  checked list). Bound last, it runs before the page's own handlers,
  which may consume the event; it compares soon after them
  (`patterns.later.soon`), as they may change other controls (a
  status's priorities, the working hours). Typing in a number box
  enables Apply at once. Durations' Delete buttons, made after, call
  `edited()`.
- A page's other effects follow only a real change: the Theme page's
  redraw of open calendars, date pickers and spell-checked fields;
  the Statuses page's re-sort of the task views.

## Layout

Each page is a `ScrolledBookPage` (`widgets/notebook.py`): rows added
with `addEntry()` to a grid, cells aligned top left by default
([TODO.md](TODO.md#8-bookpage-default-alignment-inconsistency) 8).
The `add*Setting` helpers place a control and its grey help text;
Theme and Statuses lay out their own columns
([TODO.md](TODO.md#9-preferences-page-alignment-overrides) 9).
`SettingsPage.fit()` wraps the labels of the first column, finding
them through the grid (`GetItemPosition()`): in a test run, wxPython
handed back a grid item as a plain `SizerItem`, without `GetPos()`,
and the dialog failed to open (P248 in
[REFINEMENT_REFACTOR.md](REFINEMENT_REFACTOR.md)).

## History

Until 2026-10-07 (the same in 2.0.3.0):

- **Cancel kept some changes** (P247): Durations' Add and Delete and
  the Theme page's colours, System checkboxes and Reset buttons saved
  at once, redrawing open calendars as the user picked. Preferences >
  Durations, Delete "2 days", Cancel: "2 days" was gone, from
  TaskCoach.ini too.
- **OK and Apply were always enabled**, asked on GitHub as #329
  ("apply in prefs ought to be greyed out if nothing has changed"),
  first deferred (D24). The first plan (TODO.md 10, moved here)
  compared on `EVT_CHILD_FOCUS`; it fires when a control gains focus,
  so it missed a checkbox click (GTK toggles on release; macOS gives a
  clicked checkbox no focus) and the last edit (a disabled button
  takes no focus). It also kept OK greyed until a change, which
  Windows' guidelines do not.
- The Statuses page re-sorted the task views at every OK.
- Unchecking System for "Other Months Days Background" kept showing
  the system's colour, though the saved one was then used.

## Key Files

| File | Holds |
|------|-------|
| `taskcoachlib/gui/dialog/preferences.py` | The pages and the dialog's Apply state |
| `taskcoachlib/widgets/dialog.py` | `NotebookDialog`: OK, Apply, Cancel |
| `taskcoachlib/widgets/notebook.py` | The pages' layout |
| `taskcoachlib/config/defaults.py` | The default values |
| `taskcoachlib/config/settings.py` | The settings store |
| `tests/unittests/guiTests/PreferencesTest.py` | Cancel, OK, Apply and Apply's state |
