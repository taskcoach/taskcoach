# Numeric Controls

`NumericCtrl` — general-purpose numeric input with free typing and blur-time
validation.

## Index

- [Overview](#overview)
- [Class Hierarchy](#class-hierarchy)
- [NumericCtrl API](#numericctrl-api)
- [Blur-Time Validation](#blur-time-validation)
- [EVT_VALUE_CHANGED Pattern](#evt_value_changed-pattern)
- [Locale Decimal Handling](#locale-decimal-handling)
- [Preferences](#preferences)
- [UX Rationale](#ux-rationale)
- [Cross-References](#cross-references)

---

## Overview

`NumericCtrl` is a `wx.TextCtrl` subclass that:

- Allows **free typing** — no keystroke blocking, no validator
- **Validates on blur** — parses text as float, formats if valid, reverts to
  domain value if invalid
- Fires **`EVT_VALUE_CHANGED`** on blur (valid input) and from `SetValue()`
  (programmatic writes)
- Handles **locale decimal** — displays with locale separator, returns Python
  float with period decimal internally

**File:** `taskcoachlib/widgets/numericctrl.py`

---

## Class Hierarchy

```
numericctrl.py:
  NumericCtrl(wx.TextCtrl)
      decimal_places=None  → floating: "12.3" stays "12.3"
      decimal_places=2     → fixed: "12.3" becomes "12.30"

currencyctrl.py:
  CurrencyCtrl(NumericCtrl)
      decimal_places = locale frac_digits (default 2)
```

See [MONETARY_CONTROLS.md](MONETARY_CONTROLS.md) for `CurrencyCtrl` details.

---

## NumericCtrl API

### Constructor

```python
NumericCtrl(parent, value=0.0, decimal_places=None, decimal_char=None, **kwargs)
```

- `value` — initial float value
- `decimal_places` — `None` = floating (strip trailing zeros), `int` = fixed
  (always format to N places)
- `decimal_char` — override for locale decimal. Fallback chain:
  explicit param → configured pref → `locale.localeconv()["decimal_point"]` → `"."`

### GetValue() → float

Returns the current value as a Python float. Always uses period decimal
internally, regardless of display locale.

### SetValue(float)

Formats the float for display using locale decimal. Updates `_lastSetValue`
(the domain reference value) and fires `EVT_VALUE_CHANGED`.

---

## Blur-Time Validation

The control stores `_lastSetValue` — updated only by `SetValue(float)` (called
by the constructor and by `AttributeSync` when pushing domain values). This
tracks what the domain last told the control to display.

On focus loss (`_onKillFocus`):

1. Read raw text from control
2. Replace locale decimal with `.`, try `float()`
3. **If valid:** update `_lastSetValue`, format display, fire `EVT_VALUE_CHANGED`
4. **If invalid:** revert display to `_format(_lastSetValue)`, do NOT fire
   `EVT_VALUE_CHANGED` (nothing changed in the domain)

Empty field is treated as `0.0`.

---

## EVT_VALUE_CHANGED Pattern

Reuses the existing `EVT_VALUE_CHANGED` / `ValueChangedEvent` from
`maskedtimectrl.py`. Same event type used by `DurationCtrl`, `DateTimeCombo`,
and now `NumericCtrl`.

Fires from:
- `_onKillFocus` — after successful blur validation (user finished editing)
- `SetValue()` — when called programmatically (domain pushed a new value)

`AttributeSync` binds `EVT_VALUE_CHANGED` instead of `EVT_KILL_FOCUS`. This
completes ATTRIBUTE_PATTERN.md TODO #1 for monetary controls.

---

## Locale Decimal Handling

### Display

`_format(value)` replaces `"."` with the locale decimal character for display.

- `decimal_places=None` → `"%g"` formatting (strip trailing zeros)
- `decimal_places=2` → `"%.2f"` formatting (fixed 2 places)

### Input parsing

`GetValue()` and `_onKillFocus` replace the locale decimal with `"."` before
calling `float()`.

### Fallback chain

```
explicit decimal_char param
  → settings.Settings().get("view", "decimal_separator")
    → locale.localeconv()["decimal_point"]
      → "."
```

---

## Preferences

Two settings in Preferences → Regional:

**Decimal separator** (`view/decimal_separator`):
- `""` — Automatic (detect from system)
- `"."` — Period
- `","` — Comma

**Currency decimal places** (`view/currency_decimal_places`):
- `""` — Automatic (from locale `frac_digits`)
- `"0"` — 0 places (e.g. JPY, KRW)
- `"2"` — 2 places (e.g. USD, EUR)
- `"3"` — 3 places (e.g. BHD, KWD)

Changes require restart. See [LOCALE.md](LOCALE.md) for the common pattern.

---

## UX Rationale

Modern best practice for numeric input fields ([Smashing Magazine](https://www.smashingmagazine.com/2022/09/inline-validation-web-forms-ux/),
[David Luhr](https://luhr.co/blog/2025/07/01/a-deep-dive-on-the-ux-of-number-inputs/)):

- **Do NOT block characters on keypress.** Per-keystroke filtering creates
  frustrating workarounds and confusing behavior.
- **Allow free typing**, then validate and correct on blur.
- **Revert to last valid value** on invalid input (not 0.00). The domain value
  via `_lastSetValue` provides the revert target.
- **No error messages** — these fields sync to the domain model on blur via
  `AttributeSync`. Inline errors with no resolution path would just sit there.
- **Never trap focus** — universally discouraged UX pattern.

The previous `CurrencyValidator` approach blocked period keystrokes on GTK,
deleted characters in insert mode, and allowed invalid paste content. The
free-typing approach eliminates all of these issues.

---

## Cross-References

- **Locale handling:** [LOCALE.md](LOCALE.md) — three-layer pattern, settings
  keys, detection mechanisms
- **Monetary controls:** [MONETARY_CONTROLS.md](MONETARY_CONTROLS.md) —
  `CurrencyCtrl` subclass, currency-specific locale handling
- **Attribute sync:** [ATTRIBUTE_PATTERN.md](ATTRIBUTE_PATTERN.md) — Layer 2
  (UI↔Domain), `EVT_VALUE_CHANGED` migration
- **Date/time controls:** [DATETIME_CONTROLS.md](DATETIME_CONTROLS.md) —
  same `EVT_VALUE_CHANGED` pattern, same blur-time commit approach
