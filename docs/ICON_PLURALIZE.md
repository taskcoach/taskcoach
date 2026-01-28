# Icon Plural/Singular Mapping

> See also: [TASK_STATUS.md](TASK_STATUS.md#pluralsingular-transformation) for how tasks apply this mapping.

## Overview

The icon system automatically converts icons between singular and plural forms
based on whether a `CompositeObject` (task, category, note) has children.
This is implemented in `CompositeObject.pluralOrSingularIcon()` at
`taskcoachlib/domain/base/object.py:794`.

## Complete Plural Mapping Table

Defined in `taskcoachlib/domain/attribute/icon/__init__.py`:

### LED → Folder (Task Status Icons)

| Singular (No Children) | Plural (Has Children) |
|------------------------|-----------------------|
| `led_blue_icon`        | `folder_blue_icon`    |
| `led_blue_light_icon`  | `folder_blue_light_icon` |
| `led_grey_icon`        | `folder_grey_icon`    |
| `led_green_icon`       | `folder_green_icon`   |
| `led_orange_icon`      | `folder_orange_icon`  |
| `led_purple_icon`      | `folder_purple_icon`  |
| `led_red_icon`         | `folder_red_icon`     |
| `led_yellow_icon`      | `folder_yellow_icon`  |

### Other Icons

| Singular (No Children) | Plural (Has Children)          |
|------------------------|--------------------------------|
| `book_icon`            | `books_icon`                   |
| `cogwheel_icon`        | `cogwheels_icon`               |
| `envelope_icon`        | `envelopes_icon`               |
| `heart_icon`           | `hearts_icon`                  |
| `key_icon`             | `keys_icon`                    |
| `checkmark_green_icon` | `checkmark_green_icon_multiple` |
| `person_icon`          | `persons_icon`                 |

### Reverse (Singular) Mapping

The singular mapping is auto-generated as the reverse of the plural mapping.
For example, `folder_blue_icon` → `led_blue_icon`, `persons_icon` → `person_icon`.

### Open Folder Mapping

When a folder icon is in "selected" state, it maps to an open variant:

| Folder Icon              | Open Variant                  |
|--------------------------|-------------------------------|
| `folder_blue_icon`       | `folder_blue_open_icon`       |
| `folder_grey_icon`       | `folder_grey_open_icon`       |
| `folder_green_icon`      | `folder_green_open_icon`      |
| `folder_orange_icon`     | `folder_orange_open_icon`     |
| `folder_purple_icon`     | `folder_purple_open_icon`     |
| `folder_red_icon`        | `folder_red_open_icon`        |
| `folder_yellow_icon`     | `folder_yellow_open_icon`     |

## Pluralization Logic

```
pluralOrSingularIcon(myIcon, native=True)
    native = True  → icon was inherited (not set directly on this object)
    native = False → icon was explicitly set by the user on this object
```

| Has Children | native (inherited) | Action |
|--------------|--------------------|--------|
| Yes          | Yes                | Pluralize |
| Yes          | No                 | Pluralize |
| No           | Yes                | Singularize |
| No           | No                 | No change (keep user's choice) |

**Key rule:** If the object has children, the icon is ALWAYS pluralized regardless
of whether it was user-set or inherited.

## Callers

| Location | Context |
|----------|---------|
| `object.py:782` | `CompositeObject.icon(recursive=True)` — categories, notes |
| `object.py:790` | `CompositeObject.selectedIcon(recursive=True)` — categories, notes |
| `task.py:1244` | `Task.icon(recursive=True)` — task display icon |
| `task.py:1260` | `Task.selectedIcon(recursive=True)` — task selected icon |
| `task.py:1288` | `Task.iconForStatus()` — status LED icons (always native=True) |

## See Also

- [ICON_LIBRARY.md](ICON_LIBRARY.md) - Icon sources, structure, and adding new icons

## Known Issue: Category Icon Pluralization

When a user sets `person_icon` on a parent category:
- The parent (which has children) shows `persons_icon` (people) — **unexpected**
- Child categories with children also show `persons_icon`
- Child categories without children show `person_icon`

This happens because categories use the same `CompositeObject.icon()` path as
tasks, which applies `pluralOrSingularIcon()`. For tasks this makes sense
(LED → folder), but for categories it produces confusing results since the user
explicitly chose a specific icon.
