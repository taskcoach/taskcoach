"""
Task Coach - Your friendly task manager
Copyright (C) 2004-2016 Task Coach developers <developers@taskcoach.org>

Task Coach is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Task Coach is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import wx, os, locale
from taskcoachlib import patterns, operating_system
from . import po2dict


def _log_i18n(msg):
    """Log i18n-related messages for debugging."""
    print(f"[i18n] {msg}")


# Directory containing .po files
_LOCALES_DIR = os.path.join(os.path.dirname(__file__), "locales")


class Translator(metaclass=patterns.Singleton):
    def __init__(self, language):
        self.__locale = None
        self.__language = {}
        self.__encoding = "UTF-8"
        self._locale_ok = True  # Track if locale was set successfully
        _log_i18n(f"Initializing Translator with language: {language!r}")

        self._loadTranslation(language)
        self._setLocale(language)

    @property
    def locale_ok(self):
        """Return True if the system locale was set successfully."""
        return self._locale_ok

    def _loadTranslation(self, language):
        """Load translation from .po file in locales directory."""
        # If a full path to .po file is given, load it directly
        if language.endswith(".po") and os.path.isfile(language):
            self._loadPoFile(language)
            return

        # Try to find .po file in locales directory
        for lang_code in self._localeStrings(language):
            po_file = os.path.join(_LOCALES_DIR, f"{lang_code}.po")
            if os.path.isfile(po_file):
                self._loadPoFile(po_file)
                _log_i18n(f"Loaded translation: {po_file}")
                return
            _log_i18n(f"Translation file not found: {po_file}")

        _log_i18n(f"No translation found for '{language}'. Using English.")

    def _loadPoFile(self, poFilename):
        """Load translation directly from a .po file."""
        try:
            translations, encoding = po2dict.parse(poFilename)
            self.__language = translations
            self.__encoding = encoding
        except Exception as e:
            _log_i18n(f"Failed to load {poFilename}: {e}")

    def _setLocale(self, language):
        """Try to set the locale, trying possibly multiple localeStrings.

        IMPORTANT: wx.Locale objects must be properly managed to avoid segfaults.
        The old locale must be deleted before creating a new one.
        See: https://discuss.wxpython.org/t/questions-on-the-locale-issue/36084
        """
        _log_i18n(f"Setting locale for language: {language!r}")

        if not operating_system.isGTK():
            try:
                locale.setlocale(locale.LC_ALL, "")
                _log_i18n("Set Python locale to system default (non-GTK)")
            except locale.Error as e:
                _log_i18n(f"Failed to set Python locale: {e}")

        # Set the wxPython locale:
        locale_set = False
        for localeString in self._localeStrings(language):
            _log_i18n(f"Trying wx.Locale for: {localeString!r}")
            languageInfo = wx.Locale.FindLanguageInfo(localeString)
            if languageInfo:
                _log_i18n(f"Found wx language info: {languageInfo.CanonicalName} "
                          f"(Language={languageInfo.Language})")

                # CRITICAL: Delete old locale before creating new one to prevent
                # segfaults. The C++ locale object must be destroyed first.
                if self.__locale is not None:
                    _log_i18n("Deleting previous wx.Locale object")
                    del self.__locale
                    self.__locale = None

                try:
                    # Suppress wx warning dialog if locale can't be fully set
                    log_null = wx.LogNull()
                    self.__locale = wx.Locale(languageInfo.Language)
                    del log_null
                    # Check if locale was properly initialized
                    if not self.__locale.IsOk():
                        _log_i18n(f"wx.Locale created but IsOk() returned False")
                        self._locale_ok = False
                    else:
                        _log_i18n(f"Created wx.Locale successfully")

                    # Add the wxWidgets message catalog. This is really only for
                    # py2exe'ified versions, but it doesn't seem to hurt on other
                    # platforms...
                    localeDir = os.path.join(
                        wx.StandardPaths.Get().GetResourcesDir(), "locale"
                    )
                    self.__locale.AddCatalogLookupPathPrefix(localeDir)
                    self.__locale.AddCatalog("wxstd")
                    locale_set = True
                    break
                except Exception as e:
                    _log_i18n(f"Failed to create wx.Locale for {localeString}: {e}")
                    self.__locale = None
            else:
                _log_i18n(f"No wx language info found for: {localeString!r}")

        if not locale_set:
            _log_i18n(f"WARNING: Could not set wx.Locale for language '{language}'")
            self._locale_ok = False

        if operating_system.isGTK():
            try:
                locale.setlocale(locale.LC_ALL, "")
                _log_i18n("Set Python locale to system default (GTK)")
            except locale.Error as e:
                # Mmmh. wx will display a message box later, so don't do anything.
                _log_i18n(f"Failed to set Python locale on GTK: {e}")

        self._fixBrokenLocales()

    def _fixBrokenLocales(self):
        try:
            current_language = locale.getlocale(locale.LC_TIME)[0]
        except Exception as e:
            _log_i18n(f"Failed to get LC_TIME locale: {e}")
            return

        if current_language and "_NO" in current_language:
            _log_i18n(f"Detected problematic Norwegian locale: {current_language}")
            # nb_BO and ny_NO cause crashes in the wx.DatePicker. Set the
            # time part of the locale to some other locale. Since we don't
            # know which ones are available we try a few. First we try the
            # default locale of the user (''). It's probably *_NO, but it
            # might be some other language so we try just in case. Then we try
            # English (GB) so the user at least gets a European date and time
            # format if that works. If all else fails we use the default
            # 'C' locale.
            for lang in ["", "en_GB.utf8", "C"]:
                try:
                    locale.setlocale(locale.LC_TIME, lang)
                    _log_i18n(f"Set LC_TIME to: {lang!r}")
                except locale.Error as e:
                    _log_i18n(f"Failed to set LC_TIME to {lang!r}: {e}")
                    continue
                try:
                    current_language = locale.getlocale(locale.LC_TIME)[0]
                except Exception:
                    break
                if current_language and "_NO" in current_language:
                    continue
                else:
                    break

    def _localeStrings(self, language):
        """Extract language and language_country from language if possible."""
        localeStrings = []
        if language:
            localeStrings.append(language)
            if "_" in language:
                localeStrings.append(language.split("_")[0])
        return localeStrings

    def translate(self, string):
        """Look up string in the current language dictionary. Return the
        passed string if no language dictionary is available or if the
        dictionary doesn't contain the string."""
        return self.__language.get(string, string)


