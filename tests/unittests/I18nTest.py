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

import os
import types
from unittest import mock

import test
from taskcoachlib import i18n, operating_system


class SystemLanguageTest(test.TestCase):
    """The language the application starts in when the user picked
    none (docs/LOCALE.md)."""

    def language(self, windows, environment, **locale_functions):
        with mock.patch.object(
            operating_system, "isWindows", return_value=windows
        ), mock.patch.dict(os.environ, environment):
            return i18n.system_language(
                types.SimpleNamespace(**locale_functions)
            )

    def test_windows_reads_its_regional_format(self):
        # Windows sets no LANG, and Python has no LC_MESSAGES there
        language = self.language(
            True,
            {"LC_ALL": "", "LC_MESSAGES": "", "LANG": "de_DE.UTF-8"},
            getdefaultlocale=lambda: ("pt_BR", "cp1252"),
        )
        self.assertEqual("pt_BR", language)

    def test_windows_without_a_region_names_none(self):
        language = self.language(
            True, {}, getdefaultlocale=lambda: (None, None)
        )
        self.assertIsNone(language)

    def test_elsewhere_the_first_variable_set_names_it(self):
        language = self.language(
            False,
            {"LC_ALL": "", "LC_MESSAGES": "fr_FR.UTF-8", "LANG": "en_US"},
        )
        self.assertEqual("fr_FR", language)

    def test_elsewhere_without_variables_the_locale_names_it(self):
        language = self.language(
            False,
            {"LC_ALL": "", "LC_MESSAGES": "", "LANG": "C"},
            LC_MESSAGES=5,
            getlocale=lambda category: ("es_ES", "UTF-8"),
        )
        self.assertEqual("es_ES", language)


class MacSystemLanguageTest(test.TestCase):
    """Started from the Finder, a Mac app has no locale variables and
    the bundle's launcher (py2app) sets the C locale to en_US: the
    language is the first of macOS's preferred languages."""

    def language(self, environment, preferred):
        bundle_locale = types.SimpleNamespace(
            LC_MESSAGES=5, getlocale=lambda category: ("en_US", "UTF-8")
        )
        cleared = {"LC_ALL": "", "LC_MESSAGES": "", "LANG": ""}
        with mock.patch.object(
            operating_system, "isWindows", return_value=False
        ), mock.patch.object(
            operating_system, "isMac", return_value=True
        ), mock.patch.object(
            i18n, "_mac_preferred_language", return_value=preferred
        ), mock.patch.dict(
            os.environ, dict(cleared, **environment)
        ):
            return i18n.system_language(bundle_locale)

    def test_the_first_preferred_language_names_it(self):
        self.assertEqual("fr_CA", self.language({}, "fr-CA"))

    def test_a_language_without_region(self):
        self.assertEqual("pt", self.language({}, "pt"))

    def test_started_from_a_terminal_its_variables_name_it(self):
        self.assertEqual(
            "es_MX", self.language({"LANG": "es_MX.UTF-8"}, "fr-CA")
        )

    def test_no_preferred_language_leaves_the_locale(self):
        self.assertEqual("en_US", self.language({}, None))

    def test_reading_it_off_macos_names_none(self):
        self.assertIsNone(i18n._mac_preferred_language())

    def test_it_is_read_once(self):
        # Every string translated asks for the language
        read = i18n._mac_preferred_language
        read.cache_clear()
        self.addCleanup(read.cache_clear)
        with mock.patch.object(
            i18n.ctypes.cdll, "LoadLibrary", side_effect=OSError("none")
        ) as load:
            read()
            read()
        self.assertEqual(1, load.call_count)
