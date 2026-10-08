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

The settings functions read the application's one settings object
through the settings module ([SETTINGS.md](SETTINGS.md#usage)):
the date and time formats as the application started with them, as the
lists show dates (a change applies after a restart, as Preferences
says), the other options as they are now.

Example (date format):
```
getDetectedLocaleDateFormat()     # Layer 1: strftime("%x") probe
getDateFormatFromSettings()       # Layer 2: settings.get("view", "dateformat"), as at start
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
| `language_set_by_user` | `view` | locale code / `""` | Windows: its regional format; elsewhere env vars + `locale.getlocale` | `"en_US"` | `application.py` |
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

- **Files:** `numericctrl.py`, `currencyctrl.py`

### System language

Cascading checks for language selection:

1. Command-line options (`--language`, `--pofile`)
2. User preference (`view/language_set_by_user`)
3. External setting (`view/language`)
4. The system's language, below
5. Final fallback: `"en_US"`

Step 4 is `i18n.system_language()`, the one reading of the system's
language: the spell check's default language and the strings
translated before the translator exists use it too.

- **Windows:** its "Regional format", as `locale.getdefaultlocale()`
  reads it from Windows, e.g. `pt_BR`. Windows sets no `LANG` and
  Python has no `LC_MESSAGES` there
  ([locale docs](https://docs.python.org/3/library/locale.html#locale.LC_MESSAGES)).
  From 2.0.0.101 to 2.0.3.3 only the environment was read, so Windows
  started in English
  ([#484](https://github.com/taskcoach/taskcoach/issues/484)).
  - Python's own call, not a workaround: nothing to revert. Python
    deprecated it in 3.11, then took it back as the only way to name
    the Windows locale this way
    ([gh-130796](https://github.com/python/cpython/issues/130796)):
    no longer deprecated from 3.13.15, 3.14.7 and 3.15 (the Windows
    build uses 3.13.16). 3.11 to 3.13.14 work, with a
    `DeprecationWarning` Python hides by default.
  - It asks Windows (`GetLocaleInfoA`, `LOCALE_USER_DEFAULT`): the
    regional format, not the display language. Nothing found starts
    in English; a region without a translation, in its language's,
    else English.
- **Elsewhere:** the environment, in POSIX order: the first set of
  `LC_ALL`, `LC_MESSAGES` and `LANG` (encoding suffix such as
  `.UTF-8` stripped; `C` or `POSIX` goes on), else
  `locale.getlocale(locale.LC_MESSAGES)`. `getdefaultlocale()` reads
  `LC_CTYPE` instead of `LC_MESSAGES`.

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
    → AttributeSync → domain → task.set_hourly_fee(25.5)
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

On Windows the `wx.Locale` comes last, so the detected formats are
those of the language; with the language detected, of the region.
On GTK `setlocale(LC_ALL, "")` comes last: those of the system.

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
