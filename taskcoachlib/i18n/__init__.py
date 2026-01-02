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

import wx, os, sys, importlib, tempfile, locale, gettext
from taskcoachlib import patterns, operating_system
from . import po2dict


def _log_i18n(msg):
    """Log i18n-related messages for debugging."""
    print(f"[i18n] {msg}")


class Translator(metaclass=patterns.Singleton):
    def __init__(self, language):
        self.__locale = None  # Initialize to None for proper lifecycle management
        _log_i18n(f"Initializing Translator with language: {language!r}")

        load = (
            self._loadPoFile if language.endswith(".po") else self._loadModule
        )
        module, language = load(language)
        self._installModule(module)
        self._setLocale(language)

    def _loadPoFile(self, poFilename):
        """Load the translation from a .po file by creating a python
        module with po2dict and them importing that module."""
        language = self._languageFromPoFilename(poFilename)
        pyFilename = self._tmpPyFilename()
        po2dict.make(poFilename, pyFilename)
        module = importlib.load_source(language, pyFilename)
        os.remove(pyFilename)
        return module, language

    def _tmpPyFilename(self):
        """Return a filename of a (closed) temporary .py file."""
        tmpFile = tempfile.NamedTemporaryFile(suffix=".py")
        pyFilename = tmpFile.name
        tmpFile.close()
        return pyFilename

    def _loadModule(self, language):
        """Load the translation from a python module that has been
        created from a .po file with po2dict before."""
        module = None
        tried_modules = []
        for moduleName in self._localeStrings(language):
            tried_modules.append(moduleName)
            try:
                module = __import__(moduleName, globals())
                _log_i18n(f"Loaded translation module: {moduleName}")
                break
            except ImportError as e:
                _log_i18n(f"Could not load translation module '{moduleName}': {e}")
                module = None
        if module is None:
            _log_i18n(f"No translation module found for language '{language}' "
                      f"(tried: {tried_modules}). Using English.")
        return module, language

    def _installModule(self, module):
        """Make the module's translation dictionary and encoding available."""
        # pylint: disable=W0201
        if module:
            self.__language = module.dict
            self.__encoding = module.encoding

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
                    self.__locale = wx.Locale(languageInfo.Language)
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

    def _languageFromPoFilename(self, poFilename):
        return os.path.splitext(os.path.basename(poFilename))[0]

    def translate(self, string):
        """Look up string in the current language dictionary. Return the
        passed string if no language dictionary is available or if the
        dictionary doesn't contain the string."""
        try:
            return self.__language[string].decode(self.__encoding)
        except (AttributeError, KeyError):
            return string


def currentLanguageIsRightToLeft():
    return wx.GetApp().GetLayoutDirection() == wx.Layout_RightToLeft


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
