# Settings

## Table of Contents

1. [TODO](#todo)
2. [One Settings Object (To Do 70)](#one-settings-object-to-do-70)
3. [Known Anomalies](#known-anomalies)
4. [ConfigParser Architecture](#configparser-architecture)
5. [Usage](#usage)
6. [In-Place Editing Options](#in-place-editing-options)
7. [Key Files](#key-files)

---

## TODO

1. **Modernize the settings system**: one typed settings object that
   any module reads and writes by attribute, `ConfigParser` replaced by
   a purpose-built class. To Do 70, [One Settings
   Object](#one-settings-object-to-do-70): steps 5 and 6 are left.
2. ~~Create `settings2.py`, a read-only copy~~: done; gone 2026-10-03
   (To Do 70 step 4).
3. ~~Migrate the tooltip config lookup~~: done.
4. ~~Migrate the hover config lookup~~: done.
5. ~~Migrate the other call sites~~: done 2026-10-03 (To Do 70 step 3).
6. ~~Wire `EVT_SYS_COLOUR_CHANGED`~~: done, [System theme
   changes](#system-theme-changes).
7. ~~Refine the refresh triggers~~: with no copy there is nothing to
   refresh (To Do 70 step 4).
8. ~~`"settings2.changed"` listeners~~: gone with the copy; its one
   listener takes the option's event (`"feature.decimal_time"`).

---

## One Settings Object (To Do 70)

**Asked by designer 2026-10-02** (To Do 70 in
[MASTER_SCHEDULER_REFACTOR.md](MASTER_SCHEDULER_REFACTOR.md#to-do)):
"There's supposed to be one global settings object ... I was creating
a virtual layer over it. And it should be much simplified ... we
should make a new task to completely refactor this." Started
2026-10-03 in this branch, **asked by designer**.

### Now (2026-10-03)

- One `Settings` object, made by the application, reached four ways:
  passed down through constructors, the class attributes
  `Task.settings` and `Attachment.settings`, `wx.GetApp().settings`
  (3 places), and `settings2`'s copy (about 40 reads).
- 303 calls on it in 65 files: 194 reads, 83 writes, the rest file
  paths and sections. The caller picks the type (`getboolean`,
  `getint`, `getlist`, ...); nothing declares an option's type.
- Passing it down: 92 functions take a `settings` parameter (61 of
  them constructors), 263 calls pass it on, 39 attributes keep it.
  Most in `menu.py`, `viewer/task.py`, `uicommand.py`, `editor.py`.
- `settings2` is refreshed a second after a change (`window.theme` at
  once): a read in that second gets the old value.
- 18 listeners of setting changes, on the option's event
  (`"view.statusbar"`) or the section's (`"settings.<section>"`); one
  on `"settings2.changed"` (viewers, for `feature.decimal_time`).
- Tests: 79 files make 143 objects of their own and set `Task.settings`
  93 times, while the harness makes the one `settings2` reads; code
  under test can read either.
- 46 declared sections with 498 options: 224 true/false, 44 whole
  numbers, 112 Python literals, 118 texts. Viewer instances
  (`taskviewer1`) and editor windows (`taskdialog_with_<tabs>`) add
  sections while running; files from old releases keep sections no
  code reads (`syncml`, `iphone`).
- Old files' values are fixed at every read (`_fixValuesFromOldIniFiles`
  in `get()`), and a bad value shows an error when first read.

### Target

TODO 1: one typed settings object that any module reads and writes by
attribute; the INI file stays as it is.

```python
from taskcoachlib.config import settings

settings.view.statusbar                  # True
settings.view.statusbar = False          # stored, "view.statusbar" sent
settings.section("taskviewer1").sortby   # a section named while running
settings.get(section, option)            # names computed by the caller
```

- Each option's type comes from its default: true/false, whole number,
  Python literal, text. A viewer instance takes its template's types,
  an editor window section one template's.
- No copy and no refresh: every read is of the one object.
  `window.theme_is_dark` is recomputed when the theme setting or the
  system theme changes.
- The same change events as now.
- The INI file keeps its sections and text values; old values are
  converted once, on load.
- Tests: the harness resets the one object before each test.

### Decisions

1. In this branch, **asked by designer 2026-10-03**.
2. The target is TODO 1's: a typed class in place of `ConfigParser`,
   read and written by attribute, the INI format kept.
3. Module by module, each step tested and pushed; it ends with
   `ConfigParser` and `settings2` gone.
4. With no copy there is nothing to refresh; the option and section
   events stay, `"settings2.changed"` goes (its one listener takes
   `"feature.decimal_time"`).
5. Viewer instance 0 keeps using the template section: a new viewer
   copies the previous one's, which users have (released behaviour);
   the defaults stay in `defaults.py`.

### Steps

1. Typed attribute access and module-level access on the existing
   object, with tests.
2. Tests use the one object, reset before each test; `Task.settings`,
   `Attachment.settings` and `wx.GetApp().settings` point to it.
3. Module by module, from the widgets and the domain up to the menus,
   main window and application: the parameters and attributes go,
   reads and writes become attribute access, and the module's tests
   follow.
4. `settings2`'s readers move to `settings`; `settings2` goes.
5. The store: no `ConfigParser` subclass; `configparser` only reads and
   writes the file; old values converted on load.
6. Options nothing reads leave `defaults.py` (static scan and a full
   suite run logging every read).

Each step: tests that fail before and pass after where behaviour is
fixed, the full suite, and an app check of what it touches.

Status: steps 1 to 4 done 2026-10-03. No module takes or keeps the
object but the application, which makes, loads, locks and saves it;
every other module reads and writes options by attribute
(`settings.get()` and `settings.set()` for computed names) and takes
the folders from `settings.templates_dir()` and
`settings.backups_dir()`. Gone with it: `Task.settings`,
`Attachment.settings` and `wx.GetApp().settings`; the settings base of
31 UI commands, which only handed the object on; parameters nothing
read (the object in the export writers and the view container, the
task file in Preferences); the text layer of the Preferences pages (a
choice list's text is converted to the option's type on save); and
`settings2`, the read-only copy refreshed a second after a change.
Steps 5 and 6 are left.

### Risks

- It touches 65 files and 79 test files. Checks: the full suite after
  each step, an app check of each area touched.
- An option read as two types: none among the 64 named directly; the
  ones reached through computed names are checked by the logged run.
- Reads in drawing loops (hover line width, theme) stay plain
  attribute reads: typed values are cached.
- An older release reads the same INI file: its format is unchanged.

---

## Known Anomalies

### System theme changes

With **Mode** Automatic, Task Coach follows a system light/dark switch
while running on Linux and macOS. `MainWindow` handles
`EVT_SYS_COLOUR_CHANGED` and also compares `detect_dark_theme()` with
its last value every second, a safety net for a switch wx does not
report. On Windows `detect_dark_theme()` follows the Mode applied to
the native controls at startup, so Task Coach's colours keep matching
them and a switch applies after a restart. Only the Theme page's
"Detected" label reads the system setting there
(`detect_system_dark_theme()`, wxPython 4.3).
Whichever sees a switch first handles it, once: the
`"system.theme_colour_changed"` Publisher event updates an open Theme
preferences page; with Mode Automatic, `settings.send_changed("window",
"theme")` then re-themes tasks and task viewers as a Mode change in
Preferences does. `window.theme_is_dark` is computed at each read.

The AGW `AuiManager` consumes `EVT_SYS_COLOUR_CHANGED` (see
[AUI.md](AUI.md#system-colour-change-event)). The main window's manager
lets it through; editor pages sit in an AGW `AuiNotebook` and never get
it, so `MultiLineTextCtrl` checks the system colours at paint time.

Limits:

- GNOME 42+ "Dark Style" only sets the `color-scheme` portal setting,
  which GTK 3 ignores and wxWidgets reads only from 3.2.3: with 3.2.2
  the app stays light, so there is nothing to follow. Switches that
  also change the GTK theme (e.g. Ubuntu's Yaru-dark) are followed.
- On Windows, native controls and Task Coach's colours keep the Mode
  applied at startup until a restart
  ([WINDOWS.md](WINDOWS.md#dark-mode)).

---

## ConfigParser Architecture

### Section types

All settings live in a single `ConfigParser` instance (`settings.current()`)
with no formal separation between section types. Three kinds of sections
coexist in the same flat namespace:

| Type | Examples | Created by | Used by |
|------|----------|------------|---------|
| **App settings** | `window`, `view`, `file`, `icon`, `iconpicker`, `version`, `feature`, `behavior`, `fgcolor`, `bgcolor`, `font`, `printer`, `export` | `initializeWithDefaults()` from `defaults.defaults` | Preferences dialog, mainwindow, application code |
| **Viewer templates** | `taskviewer`, `categoryviewer`, `effortviewer`, `noteviewer` | `initializeWithDefaults()` from `defaults.defaults` | Never read directly — serve as copy source for viewer instances |
| **Viewer instances** | `taskviewer1`, `effortviewer2`, `categoryviewer1` | Loaded from INI file (previous session), or created at runtime by `Viewer.settingsSection()` via `settings.add_section(section, copy_from=...)` | Individual viewer windows |

There is **no property or flag** distinguishing these types. The only
signal is naming convention: viewer instances have a trailing digit,
viewer templates match a `defaults.defaults` key that ends in `viewer`
or `viewerin*editor`, and app settings are everything else.

### Viewer instance 0 problem

The first viewer of each type uses `instanceNumber=0`, which means
`settingsSection()` returns the bare template name (e.g., `"taskviewer"`).
This means the template section doubles as the live section for instance 0.
The viewer writes its column widths, sort order, x/y position, etc.
directly into the template, overwriting the original defaults. When a
second viewer is created and copies from the "template", it actually
copies instance 0's live state, not the original defaults.

The only true defaults are in `defaults.defaults` (the Python dict in
`defaults.py`), not in ConfigParser.

### Persistence

On Linux the INI file is in `$XDG_CONFIG_HOME/Task Coach`
(`~/.config/Task Coach` when unset or empty), readable by the user
only; templates and backups are in `$XDG_DATA_HOME/Task Coach`
(`~/.local/share/Task Coach`). `_xdg_dir()` in `settings.py` finds
them, in place of the pyxdg package (To Do 74 in
[MASTER_SCHEDULER_REFACTOR.md](MASTER_SCHEDULER_REFACTOR.md#to-do)).

The INI file is written to disk **once at shutdown** by `Settings.save()`,
called from `application.py`. All `Settings.set()` / `setboolean()` /
`setvalue()` calls during the session update the in-memory ConfigParser
only.

The Preferences dialog also writes to ConfigParser in memory via the
same `Settings.set*()` methods. When the user clicks Save/OK in
Preferences, the values are in memory and persist to the INI file at
shutdown (or on the next `Settings.save()` call).

At startup, `Settings.__init__()` runs:

1. `initializeWithDefaults()` — creates all sections from
   `defaults.defaults` with default values
2. `ConfigParser.read(inifile)` — merges saved INI on top (existing
   sections get updated values, new sections like `taskviewer1` get
   added)
3. `_migrateOldSettingNames()` renames options, and
   `_remove_obsolete_settings()` drops the ones no release reads
   (`_OBSOLETE_SETTINGS`), so an old INI file carries neither forward.
   An option retired from `defaults.py` goes on that list; a retired
   view goes on `_OBSOLETE_VIEWERS`, which drops its template section
   and numbered instances (the Dependency Graph's, P82).

After step 2, ConfigParser contains both the original template sections
(possibly overwritten by INI values from instance 0) and all viewer
instance sections saved from the previous session.

Each save also writes `[version] python`, `wxpython`, `pythonfrozen`
and `current`: the Python, wxPython and Task Coach that wrote the file,
and whether Task Coach ran frozen (an installer build). Nothing reads
them; they tell whoever reads a settings file a user sent which build
wrote it. Kept, **ruled by designer 2026-10-02** (P67 in
[MASTER_SCHEDULER_REFACTOR.md](MASTER_SCHEDULER_REFACTOR.md#pre-existing-issues)).
`[version] notify` and `notified` are the update check's
([PACKAGING.md](PACKAGING.md)).

---

## Usage

Any module reads and writes the one object (To Do 70, [One Settings
Object](#one-settings-object-to-do-70)):

```python
from taskcoachlib.config import settings

settings.view.descriptionpopups          # bool
settings.window.hoverlinewidth           # int
settings.window.theme_is_dark            # computed at each read
settings.view.statusbar = False          # stored, "view.statusbar" sent
settings.section(self.settingsSection()).sortby
settings.get("icon", "%stasks" % status) # a name computed by the caller
settings.set("view", option, value)      # written by a computed name
settings.from_text("view", "defaultsnoozetime", "15")  # 15, a choice's text
settings.send_changed("window", "theme") # listeners told, value unchanged
settings.templates_dir()                 # folders, made if missing
settings.backups_dir()
```

No constructor parameter, no getter lambda, no copy. A value of another
type than the option's default is refused (`TypeError`); an option or
section no defaults name raises `AttributeError`. Before the
application has its settings (a module reading while it loads), reads
give the defaults.

Sections made while running, a viewer instance's (`taskviewer1`) and
an editor window's (`taskdialog_with_<tabs>`), are made without telling
any listener:

```python
settings.has_section("taskviewer1")
settings.add_section("taskviewer1", copy_from="taskviewer")  # its values
settings.add_section("notedialog_with_subject")  # the template's defaults
```

A view and an editor window reach their own section as `self.options`
(`self.options.sortby`).

Only the application makes the `Settings` object
(`config.settings.use()`); `OneSettingsObjectTest` fails on any other,
and on any module but the application calling `settings.current()`. The
date, time and amount controls once each made their own, which read
the default settings file from disk: a file given with `--ini` was
ignored, a Preferences change reached them only after a restart, and
each copy stayed in memory (P151, P152 in
[MASTER_SCHEDULER_REFACTOR.md](MASTER_SCHEDULER_REFACTOR.md#pre-existing-issues)).

Tests use the same object, the harness's: it is reset to the defaults
after each test (`Settings.reset()`), so a test sets what it needs. A
test that needs other file locations installs its own object with
`config.settings.use()`; the harness puts its own back.

---

## In-Place Editing Options

**Asked by designer 2026-10-02**, To Do 68 and 69 in
[MASTER_SCHEDULER_REFACTOR.md](MASTER_SCHEDULER_REFACTOR.md#to-do);
what they change: [LIST_MANAGEMENT.md](LIST_MANAGEMENT.md#in-place-editing).
On the Features page, by Hoverover popups:

| Option | Setting | Default | On |
|--------|---------|---------|----|
| Edit cells in place | `feature.in_place_editing` | Off | F2 on the cell just clicked, Edit in place on the right-click menu |
| Edit in place with a slow double click | `feature.in_place_slow_double_click` | Off | Also a slow double click, while the first is on |

## Key Files

| File | Purpose |
|------|---------|
| `taskcoachlib/config/settings.py` | `Settings` class (ConfigParser subclass) and the module every other module reads it through |
| `taskcoachlib/config/defaults.py` | Default values and type schema |
| `taskcoachlib/config/__init__.py` | Package exports |
