# Appearance Styles

## Table of Contents

- [TODO](#todo)
- [Overview](#overview)
- [SSOT Architecture](#ssot-architecture)
- [Field Types](#field-types)
- [Derivation Sources by Object Type](#derivation-sources-by-object-type)
  - [Task](#task)
  - [Note](#note)
  - [Category](#category)
  - [Attachment](#attachment)
  - [Effort](#effort)
- [Category Style Priority](#category-style-priority)
- [Default Icons](#default-icons)
- [ComputeStyles Polling](#computestyles-polling)
  - [Processing Order](#processing-order)
  - [Owned Object Traversal](#owned-object-traversal)
- [Stored Procedures](#stored-procedures)
  - [computeDerived](#computederived)
  - [computeEffective](#computeeffective)
  - [_getFromCategories](#_getfromcategories)
  - [_getFromParent](#_getfromparent)
- [SSOT Accessors (base Object)](#ssot-accessors-base-object)
- [Appearance Tab (Editor)](#appearance-tab-editor)
- [File Reference](#file-reference)
- [See Also](#see-also)

---

## TODO

1. **Attachment styling**: Attachments appear to use the parent task's styling
   for fg/bg/font, but not for icon (icon is file-type based). However,
   attachments have no categories and the current `computeDerived` gives them
   no sources. Consider whether the Attachment Appearance tab and the
   Attachment branch in the derived/effective logic should be removed entirely,
   or whether parent-task inheritance should be added properly.

2. **Note styling incomplete**: Notes now correctly derive icon from categories
   (via `_getFromCategories`), but legacy behavior shows that Notes do not
   derive fg/bg/font styling from their categories. The refactored
   `computeDerived` applies `_getFromCategories` for all field types, but the
   actual results need to be reviewed and tested to confirm that category
   fg/bg/font values now flow through to Notes as expected.

---

## Overview

All domain objects (Task, Category, Note, Attachment) use a Single Source of
Truth (SSOT) architecture for appearance properties. Each object stores derived,
override, and effective values for each style field. A per-second polling system
(`ComputeStyles`) recomputes derived and effective values for all objects.

Efforts are the exception: they have no appearance/styling system and use a
hardcoded icon (`clock_icon`).

---

## SSOT Architecture

Each style field has three layers per object:

| Layer | Description | Persisted? |
|-------|-------------|------------|
| **Override** | Explicitly set by user via Appearance tab | Yes |
| **Derived** | Computed from sources (categories, parent, status) | No (volatile) |
| **Effective** | Override if set, otherwise derived | No (volatile) |

Volatile fields are recomputed by `ComputeStyles` polling within 1 second of
any change. They are `None` after file load until the first poll runs.

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
2. **Parent task** - `parent.effectiveXxx()` (via `_getFromParent`)
3. **Status** - `statusIcon()`, `statusFgColor()`, etc. from `computeStoredStatus()`

Source labels: `[Category] name`, `[Task] name`, `[Status] active/completed/...`

### Note

Sources checked in order:

1. **Categories** - sorted by `stylePriority` descending (via `_getFromCategories`)
2. **Parent note** - `parent.effectiveXxx()` (via `_getFromParent`)

Source labels: `[Category] name`, `[Note] name`

Notes are categorizable (`CategorizableCompositeObject`), same as Tasks.

### Category

Sources checked in order:

1. **Parent category** - `parent.effectiveXxx()` (via `_getFromParent`)

Source label: `[Category] name`

### Attachment

No sources. Derived value is always `None`. Only override or default icon applies.

### Effort

Not processed by the appearance system. Uses hardcoded `clock_icon`.

---

## Category Style Priority

When an object belongs to multiple categories, `stylePriority` determines which
category's appearance wins. Higher priority = checked first.

- Stored on `Category` as `__stylePriority` (integer, default 0)
- Sorted descending: `categories.sort(key=stylePriority, reverse=True)`
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
| Category | `folder_blue_icon` | `"System Theme"` |
| Note | `note_icon` | `"System Theme"` |
| Attachment | `paperclip_icon` | `"System Theme"` |

Tasks get their default icon from status (e.g., `led_blue_icon` for active).

---

## ComputeStyles Polling

`ComputeStyles` subscribes to `timer.second` and recomputes all objects every
second. This catches all changes without explicit triggers.

**File:** `taskcoachlib/domain/base/appearance.py` (class `ComputeStyles`)

### Processing Order

1. **Categories** (so tasks/notes can read their effective values)
2. **Tasks** (including child tasks via flat `CompositeSet`)
3. **Global notes** (standalone notes from `taskFile.notes()`)

### Owned Object Traversal

`_computeForObject` recursively processes owned objects after computing
the object's own styles:

- `obj.notes(recursive=True)` - all owned notes (flat list + children)
- `obj.attachments()` - all owned attachments

This covers the full ownership graph: task -> notes -> attachments -> notes -> ...
No circular ownership exists because users create new objects under owners.

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

### _getFromParent

Shared helper for Task, Note, and Category derivation. Checks the object's
parent for a non-system-theme effective value, returns `(value, source)`.

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
| `taskcoachlib/domain/base/appearance.py` | SSOT stored procedures, ComputeStyles, constants |
| `taskcoachlib/domain/base/object.py` | SSOT accessor/setter methods on base Object |
| `taskcoachlib/domain/task/task.py` | Task status icon/color/font, `computeStoredStatus()` |
| `taskcoachlib/domain/category/category.py` | `stylePriority` attribute |
| `taskcoachlib/domain/categorizable/categorizable.py` | Legacy category color/font mixers |
| `taskcoachlib/command/categoryCommands.py` | `EditStylePriorityCommand` |
| `taskcoachlib/config/defaults.py` | Default status icons/colors/fonts/sort priorities |
| `taskcoachlib/gui/dialog/editor.py` | `TaskAppearancePage` (Appearance tab in editor) |
| `taskcoachlib/gui/dialog/preferences.py` | `StatusesPage` (Statuses tab in preferences) |

---

## See Also

- [TASK_STATUS.md](TASK_STATUS.md) - Task status system and status-based icon defaults
- [SCHEDULERS.md](SCHEDULERS.md) - GlobalTimer architecture (drives ComputeStyles polling)
- [ICON_LIBRARY.md](ICON_LIBRARY.md) - Icon sources, structure, and adding new icons
- [ICON_PLURALIZE.md](ICON_PLURALIZE.md) - Plural/singular icon mapping (may be removed)
