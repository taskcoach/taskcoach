# Settings

## Table of Contents

1. [TODO](#todo)
2. [One Settings Object (To Do 70)](#one-settings-object-to-do-70)
3. [Known Anomalies](#known-anomalies)
4. [ConfigParser Architecture](#configparser-architecture)
5. [Current State](#current-state)
6. [Problem](#problem)
7. [Read-Only Shim](#read-only-shim)
8. [Initialization](#initialization)
9. [Usage](#usage)
10. [Writes Stay on the Existing API](#writes-stay-on-the-existing-api)
11. [In-Place Editing Options](#in-place-editing-options)
12. [Key Files](#key-files)

---

## TODO

1. **Modernize the settings system.** The current `ConfigParser`-based
   design is 2004-era: no type schema, string-only storage, instance
   threaded through constructors. A modern settings system would have
   typed field declarations, module-level singleton access, and
   attribute-style reads/writes. The read-only shim below is a temporary
   bridge — it provides module-level access without refactoring the
   underlying `ConfigParser`. The long-term goal is to replace
   `ConfigParser` entirely with a purpose-built settings class.
2. ~~**Create `settings2.py` and wire init in `application.py`.**~~ Done.
3. ~~**Migrate tooltip config lookup** — replace pubsub subscription with
   direct `settings2.view.descriptionpopups` read. First consumer of
   the shim.~~ Done.
4. ~~**Migrate hover config lookup**: replace getter lambda with direct
   `settings2.window.hoverlinewidth` read. Remove `_hoverSettingGetter`
   indirection.~~ Done.
5. **Gradually migrate other read-only call sites** as code is touched.
   No big-bang refactor — incremental adoption.
6. ~~**Wire `EVT_SYS_COLOUR_CHANGED`** to recompute `theme_is_dark`.~~ Done.
   `MainWindow` sends the `"system.theme_colour_changed"` Publisher event
   on a light/dark switch; settings2 subscribes and recomputes. See
   [System theme changes](#system-theme-changes).
7. **Refine refresh triggers.** Eventually, replace the 1-second debounce
   with a proper batched signal when `ConfigParser` is replaced.
8. **Wire `"settings2.changed"` listeners.** Consumers that need to
   react to setting changes (e.g. themed colours after a dark/light
   switch) should register via
   `patterns.Publisher().registerObserver(callback, eventType="settings2.changed")`.
   First listener (2026-09-28): viewers redraw when
   `feature.decimal_time` changes.

Items 1, 5, 7 and 8 are To Do 70's: [One Settings
Object](#one-settings-object-to-do-70).

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

Status: steps 1 and 2 done 2026-10-03; step 3 done for the widgets,
the domain (`Task.settings` and `Attachment.settings` are gone), the
printer, the export writers (whose `settings` parameter nothing read),
the automatic save, backup, import and export, the tips and balloon
tips, the version check, the reminders, the idle time notice, the
window size tracker, the templates dialog, the date and time entry
helpers and the list columns (which handed the object to the in-place
editors), and the UI commands (31 of which had a settings base only to
be handed the object). The menus, views, editors, toolbars, export
dialog, Preferences, tray icon and main window are left; where one of
them still takes the object, the code moved so far passes
`settings.current()`.

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
`"system.theme_colour_changed"` Publisher event makes settings2
recompute `window.theme_is_dark` and updates an open Theme preferences
page; with Mode Automatic, the `"settings.window.theme"` message then
re-themes tasks and task viewers as a Mode change in Preferences does.

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

### Frequent implicit refreshes

Any `Settings.set()` call triggers `settings2.schedule_refresh()`, which
starts a 1-second debounce timer. When the timer fires, settings2
re-snapshots all monitored sections from ConfigParser and recomputes
derived values (including `window.theme_is_dark`).

In practice, `Settings.set()` is called frequently:

- **Window/dialog close** — every editor and dialog saves its position
  and size to ConfigParser on close. This is the most common trigger.
- **Viewer state changes** — column widths, sort order, scroll position.
- **Preferences OK** — writes all changed options in a burst (collapsed
  into one debounce refresh).
- **Any explicit setting change** — toggle, checkbox, toolbar state.

Because dialogs and viewers save geometry on close, settings2 is
re-snapshotted relatively often during normal use. Computed values like
`theme_is_dark` are recomputed on each refresh.

---

## ConfigParser Architecture

### Section types

All settings live in a single `ConfigParser` instance (`wx.GetApp().settings`)
with no formal separation between section types. Three kinds of sections
coexist in the same flat namespace:

| Type | Examples | Created by | Used by |
|------|----------|------------|---------|
| **App settings** | `window`, `view`, `file`, `icon`, `iconpicker`, `version`, `feature`, `behavior`, `fgcolor`, `bgcolor`, `font`, `printer`, `export` | `initializeWithDefaults()` from `defaults.defaults` | Preferences dialog, mainwindow, application code |
| **Viewer templates** | `taskviewer`, `categoryviewer`, `effortviewer`, `noteviewer` | `initializeWithDefaults()` from `defaults.defaults` | Never read directly — serve as copy source for viewer instances |
| **Viewer instances** | `taskviewer1`, `effortviewer2`, `categoryviewer1` | Loaded from INI file (previous session), or created at runtime by `Viewer.settingsSection()` via `Settings.add_section(section, copyFromSection=...)` | Individual viewer windows |

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

## Current State

Settings are stored in a `ConfigParser`-based `Settings` class
(`taskcoachlib/config/settings.py`). The instance is created in
`application.py` at startup and threaded through constructors to every
viewer, editor, toolbar, and dialog.

Reading a value requires the instance reference plus the section name,
option name, and correct type method:

```python
self.settings.getboolean("view", "descriptionpopups")
self.settings.getint("window", "hoverlinewidth")
self.settings.get("taskviewer", "sortby")
```

Defaults are declared in `taskcoachlib/config/defaults.py` as a dict of
`{section: {option: string_value}}`. The string values encode the type
implicitly: `"True"` / `"False"` for booleans, `"8"` for ints, etc.

---

## Problem

Any code that needs a config value must have a reference to the `Settings`
instance. This creates unnecessary coupling:

- **Constructor threading** — the instance is passed through 5+ layers of
  constructors to reach the widget that reads it.
- **Getter lambdas** — when a widget layer shouldn't depend on the config
  layer, a lambda was injected to bridge the gap (e.g. the former
  `_hoverSettingGetter` in `treectrl.py`, now removed).
- **Change subscriptions**: some code subscribes to setting-change events
  topics instead of just reading the value when needed, adding complexity
  for a simple config lookup.

Settings are global application state. Any module should be able to read
them directly.

---

## Read-Only Shim

`settings2` (`taskcoachlib/config/settings2.py`) is a singleton class
(`_Settings2`) with PEP 562 module-level `__getattr__`. ConfigParser
values are snapshotted into `SimpleNamespace` attributes at init, and
re-snapshotted on debounced setting changes. Access is a plain attribute
read — no ConfigParser lookup, no computation at read time.

```python
from taskcoachlib.config import settings2

settings2.view.descriptionpopups     # True (bool)
settings2.window.hoverlinewidth      # 1 (int)
settings2.window.theme               # "automatic" (str)
settings2.window.theme_is_dark       # False (computed)
```

### How it works

1. `init()` calls `_refresh(build=True)` — creates a `SimpleNamespace`
   per section in `_SETTING_SECTIONS`, populates options as attributes,
   sets `_initialized = True`.
2. `Settings.set()` calls `settings2.schedule_refresh()` on every value
   change, which restarts a 1-second debounce
   (`patterns.later.debounced`, [DEFERRED_CALLS.md](DEFERRED_CALLS.md)).
   No-op before `init()`.
3. When it runs, `_refresh(build=False)` re-walks ConfigParser
   and overwrites all attributes on existing namespaces.
4. After refresh, `_compute_settings_all()` recomputes derived values.
5. After refresh + compute, fires
   `patterns.Event("settings2.changed", _instance).send()`.
6. Module-level `__getattr__` delegates to the singleton instance.

```
settings2.window.theme_is_dark
    │
    └── _instance.window.theme_is_dark
        (plain attribute on SimpleNamespace)
```

The structure (sections and option names) never changes after init —
only values are updated.

### Monitored sections

Only sections listed in `_SETTING_SECTIONS` are snapshotted. Add entries
as code is migrated to use the shim.

```python
_SETTING_SECTIONS = {
    "icon",
    "iconpicker",
    "view",
    "window",
}
```

### Type map

Settings in `_TYPES_MAP` get type-converted during refresh. All others
are stored as raw strings.

```python
_TYPES_MAP = {
    ("view", "descriptionpopups"): bool,
    ("window", "hoverlinewidth"): int,
    ("iconpicker", "theme_nuvola"): bool,
    ...
}
```

| In type map | INI value valid | Returns |
|---|---|---|
| `bool` | `"True"` | `True` |
| `bool` | `"banana"` | default from `defaults.py` |
| `int` | `"3"` | `3` |
| `int` | `"banana"` | default from `defaults.py` |
| not in map | anything | raw string, as-is |

### Computed values

Computed from snapshotted values during `_compute_settings_all()`. They
live as regular attributes on the same `SimpleNamespace` objects.

| Attribute | Derivation |
|---|---|
| `window.theme_is_dark` | Resolves `window.theme` ("automatic"/"light"/"dark") to a bool. When "automatic", calls `detect_dark_theme()`. |

### Refresh triggers

- `init(settings)` — startup (build, before wxApp)
- `wx_ready()` — after wxApp created (re-refresh with display-dependent
  computed settings)
- `Settings.set()` — debounced 1-second timer; burst writes (e.g.
  Preferences OK) collapse into a single refresh. Setting
  `window.theme` also refreshes at once (`refresh_now()`), before the
  change is sent, since its listeners read `window.theme_is_dark`
- System light/dark switch: `MainWindow` sends
  `patterns.Event("system.theme_colour_changed", self)` (see
  [System theme changes](#system-theme-changes)). Settings2 subscribes
  in `wx_ready()` and recomputes `_compute_settings_all()` (no full
  ConfigParser re-read needed).

### Completion signal

After each refresh or recomputation, settings2 fires a Publisher signal:

```python
patterns.Event("settings2.changed", _instance).send()
```

This fires after:
- debounced `Settings.set()` refresh
- system light/dark switch recomputation

Listeners register with:

```python
from taskcoachlib.config import settings2
patterns.Publisher().registerObserver(
    callback,
    eventType="settings2.changed",
)
```

---

## Initialization

Two-phase init in `application.py`:

```python
# Phase 1 — after Settings created, before wxApp
settings2.init(self.settings)

# Phase 2 — after wxApp created (display connection available)
settings2.wx_ready()
```

**Phase 1** (`init(settings)`) stores the `Settings` reference, builds
the snapshot (`_refresh(build=True)`), and enables debounced refresh.
Computed settings that require a display (e.g. `theme_is_dark` in
"automatic" mode) are skipped because wxApp does not exist yet.

**Phase 2** (`wx_ready()`) re-runs `_refresh(build=False)` now that
wxApp and the display connection exist. This computes all display-dependent
settings.

Before `init()`, `schedule_refresh()` is a no-op (setting writes during
startup do not trigger refresh).

After init, any module can import and use the shim. The shim uses a
stored `Settings` reference (no `wx.GetApp()` dependency).

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
```

No constructor parameter, no getter lambda, no copy. A value of another
type than the option's default is refused (`TypeError`); an option or
section no defaults name raises `AttributeError`. Before the
application has its settings (a module reading while it loads), reads
give the defaults.

Only the application makes the `Settings` object
(`config.settings.use()`); `Settings2Test` fails on any other. The
date, time and amount controls once each made their own, which read
the default settings file from disk: a file given with `--ini` was
ignored, a Preferences change reached them only after a restart, and
each copy stayed in memory (P151, P152 in
[MASTER_SCHEDULER_REFACTOR.md](MASTER_SCHEDULER_REFACTOR.md#pre-existing-issues)).

Tests use the same object, the harness's: it is reset to the defaults
after each test (`Settings.reset()`), so a test sets what it needs. A
test that needs other file locations installs its own object with
`config.settings.use()`; the harness puts its own back.

Not yet moved (To Do 70, step 3): code that is passed the object or
reads `settings2` still works on the same object.

---

## Writes Stay on the Existing API

The shim is read-only. All writes go through the existing `Settings`
methods:

```python
self.settings.setboolean(section, option, value)
self.settings.settext(section, option, value)
```

These methods handle change detection, change events
([PUBLISHER_OBSERVER.md](PUBLISHER_OBSERVER.md#settings-events)), and
persistence. `Settings.set()` also calls `settings2.schedule_refresh()`
to trigger a debounced shim refresh (see [Refresh triggers](#refresh-triggers)).

---


## In-Place Editing Options

**Asked by designer 2026-10-02**, To Do 68 and 69 in
[MASTER_SCHEDULER_REFACTOR.md](MASTER_SCHEDULER_REFACTOR.md#to-do);
what they change: [LIST_MANAGEMENT.md](LIST_MANAGEMENT.md#in-place-editing).
On the Features page, by Hoverover popups, read through `settings2`:

| Option | Setting | Default | On |
|--------|---------|---------|----|
| Edit cells in place | `feature.in_place_editing` | Off | F2 on the cell just clicked, Edit in place on the right-click menu |
| Edit in place with a slow double click | `feature.in_place_slow_double_click` | Off | Also a slow double click, while the first is on |

## Key Files

| File | Purpose |
|------|---------|
| `taskcoachlib/config/settings2.py` | Read-only shim (module-level proxy) |
| `taskcoachlib/config/settings.py` | `Settings` class (ConfigParser subclass) |
| `taskcoachlib/config/defaults.py` | Default values and type schema |
| `taskcoachlib/config/__init__.py` | Package exports |
