# Duration Calculations

Duration calculations for Edit Task Dates and Edit Effort windows.

## Index

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
- [Persistence](#persistence)

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

The logic flow is triggered by ONE user-initiated change at a time. The user makes
a single change (checkbox, field value, or dropdown), then the logic processes
(including loops) until it stabilizes and exits. Only then is the system ready
for the next user change.

```
Start: Automatic, all fields empty

0. Store last user action and skip any step that changes the user's explicitly set value.
   0.1 User unchecked Start-Date
   0.2 User unchecked Due-Date

1. If Mode Automatic
   1.1 If Start-Date set, Then set Adj-Due mode, Loop
   1.2 If Due-Date set, Then set Adj-Start mode, Loop
   1.3 If Implicit chosen, Then set Implicit mode, Loop
   1.4 If Adj-Due chosen, Then set Adj-Due mode, Loop
   1.5 If Adj-Start chosen, Then set Adj-Start mode, Loop

2. If Mode Adj-Due
   2.1 Activate Start-Date, If not unchecked by user [Ref2, 0.1]
   2.2 Activate Due-Date (Read-Only) [Ref2]
   2.3 Disable Automatic mode option in dropdown [Ref1]
   2.4 If Duration changed, Then adj Due-Date
   2.5 If Start-Date changed, Then adj Due-Date
   2.6 If Start-Date disabled, Then
       2.6.1 Deactivate Due-Date
       2.6.2 Reactivate Automatic mode option in dropdown
       2.6.3 Set Automatic mode, Loop

3. If Mode Adj-Start
   3.1 Activate Due-Date, If not unchecked by user [Ref2, 0.2]
   3.2 Activate Start-Date (Read-Only) [Ref2]
   3.3 Disable Automatic mode option in dropdown [Ref1]
   3.4 If Duration changed, Then adj Start-Date
   3.5 If Due-Date changed, Then adj Start-Date
   3.6 If Due-Date disabled, Then
       3.6.1 Deactivate Start-Date
       3.6.2 Reactivate Automatic mode option in dropdown
       3.6.3 Set Automatic mode, Loop

4. If Mode Implicit
   4.1 Disable Automatic mode option in dropdown [Ref1]
   4.2 If Start-Date enabled
       4.2.1 If Due-Date enabled
           4.2.1.1 Enable Duration (Read-Only)
           4.2.1.2 Adj Duration
           4.2.1.3 If Start-Date changed, Then adj Duration
           4.2.1.4 If Due-Date changed, Then adj Duration
       4.2.2 If Due-Date disabled, Then disable Duration
   4.3 If Start-Date disabled, Then disable Duration

5. Update Field States (See: UI Field States section)

Glossary:
   Adj-Due    = Adjust Due Date mode
   Adj-Start  = Adjust Planned Start Date mode
   Start-Date = Planned Start Date-Time Combo Control with Checkbox
   Due-Date   = Due Date-Time Combo Control with Checkbox

References:
   [Ref1] Covered by "Calculation Mode Dropdown Build Logic" section
   [Ref2] Covered by "UI Field States" section
```

```
Implements: __syncDurationState()
Called on: Every change of Start-Date, Due-Date, Duration, Presets, or Mode dropdown.
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
Called on: Lost focus of Start-Date, Due-Date, Duration, or Presets fields.
```

### UI Field States

| Calc Mode | Start | Due | Start Field | Duration Field | Due Field |
|-----------|-------|-----|-------------|----------------|-----------|
| Automatic | ❌ | ❌ | Editable | Editable | Editable |
| Adjust Due | ✅ | ✅ | Editable + Check | Editable | Read-only + Check |
| Adjust Start | ✅ | ✅ | Read-only + Check | Editable | Editable + Check |
| Implicit | ✅ | ✅ | Editable | Read-only | Editable |
| Implicit | ✅ | ❌ | Editable | Disabled | Editable |
| Implicit | ❌ | ✅ | Editable | Disabled | Editable |

Key: Disabled = Field is disabled and unchecked
     + Check = Ensure checkbox is checked when setting this field state

```
Implements: __updateFieldStates()
Called on: Every change of Start-Date, Due-Date, Duration, or Presets fields (after main calc logic).
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

| Mode | Inputs | Output (Calculated) | Read-Only Field |
|------|--------|---------------------|-----------------|
| **Standard** | Set Start, Set Duration | Stop | None |
| **Retroactive** | Set Stop, Set Duration | Start | Start |
| **Implicit** | Set Start, Set Stop | Duration | Duration |

### Logic Flow

```
Start: Standard mode, Stop-Date disabled

1. If Mode Standard
   1.1 If Retroactive mode chosen, Loop
   1.2 Set Start-Date editable
   1.3 If Start-Date changed, Then
       1.3.1 If Duration > 0, Then adj Stop-Date
   1.4 If Duration changed, Then
       1.4.1 If Duration > 0, Then
           1.4.1.1 Enable Stop-Date
           1.4.1.2 Adj Stop-Date
       1.4.2 If Duration = 0, Then disable Stop-Date
   1.5 If Stop-Date changed, Then
       1.5.1 If Stop-Date <= Start-Date, Then
           1.5.1.1 Set Stop-Date = Start-Date + 1s
           1.5.1.2 Adj Duration to 1s
       1.5.2 If Stop-Date > Start-Date, Then adj Duration

2. If Mode Retroactive
   2.1 If Standard mode chosen, Loop
   2.2 Set Start-Date read-only
   2.3 If Duration changed, Then
       2.3.1 If Duration > 0, Then
           2.3.1.1 Enable Stop-Date
           2.3.1.2 Adj Start-Date
       2.3.2 If Duration = 0, Then disable Stop-Date
   2.4 If Stop-Date changed, Then
       2.4.1 If Duration <= 0, Then
           2.4.1.1 Set Duration to 1s
           2.4.1.2 Set Start-Date = Stop-Date - 1s
       2.4.2 If Duration > 0, Then adj Start-Date

3. If Mode Implicit
   3.1 Set Start-Date editable
   3.2 Set Duration read-only
   3.3 If Start-Date changed or Stop-Date changed or Mode changed, Then
       3.3.1 If Stop-Date enabled and Stop > Start, Then adj Duration = Stop - Start
       3.3.2 If Stop-Date enabled and Stop <= Start, Then Duration = 0

Auto-Switch Logic (in __syncEffortState, same pattern as Time Spent state check):
   A1. If Mode = Standard AND Stop-Date active (IsChecked) AND Duration = 0, Then switch to Implicit
   A2. If Duration preset selected AND Mode = Implicit, Then switch to Standard

Glossary:
   adj        = recalculate/adjust
   Start-Date = Start Date-Time Combo Control with Checkbox
   Stop-Date  = Stop Date-Time Combo Control with Checkbox
   Duration   = Effort Duration Control
```

```
Implements: __syncEffortState()
Called on: Every change of Start-Date, Stop-Date, Duration, or Mode dropdown.
Note: UI-only — updates control values (SetDateTime, SetDuration, SetChecked).
      No persistence commands. Saving happens when the dialog is closed/saved.
```

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
| Standard | ❌ | ❌ | Check Stop | Auto-switch → Implicit, Duration = Stop - Start (read-only) |
| Standard | ❌ | ❌ | Set Retroactive | Start read-only |
| Standard | ✅ | ✅ | Change Duration | Stop recalculated |
| Standard | ✅ | ✅ | Change Start | Stop recalculated, Duration unchanged |
| Standard | ✅ | ✅ | Change Stop | Duration recalculated, Start unchanged |
| Standard | ✅ | ✅ | Uncheck Stop | Stop disabled |
| Standard | ✅ | ✅ | Set Duration to zero | Stop disabled, Duration = 0 |
| Standard | ✅ | ✅ | Set Retroactive | Start read-only, Start = Stop - Duration |
| Standard | ✅ | ✅ | Set Implicit | Duration read-only, Duration = Stop - Start |
| Standard | ❌ | ❌ | Set Implicit | Duration read-only |
| Retroactive | ❌ | ❌ | Enter Duration | Stop auto-enabled, Start = Stop - Duration |
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
| Implicit | ✅ | ✅ | Select duration preset | Auto-switch → Standard, Stop = Start + Duration |
| Implicit | ✅ | ✅ | Uncheck Stop | Duration disabled |
| Implicit | ✅ | ✅ | Set Standard | Duration editable |
| Implicit | ✅ | ✅ | Set Retroactive | Start read-only, Duration editable |

---

## Persistence

- **Task Dates**: Mode stored in task's `plannedDurationMode` attribute
- **Effort**: Mode stored in effort's `entryMode` attribute (values: `"standard"`, `"retroactive"`, `"implicit"`)
