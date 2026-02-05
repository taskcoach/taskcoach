# Locale Handling

Unified reference for all locale and regional settings in the application.

## Index

- [Three-Layer Pattern](#three-layer-pattern)
- [Settings Keys](#settings-keys)
- [Detection Mechanisms](#detection-mechanisms)
- [Data vs Display](#data-vs-display)
- [Restart Requirement](#restart-requirement)
- [Locale Initialization](#locale-initialization)
- [Cross-References](#cross-references)

---

## Three-Layer Pattern

All locale concerns follow the same three-layer access pattern:

1. **Detection function** — pure locale detection, no settings involved.
   Returns what the system locale provides.
2. **Settings function** — reads the user preference only. Returns empty
   string if automatic (no override).
3. **Effective function** — combines both: setting → detection → default.
   This is what controls and renderers call.

Example (date format):
```
getDetectedLocaleDateFormat()     # Layer 1: strftime("%x") probe
getDateFormatFromSettings()       # Layer 2: settings.Settings().get("view", "dateformat")
getEffectiveDateFormat()          # Layer 3: setting → detection → ISO default
```

Example (decimal separator):
```
_get_locale_decimal_char()        # Layer 1: locale.localeconv()["decimal_point"]
_get_configured_decimal_char()    # Layer 3: setting → locale → "."
```

---

## Settings Keys

| Setting key | Section | Values | Detection method | Default | File |
|---|---|---|---|---|---|
| `language_set_by_user` | `view` | locale code / `""` | env vars + `locale.getlocale` | `"en_US"` | `application.py` |
| `dateformat` | `view` | `"YMD-"`, `"MDY/"`, `"DMY/"`, `"DMY."`, `"YMD/"`, `""` | `strftime("%x")` probe | ISO `YYYY-MM-DD` | `maskedtimectrl.py` |
| `timeformat` | `view` | `"24"`, `"12"`, `""` | `strftime("%X")` AM/PM check | `"24"` | `maskedtimectrl.py` |
| `decimal_separator` | `view` | `"."`, `","`, `""` | `locale.localeconv()["decimal_point"]` | `"."` | `numericctrl.py` |
| `currency_decimal_places` | `view` | `"0"`, `"2"`, `"3"`, `""` | `locale.localeconv()["frac_digits"]` | `2` | `currencyctrl.py` |

All defaults defined in `taskcoachlib/config/defaults.py`, `view` section.

---

## Detection Mechanisms

### strftime probing (date/time)

Formats a test date/time with locale-aware `strftime` directives and parses
the output to detect field order, separator, and 12/24h mode.

- **Date:** `datetime.date(3333, 11, 22).strftime("%x")` — searches for
  positions of year/month/day in output to determine field order and separator.
- **Time:** `datetime.time(14, 30).strftime("%X")` — checks for AM/PM
  indicators via `strftime("%p")`.
- **File:** `taskcoachlib/widgets/maskedtimectrl.py`

### locale.localeconv() dict (numeric/currency)

Returns a dict with numeric formatting conventions. Key fields:

| Field | Meaning | Example (en_US) | Example (de_DE) | Sentinel |
|---|---|---|---|---|
| `decimal_point` | Decimal separator | `"."` | `","` | `""` → fallback to `"."` |
| `frac_digits` | Currency decimal places | `2` | `2` | `127` (CHAR_MAX) → fallback to `2` |
| `thousands_sep` | Thousands separator | `","` | `"."` | Can be empty or non-ASCII |
| `grouping` | Grouping pattern | `[3, 3, 0]` | `[3, 3, 0]` | — |

- **Files:** `numericctrl.py`, `currencyctrl.py`, `masked.py`

### Environment variables + locale.getlocale() (language)

Cascading checks for language selection:

1. Command-line options (`--language`, `--pofile`)
2. User preference (`view/language_set_by_user`)
3. External setting (`view/language`)
4. `LANG` environment variable (strip `.UTF-8` suffix)
5. `LC_ALL` environment variable
6. `locale.getlocale(locale.LC_MESSAGES)`
7. Final fallback: `"en_US"`

- **Files:** `application.py`, `i18n/__init__.py`

---

## Data vs Display

**Locale is UI-only.** Domain and persistence always use Python defaults:

- **Numeric:** Python `float` with period decimal. `str(25.5)` → `"25.5"`.
- **Date/time:** Python `datetime` objects. XML uses ISO-like format.
- **The control is the locale boundary.** `NumericCtrl.GetValue()` returns
  Python float (period). `NumericCtrl.SetValue(float)` displays with locale
  decimal. Same for `DateComboRouterCtrl`, `TimeCtrl`.

Data flow example (German locale, comma decimal):
```
User types "25,50"
  → CurrencyCtrl displays "25,50" (locale)
  → CurrencyCtrl.GetValue() → 25.5 (Python float, period)
    → AttributeSync → domain → task.setHourlyFee(25.5)
      → XML writer: str(25.5) → "25.5" (period, always)
```

---

## Restart Requirement

Format changes (date, time, decimal separator, currency decimal places)
require a restart because:

- `render.py` compiles format strings once at module load time
- Controls are created with the effective format at construction time
- Changing the format setting does not retroactively update existing controls

The Regional preferences page shows a restart warning when any format setting
is changed from its original value.

---

## Locale Initialization

At startup, `Application.__init_language()` calls `i18n.Translator(language)`
which:

1. Calls `locale.setlocale(locale.LC_ALL, ...)` with the resolved locale
2. Creates a `wx.Locale` instance for wxWidgets
3. Loads the gettext translation catalog
4. Works around broken locales (e.g. Norwegian `nb_NO` vs `no_NO`)

After this, `locale.localeconv()` returns the correct values for the active
locale, and `strftime` uses the locale's date/time formatting.

---

## Cross-References

- **Date/time controls:** [DATETIME_CONTROLS.md](DATETIME_CONTROLS.md) —
  `DateComboRouterCtrl`, `TimeCtrl`, `DateTimeComboCtrl`, locale detection via strftime
- **Numeric controls:** [NUMERIC_CONTROLS.md](NUMERIC_CONTROLS.md) —
  `NumericCtrl`, blur validation, decimal separator handling
- **Monetary controls:** [MONETARY_CONTROLS.md](MONETARY_CONTROLS.md) —
  `CurrencyCtrl`, currency decimal places from locale
- **Attribute sync:** [ATTRIBUTE_PATTERN.md](ATTRIBUTE_PATTERN.md) —
  Layer 2 (UI↔Domain sync), `EVT_VALUE_CHANGED` pattern
