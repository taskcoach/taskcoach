# Monetary Controls

This document describes the monetary (currency/amount) input controls used in Task Coach, the legacy control's known issues, and the replacement.

## Table of Contents

- [Background](#background)
- [Current Control — AmountCtrl (masked.NumCtrl)](#current-control--amountctrl-maskednumctrl)
  - [Architecture](#architecture)
  - [Known Bugs in wxPython Phoenix](#known-bugs-in-wxpython-phoenix)
- [Replacement — CurrencyCtrl](#replacement--currencyctrl)
  - [Design](#design)
  - [Locale Handling](#locale-handling)
  - [Future Considerations](#future-considerations)
- [Usage Sites](#usage-sites)
- [Files](#files)

## Background

Task Coach uses monetary amount fields in the Budget tab of the task editor for hourly fee, fixed fee, and revenue. These fields require locale-aware decimal input with two decimal places.

wxPython does not provide a built-in currency input control. The C++ `wxFloatingPointValidator` is intentionally excluded from the Python binding. The wxPython community has long noted this gap — a [wxPython forum discussion on money controls](https://discuss.wxpython.org/t/money-control/24654) confirms that developers typically build custom solutions.

## Current Control — AmountCtrl (masked.NumCtrl)

### Architecture

`AmountCtrl` (`taskcoachlib/widgets/masked.py`) is a thin wrapper around `wx.lib.masked.NumCtrl`, a **standard wxPython widget** — it is not custom to Task Coach. The wrapper configures locale-aware parameters:

```python
class AmountCtrl(FixOverwriteSelectionMixin, masked.NumCtrl):
    def __init__(self, parent, value=0, locale_conventions=None):
        locale_conventions = locale_conventions or locale.localeconv()
        # ... extracts decimalChar, groupChar from locale ...
        super().__init__(
            parent, value=value,
            allowNegative=False, fractionWidth=2,
            selectOnEntry=True,
            decimalChar=decimalChar, groupChar=groupChar,
            groupDigits=groupDigits,
        )
```

`AmountEntry` (`taskcoachlib/gui/dialog/entry.py`) wraps `AmountCtrl` in a `PanelWithBoxSizer`, adding read-only support (disable + grey background) and `NavigateBook()` for notebook tab traversal.

### Known Bugs in wxPython Phoenix

`wx.lib.masked.NumCtrl` has **open, unfixed bugs** in wxPython Phoenix that cause crashes during normal typing. These are fundamental event-handling bugs in the masked edit framework, not Task Coach configuration problems.

**Issue [#2587](https://github.com/wxWidgets/Phoenix/issues/2587)** (open, reported Dec 2024, wxPython 4.2.1+):

Three distinct crashes:
1. **`_adjustFloat` ValueError** — Deleting the initial value then typing triggers `ValueError: not enough values to unpack` when `_adjustFloat` splits on the decimal character. The value string no longer contains the expected decimal point.
2. **`_insertKey` IndexError** — Deletion and re-entry triggers `IndexError: string index out of range` in the character validation logic.
3. **Fatal crash on macOS** — Moving cursor then typing a decimal point causes `NSTextRange` assertion failure and `PyGILState_Release: thread state must be current when releasing` — a fatal Python crash.

**Issue [#1179](https://github.com/wxWidgets/Phoenix/issues/1179)** (open, wxPython 4.0.4+):

- **Select-and-type IndexError** — Selecting multiple characters with mouse and pressing a number key causes `IndexError: string index out of range`.
- **Root cause**: Phoenix changed event ordering between `EVT_KEY_DOWN` and `EVT_CHAR`. After `_OnKeyDown`, the TextCtrl contents are already changed, but `_OnChar` still expects the original unmodified value. This event ordering worked correctly in Classic wxPython but broke in Phoenix.
- A tentative workaround (overriding `_OnKeyDown` to call `_OnChar` directly) was suggested but never officially implemented.

**No fix has been merged** for either issue as of January 2026.

## Replacement — CurrencyCtrl

### Design

`CurrencyCtrl` (`taskcoachlib/widgets/currencyctrl.py`) replaces `AmountCtrl` using `wx.TextCtrl` + custom `wx.Validator`. This is the approach recommended by the wxPython community (including the reporter of issue #2587) as the standard pattern for currency input.

Implementation:
- `wx.TextCtrl` with `wx.TE_RIGHT` (right-aligned, standard for monetary amounts)
- `CurrencyValidator` (`wx.Validator` subclass): filters keystrokes to digits, single decimal point, and navigation keys
- On focus-loss: auto-formats to 2 decimal places (e.g., `5` becomes `5.00`)
- `GetValue()` returns `float`, `SetValue(float)` sets formatted text
- Read-only support handled by `AmountEntry` wrapper (disable + grey background)
- Locale-aware decimal point from `locale.localeconv()`

`AmountEntry` (`taskcoachlib/gui/dialog/entry.py`) wraps `CurrencyCtrl` in a `PanelWithBoxSizer`, providing read-only support and `NavigateBook()` for notebook tab traversal. `AttributeSync` uses `wx.EVT_KILL_FOCUS` to trigger persistence, which aligns with the focus-loss formatting.

### Locale Handling

Locale handling (preserved from the legacy control):
- **Decimal point**: `locale.localeconv()["decimal_point"]` (e.g., `.` in en_US, `,` in de_DE)
- **Formatting**: `"%.2f" % value` with locale decimal char substitution

### Future Considerations

- **Currency symbols**: Currently not displayed in controls (the label provides context). Could add optional prefix/suffix rendering.
- **Negative amounts**: Currently `allowNegative=False`. Could be added if budget scenarios require it.
- **Thousands grouping during input**: Current control groups digits; the TextCtrl replacement could add this on focus-loss formatting.
- **Alternative: `wx.SpinCtrlDouble`**: A native wxPython widget that enforces numeric input with configurable decimal places. However, the spinner UI (up/down arrows) is inappropriate for dollar amount fields.

## Usage Sites

| File | Widget | Field | Editable |
|------|--------|-------|----------|
| `taskcoachlib/gui/dialog/editor.py` | `AmountEntry` → `CurrencyCtrl` | Hourly fee | Yes |
| `taskcoachlib/gui/dialog/editor.py` | `AmountEntry` → `CurrencyCtrl` | Fixed fee | Yes |
| `taskcoachlib/gui/dialog/editor.py` | `AmountEntry` → `CurrencyCtrl` | Revenue | No (read-only) |

## Files

| File | Purpose |
|------|---------|
| `taskcoachlib/widgets/currencyctrl.py` | `CurrencyCtrl` + `CurrencyValidator` (replacement) |
| `taskcoachlib/widgets/masked.py` | Legacy `AmountCtrl` (wraps `wx.lib.masked.NumCtrl`) — no longer used by AmountEntry |
| `taskcoachlib/gui/dialog/entry.py` | `AmountEntry` (wraps `CurrencyCtrl` in panel) |
| `taskcoachlib/gui/dialog/editor.py` | Budget tab uses `AmountEntry` for fee/revenue fields |
