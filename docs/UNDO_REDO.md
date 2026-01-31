# Undo/Redo

## Table of Contents

1. [TODO: Refactoring](#todo-refactoring)
2. [Current Implementation](#current-implementation)
3. [Command Pattern](#command-pattern)
4. [Interaction with Attribute Pattern](#interaction-with-attribute-pattern)
5. [References](#references)

## TODO: Refactoring

The current approach wraps **every** field write in a command, including
derived value adjustments (e.g., duration recalculated from start/stop).
This produces multiple undo stack entries for a single logical user action.

The Attribute pattern should manage true change detection for undo/redo.
Only genuine user-initiated changes should create undo entries. Derived
adjustments (sync calc results) should be treated as side effects of the
originating command, not independent commands.

Proposed approach:
- The originating command (e.g., start date change) should encapsulate all
  derived adjustments within its own `do_command()`/`undo_command()`.
- Alternatively, introduce a composite command or transaction that groups
  the primary change with its derived adjustments into a single undo entry.
- The Attribute pattern's change detection (no-op on equal values) already
  prevents spurious notifications — this same principle should extend to
  preventing spurious undo entries.

## Current Implementation

The undo/redo system is built on the Command pattern. Every user-initiated
change to a domain object is wrapped in a Command subclass (e.g.,
`EditEffortDurationCommand`, `EditEffortStartDateTimeCommand`,
`EditPlannedDurationCommand`). Each command stores old and new values and
implements `do_command()`, `undo_command()`, and `redo_command()`.

Commands are executed via `.do()`, which pushes them onto the undo stack.
Undo pops the command and calls `undo_command()`, restoring old values.
Redo re-executes via `redo_command()`.

## Command Pattern

Commands wrap **all** field changes, including derived value adjustments.
For example, when the user changes a start date:

1. `EditEffortStartDateTimeCommand` fires, writing the new start to the domain.
2. The sync calc (`__syncEffortState`) detects that duration must be
   recalculated and fires `EditEffortDurationCommand` to adjust duration.

Both commands land on the undo stack. Undoing the start change does **not**
automatically undo the derived duration adjustment — each command is
independent on the stack.

## Interaction with Attribute Pattern

The Attribute pattern (see [ATTRIBUTE_PATTERN.md](ATTRIBUTE_PATTERN.md))
manages value storage, change detection, and pubsub notification. Commands
call the domain setter (e.g., `effort.setDuration()`), which delegates to
`Attribute.set()`. The Attribute fires its callback only on actual change,
which sends pubsub notifications. AttributeSync in the editor subscribes to
these notifications and updates the UI.

The flow:

```
User edit → AttributeSync → Command.do() → domain setter → Attribute.set()
  → callback (on change) → pubsub → AttributeSync.onAttributeChanged → UI update
```

## References

- [ATTRIBUTE_PATTERN.md](ATTRIBUTE_PATTERN.md) — Attribute storage, change
  detection, and pubsub notification pattern
- [DURATION_CALCULATIONS.md](DURATION_CALCULATIONS.md) — Duration sync calc
  logic for tasks and efforts
- `taskcoachlib/command/base.py` — Base command classes
- `taskcoachlib/command/effortCommands.py` — Effort-specific commands
- `taskcoachlib/command/taskCommands.py` — Task-specific commands
- `taskcoachlib/gui/dialog/attributesync.py` — AttributeSync (Layer 2 wiring)