def currentLanguageIsRightToLeft():
    return wx.GetApp().GetLayoutDirection() == wx.Layout_RightToLeft


def isCurrentLocaleOk():
    """Return True if the current locale was set up successfully."""
    try:
        return Translator._instance.locale_ok
    except AttributeError:
        return True  # Not initialized yet, assume OK


def isLocaleAvailable(language_code):
    """Check if a locale is available on the system for the given language code.

    This tests whether wx.Locale can be created for this language without
    actually creating one (which would affect the running application).
    """
    if not language_code:
        return True  # Default/empty means system locale

    # Get locale strings to try (e.g., "tr_TR" -> ["tr_TR", "tr"])
    locale_strings = [language_code]
    if "_" in language_code:
        locale_strings.append(language_code.split("_")[0])

    for locale_string in locale_strings:
        language_info = wx.Locale.FindLanguageInfo(locale_string)
        if language_info:
            # wx knows about this language, but is the system locale installed?
            # Try to check if the locale exists on the system
            try:
                # Test if we can set this locale temporarily
                test_locale_str = language_info.CanonicalName
                # Try common locale name formats
                for suffix in ['.UTF-8', '.utf8', '']:
                    try:
                        locale.setlocale(locale.LC_ALL, test_locale_str + suffix)
                        locale.setlocale(locale.LC_ALL, '')  # Reset
                        return True
                    except locale.Error:
                        continue
            except Exception:
                pass

    return False


def _get_system_language():
    """Get the system language from environment or locale settings.

    Note: locale.getdefaultlocale() is deprecated since Python 3.11 and
    doesn't reliably read LANG environment variable on Linux. We check
    environment variables directly first.
    """
    # Check LANG and LC_ALL environment variables first
    lang = os.environ.get('LANG', os.environ.get('LC_ALL', ''))
    if lang:
        # Strip encoding suffix (e.g., "de_DE.UTF-8" -> "de_DE")
        lang = lang.split('.')[0]
        if lang and lang != "C" and lang != "POSIX":
            return lang

    # Fallback to locale.getlocale()
    try:
        lang = locale.getlocale(locale.LC_MESSAGES)[0]
        if lang and lang != "C" and lang != "POSIX":
            return lang
    except Exception:
        pass

    # Final fallback
    return "en_US"


def translate(string):
    return Translator(_get_system_language()).translate(string)


_ = translate  # This prevents a warning from pygettext.py

# Inject into builtins for 3rdparty packages
import builtins

builtins.__dict__["_"] = _
