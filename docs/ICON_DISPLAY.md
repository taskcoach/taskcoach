# Icon Display

How icons are rendered in viewer columns.

## Table of Contents

- [Single-Image Columns](#single-image-columns)
- [Multi-Image Columns](#multi-image-columns)
- [Category Icons Column](#category-icons-column)
- [File Reference](#file-reference)
- [See Also](#see-also)

---

## Single-Image Columns

Most columns display one icon per cell (subject, status, attachments, notes).
The Column class holds an `imageIndicesCallback` that returns a dict mapping
item states (normal/expanded) to image list indices. During refresh, the
tree control calls the adapter which calls the column callback, then sets
the image on the tree item. HyperTreeList's PaintItem reads the stored
image index and draws it.

---

## Multi-Image Columns

Some columns display multiple icons side by side in a single cell. The
Column class accepts a `multiImageIndicesCallback` that returns a list of
image indices. The tree refresh checks the adapter for multi-image columns
first; if true, stores the list on the tree item via `SetImages`. PaintItem
checks for multi-images before single images and draws each icon at
successive x positions, spaced by icon width + 1 pixel.

A column with `multiImageIndicesCallback` reports `hasImages() == True`
so the existing image refresh path includes it without needing separate
column scanning.

---

## Category Icons Column

Displays icons for all categories assigned to a task, sorted by category
style priority descending.

The column subscribes to category add/remove and appearance change events.
When refreshed, the callback sorts the task's categories by `stylePriority`,
collects each category's `effectiveIcon`, and maps the icon names to image
list indices. No domain Attribute is needed — icons are computed on demand,
same pattern as the categories column's text render.

---

## File Reference

- Column class (single + multi image): `taskcoachlib/widgets/itemctrl.py`
- Viewer adapter: `taskcoachlib/gui/viewer/base.py`
- Tree refresh: `taskcoachlib/widgets/treectrl.py` (`_refreshImage`)
- HyperTreeList storage + painting: `patches/wxpython/hypertreelist.py`
- Category icons column + callback: `taskcoachlib/gui/viewer/task.py`

---

## See Also

- [APPEARANCE_STYLES.md](APPEARANCE_STYLES.md) - Effective/derived icon SSOT
- [ICON_LIBRARY.md](ICON_LIBRARY.md) - Icon catalog and art provider
- [TASK_STATUS.md](TASK_STATUS.md) - Status icons and appearance inheritance
