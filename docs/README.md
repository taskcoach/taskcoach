# Developer Documentation

For working on Task Coach: running it from source, testing, building
the packages, and what each document here covers. To install Task
Coach, see the [README](../README.md).

## Running from Source

On Linux:

```bash
git clone --depth 1 https://github.com/taskcoach/taskcoach.git
cd taskcoach
./setup.sh
./taskcoach-run.sh
```

`setup.sh` detects the distribution and runs its setup script
(`setup_debian13_trixie.sh` and the like): the system packages, and a
virtual environment in `.venv` for the rest. `taskcoach-run.sh`
starts Task Coach in that environment. Options and troubleshooting:
[DEBIAN_BOOKWORM_SETUP.md](DEBIAN_BOOKWORM_SETUP.md).

`./test_taskcoach.sh` checks an installation from source: the Python
version, the dependencies, the module imports, and that Task Coach's
own tree widget is loaded.

The tray icon on Linux needs libayatana-appindicator, which the setup
scripts install; by hand:

```bash
sudo apt install python3-gi gir1.2-ayatanaappindicator3-0.1   # Debian, Ubuntu
sudo dnf install python3-gobject libayatana-appindicator-gtk3 # Fedora
sudo pacman -S python-gobject libayatana-appindicator         # Arch Linux
```

## Working on the Code

- [DEVELOPMENT.md](DEVELOPMENT.md): the standards: style and naming,
  verifying a change in the full app with its debug log, documentation,
  commits. Also [CONTRIBUTING.md](../CONTRIBUTING.md).
- [TESTING.md](TESTING.md): the test suite (`tests/test.py`), the
  certified platform, running it.
- [LOGGING_GUIDE.md](LOGGING_GUIDE.md): the app's debug log and what to
  read in it.
- [CHANGELOG.md](../CHANGELOG.md): what changes for users in each
  release.

## Architecture

Task Coach is a desktop application in Python with wxPython for its
GUI. It follows the Model-View-Controller pattern with three main
layers:

- **Domain layer**: tasks, categories, efforts, notes and the other
  domain objects
- **GUI layer**: viewers, controllers, dialogs, menus and the other GUI
  components
- **Persistence layer**: loading and saving the domain objects to XML
  files (`.tsk`), and the exports

Key packages in `taskcoachlib/`:

| Package | Description |
|---------|-------------|
| `domain` | Domain objects (tasks, categories, effort, notes) |
| `gui` | Viewers, dialogs, and UI components |
| `command` | Undo/redo-capable user actions (Command pattern) |
| `config` | User settings and TaskCoach.ini handling |
| `persistence` | .tsk file format (XML) and export functionality |
| `i18n` | Internationalization and translations |
| `widgets` | Adapted wxPython widgets |

## Documents

### Standards and Tools

| Document | What it covers |
|----------|----------------|
| [DEVELOPMENT.md](DEVELOPMENT.md) | Standards for writing, verifying, documenting and committing |
| [TESTING.md](TESTING.md) | The test suite and its certified platform |
| [LOGGING_GUIDE.md](LOGGING_GUIDE.md) | How Task Coach logs, and what to read when verifying |
| [PEP8_MIGRATION.md](PEP8_MIGRATION.md) | The PEP 8 migration: what to rename and what stays |
| [SECURITY.md](SECURITY.md) | The dynamic dispatch policy |
| [GITHUB_INFO.md](GITHUB_INFO.md) | The GitHub repository's description and topics |

### Features

| Document | What it covers |
|----------|----------------|
| [TASK_FIELDS.md](TASK_FIELDS.md) | Each task field: meaning, display, sorting, editing |
| [TASK_STATUS.md](TASK_STATUS.md) | Task statuses, their transitions and display |
| [TASK_STATUS_SORT.md](TASK_STATUS_SORT.md) | Sorting by status first |
| [TASK_STATISTICS.md](TASK_STATISTICS.md) | The task statistics view |
| [CATEGORIES.md](CATEGORIES.md) | An item's categories and what subtasks inherit |
| [EFFORTS.md](EFFORTS.md) | Efforts: time tracking and its views |
| [ATTACHMENTS.md](ATTACHMENTS.md) | Attachments: adding, showing, opening, saving |
| [EMAIL_ATTACHMENTS.md](EMAIL_ATTACHMENTS.md) | Mails dragged from a mail program |
| [REMINDERS.md](REMINDERS.md) | Reminders and their popup |
| [IDLE.md](IDLE.md) | Idle time detection and what it does |
| [DATETIME_PRESETS.md](DATETIME_PRESETS.md) | Default dates and times for new tasks |
| [DURATION_CALCULATIONS.md](DURATION_CALCULATIONS.md) | Durations in the task dates and effort editors |
| [APPEARANCE_STYLES.md](APPEARANCE_STYLES.md) | Colours, fonts and icons of items |
| [UNDO_REDO.md](UNDO_REDO.md) | Undo and redo |
| [SETTINGS.md](SETTINGS.md) | The settings and TaskCoach.ini |
| [PREFERENCES.md](PREFERENCES.md) | The Preferences dialog: its pages, OK, Apply and Cancel |
| [SESSION_END.md](SESSION_END.md) | What is saved, and when, at quit, logout and shutdown |
| [FILE_LOCKING.md](FILE_LOCKING.md) | Locking task files and the settings file |
| [FILE_DIALOGS.md](FILE_DIALOGS.md) | Where each file dialog opens |
| [EXPORTS.md](EXPORTS.md) | What the exports write, and in which order |
| [LOCALE.md](LOCALE.md) | Locale and regional settings |
| [TRANSLATIONS.md](TRANSLATIONS.md) | How translations work, and contributing them |
| [SPELLCHECKING.md](SPELLCHECKING.md) | Spell checking |
| [MARKDOWN.md](MARKDOWN.md) | A Markdown preview of descriptions, requested and parked: the open question |
| [SYNC.md](SYNC.md) | Synchronization, a possible future feature |
| [TODO_TXT.md](TODO_TXT.md) | Todo.txt, removed: why, and how to bring it back |
| [SPOKEN_REMINDERS.md](SPOKEN_REMINDERS.md) | Spoken reminders, removed: why, a better way, and how to bring them back |

