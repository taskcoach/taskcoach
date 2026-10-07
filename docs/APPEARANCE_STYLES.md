# Appearance Styles

## Table of Contents

- [TODO](#todo)
- [Overview](#overview)
- [SSOT Architecture](#ssot-architecture)
- [What the Views Draw](#what-the-views-draw)
- [Field Types](#field-types)
- [Derivation Sources by Object Type](#derivation-sources-by-object-type)
  - [Task](#task)
  - [Note](#note)
  - [Category](#category)
  - [Attachment](#attachment)
  - [Effort](#effort)
- [Category Style Priority](#category-style-priority)
- [Default Icons](#default-icons)
- [The Master Loop](#the-master-loop)
  - [Processing Order](#processing-order)
  - [Owned Object Traversal](#owned-object-traversal)
- [Stored Procedures](#stored-procedures)
  - [computeDerived](#computederived)
  - [computeEffective](#computeeffective)
  - [_getFromCategories](#_getfromcategories)
  - [_get_from_parent](#_get_from_parent)
- [SSOT Accessors (base Object)](#ssot-accessors-base-object)
- [Appearance Tab (Editor)](#appearance-tab-editor)
- [File Reference](#file-reference)
- [See Also](#see-also)

---

## TODO

1. **Attachment styling**: deferred, not in this release (D3 in
   [MASTER_SCHEDULER_REFACTOR.md](MASTER_SCHEDULER_REFACTOR.md#deferred-and-will-not-do)).
   Attachments draw only their own style, as on master: no categories,
   and `computeDerived` gives them no sources. Open for later: remove
   their Appearance tab and branch, or inherit the owner's style.

2. ~~**Note styling incomplete**~~: **Done.** Tested and confirmed that
   `computeDerived` correctly flows category fg/bg/font/icon values through
   to Notes via `_getFromCategories` for all field types.

3. ~~**Category assignment triggers filter refresh**~~: **Done
   2026-09-29.** Membership events (`member_added/removed_event_type()`) have
   their own handler, `CategoryFilter.on_membership_changed()`, which
   refilters only when the category or one it is under is filtered;
   filter events (`filterChangedEventType`) still refilter.

---

## Overview

All domain objects (Task, Category, Note, Attachment) use a Single Source of
Truth (SSOT) architecture for appearance properties. Each object stores derived,
override, and effective values for each style field. The master loop
(`MasterScheduler`), at the seconds that matter, recomputes derived and
effective values for all objects.

Efforts are the exception: they have no styles of their own and are drawn in
their task's.

---

## SSOT Architecture

Each style field has three layers per object:

| Layer | Description | Persisted? |
|-------|-------------|------------|
| **Override** | Explicitly set by user via Appearance tab | Yes |
| **Derived** | Computed from sources (categories, parent, status) | No (volatile) |
| **Effective** | Override if set, otherwise derived | No (volatile) |

Volatile fields are recomputed by the master loop within 1 second of any
change. A file read or merged is computed at once, before the views
draw it.

---

## What the Views Draw

Every view, widget, export and print, the tray and the editor's lists
draw the effective styles through:

| Method | Returns |
|--------|---------|
| `shown_fg_color()`, `shown_bg_color()`, `shown_font()` | The effective value, None for the system theme (the widget's own) |
| `shown_icon_id()` | The effective icon |

Efforts return their task's. The views refresh on the four effective
events (`effective_style_event_types()`); each setter sends one event
for a field's value, default and source together. An item's own style
shows at once (its setter computes its effective value), styles from
categories, parents and the status at the loop's next pass.

---

## Field Types

Four style fields, defined in `FIELD_TYPES`:

| Field | Default (no value) | No-value source |
|-------|-------------------|-----------------|
| `fgColor` | `SYS_COLOUR_WINDOWTEXT` | `"System Theme"` |
| `bgColor` | `SYS_COLOUR_WINDOW` | `"System Theme"` |
| `font` | `SYS_DEFAULT_GUI_FONT` | `"System Theme"` |
| `icon` | `""` (empty) | `"N/A"` |

Icons have type-specific defaults applied in `computeDerived` (see
[Default Icons](#default-icons)).

---

## Derivation Sources by Object Type

### Task

Sources checked in order (first non-system-theme value wins):

1. **Categories** - sorted by `stylePriority` descending (via `_getFromCategories`)
2. **Parent task** - `parent.effectiveXxx()` (via `_get_from_parent`), unless
   it comes from the parent's own status or tracking: each task shows its own
3. **Status** - `status_icon_id()`, `statusFgColor()`, etc. from `compute_stored_status()`

Source labels: `[Category] name`, `[Task] name`, `[Status] active/completed/...`

### Note

Sources checked in order:

1. **Categories** - sorted by `stylePriority` descending (via `_getFromCategories`)
2. **Parent note** - `parent.effectiveXxx()` (via `_get_from_parent`)

Source labels: `[Category] name`, `[Note] name`

Notes are categorizable (`CategorizableCompositeObject`), same as Tasks.

### Category

Sources checked in order:

1. **Parent category** - `parent.effectiveXxx()` (via `_get_from_parent`)

Source label: `[Category] name`

### Attachment

No sources. Derived value is always `None`. Only override or default icon applies.

### Effort

Not processed by the appearance system: `shown_*()` return its task's.

---

## Category Style Priority

When an object belongs to multiple categories, `stylePriority` determines which
category's appearance wins. Higher priority = checked first.

- Stored on `Category` as an Attribute (integer, default 0), saved as
  the category's `stylePriority` (omitted when 0)
- Sorted descending by `stylePriority`; equal priorities by name, then
  ID, so the choice is the same in every session (a set's order is not).
  **Ruling, 2026-09-29:** equal priorities take the first by name; the
  colours of several categories are no longer mixed, as they were
  before the views drew the effective styles
  ([MASTER_SCHEDULER_REFACTOR.md](MASTER_SCHEDULER_REFACTOR.md#views-on-the-effective-styles)).
  `by_style_priority()` gives this order; the task viewer's Category
  icons column shows the icons in it too.
- The status priority (Preferences > Statuses) only orders tasks
  sorted by status; statuses do not compete with categories, whose
  styles come first.
- First category with a non-system-theme value for the field wins
- Editable via `EditStylePriorityCommand`

**File:** `taskcoachlib/domain/category/category.py` (stylePriority accessor)
**File:** `taskcoachlib/command/categoryCommands.py` (EditStylePriorityCommand)

---

## Default Icons

Types without a status-based icon fallback get a default icon via
`TYPE_DEFAULT_ICONS` in `appearance.py`, applied at the end of `computeDerived`
when no other source provides an icon:

| Type | Default Icon | Source Label |
|------|-------------|-------------|
| Note | `nuvola_apps_knotes` | `"System Theme"` |
| Attachment | `nuvola_status_mail-attachment` | `"System Theme"` |

Tasks get their default icon from status (e.g., `nuvola_actions_ledblue` for active).
Categories have none (removed in #389): an icon of their own or their parent's.

---

## The Master Loop

The scheduler's pass runs `computeStyles()` for the objects a change or
a time condition concerns and what reads them, each once; the full
loop, for every object, when what every object reads changed
([MASTER_SCHEDULER_REFACTOR.md](MASTER_SCHEDULER_REFACTOR.md#incremental-pass)).

**File:** `taskcoachlib/gui/scheduler.py` (`MasterScheduler._run_pass()`)

### Processing Order

Each object once, sorted by kind, then depth (`_order()`), so what an
object reads is processed before it:

1. **Categories** (so tasks and notes can read their effective values)
2. **Tasks** (parents before subtasks)
3. **Notes**, global and owned (parents before subnotes)
4. **Attachments**

### Owned Object Traversal

The full loop takes each task's, category's and note's owned objects
with them (`_owned()`): `obj.notes(recursive=True)` and
`obj.attachments()`, then what those own in turn (task -> notes ->
attachments -> notes -> ...), and sorts them into the order above: an
owned note reads its categories, never its owner. No circular
ownership exists because users create new objects under owners.

---

## Stored Procedures

### computeDerived

Computes the derived value for one field of one object. Checks sources in
type-specific order and writes via `obj.setDerivedXxx(value, source)`.

### computeEffective

Computes the effective value: override if set, otherwise derived. Writes via
`obj.setEffectiveXxx(value, default, source)`.

### _getFromCategories

Shared helper for Task and Note derivation. Gets the object's categories,
sorts by `stylePriority` descending, returns `(value, source)` from the first
category with a non-system-theme effective value.

### _get_from_parent

Shared helper for Task, Note, and Category derivation. Checks the object's
parent for a non-system-theme effective value, returns `(value, source)`. A
task skips its parent's value from the parent's own status or tracking.

---

## SSOT Accessors (base Object)

All accessors are defined on `taskcoachlib/domain/base/object.py`:

| Method | Returns |
|--------|---------|
| `derivedXxx()` | Derived value (or field default) |
| `derivedXxxSource()` | Source label for derived value |
| `effectiveXxx()` | Effective value (override or derived) |
| `effectiveXxxSource()` | Source label for effective value |
| `setDerivedXxx(value, source)` | Write derived SSOT |
| `setEffectiveXxx(value, [default,] source)` | Write effective SSOT |

Where `Xxx` is `FgColor`, `BgColor`, `Icon`, or `Font`.

---

## Appearance Tab (Editor)

`TaskAppearancePage` (extends `ScrolledPage`) shows three sections:

1. **Derived values** - read-only display with source labels
2. **Override values** - user-editable controls
3. **Effective values** - read-only computed result

Used by Tasks, Categories, Notes, and Attachments (each editor includes
an `"appearance"` page).

**File:** `taskcoachlib/gui/dialog/editor.py` (class `TaskAppearancePage`)

---

## File Reference

| File | Purpose |
|------|---------|
| `taskcoachlib/domain/base/appearance.py` | SSOT stored procedures, `computeStyles()`, constants |
| `taskcoachlib/domain/base/object.py` | SSOT accessor/setter methods and `shown_*()` on base Object |
| `taskcoachlib/domain/task/task.py` | Task status icon/color/font, `compute_stored_status()` |
| `taskcoachlib/domain/category/category.py` | `stylePriority` attribute |
| `taskcoachlib/command/categoryCommands.py` | `EditStylePriorityCommand` |
| `taskcoachlib/config/defaults.py` | Default status icons/colors/fonts/sort priorities |
| `taskcoachlib/gui/dialog/editor.py` | `TaskAppearancePage` (Appearance tab in editor) |
| `taskcoachlib/gui/dialog/preferences.py` | `StatusesPage` (Statuses tab in preferences) |

---

## See Also

- [TASK_STATUS.md](TASK_STATUS.md) - Task status system and status-based icon defaults
- [SCHEDULERS.md](SCHEDULERS.md) - GlobalTimer architecture (drives the master loop)
- [ICON_LIBRARY.md](ICON_LIBRARY.md) - Icon sources, structure, and adding new icons
