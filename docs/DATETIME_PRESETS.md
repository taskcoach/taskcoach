# DateTime Presets and Proposed Dates

Default date/time values for new tasks, configured in Preferences.

## Index

- [TODO](#todo)
- [Overview](#overview)
- [Preference Setting Format](#preference-setting-format)
- [Preset Mode](#preset-mode)
  - [Flow](#flow)
  - [Constructor Bypass Problem](#constructor-bypass-problem)
  - [Completion Date Preset](#completion-date-preset)
  - [Reminder Preset](#reminder-preset)
- [Propose Mode](#propose-mode)
  - [Old Behavior (DateTimeEntry)](#old-behavior-datetimeentry)
  - [Initial Bug (DateTimeComboCtrl)](#initial-bug-datetimecomboctrl2)
  - [Fix](#fix)
- [Duration Mode Interaction](#duration-mode-interaction)
- [Suggested DateTime Computation](#suggested-datetime-computation)
- [Reminder Scheduling on Load](#reminder-scheduling-on-load)
- [Related Documentation](#related-documentation)

---

## TODO

1. **Unify preset and propose paths through the Attribute model or
   DateTimeComboCtrl public API.** Currently, preset mode writes directly to
   the Task constructor kwargs (`uicommand.py:1693-1708`), bypassing both
   the Attribute setter/callback chain and the editor widget API. Propose
   mode relies on the editor widget to pre-fill a display value. These two
   paths should be consolidated so that both modes go through the same
   public interface — either:
   - The Attribute model (setter + callback), so all domain invariants
     (recurrence, reminder clearing, child completion) fire correctly; or
   - A new `DateTimeComboCtrl` method such as
     `ActivateValue(value, proposed=True)` + `DeactivateValue()`, where
     `proposed=True` means: set the internal display value and mark the
     checkbox checked, but flag the value as "proposed" so the editor
     knows whether the user has explicitly confirmed it.
   This would eliminate the split between `uicommand.py` (preset) and
   `editor.py` (propose) and ensure domain invariants are always enforced.

2. **Preset completion date bypasses `_onCompletionDateTimeChanged`.**
   When `uicommand.py` passes `completionDateTime=...` to the Task
   constructor, the Attribute is initialized directly (no `.set()` call),
   so the callback never fires. This means recurrence is not triggered,
   reminder is not cleared, children are not completed, and parent
   completion cascade does not happen. The task is born in an inconsistent
   state. See [Constructor Bypass Problem](#constructor-bypass-problem).

3. ~~**Fix propose mode for DateTimeComboCtrl**~~ — **Done.** `suggestedValue`
   parameter added to `DateTimeComboCtrl.__init__()`. Editor passes preference-
   computed datetime at construction. See [Fix](#fix) section.

4. **Duration mode interaction with presets needs resolution.** New tasks
   start in Implicit mode for legacy and preset/propose compatibility
   reasons (see DURATION_CALCULATIONS.md "Logic Flow" note). Implicit
   mode keeps both fields independently editable, avoiding conflicts
   with preset/propose values. However, if a duration mode preference
   is ever added, the interaction must be carefully designed. See
   [Duration Mode Interaction](#duration-mode-interaction).

---

## Overview

When creating a new task, each date field (planned start, due date, actual
start, completion, reminder) can be pre-filled based on user preferences.
There are two modes:

| Mode | Checkbox State | Value Persisted | Where Applied |
|------|---------------|----------------|---------------|
| **Preset** | Checked | Yes — on the domain object at creation | `uicommand.py` (before editor opens) |
| **Propose** | Unchecked | No — display hint only, hidden behind "N/A" | Editor widget (when editor opens) |

Both modes compute the same datetime using `task.Task.suggestedDateTime()`.
The mode only controls where and how the value is applied.

---

## Preference Setting Format

Settings are stored in `TaskCoach.ini` under `[view]`:

```ini
defaultplannedstartdatetime = propose_today_currenttime
defaultduedatetime = propose_tomorrow_endofworkingday
defaultactualstartdatetime = propose_today_currenttime
defaultcompletiondatetime = propose_today_currenttime
defaultreminderdatetime = propose_tomorrow_startofworkingday
```

Format: `{preset|propose}_{day}_{time}`

**Day options:** `today`, `tomorrow`, `dayaftertomorrow`, `nextfriday`, `nextmonday`

**Time options:** `startofday`, `startofworkingday`, `currenttime`, `endofworkingday`, `endofday`

The prefix (`preset` or `propose`) determines the mode. The `suggestedDateTime()`
method strips the prefix (`dummy_prefix` at `task.py:1944`) and computes the
same datetime regardless of mode.

**File:** `taskcoachlib/config/defaults.py:78-82`

**Preferences UI:** `taskcoachlib/gui/dialog/preferences.py:2038-2127`

The preferences UI help text explains the distinction:

> New tasks start with "Preset" dates and times filled in and checked.
> "Proposed" dates and times are filled in, but not checked.

Note: Completion date only supports propose mode (`[check_choices[1]]` at
`preferences.py:2103`).

---

## Preset Mode

### Flow

When the preference starts with `"preset"`:

1. **Task creation** (`uicommand.py:1691-1708`):
   ```python
   def do_command(self, event, show=True):
       kwargs = self.taskKeywords.copy()
       if self.__shouldPresetPlannedStartDateTime():
           kwargs["plannedStartDateTime"] = task.Task.suggestedPlannedStartDateTime()
       if self.__shouldPresetDueDateTime():
           kwargs["dueDateTime"] = task.Task.suggestedDueDateTime()
       # ... same for actualStart, completion, reminder
       newTaskCommand = command.NewTaskCommand(self.taskList, **kwargs)
   ```

2. **Task constructor** (`task.py:84-89`): The value is stored directly
   in the Attribute via `Attribute.__init__()`, NOT via `.set()`.

3. **Editor opens**: Reads from domain object. Value is non-None, so
   `DateTimeComboCtrl` is constructed with `value=datetime`, checkbox starts
   checked, fields show the preset datetime.

### Constructor Bypass Problem

`Attribute.__init__()` stores the value but does **NOT** fire the callback.
Callbacks only fire on `Attribute.set()`. This means any business logic in
the `_on*Changed` callback is skipped when a value is set via the constructor.

For most date fields this is harmless — the callbacks for planned start,
due date, and actual start just send pubsub notifications and mark dirty,
which happen separately during task creation.

But for **completion date** and **reminder**, the callbacks contain
important business logic that is bypassed.

### Completion Date Preset

When `completionDateTime` is passed to the Task constructor:

| Expected Side Effect | Actually Fires? | Why |
|---------------------|----------------|-----|
| Recurrence triggered (`self.recur()`) | No | Callback not fired |
| Reminder cleared (`self.setReminder(None)`) | No | Callback not fired |
| Percentage set to 100 | Yes | Handled separately in `__init__` lines 87-94 |
| Children completed | No | Callback not fired |
| Effort tracking stopped | No | Callback not fired |
| Parent completion cascade | No | Callback not fired |

The task is born in an **inconsistent state**: marked completed (percentage
100) but without any of the normal completion side effects.

Note: The preferences UI only allows propose mode for completion date
(`preferences.py:2103`), so this path may never be reached in normal usage.
But nothing prevents setting `"preset_..."` manually in `TaskCoach.ini`.

### Reminder Preset

When `reminder` is passed to the Task constructor, `setReminder()` is not
called, so the `reminderChangedEventType` pubsub event is not fired.

This is **not a problem** because the `ReminderController` uses polling —
it iterates all tasks every second and checks `task.reminder()` directly.
It does not rely on pubsub events to discover reminders, only to clear
its "already shown" set when a reminder is snoozed.

**File:** `taskcoachlib/gui/remindercontroller.py:63-98`

---

## Propose Mode

### Old Behavior (DateTimeEntry)

The old `DateTimeEntry` control (removed in the DateTimeComboCtrl refactor)
accepted a `suggestedDateTime` parameter:

```python
class DateTimeEntry(widgets.DateTimeCtrl):
    def __init__(self, parent, ..., suggestedDateTime=None, ...):
        if initialDateTime == date.DateTime() and suggestedDateTime:
            self.setSuggested(suggestedDateTime)
        else:
            self.SetValue(initialDateTime)

    def setSuggested(self, suggestedDateTime):
        super().SetValue(suggestedDateTime)  # Pre-fill display fields
        super().SetNone()                    # Uncheck (shows "N/A", hides values)
```

The old editor computed and passed the suggested datetime:

```python
# editor.py (old addDateEntry, ~line 1512)
suggestedDateTime = getattr(self.items[0], "suggestedDueDateTime")()
dateTimeEntry = entry.DateTimeEntry(..., suggestedDateTime=suggestedDateTime, ...)
```

Result: The display fields showed the suggested datetime (hidden behind
"N/A"), and when the user checked the checkbox, the suggested value appeared.
The value was **never persisted** until the user checked the box and the
editor committed it through a command.

### Initial Bug (DateTimeComboCtrl)

`DateTimeComboCtrl` was originally created without suggested datetime support.
When `value=None` (propose mode), the constructor defaulted to
`datetime.now()`, ignoring the user's preference setting entirely.

### Fix

**Done.** `suggestedValue` parameter added to `DateTimeComboCtrl.__init__()`.
The editor passes the preference-computed datetime at construction time:

```python
def __init__(self, parent, value=None, suggestedValue=None, ...):
    ...
    display_value = value if value is not None else (suggestedValue or datetime.datetime.now())
```

The sub-controls are initialized with the suggested datetime and hold it
while the checkbox is unchecked. In preset mode, `value` is already
non-None, so `suggestedValue` is ignored.

For how the sub-controls serve as the stash for DateTimeComboCtrl (retaining
the proposed value through activate/deactivate cycles), see
[DATETIME_CONTROLS.md — Sub-Control Stash Model](DATETIME_CONTROLS.md#sub-control-stash-model).

**Editor construction sites** (`taskcoachlib/gui/dialog/editor.py`):

| Date Field | suggestedValue |
|-----------|---------------|
| Planned start | `task.Task.suggestedPlannedStartDateTime()` |
| Due date | `task.Task.suggestedDueDateTime()` |
| Actual start | `task.Task.suggestedActualStartDateTime()` |
| Completion | `task.Task.suggestedCompletionDateTime()` |
| Reminder | `task.Task.suggestedReminderDateTime()` |

---

## Duration Mode Interaction

New tasks start in **Implicit** duration mode (see DURATION_CALCULATIONS.md
"Logic Flow" note). This is intentional: Implicit mode keeps both start
and due fields independently editable, so preset and propose values can
be applied to either field without conflict.

If the default were Automatic mode instead, it would immediately resolve
to adjdue or adjstart when a date is checked, making the other field
read-only and overriding its preset/propose value:

| Start Setting | Due Setting | Automatic Would Resolve To | Problem |
|--------------|------------|---------------------------|---------|
| Preset | Preset | adjdue (start first) | Due preset overwritten by start+duration calc |
| Preset | Propose | adjdue | Due is read-only — propose value unreachable |
| Propose | Preset | adjstart | Start is read-only — propose value unreachable |
| Propose | Propose | stays Automatic | No conflict — both fields editable until user checks one |

Implicit mode avoids all of these problems. Both fields remain editable
regardless of the preset/propose combination.

If a duration mode preference is ever added, these interactions must be
carefully designed — the chosen mode must be compatible with the
preset/propose settings, or the mode must be forced to implicit when
presets are active.

---

## Suggested DateTime Computation

The `suggestedDateTime()` classmethod computes a datetime from the preference
setting and `now()`. It is called at dialog open time (propose mode) or at
task creation time (preset mode).

**File:** `taskcoachlib/domain/task/task.py:1941-1989`

```python
@classmethod
def suggestedDateTime(cls, defaultDateTimeSetting, now=date.Now):
    defaultDateTime = cls.settings.get("view", defaultDateTimeSetting)
    dummy_prefix, defaultDate, defaultTime = defaultDateTime.split("_")
    dateTime = now()
    # Apply day offset: today, tomorrow, dayaftertomorrow, nextfriday, nextmonday
    # Apply time: startofday, startofworkingday, currenttime, endofworkingday, endofday
    ...
```

Key points:
- Always computed from `now()` at call time — "tomorrow" means tomorrow
  from when the method is called, not relative to task creation date
- The `dummy_prefix` is the mode (`preset`/`propose`) — discarded here
- Working day hours come from `efforthourstart` / `efforthourend` settings

Convenience classmethods:
- `suggestedPlannedStartDateTime()` → reads `defaultplannedstartdatetime`
- `suggestedDueDateTime()` → reads `defaultduedatetime`
- `suggestedActualStartDateTime()` → reads `defaultactualstartdatetime`
- `suggestedCompletionDateTime()` → reads `defaultcompletiondatetime`
- `suggestedReminderDateTime()` → reads `defaultreminderdatetime`

---

## Reminder Scheduling on Load

When a `.tsk` file is loaded, tasks are reconstructed via `__init__` with
reminder values from XML. The reminder is stored directly in `self.__reminder`
(not through `setReminder()`), so no pubsub event fires.

This works because `ReminderController` uses **polling** (checks all tasks
every second via `timer.second`), not event-driven scheduling. It reads
`task.reminder()` directly and doesn't need a pubsub notification to
discover reminders.

The pubsub subscription (`_onReminderChanged`) is only used to clear the
"already shown" set when a reminder is snoozed — so it can fire again at the
new snooze time.

**File:** `taskcoachlib/gui/remindercontroller.py`

---

## Related Documentation

- [DATETIME_CONTROLS.md](DATETIME_CONTROLS.md) — DateTimeComboCtrl widget API,
  ActivateValue/DeactivateValue, suggested datetime old behavior reference
- [ATTRIBUTE_PATTERN.md](ATTRIBUTE_PATTERN.md) — Attribute model, setter/callback
  pattern, constructor vs `.set()` behavior, three-layer relationship
- [DURATION_CALCULATIONS.md](DURATION_CALCULATIONS.md) — Duration modes,
  starting state documentation ("Start: Implicit mode")
- [PERSISTENCE_XML.md](PERSISTENCE_XML.md) — XML writer/reader, skip conditions,
  round-trip consistency
