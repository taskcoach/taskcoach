# Translation Guide for Task Coach

This document explains how translations work in Task Coach and how to contribute translations.

## Overview

Task Coach uses GNU gettext `.po` files for translations. The app loads these files directly at startup - no compilation step required.

**Current status:** 53 languages supported, stored in `taskcoachlib/i18n/locales/`

## How It Works

### At Runtime

1. App starts → determines language from settings or system
2. Loads single `.po` file (e.g., `fr.po` for French)
3. `_("string")` calls look up translations in a dictionary
4. Untranslated entries (where `msgstr` is an empty string `""`) fall back to English

### File Locations

| File | Purpose |
|------|---------|
| `taskcoachlib/i18n/locales/*.po` | Translation files (53 languages) |
| `i18n.in/messages.pot` | Template with all translatable strings |
| `taskcoachlib/i18n/po2dict.py` | Parser that loads .po files |
| `taskcoachlib/i18n/__init__.py` | Translator class |

## For Translators

### Updating an Existing Translation

1. Find your language file in `taskcoachlib/i18n/locales/` (e.g., `fr.po`)
2. Open with a text editor or [Poedit](https://poedit.net/)
3. Find untranslated entries (empty `msgstr`)
4. Fill in translations
5. Submit a pull request

### .po File Format

```po
# Comment about context
#: taskcoachlib/gui/dialog/preferences.py:682
msgid "Changing the language requires a restart of %s."
msgstr "Le changement de langue nécessite un redémarrage de %s."
```

- `msgid` = English source text (do not modify)
- `msgstr` = Your translation
- `%s`, `%(name)s` = Placeholders (must be preserved)

### Empty and Whitespace-Only Translations

How the parser handles empty or whitespace-only `msgstr` values:

| `msgstr` value | Result |
|----------------|--------|
| `""` (empty) | Falls back to English |
| `"   "` (spaces only) | Displays spaces (likely a mistake) |
| `"\t"` (tab only) | Displays tab (likely a mistake) |
| `"\n"` (newline only) | Displays newline (likely a mistake) |

Only truly empty strings (`""`) fall back to English. Whitespace-only strings are treated as valid translations.

**Best practice:** Use a .po editor like [Poedit](https://poedit.net/) which prevents these errors.

### Creating a New Translation

1. Copy `i18n.in/messages.pot` to `taskcoachlib/i18n/locales/<lang>.po`
2. Update the header (Language, translator info)
3. Translate all `msgstr` entries
4. Submit a pull request

### Translation Tools

- **[Poedit](https://poedit.net/)** - GUI editor for .po files
- **Text editor** - .po files are plain text
- **`msgmerge`** - Merge template updates into existing translations

## For Developers

### Marking Strings for Translation

Use the `_()` function:

```python
from taskcoachlib.i18n import _

message = _("This text will be translated")
error = _("File not found: %(filename)s") % {"filename": path}
```

### Extracting New Strings

After adding new translatable strings, update the template:

```bash
# Extract all _("string") calls
find taskcoachlib -name "*.py" -not -path "*/i18n/locales/*" > /tmp/pyfiles.txt
xgettext --language=Python --keyword=_ --output=i18n.in/messages.pot \
    --from-code=UTF-8 --files-from=/tmp/pyfiles.txt
```

### Updating All Translation Files

After extracting new strings, merge into existing translations:

```bash
cd taskcoachlib/i18n/locales
for po in *.po; do
    msgmerge --update "$po" ../../../i18n.in/messages.pot
done
```

This adds new strings (untranslated) and marks removed strings as obsolete.

### Testing a Translation

```bash
# Run with specific language
python taskcoach.py --language fr_FR

# Or load a .po file directly
python taskcoach.py --pofile path/to/test.po
```

## Locale vs Translation

| Aspect | Translation | Locale |
|--------|-------------|--------|
| What it is | UI text in `.po` files | System date/number formats |
| Failure mode | Falls back to English | Warning in preferences |
| Affects | Menu items, labels, messages | Date pickers, time display |
| Requirement | Always works | Requires system locale installed |

If you see a warning about locale not matching, it means:
- Your translations ARE working
- System date/time formats may appear in your system's locale instead of chosen language

## Submitting Translations

1. Fork the repository
2. Make your changes to `.po` files
3. Test with `python taskcoach.py --language <code>`
4. Submit a pull request

Or open an issue describing what needs translation help.

## Language Codes

Task Coach uses locale codes in the format `language_COUNTRY` (e.g., `pt_BR`, `zh_CN`, `en_GB`).

References:
- [SimpleLocalize Locale List](https://simplelocalize.io/data/locales/)
- [Science.co.il Locale Codes](https://www.science.co.il/language/Locale-codes.php)
- [Fincher.org Country Language List](https://www.fincher.org/Utilities/CountryLanguageList.shtml)

Available languages are in `taskcoachlib/i18n/locales/`.
