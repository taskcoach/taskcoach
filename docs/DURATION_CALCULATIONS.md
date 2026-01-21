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

```
Start: Automatic, all fields empty

1. If Mode Automatic
   1.1 If Start-Date set, Then set Adj-Due mode, Loop
   1.2 If Due-Date set, Then set Adj-Start mode, Loop
   1.3 If Implicit chosen, Then set Implicit mode, Loop
   1.4 If Adj-Due chosen, Then set Adj-Due mode, Loop
   1.5 If Adj-Start chosen, Then set Adj-Start mode, Loop

2. If Mode Adj-Due
   2.1 Activate Start-Date
   2.2 Activate Due-Date (Read-Only)
   2.3 Disable Automatic mode option in dropdown
   2.4 If Duration changed, Then adj Due-Date
   2.5 If Start-Date changed, Then adj Due-Date
   2.6 If Start-Date disabled, Then
       2.6.1 Deactivate Due-Date
       2.6.2 Reactivate Automatic mode option in dropdown
       2.6.3 Set Automatic mode, Loop

3. If Mode Adj-Start
   3.1 Activate Due-Date
   3.2 Activate Start-Date (Read-Only)
   3.3 Disable Automatic mode option in dropdown
   3.4 If Duration changed, Then adj Start-Date
   3.5 If Due-Date changed, Then adj Start-Date
   3.6 If Due-Date disabled, Then
       3.6.1 Deactivate Start-Date
       3.6.2 Reactivate Automatic mode option in dropdown
       3.6.3 Set Automatic mode, Loop

4. If Mode Implicit
   4.1 Disable Automatic mode option in dropdown
   4.2 If Start-Date enabled
       4.2.1 If Due-Date enabled
           4.2.1.1 Enable Duration (Read-Only)
           4.2.1.2 Adj Duration
           4.2.1.3 If Start-Date changed, Then adj Duration
           4.2.1.4 If Due-Date changed, Then adj Duration
       4.2.2 If Due-Date disabled, Then disable Duration
   4.3 If Start-Date disabled
       4.3.1 If Due-Date enabled, Then disable Duration
       4.3.2 If Due-Date disabled, Then
           4.3.2.1 Reactivate Automatic mode option in dropdown
           4.3.2.2 Set Automatic mode, Loop

5. Update Field States (See: UI Field States section)

Glossary:
   Adj-Due    = Adjust Due Date mode
   Adj-Start  = Adjust Planned Start Date mode
   Start-Date = Planned Start Date
   Due-Date   = Due Date
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
| Adjust Due | ✅ | ✅ | Editable | Editable | Read-only |
| Adjust Start | ✅ | ✅ | Read-only | Editable | Editable |
| Implicit | ✅ | ✅ | Editable | Read-only | Editable |
| Implicit | ✅ | ❌ | Editable | Disabled | Editable |
| Implicit | ❌ | ✅ | Editable | Disabled | Editable |

Key: Disabled = Field is disabled and unchecked

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

### Field Change Effects

| Calc Mode | User Changes | Duration | Start | Stop |
|-----------|--------------|----------|-------|------|
| Standard | Start | Recalculated | - | Unchanged |
| Standard | Duration | - | Unchanged | Recalculated |
| Standard | Stop | Recalculated | Unchanged | - |
| Retroactive | Duration | - | Recalculated | Unchanged |
| Retroactive | Stop | Unchanged | Recalculated | - |

### Action Sequence

| Calc Mode | Stop | Action | Result |
|-----------|------|--------|--------|
| Standard | ❌ | Enter Duration | Stop auto-enabled, Stop = Start + Duration |
| Standard | ❌ | Change Start | No effect (no Stop to calculate from) |
| Standard | ❌ | Check Stop | Duration = Stop - Start |
| Standard | ❌ | Set Retroactive | Duration disabled, Start read-only |
| Standard | ✅ | Change Duration | Stop recalculated |
| Standard | ✅ | Change Start | Duration recalculated, Stop unchanged |
| Standard | ✅ | Change Stop | Duration recalculated, Start unchanged |
| Standard | ✅ | Uncheck Stop | Duration shows 0, still editable |
| Standard | ✅ | Reset to zero | Stop cleared, Duration = 0 |
| Standard | ✅ | Set Retroactive | Start read-only, Start = Stop - Duration |
| Retroactive | ❌ | Check Stop | Duration enabled, Start = Stop - Duration |
| Retroactive | ❌ | Set Standard | Start editable, Duration enabled |
| Retroactive | ✅ | Enter Duration | Start = Stop - Duration |
| Retroactive | ✅ | Change Duration | Start recalculated, Stop unchanged |
| Retroactive | ✅ | Change Stop | Start recalculated, Duration unchanged |
| Retroactive | ✅ | Uncheck Stop | Duration disabled, Start unchanged |
| Retroactive | ✅ | Reset to zero | Stop cleared, Duration disabled |
| Retroactive | ✅ | Set Standard | Start editable, Duration enabled |

---

## Persistence

- **Task Dates**: Mode stored in task's `plannedDurationMode` attribute
- **Effort**: Mode stored in effort's `entryMode` attribute
