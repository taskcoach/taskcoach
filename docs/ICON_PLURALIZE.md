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
| `nuvola_actions_ledblue`        | `nuvola_mimetypes_inode-directory` |
| `nuvola_actions_ledlightblue` | `taskcoach_actions_folder_blue_light_icon` |
| `taskcoach_actions_led_grey_icon`        | `nuvola_places_folder-grey`    |
| `nuvola_actions_ledgreen`       | `nuvola_places_folder-green`   |
| `nuvola_actions_ledorange`     | `nuvola_places_folder-orange`  |
| `nuvola_actions_ledpurple`      | `nuvola_places_folder-violet`  |
| `nuvola_actions_ledred`         | `nuvola_places_folder-red`     |
| `nuvola_actions_ledyellow`     | `nuvola_places_folder-yellow`  |

### Other Icons

| Singular (No Children) | Plural (Has Children)          |
|------------------------|--------------------------------|
| `nuvola_actions_ok` | `taskcoach_actions_checkmark_green_icon_multiple` |

### Reverse (Singular) Mapping

The singular mapping is auto-generated as the reverse of the plural mapping.
For example, `nuvola_mimetypes_inode-directory` → `nuvola_actions_ledblue`, `nuvola_apps_kuser` → `nuvola_apps_preferences-desktop-user`.

### Open Folder Mapping — DEPRECATED

Open folder icon variants (`folder_*_open_icon`) have been removed. The tree
expand/collapse arrow already indicates whether a node is expanded, making
separate open-folder icons redundant. The `itemImageOpen` dict and
`getImageOpen()` function have been deleted from `domain/attribute/icon/__init__.py`.

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

When a user sets `nuvola_apps_preferences-desktop-user` on a parent category:
- The parent (which has children) shows `nuvola_apps_kuser` (people) — **unexpected**
- Child categories with children also show `nuvola_apps_kuser`
- Child categories without children show `nuvola_apps_preferences-desktop-user`

This happens because categories use the same `CompositeObject.icon()` path as
tasks, which applies `pluralOrSingularIcon()`. For tasks this makes sense
(LED → folder), but for categories it produces confusing results since the user
explicitly chose a specific icon.
