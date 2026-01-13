# Python 3 Migration Documentation Index

This index provides navigation to the Python 3 migration documentation, which has been split into multiple parts for easier navigation.

## Contributing Guidelines

**Maximum page size: 700 lines.** When adding new content:
1. Add to the last page if it has room
2. If the last page exceeds 700 lines, create a new page (e.g., `PYTHON3_MIGRATION_6.md`)
3. Update this index with the new page and its sections

Current page sizes:
- Page 1: 680 lines
- Page 2: 722 lines (slightly over)
- Page 3: 591 lines
- Page 4: 717 lines
- Page 5: 380 lines

## Document Overview

| Document | Content |
|----------|---------|
| [PYTHON3_MIGRATION_1.md](PYTHON3_MIGRATION_1.md) | Widget Resizing, wx.Timer Crash, Ctrl+C Crash, wxPython Compatibility |
| [PYTHON3_MIGRATION_2.md](PYTHON3_MIGRATION_2.md) | Bundled Library Cleanup, Twisted Removal, Window Position Tracking |
| [PYTHON3_MIGRATION_3.md](PYTHON3_MIGRATION_3.md) | GTK Issues, AUI Issues, Known Issues |
| [PYTHON3_MIGRATION_4.md](PYTHON3_MIGRATION_4.md) | Logging, Python 3.12+, File Locking, App Icons, i18n, SyncML Removal |
| [PYTHON3_MIGRATION_5.md](PYTHON3_MIGRATION_5.md) | Mobile Sync, Filesystem Monitors, Growl, X11 Session Management Removals |

---

## Part 1: Core wxPython Issues

**File:** [PYTHON3_MIGRATION_1.md](PYTHON3_MIGRATION_1.md)

- [Widget Resizing Issues](PYTHON3_MIGRATION_1.md#widget-resizing-issues)
- [wx.Timer Crash During Window Destruction](PYTHON3_MIGRATION_1.md#wxtimer-crash-during-window-destruction)
- [Ctrl+C Crash with AUI Event Handler Assertion](PYTHON3_MIGRATION_1.md#ctrlc-crash-with-aui-event-handler-assertion)
- [wxPython Compatibility](PYTHON3_MIGRATION_1.md#wxpython-compatibility)

---

## Part 2: Library Cleanup and Framework Removal

**File:** [PYTHON3_MIGRATION_2.md](PYTHON3_MIGRATION_2.md)

- [Bundled Third-Party Library Cleanup](PYTHON3_MIGRATION_2.md#bundled-third-party-library-cleanup)
- [Twisted Framework Removal](PYTHON3_MIGRATION_2.md#twisted-framework-removal)
- [Window Position Tracking with AUI](PYTHON3_MIGRATION_2.md#window-position-tracking-with-aui)

---

## Part 3: GTK and AUI Issues

**File:** [PYTHON3_MIGRATION_3.md](PYTHON3_MIGRATION_3.md)

- [GTK3 Menu Size Allocation Bug](PYTHON3_MIGRATION_3.md#gtk3-menu-size-allocation-bug)
- [Search Box Visibility in AUI Toolbars](PYTHON3_MIGRATION_3.md#search-box-visibility-in-aui-toolbars)
- [AUI Divider Drag Visual Feedback](PYTHON3_MIGRATION_3.md#aui-divider-drag-visual-feedback)
- [GTK BitmapComboBox Icon Clipping](PYTHON3_MIGRATION_3.md#gtk-bitmapcombobox-icon-clipping)
- [Known Issues](PYTHON3_MIGRATION_3.md#known-issues)

---

## Part 4: Infrastructure, i18n, and Feature Removals

**File:** [PYTHON3_MIGRATION_4.md](PYTHON3_MIGRATION_4.md)

- [Logging Infrastructure](PYTHON3_MIGRATION_4.md#logging-infrastructure-redirectedoutput--simple-custom-logging)
- [Python 3.12+ Escape Sequence Warning](PYTHON3_MIGRATION_4.md#python-312-escape-sequence-warning)
- [File Locking: lockfile to fasteners Migration](PYTHON3_MIGRATION_4.md#file-locking-lockfile--fasteners-migration)
- [App Icon Grouping Across Platforms](PYTHON3_MIGRATION_4.md#app-icon-grouping-across-platforms)
- [Future Work](PYTHON3_MIGRATION_4.md#future-work)
- [Internationalization and Locale Issues](PYTHON3_MIGRATION_4.md#internationalization-and-locale-issues)
- [SyncML Removal](PYTHON3_MIGRATION_4.md#syncml-removal)

---

## Part 5: Feature Removals (Continued)

**File:** [PYTHON3_MIGRATION_5.md](PYTHON3_MIGRATION_5.md)

- [Mobile Sync Features Removal](PYTHON3_MIGRATION_5.md#mobile-sync-features-removal)
- [Native Filesystem Monitors: Deleted](PYTHON3_MIGRATION_5.md#native-filesystem-monitors-deleted)
- [Growl Notification Support Removal](PYTHON3_MIGRATION_5.md#growl-notification-support-removal)
- [X11 Session Management Removal](PYTHON3_MIGRATION_5.md#x11-session-management-removal)
- [Contributing to This Document](PYTHON3_MIGRATION_5.md#contributing-to-this-document)

---

**Last Updated:** January 2026
