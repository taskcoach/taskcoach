# Duration Calculations

Duration calculations for Edit Task Dates and Edit Effort windows.

## Index

- [TODO](#todo)
- [Preconditions and Global Logic](#preconditions-and-global-logic)
- [Edit Task Dates Window](#edit-task-dates-window)
  - [Duration Modes](#duration-modes)
  - [Logic Flow](#logic-flow)
  - [Calculation Mode Dropdown Build Logic](#calculation-mode-dropdown-build-logic)
  - [UI Field States](#ui-field-states)
  - [Action Sequence](#action-sequence)
- [Edit Effort Window](#edit-effort-window)
  - [Entry Modes](#entry-modes)
  - [Field Change Effects](#field-change-effects)
  - [Action Sequence](#action-sequence-1)
- [Preset Dropdown Sync](#preset-dropdown-sync)
- [Persistence](#persistence)

---

## TODO

5. Add cross-references to ATTRIBUTE_PATTERN.md:
   - Section 0.2 change-only rule is the UI-level equivalent of
     Attribute.set()'s equality check (Layer 3 in ATTRIBUTE_PATTERN.md).
   - No-mode safety relates to ATTRIBUTE_PATTERN.md §Value Normalization.
6. Add section 0.5: No-mode safety. If mode is None or invalid, sync
   functions must return immediately without entering any mode branch.
   No silent fallback to a default mode.
   - 0.5.1 __syncTaskState: if mode not in valid set → return.
   - 0.5.2 __syncEffortState: if mode not in valid set → return.
     Current gap: else branch catches None mode incorrectly.
7. Add section 0.6: Calculation mode is always explicitly required.
   If no mode explicitly set, never default to a calculation mode.
   In logic flow, add final item (e.g. item 5 for Task, item 4 for
   Effort): "If no calculation mode specified, do nothing."
   OPEN QUESTION: How to differentiate between loading in process
   (mode not yet set, should wait) and invalid value requiring reset
   to automatic?
9. ~~DateTimeComboCtrl Checkbox toggle EVT_KILL_FOCUS gap~~ — **Resolved.**
   ~~Editor binds `EVT_CHECKBOX` via `combo.Bind(wx.EVT_CHECKBOX, handler)`
   and calls `sync.commit()` explicitly.~~
   **Update:** EVT_CHECKBOX is no longer exposed by DateTimeComboCtrl. All
   AttributeSync instances use `EVT_VALUE_CHANGED` as `editedEventType`,
   which fires on checkbox toggle AND date/time edits. External
   EVT_CHECKBOX handlers and `sync.commit()` hacks removed.
   See [DATETIME_CONTROLS.md](DATETIME_CONTROLS.md) TODO item 3.
10. **Reconcile legacy "datestied" preference with duration mode.**
   The `view.datestied` setting (`preferences.py:2029`) is a legacy
   predecessor to duration mode. It has three options: nothing, "changing
   start shifts due" (`startdue`), or "changing due shifts start"
   (`duestart`). It only applies to **inline edits in the task list
   viewer** (`gui/viewer/task.py:2121-2131`) via `keep_delta=True` on
   `EditPlannedStartDateTimeCommand` / `EditDueDateTimeCommand`. It is
   not wired into the editor dialog at all. Duration mode does the same
   thing bidirectionally with explicit UI in the editor. These two
   mechanisms should be unified or the legacy setting should be removed
   in favor of duration mode.
11. Effort Logic Flow: Renumber sections 1, 2, 3 to match the task
    section pattern — consolidate x.1/x.2 mode-change rules into
    a single x.1 note, renumber remaining items.

## Notes

1. Negative durations are permitted to avoid silent errors and unexpected
   behaviour for the user. The user should see that their inputs are giving
   negative durations.

---

## Preconditions and Global Logic

All logic flows share these preconditions and rules.

The logic flow is triggered by ONE user-initiated change at a time. The user makes
a single change (checkbox, field value, or dropdown), then the logic processes
(including loops) until it stabilizes and exits. Only then is the system ready
for the next user change.

```
0. Preconditions and global logic.
   0.1 User actions. Store last user action and skip any step that changes
       the user's explicitly set value.
       0.1.1 User explicitly changed Start-Date
       0.1.2 User explicitly changed Stop-Date / Due-Date
       0.1.3 User explicitly changed Duration
       0.1.4 User explicitly changed Mode
   0.2 Change-only rule. Only set or change a value if required (i.e., the
       new value differs from the current value). This is also looping
       protection.
   0.3 Recursive safety.
       0.3.1 Any recursive call assumes starting at depth 0 if no depth
             received and passes depth+1 to the next call.
       0.3.2 Loop calls must pass sourceField=None (or omit it).
       0.3.3 depth == 1 should never receive a user action, log error,
             continue.
       0.3.4 Depth > 1 should never occur, log error, exit.
   0.4 Sync-mode guard. If sync is already in progress, early exit.
       Flag lives on the domain SSOT instance (task or effort), shared
       across all editor windows editing the same object. Prevents
       re-entry from synchronous pubsub callbacks triggered by commands
       within the sync function. The loop (direct recursion) is the
       guaranteed path for processing mode changes — suppressed
       callbacks are harmless because the loop completes the state
       transition. Any deferred callback that arrives after sync-mode
       clears will run against the correct final state.
```

---

## Edit Task Dates Window

### Duration Modes

| Mode | Inputs | Output (Calculated) | Notes |
|------|--------|---------------------|-------|
| **Automatic** | Set Start-Date, Set Due-Date | Set Adj Mode | Auto-detects direction |
| **Implicit** | Set Start-Date, Set Due-Date | Duration | Never auto-changed by system |
| **Adjust Due Date** | Set Start-Date, Set Duration | Due-Date | Due-Date always auto-enabled |
| **Adjust Start Date** | Set Due-Date, Set Duration | Start-Date | Start-Date always auto-enabled |

---

### Logic Flow

```
Start: Implicit mode, all fields empty (see note below)

Note: New tasks always start in Implicit mode, not Automatic. This is
intentional for two reasons:
  (a) Legacy compatibility — the original code had no explicit calc
      modes; it only saved planned start and due dates, so the duration
      was always implied. The explicit calc mode system defaults to
      Implicit to preserve this behavior.
  (b) Preset/propose support — Automatic mode immediately resolves to
      adjdue or adjstart when a date is checked, which would make the
      calculated field read-only and override any preset/propose value
      for that field. Implicit mode keeps both fields independently
      editable, allowing preset and propose values to be applied without
      conflict. See DATETIME_PRESETS.md "Duration Mode Interaction".

0. See Preconditions and Global Logic section above.
   0.4 Sync-mode guard... See section above.
       0.4.1 Flag: task._durationSyncInProgress on domain Task instance.

1. If Mode Automatic
   1.1 Note: Mode changes away never come back here
   1.2 If Start-Date exists, Then set Adj-Due mode, Loop
   1.3 If Due-Date exists, Then set Adj-Start mode, Loop

2. If Mode Adj-Due
   2.1 Note: Mode changes away never come back here
   2.2 Activate Start-Date, If not Unset-Action [Ref2, 0.1.1]
   2.3 Activate Due-Date (Read-Only) [Ref2]
   2.4 Disable Automatic mode option in dropdown [Ref1]
   2.5 If Duration changed, Then adj Due-Date
   2.6 If Start-Date Unset-Action, Then
       2.6.1 Set Sync-Mode [0.4]
       2.6.2 Deactivate Due-Date
       2.6.3 Reactivate Automatic mode option in dropdown
       2.6.4 Set Automatic mode
       2.6.5 Unset Sync-Mode
       2.6.6 Loop
   2.7 If Start-Date changed, Then adj Due-Date

3. If Mode Adj-Start
   3.1 Note: Mode changes away never come back here
   3.2 Activate Due-Date, If not Unset-Action [Ref2, 0.1.2]
   3.3 Activate Start-Date (Read-Only) [Ref2]
   3.4 Disable Automatic mode option in dropdown [Ref1]
   3.5 If Duration changed, Then adj Start-Date
   3.6 If Due-Date Unset-Action, Then
       3.6.1 Set Sync-Mode [0.4]
       3.6.2 Deactivate Start-Date
       3.6.3 Reactivate Automatic mode option in dropdown
       3.6.4 Set Automatic mode
       3.6.5 Unset Sync-Mode
       3.6.6 Loop
   3.7 If Due-Date changed, Then adj Start-Date

4. If Mode Implicit
   4.1 Note: Mode changes away never come back here
   4.2 Disable Automatic mode option in dropdown [Ref1]
   4.3 If Start-Date exists
       4.3.1 If Due-Date exists
           4.3.1.1 Enable Duration (Read-Only)
           4.3.1.2 Adj Duration
           4.3.1.3 Negative Durations permitted
       4.3.2 If Due-Date Unset-Action, Then disable Duration
   4.4 If Start-Date Unset-Action, Then disable Duration

5. Update Field States (See: UI Field States section)

Glossary:
   adj          = recalculate/adjust
   Adj-Due      = Adjust Due Date mode
   Adj-Start    = Adjust Planned Start Date mode
   Set-Action   = explicit user change from no value or zero value to a value
   Unset-Action = explicit user change from a value to no value or zero value
   Start-Date   = Planned Start Date-Time Combo Control with Checkbox
   Due-Date     = Due Date-Time Combo Control with Checkbox
   Sync-Mode    = Re-entry guard flag [0.4]

References:
   [Ref1] Covered by "Calculation Mode Dropdown Build Logic" section
   [Ref2] Covered by "UI Field States" section
```

```
Implements: __syncTaskState()
Called on: Every change of Start-Date, Due-Date, Duration, or Mode dropdown.
Note: Business logic — reads/sets domain values through commands.
      The attribute pattern (Layer 2) updates widgets automatically.
      All sync goes through EVT_VALUE_CHANGED → AttributeSync → command.
```

### Calculation Mode Dropdown Build Logic

| Mode | Automatic Option |
|------|------------------|
| Automatic | Enabled |
| Adjust Due | Disabled |
| Adjust Start | Disabled |
| Implicit | Disabled |

```
Rule: If current mode is Automatic, enable Automatic option; otherwise disable it.
Implements: __updateDurationModeDropdown()
Called on: Lost focus of Start-Date, Due-Date, or Duration fields.
```

### UI Field States

| Calc Mode | Start | Due | Start Field | Duration Field | Presets | Due Field |
|-----------|-------|-----|-------------|----------------|---------|-----------|
| Automatic | ❌ | ❌ | Editable | Editable | Enabled | Editable |
| Adjust Due | ✅ | ✅ | Editable + Check | Editable | Enabled | Read-only + Check |
| Adjust Start | ✅ | ✅ | Read-only + Check | Editable | Enabled | Editable + Check |
| Implicit | ✅ | ✅ | Editable | Read-only | Disabled | Editable |
| Implicit | ✅ | ❌ | Editable | Disabled | Disabled | Editable |
| Implicit | ❌ | ✅ | Editable | Disabled | Disabled | Editable |

Key: Disabled = Field is disabled and unchecked
     + Check = Ensure checkbox is checked when setting this field state

```
Implements: __updateFieldStates()
Called on: Every change of Start-Date, Due-Date, or Duration (after main calc logic).
```

### Action Sequence

| Calc Mode | Start | Due | Action | Result |
|-----------|-------|-----|--------|--------|
| Automatic | ❌ | ❌ | Check Start | Calc Mode → Adjust Due, Due auto-enabled |
| Automatic | ❌ | ❌ | Check Due | Calc Mode → Adjust Start, Start auto-enabled |
| Automatic | ❌ | ❌ | Set Implicit | Calc Mode → Implicit |
| Automatic | ❌ | ❌ | Set Adjust Due | Calc Mode → Adj-Due, Start & Due auto-enabled |
| Automatic | ❌ | ❌ | Set Adjust Start | Calc Mode → Adj-Start, Due & Start auto-enabled |
| Implicit | ✅ | ✅ | Change Start | Duration recalculated, Due unchanged |
| Implicit | ✅ | ✅ | Change Due | Duration recalculated, Start unchanged |
| Implicit | ✅ | ✅ | Uncheck Start | Duration disabled (needs both dates) |
| Implicit | ✅ | ✅ | Uncheck Due | Duration disabled (needs both dates) |
| Implicit | ✅ | ✅ | Set Automatic | Automatic disabled (both dates checked) |
| Implicit | ✅ | ✅ | Set Adjust Due | Calc Mode → Adjust Due |
| Implicit | ✅ | ✅ | Set Adjust Start | Calc Mode → Adjust Start |
| Adjust Due | ✅ | ❌ | None | Incorrect State, Error |
| Adjust Due | ✅ | ✅ | Change Start | Due recalculated |
| Adjust Due | ✅ | ✅ | Change Duration | Due recalculated |
| Adjust Due | ✅ | ✅ | Uncheck Start | Due deactivated, Calc Mode → Automatic |
| Adjust Due | ✅ | ✅ | Uncheck Due | Read-Only, no changes |
| Adjust Due | ✅ | ✅ | Set Automatic | Automatic disabled (both dates checked) |
| Adjust Due | ✅ | ✅ | Set Implicit | Calc Mode → Implicit |
| Adjust Due | ✅ | ✅ | Set Adjust Start | Calc Mode → Adjust Start |
| Adjust Start | ❌ | ✅ | None | Incorrect State, Error |
| Adjust Start | ✅ | ✅ | Change Due | Start recalculated |
| Adjust Start | ✅ | ✅ | Change Duration | Start recalculated |
| Adjust Start | ✅ | ✅ | Uncheck Due | Start deactivated, Calc Mode → Automatic |
| Adjust Start | ✅ | ✅ | Uncheck Start | Read-Only, no changes |
| Adjust Start | ✅ | ✅ | Set Automatic | Automatic disabled (both dates checked) |
| Adjust Start | ✅ | ✅ | Set Implicit | Calc Mode → Implicit |
| Adjust Start | ✅ | ✅ | Set Adjust Due | Calc Mode → Adjust Due |

---

## Edit Effort Window

### Entry Modes

| Mode | Inputs | Output (Calculated) | Read-Only Field | Presets |
|------|--------|---------------------|-----------------|---------|
| **Standard** | Set Start, Set Duration | Stop | None | Enabled |
| **Retroactive** | Set Stop, Set Duration | Start | Start | Enabled |
| **Implicit** | Set Start, Set Stop | Duration | Duration | Disabled |

### Logic Flow

```
Start: Standard mode, Duration 0, Stop-Date disabled

0. See Preconditions and Global Logic section above.
   0.4 Sync-mode guard... See section above.
       0.4.1 Flag: effort._effortSyncInProgress on domain Effort instance.

1. If Mode Standard
   1.1 Note: Mode changes away never come back here
   1.2 See 1.1 and TODO item 11
   1.3 Set Start-Date editable
   1.4 Set Duration editable
   1.5 Set Presets dropdown enabled [Ref1]
   1.6 If Duration Unset-Action, Then disable Stop-Date
   1.7 If Stop-Date Unset-Action, Then set Duration = 0
   1.8 If Stop-Date Set-Action, Then
       1.8.1 If Duration = 0, Then set Implicit mode, Loop
       1.8.2 If Duration > 0, Then adj Duration
   1.9 If Start-Date changed, Then
       1.9.1 If Duration > 0, Then
           1.9.1.1 Set Sync-Mode [0.4]
           1.9.1.2 Adj Stop-Date
           1.9.1.3 Adj Duration *Impossible* TODO remove step? remove sync-mode?
           1.9.1.4 Unset Sync-Mode
       1.9.2 If Duration = 0, Then do nothing
   1.10 If Duration changed and exists, Then
       1.10.1 If Duration > 0, Then
           1.10.1.1 Enable Stop-Date
           1.10.1.2 Adj Stop-Date
       1.10.2 If Duration = 0, Then disable Stop-Date
   1.11 If Stop-Date changed and exists, Then adj Duration
   1.12 If Duration = 0, Then Autoheal, Thus
       1.12.1 Not possible: Disable Stop-Date Conflicts [Ref3]
   1.13 If Duration > 0, Then Autoheal, Thus
       1.13.1 Enable Stop-Date
       1.13.2 Adj Stop-Date
   1.14 If Duration < 0, Then Negative Durations permitted

2. If Mode Retroactive
   2.1 Note: Mode changes away never come back here
   2.2 See 2.1 and TODO item 11
   2.3 Set Start-Date read-only
   2.4 Set Duration editable
   2.5 Set Presets dropdown enabled [Ref1]
   2.6 If Duration Unset-Action, Then disable Stop-Date
   2.7 If Stop-Date Unset-Action, Then set Duration = 0
   2.8 If Stop-Date changed and exists, Then adj Start-Date
   2.9 If Duration changed and exists, Then
       2.9.1 If Duration > 0, Then
           2.9.1.1 Enable Stop-Date
           2.9.1.2 Adj Start-Date
       2.9.2 If Duration = 0, Then disable Stop-Date
   2.10 If Duration = 0, Then Autoheal, Thus
       2.10.1 Not possible: Disable Stop-Date Conflicts [Ref2]
   2.11 If Duration > 0, Then Autoheal, Thus
       2.11.1 Enable Stop-Date
       2.11.2 Adj Start-Date
   2.12 If Duration < 0, Then Negative Durations permitted

3. If Mode Implicit
   3.1 Note: Mode changes away never come back here
   3.2 See 3.1 and TODO item 11
   3.3 Set Presets dropdown disabled [Ref1]
   3.4 Set Start-Date editable
   3.5 If Stop-Date does not exist, Disable Duration
   3.6 If Stop-Date exists, Then
       3.6.1 Enable Duration (Read-Only)
       3.6.2 Adj Duration
       3.6.3 Negative Durations permitted

Glossary:
   adj          = recalculate/adjust
   Set-Action   = explicit user change from no value or zero value to a value
   Unset-Action = explicit user change from a value to no value or zero value
   Start-Date   = Start Date-Time Combo Control with Checkbox
   Stop-Date    = Stop Date-Time Combo Control with Checkbox
   Duration     = Effort Duration Control

References:
   [Ref1] Covered by "UI Field States" section
   [Ref2] 2.10.1 Not possible to Disable Stop-Date because it can conflict
          with 2.9.1.1 and 2.11.1 if the Stop-Date is the same as the
          Start-Date and we won't modify the values, leave as-is
   [Ref3] 1.12.1 Not possible to Disable Stop-Date because it can conflict
          with 1.10.1.1 and 1.13.1 if the Stop-Date is the same as the
          Start-Date and we won't modify the values, leave as-is
```

```
Implements: __syncEffortState()
Called on: Every change of Start-Date, Stop-Date, Duration, or Mode dropdown.
Note: Business logic — reads/sets domain values through commands.
      The attribute pattern (Layer 2) updates widgets automatically.
      All sync goes through EVT_VALUE_CHANGED → AttributeSync → command.
```

### Time Spent

Display-only field showing Now - Start. Value refreshes on a 1-second timer.
See UI Field States table for Active/Hidden display rules.

```
Implements: __updateTimeSpentDisplay()
Called on: After main calc logic; value refreshed every 1s by timer while active.
```

### UI Field States

| Entry Mode | Stop | Start Field | Duration Field | Presets | Stop Field | Time Spent |
|------------|------|-------------|----------------|---------|------------|------------|
| Standard | ❌ | Editable | Editable | Enabled | Editable | Active |
| Standard | ✅ | Editable | Editable | Enabled | Editable | Hidden |
| Retroactive | ❌ | Read-only | Editable | Enabled | Editable | Active |
| Retroactive | ✅ | Read-only | Editable | Enabled | Editable | Hidden |
| Implicit | ❌ | Editable | Disabled | Disabled | Editable | Active |
| Implicit | ✅ | Editable | Read-only | Disabled | Editable | Hidden |

Key: Disabled = Field is disabled (and unchecked for Stop)
     Read-only = Field is enabled but not user-editable
     Active = Display-only, showing Now - Start (tracking)
     Hidden = Not displayed (Stop-Date exists, not tracking)

```
Note: Currently only implements Time Spent and Presets dropdown fields.
      Other field states are set inline in the logic flow.
Implements: __updateFieldStates()
Called on: After main calc logic, every change of Start-Date, Stop-Date, Duration, or Mode dropdown.
```

---

### Field Change Effects

| Calc Mode | User Changes | Start | Duration | Stop |
|-----------|--------------|-------|----------|------|
| Standard | Start | - | Unchanged | Recalculated |
| Standard | Duration | Unchanged | - | Recalculated |
| Standard | Stop | Unchanged | Recalculated | - |
| Retroactive | Duration | Recalculated | - | Unchanged |
| Retroactive | Stop | Recalculated | Unchanged | - |
| Implicit | Start | - | Recalculated | Unchanged |
| Implicit | Stop | Unchanged | Recalculated | - |

### Action Sequence

| Calc Mode | Duration | Stop | Action | Result |
|-----------|----------|------|--------|--------|
| Standard | ❌ | ❌ | Enter Duration | Stop auto-enabled, Stop = Start + Duration |
| Standard | ❌ | ❌ | Change Start | No effect (no Stop to calculate from) |
| Standard | ❌ | ❌ | Check Stop | Set Implicit Mode, Loop |
| Standard | ❌ | ❌ | Set Retroactive | Start read-only |
| Standard | ✅ | ✅ | Change Duration | Stop recalculated |
| Standard | ✅ | ✅ | Change Start | Stop recalculated, Duration unchanged |
| Standard | ✅ | ✅ | Change Stop | Duration recalculated, Start unchanged |
| Standard | ✅ | ✅ | Uncheck Stop | Stop disabled |
| Standard | ✅ | ✅ | Set Duration to zero | Stop disabled, Duration = 0 |
| Standard | ✅ | ✅ | Set Retroactive | Start read-only, Start = Stop - Duration |
| Standard | ✅ | ✅ | Set Implicit | Duration read-only, Duration = Stop - Start |
| Standard | ❌ | ❌ | Set Implicit | Duration read-only |
| Retroactive | ❌ | ❌ | Enter Duration | Set Stop enabled, Loop |
| Retroactive | ❌ | ❌ | Check Stop | Start = Stop - Duration |
| Retroactive | ❌ | ❌ | Set Standard | Start editable |
| Retroactive | ✅ | ✅ | Change Duration | Start recalculated, Stop unchanged |
| Retroactive | ✅ | ✅ | Change Stop | Start recalculated, Duration unchanged |
| Retroactive | ✅ | ✅ | Uncheck Stop | Stop disabled |
| Retroactive | ✅ | ✅ | Set Duration to zero | Stop disabled, Duration = 0 |
| Retroactive | ✅ | ✅ | Set Standard | Start editable |
| Retroactive | ✅ | ✅ | Set Implicit | Duration read-only, Duration = Stop - Start |
| Retroactive | ❌ | ❌ | Set Implicit | Duration read-only |
| Implicit | ✅ | ✅ | Change Start | Duration recalculated, Stop unchanged |
| Implicit | ✅ | ✅ | Change Stop | Duration recalculated, Start unchanged |
| Implicit | ✅ | ✅ | Select duration preset | Set Standard Mode, Loop |
| Implicit | ✅ | ✅ | Uncheck Stop | Duration disabled |
| Implicit | ✅ | ✅ | Set Standard | Duration editable |
| Implicit | ✅ | ✅ | Set Retroactive | Start read-only, Duration editable |

---

## Preset Dropdown Sync

Both the task and effort editors have a "Presets" dropdown next to the duration
control. The dropdown must stay aligned with the current duration value:
selecting a matching preset when the duration matches, or resetting to the
"Presets..." placeholder when it doesn't.

### Sync Pattern

The preset dropdown subscribes directly to the domain's duration-changed
pubsub event. This decouples it from the source of the change — whether the
user typed a value, selected a preset, or an external source updated the
domain, the dropdown updates itself.

**Task editor:**
- Subscribes to `plannedDurationChangedEventType()` → `__updatePresetSelection()`

**Effort editor:**
- Subscribes to `durationChangedEventType()` → `__updateEffortPresetSelection()`

### Why Not a Callback?

The alternative is calling the preset update from the duration change handler
or `AttributeSync` callback. This couples the preset to the commit path —
any code that changes duration must remember to also update the preset.
Pubsub subscription ensures the preset is always correct regardless of how
the duration changed.

### Lifecycle

Subscriptions are created during `addEntries()` / `addDurationEntry()` and
unsubscribed in `close()` / `close_edit_book()`.

---

## Persistence

### Mode Attributes
- **Task Dates**: Mode stored in task's `plannedDurationMode` attribute
- **Effort**: Mode stored in effort's `entryMode` attribute (values: `"standard"`, `"retroactive"`, `"implicit"`)

### XML Format (locale-independent)

All values are stored in hardcoded formats — no locale involvement. Locale formatting is display-only. Files are portable across locales.

| Data type | XML format | Example | Writer code |
|-----------|-----------|---------|-------------|
| DateTime | `%Y-%m-%d %H:%M:%S` | `2026-01-29 15:30:00` | `writer.py:formatDateTime()` |
| Duration (budget, plannedDuration) | `H:MM:SS` (days folded into hours) | `74:30:00` (= 3d 2h 30m) | `writer.py:budgetAsAttribute()` via `TimeDelta.hoursMinutesSeconds()` |
| Float (hourlyFee, fixedFee) | `str(float)` | `25.5` | `writer.py:taskNode()` |

### Internal Types
- Durations use `date.TimeDelta` (extends `datetime.timedelta`, adds `hoursMinutesSeconds()`)
- DateTimes use `date.DateTime` (extends `datetime.datetime`)
- UI controls (`DurationCtrl`, `DateTimeComboCtrl`) return these domain types directly for `AttributeSync` compatibility
