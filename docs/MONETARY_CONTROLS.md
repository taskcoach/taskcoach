# Monetary Controls

Currency input controls used in Task Coach.

## Index

- [Overview](#overview)
- [Legacy Controls](#legacy-controls)
- [CurrencyCtrl(NumericCtrl)](#currencytrlnumericctrl)
  - [Currency Decimal Places](#currency-decimal-places)
  - [EVT_VALUE_CHANGED](#evt_value_changed)
- [Usage Sites](#usage-sites)
- [Files](#files)
- [Cross-References](#cross-references)

---

## Overview

Task Coach uses monetary amount fields in the Budget tab of the task editor
for hourly fee, fixed fee, and revenue. These fields require locale-aware
decimal input with configurable decimal places.

wxPython does not provide a built-in currency input control. The C++
`wxFloatingPointValidator` is intentionally excluded from the Python binding.

---

## Legacy Controls

Two previous implementations were abandoned:

1. **`AmountCtrl`** (`masked.py`) — wrapped `wx.lib.masked.NumCtrl`. Crashed
   during normal typing due to unfixed Phoenix bugs (#2587, #1179). Unusable.
2. **`CurrencyCtrl` + `CurrencyValidator`** — `wx.TextCtrl` with per-keystroke
   `wx.Validator` filtering. Period keystrokes were silently blocked or
   corrupted input on GTK. Paste bypassed validation entirely. Not fit for
   purpose.

Both are replaced by the current `CurrencyCtrl(NumericCtrl)`.

---

## CurrencyCtrl(NumericCtrl)

`CurrencyCtrl` is a thin subclass of `NumericCtrl` that adds currency-specific
decimal places from the locale. See [NUMERIC_CONTROLS.md](NUMERIC_CONTROLS.md)
for the base class design: free typing, blur-time validation, locale decimal
handling, `EVT_VALUE_CHANGED` pattern, domain-based revert.

```python
class CurrencyCtrl(NumericCtrl):
    def __init__(self, parent, value=0.0, decimal_char=None, **kwargs):
        decimal_places = _get_configured_currency_decimal_places()
        super().__init__(parent, value=value, decimal_places=decimal_places,
                         decimal_char=decimal_char, **kwargs)
```

### Currency Decimal Places

Fallback chain: configured pref → `locale.localeconv()["frac_digits"]` → `2`

| Source | Value | Example |
|---|---|---|
| Preferences override | User setting | `view/currency_decimal_places` |
| `locale.localeconv()["frac_digits"]` | Locale default | 2 (USD/EUR), 0 (JPY), 3 (BHD) |
| `frac_digits == 127` (CHAR_MAX) | Sentinel | Falls back to 2 |

Configurable in Preferences → Regional → "Currency decimal places".

### EVT_VALUE_CHANGED

`AttributeSync` in `BudgetPage` binds `EVT_VALUE_CHANGED` instead of
`EVT_KILL_FOCUS` for hourly fee and fixed fee. This completes
ATTRIBUTE_PATTERN.md TODO #1 for monetary controls, matching the pattern
already used by `DurationCtrl` and `DateTimeComboCtrl`.

---

## Usage Sites

| File | Widget | Field | Editable |
|------|--------|-------|----------|
| `taskcoachlib/gui/dialog/editor.py` | `AmountEntry` → `CurrencyCtrl` | Hourly fee | Yes |
| `taskcoachlib/gui/dialog/editor.py` | `AmountEntry` → `CurrencyCtrl` | Fixed fee | Yes |
| `taskcoachlib/gui/dialog/editor.py` | `AmountEntry` → `CurrencyCtrl` | Revenue | No (read-only) |

---

## Files

| File | Purpose |
|------|---------|
| `taskcoachlib/widgets/numericctrl.py` | `NumericCtrl` base class |
| `taskcoachlib/widgets/currencyctrl.py` | `CurrencyCtrl(NumericCtrl)` subclass |
| `taskcoachlib/gui/dialog/entry.py` | `AmountEntry` wrapper (panel + read-only support) |
| `taskcoachlib/gui/dialog/editor.py` | Budget tab uses `AmountEntry` for fee/revenue fields |
| `taskcoachlib/widgets/masked.py` | Legacy `AmountCtrl` — no longer used |

---

## Cross-References

- **Numeric controls:** [NUMERIC_CONTROLS.md](NUMERIC_CONTROLS.md) —
  `NumericCtrl` base class, blur validation, UX rationale
- **Locale handling:** [LOCALE.md](LOCALE.md) — three-layer pattern, settings
  keys, detection mechanisms, data vs display
- **Attribute sync:** [ATTRIBUTE_PATTERN.md](ATTRIBUTE_PATTERN.md) — Layer 2
  (UI↔Domain), `EVT_VALUE_CHANGED` migration
