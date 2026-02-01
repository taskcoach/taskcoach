# Persistence: XML Writer / Reader

How domain objects are serialized to `.tsk` XML files and deserialized back.

## Index

- [TODO](#todo)
- [Overview](#overview)
- [Writer Skip Conditions](#writer-skip-conditions)
  - [Task Node](#task-node)
  - [Recurrence Node](#recurrence-node)
  - [Effort Node](#effort-node)
  - [Base Node (All Objects)](#base-node-all-objects)
- [Reader Defaults](#reader-defaults)
- [Round-Trip Consistency](#round-trip-consistency)
- [Skip Condition Categories](#skip-condition-categories)
- [Related Documentation](#related-documentation)

---

## TODO

1. **Maybe always write values?** The writer omits attributes when the value
   equals an assumed default. This scatters default-value knowledge across
   the writer instead of centralizing it in the domain (Attribute pattern).
   Always writing every attribute would make the XML slightly larger but
   eliminate the implicit "is this worth saving" decision and the risk of
   writer/reader default mismatch. At minimum, the writer and reader should
   share a common source of truth for defaults.

2. The writer and reader independently decide defaults in two different
   files with no shared constant or domain method connecting them. They
   agree by convention, not by contract. If one changes without the other,
   round-trip silently corrupts data.

3. ~~`plannedDurationMode` skip condition uses hardcoded `"implicit"` but
   the documented default starting state is "automatic"~~ — **Resolved.**
   The actual code default is `"implicit"` (task.py:52). The
   DURATION_CALCULATIONS.md documentation has been corrected to match.
   Writer and reader both agree on `"implicit"` as the default.

---

## Overview

**File:** `taskcoachlib/persistence/xml/writer.py` (XMLWriter)
**File:** `taskcoachlib/persistence/xml/reader.py` (XMLReader)

The writer serializes domain objects to XML. For each field, it checks
whether the value equals an assumed default — if so, the XML attribute is
**omitted entirely** (not written as an empty string). The XML element has
no trace of the attribute.

The reader deserializes XML back to domain objects. For each field, if the
XML attribute is missing, the reader provides its own default via
`.get("attributeName", default)`.

These two default decisions are made independently. They happen to agree
by convention.

---

## Writer Skip Conditions

The writer conditionally omits attributes from the XML. "Skipped" means
the attribute is **not written to XML at all** — completely absent from
the element, not written as an empty value.

### Task Node

`taskNode()` — lines 144-199:

| Line | XML Attribute | Skip Condition | Type |
|------|--------------|----------------|------|
| 148 | `plannedstartdate` | `== maxDateTime` | Sentinel |
| 150 | `duedate` | `== maxDateTime` | Sentinel |
| 152 | `actualstartdate` | `== maxDateTime` | Sentinel |
| 154 | `completiondate` | `== maxDateTime` | Sentinel |
| 156 | `percentageComplete` | `== 0` (falsy) | Falsy |
| 158 | `recurrence` | empty Recurrence (falsy) | Falsy |
| 160 | `budget` | `== TimeDelta()` | Sentinel |
| 162 | `plannedDuration` | `== TimeDelta()` | Sentinel |
| 164 | `plannedDurationMode` | `!= "implicit"` (inverted) | Hardcoded string |
| 166 | `priority` | `== 0` (falsy) | Falsy |
| 168 | `hourlyFee` | `== 0` (falsy) | Falsy |
| 170 | `fixedFee` | `== 0` (falsy) | Falsy |
| 173 | `reminder` | `== maxDateTime` or `None` | Sentinel + None |
| 187 | `prerequisites` | empty string (falsy) | Falsy |
| 189 | `shouldMarkCompleted...` | `== None` | None check |

### Recurrence Node

`recurrenceNode()` — lines 201-217:

| Line | XML Attribute | Skip Condition | Type |
|------|--------------|----------------|------|
| 203 | `amount` | `<= 1` | Numeric compare |
| 205 | `count` | `<= 0` | Numeric compare |
| 207 | `max` | `<= 0` | Numeric compare |
| 209 | `stop_datetime` | `== maxDateTime` | Sentinel |
| 211 | `sameWeekday` | falsy (`False`) | Falsy |
| 213 | `recurBasedOnCompletion` | falsy (`False`) | Falsy |
| 215 | `weekdays` | falsy (empty) | Falsy |

### Effort Node

`effortNode()` — lines 219-239:

| Line | XML Attribute | Skip Condition | Type |
|------|--------------|----------------|------|
| 234 | `entryMode` | falsy or `== "standard"` | Hardcoded string |

### Base Node (All Objects)

`__baseNode()` / `baseNode()` / `baseCompositeNode()` — lines 286-353:

| Line | XML Attribute | Skip Condition | Type |
|------|--------------|----------------|------|
| 292 | `creationDateTime` | `<= DateTime.min` | Sentinel |
| 294 | `modificationDateTime` | `<= DateTime.min` | Sentinel |
| 298 | `subject` | `""` (falsy) | Falsy |
| 300 | `description` | `""` (falsy) | Falsy |
| 308 | `fgColor` | `None` (falsy) | Falsy |
| 310 | `bgColor` | `None` (falsy) | Falsy |
| 312 | `font` | `None` (falsy) | Falsy |
| 314 | `icon` | `""` (falsy) | Falsy |
| 316 | `selectedIcon` | `""` (falsy) | Falsy |
| 318 | `ordering` | `== 0` (falsy) | Falsy |
| 345 | `expandedContexts` | empty (falsy) | Falsy |

---

## Reader Defaults

When an XML attribute is missing, the reader provides a default via
`.get("attr", default)`. Selected examples from `_parse_task_node()`:

| XML Attribute | Reader Default | Matches Writer Skip? |
|--------------|---------------|---------------------|
| `subject` | `""` | Yes — writer skips `""` |
| `plannedstartdate` | not set → `None` → `maxDateTime` | Yes |
| `percentageComplete` | `"0"` → `0` | Yes |
| `priority` | `"0"` → `0` | Yes |
| `plannedDurationMode` | `"implicit"` | Yes — code default is `"implicit"` (task.py:52) |
| `budget` | `""` → `TimeDelta()` | Yes |
| `hourlyFee` | `"0"` → `0.0` | Yes |

---

## Round-Trip Consistency

A value round-trips correctly when:

```
domain.getValue() → writer skips → XML has no attribute → reader defaults → domain.setValue(default)
```

...produces the same value as the original. This works today for all fields
because the writer skip conditions and reader defaults happen to agree.

**Risk:** If the writer's skip condition or the reader's default is changed
independently, the round-trip breaks silently. There is no shared constant,
no assertion, and no test that verifies writer/reader default agreement.

---

## Skip Condition Categories

The writer uses several types of skip conditions, with varying levels of
correctness:

**Sentinel-based** (dates, budget, duration) — Comparing against an
explicit "no value" marker defined by the domain (`maxDateTime`,
`TimeDelta()`). Semantically correct — the sentinel means "not set."

**Falsy-based** (strings, numbers, booleans) — Using Python truthiness
(`if value:`). This conflates multiple concepts:
- `""` is falsy — but `""` is a valid string value (user cleared subject)
- `0` is falsy — but `0` is a valid numeric value (priority 0, zero fee)
- `None` is falsy — genuinely means "not set"
- `False` is falsy — valid boolean value

These work by accident because the falsy value happens to match the
constructor default. They'd break if any default changed to a non-falsy
value.

**Hardcoded string** (`plannedDurationMode`, `entryMode`) — Comparing
against a string literal that the writer assumes is the default. The
domain constructor defines the actual default separately. If they
diverge, data is silently lost.

---

## Related Documentation

- [ATTRIBUTE_PATTERN.md](ATTRIBUTE_PATTERN.md) — Domain Attribute model,
  value normalization, setter/callback pattern
- [DATETIME_PRESETS.md](DATETIME_PRESETS.md) — Preset/propose modes and
  how they interact with persistence
- [DURATION_CALCULATIONS.md](DURATION_CALCULATIONS.md) — Duration modes,
  starting state documentation ("Start: Automatic mode")