### User Interface

| Document | What it covers |
|----------|----------------|
| [WINDOW_GEOMETRY.md](WINDOW_GEOMETRY.md) | Window size, position and placement on the monitors |
| [AUI.md](AUI.md) | The docked and floating views (AGW AUI) |
| [LIST_MANAGEMENT.md](LIST_MANAGEMENT.md) | The views' lists: selection, rebuilds, button states |
| [MENUS.md](MENUS.md) | Enabling and disabling menu items |
| [TOOLBAR.md](TOOLBAR.md) | The toolbars: drawing, sizing, saving |
| [SYSTEM_TRAY.md](SYSTEM_TRAY.md) | The tray icon on each platform |
| [WAYLAND_ISSUES.md](WAYLAND_ISSUES.md) | Known wxPython and wxWidgets issues on Wayland |
| [BUNDLED_TREE_WIDGET.md](BUNDLED_TREE_WIDGET.md) | Task Coach's copy of wxPython's tree widget |
| [ICON_LIBRARY.md](ICON_LIBRARY.md) | The icon catalog: sizes, tiers, adding icons |
| [ICON_DISPLAY.md](ICON_DISPLAY.md) | Icons in the views' columns |
| [ICON_PICKER_REFACTORING.md](ICON_PICKER_REFACTORING.md) | The icon picker |
| [COLOUR_PICKER.md](COLOUR_PICKER.md) | The colour picker |
| [FONT_PICKER.md](FONT_PICKER.md) | The font picker |
| [DATETIME_CONTROLS.md](DATETIME_CONTROLS.md) | Time and duration input controls |
| [NUMERIC_CONTROLS.md](NUMERIC_CONTROLS.md) | Numeric input controls |
| [MONETARY_CONTROLS.md](MONETARY_CONTROLS.md) | Currency input controls |

### Internals

| Document | What it covers |
|----------|----------------|
| [ATTRIBUTE_PATTERN.md](ATTRIBUTE_PATTERN.md) | Change detection and notification in the domain model |
| [PUBLISHER_OBSERVER.md](PUBLISHER_OBSERVER.md) | Event dispatch between objects |
| [SCHEDULERS.md](SCHEDULERS.md) | Timed events |
| [DEFERRED_CALLS.md](DEFERRED_CALLS.md) | Calls made later: debounces, delays, repeats |
| [PERSISTENCE_XML.md](PERSISTENCE_XML.md) | Writing and reading `.tsk` files |
| [CRASH_GUARD.md](CRASH_GUARD.md) | Guarding against deleted wx objects |

### Packaging and Platforms

| Document | What it covers |
|----------|----------------|
| [PACKAGING.md](PACKAGING.md) | Building every package, and making a release |
| [DEBIAN_BOOKWORM_SETUP.md](DEBIAN_BOOKWORM_SETUP.md) | Running from source: setup and troubleshooting |
| [APPIMAGE.md](APPIMAGE.md) | The AppImage build |
| [FLATPAK.md](FLATPAK.md) | The Flatpak build |
| [WINDOWS.md](WINDOWS.md) | The Windows build |
| [MACOS.md](MACOS.md) | macOS: supported versions, platform features, signing |
| [MACOSX_KVM_TRY1.md](MACOSX_KVM_TRY1.md), [MACOSX_KVM_TRY2.md](MACOSX_KVM_TRY2.md) | A macOS virtual machine on Linux for testing |
| [DEPENDENCIES.md](DEPENDENCIES.md) | Each third-party package: why, use, size, alternatives |
| [THIRD_PARTY_CODE.md](THIRD_PARTY_CODE.md) | Third-party code bundled, copied or patched |

### Plans and History

| Document | What it covers |
|----------|----------------|
| [REFINEMENT_REFACTOR.md](REFINEMENT_REFACTOR.md) | The current refactor: its To Do list and open issues |
| [MASTER_SCHEDULER_REFACTOR.md](MASTER_SCHEDULER_REFACTOR.md) | The scheduler refactor of 2.0.3.0 and its issue list |
| [TODO.md](TODO.md) | Planned improvements |
| [PYTHON3_MIGRATION_INDEX.md](PYTHON3_MIGRATION_INDEX.md) | The Python 3 migration, in parts [1](PYTHON3_MIGRATION_1.md), [2](PYTHON3_MIGRATION_2.md), [3](PYTHON3_MIGRATION_3.md), [4](PYTHON3_MIGRATION_4.md) and [5](PYTHON3_MIGRATION_5.md); [PYTHON3_MIGRATION_NOTES.md](PYTHON3_MIGRATION_NOTES.md) points to them |
