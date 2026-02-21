# Settings

## Table of Contents

1. [TODO](#todo)
2. [Known Anomalies](#known-anomalies)
3. [ConfigParser Architecture](#configparser-architecture)
4. [Current State](#current-state)
5. [Problem](#problem)
6. [Read-Only Shim](#read-only-shim)
7. [Initialization](#initialization)
8. [Usage](#usage)
9. [Writes Stay on the Existing API](#writes-stay-on-the-existing-api)
10. [Key Files](#key-files)

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
4. **Migrate hover config lookup** — replace getter lambda with direct
   ~~`settings2.window.hoverlinewidth` read. Remove `_hoverSettingGetter`
   indirection.~~ Done.
5. **Gradually migrate other read-only call sites** as code is touched.
   No big-bang refactor — incremental adoption.
6. ~~**Wire `EVT_SYS_COLOUR_CHANGED`** to recompute `theme_is_dark`.~~ Done.
   `application.py` rebroadcasts as `"system.theme_colour_changed"` Publisher
   signal; settings2 subscribes and recomputes.
7. **Refine refresh triggers.** Eventually, replace the 1-second debounce
   with a proper batched signal when `ConfigParser` is replaced.
8. **Wire `"settings2.changed"` listeners.** Nobody subscribes yet.
   Consumers that need to react to setting changes (e.g. themed colours
   after a dark/light switch) should register via
   `patterns.Publisher().registerObserver(callback, eventType="settings2.changed")`.

---

## Known Anomalies

### System theme detection on Linux/GTK

`EVT_SYS_COLOUR_CHANGED` does **not** fire on GNOME 42+ when the user
toggles dark/light mode via the system Settings panel. GNOME uses the
`org.freedesktop.appearance color-scheme` D-Bus portal to signal the
change, but wxWidgets only added a portal listener in **3.2.3**. The
current build uses wxWidgets 3.2.2, so the event never arrives.

`detect_dark_theme()` (which calls `wx.SystemSettings.GetAppearance().IsDark()`)
**does** return the correct value — the wx colour cache is eventually
invalidated by GTK internally. The value is correct whenever it is
called; it is just never called at the right moment because no event
triggers it.

The Preferences dialog works around this with `EVT_IDLE` polling: it
calls `detect_dark_theme()` every idle cycle and updates the
"(Detected: ...)" label when the result changes.

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
`theme_is_dark` are recomputed on each refresh, so a system theme change
will be picked up the next time any window closes — typically within
seconds of normal interaction.

### Remaining gap

There is currently no **proactive** detection of system theme changes.
If the user switches the OS theme and does not interact with the app
(no window close, no setting change), `theme_is_dark` stays stale
until the next `Settings.set()` call. The `"settings2.changed"` signal
is already broadcast after each refresh, but no consumer subscribes to
it yet. Wiring listeners is tracked in TODO item 8.

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

After step 2, ConfigParser contains both the original template sections
(possibly overwritten by INI values from instance 0) and all viewer
instance sections saved from the previous session.

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
- **Pubsub subscriptions** — some code subscribes to setting-change pubsub
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
   change. The first call creates a `wx.CallLater` timer (1 second);
   subsequent calls reuse it via `Restart()`. No-op before `init()`.
3. When the timer fires, `_refresh(build=False)` re-walks ConfigParser
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
  Preferences OK) collapse into a single refresh
- `EVT_SYS_COLOUR_CHANGED` — `application.py` binds the wx event on the
  main window and rebroadcasts as
  `patterns.Event("system.theme_colour_changed", self).send()`.
  Settings2 subscribes in `wx_ready()` and recomputes
  `_compute_settings_all()` (no full ConfigParser re-read needed).

### Completion signal

After each refresh or recomputation, settings2 fires a Publisher signal:

```python
patterns.Event("settings2.changed", _instance).send()
```

This fires after:
- debounced `Settings.set()` refresh
- system colour change recomputation

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

### New code — use the shim

```python
from taskcoachlib.config import settings2

settings2.view.descriptionpopups     # bool
settings2.window.hoverlinewidth      # int
```

No constructor injection. No getter lambdas. No pubsub subscriptions for
read-only config lookups. See [LIST_MANAGEMENT.md](LIST_MANAGEMENT.md#settings)
for the hover/tooltip flow that uses these two settings.

### Existing code — unchanged

The shim is additive. Existing `self.settings.getboolean(...)` calls
continue to work. Migration is incremental — convert call sites as they
are touched.

### When NOT to use the shim

- **Writes** — use the existing `Settings` API (see below).
- **Per-viewer sections** — sections like `"taskviewer1"` are dynamically
  named via `settingsSection()`. The shim works (`settings2.taskviewer1.treemode`)
  but the section name must be known at call time. For code that already
  has `self.settings` and `self.settingsSection()`, the existing API may
  be clearer.

---

## Writes Stay on the Existing API

The shim is read-only. All writes go through the existing `Settings`
methods:

```python
self.settings.setboolean(section, option, value)
self.settings.settext(section, option, value)
```

These methods handle change detection, pubsub notification, and
persistence. `Settings.set()` also calls `settings2.schedule_refresh()`
to trigger a debounced shim refresh (see [Refresh triggers](#refresh-triggers)).

---

## Key Files

| File | Purpose |
|------|---------|
| `taskcoachlib/config/settings2.py` | Read-only shim (module-level proxy) |
| `taskcoachlib/config/settings.py` | `Settings` class (ConfigParser subclass) |
| `taskcoachlib/config/defaults.py` | Default values and type schema |
| `taskcoachlib/config/__init__.py` | Package exports |
