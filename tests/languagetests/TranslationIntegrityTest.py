# -*- coding: UTF-8 -*-

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

from taskcoachlib import meta
from taskcoachlib.i18n import po2dict
import string  # pylint: disable=W0402
import re
import test
import os
import shutil
import tempfile

HERE = os.path.dirname(__file__)
# Generated with xgettext (docs/TRANSLATIONS.md)
TEMPLATE = os.path.join(HERE, "..", "..", "i18n.in", "messages.pot")
LOCALES = os.path.join(HERE, "..", "..", "taskcoachlib", "i18n", "locales")


class TranslationIntegrityTestsMixin(object):
    """Unittests for translations. This class is subclassed below for each
    translated string in each language."""

    conversion_specification_re = re.compile(r"%\(\w+\)[sd]")

    @staticmethod
    def findMatches(regex, search_string):
        matches = set()
        for match in re.findall(regex, search_string):
            matches.add(match)
        return matches

    def test_matching_conversion_specifications(self):
        regex = self.conversion_specification_re
        matches_english = self.findMatches(regex, self.englishString)
        matches_translation = self.findMatches(regex, self.translatedString)
        self.assertEqual(
            matches_english, matches_translation, self.englishString
        )

    def test_matching_non_literals(self):
        for symbol in "\t", "|", "%s", "%d", "%.2f":
            self.assertEqual(
                self.englishString.count(symbol),
                self.translatedString.count(symbol),
                "Symbol ('%s') doesn't match for '%s' and '%s'"
                % (symbol, self.englishString, self.translatedString),
            )

    def test_matching_ampersands(self):
        # If the original string contains zero or one ampersands, it may be
        # an accelerator. In that case, we don't require the translated string
        # to have an accelerator as well, because many translators don't use
        # it and it doesn't break the application. However, if the original
        # string contains more than one ampersand it's probably HTML. In that
        # case we do require the number of ampersands to match exactly in the
        # original and translated string.
        translated_string = self.removeUmlauts(self.translatedString)
        nr_english_ampersand = self.englishString.count("&")
        nr_translated_ampersand = translated_string.count("&")
        if nr_english_ampersand <= 1 and "\n" not in self.englishString:
            self.assertTrue(
                nr_translated_ampersand in [0, 1],
                "'%s' has more than one '&'" % self.translatedString,
            )
        else:
            self.assertEqual(
                nr_english_ampersand,
                nr_translated_ampersand,
                "'%s' has more or less '&'s than '%s'"
                % (self.translatedString, self.englishString),
            )

    usedShortcuts = dict()
    # Some keyboard shortcuts are used more than once, list those here:
    maxShortcuts = {"Ctrl-RETURN": 2, "Shift+Ctrl+T": 3}

    def test_unique_short_cut(self):
        if "\t" in self.translatedString:
            shortcut = self.translatedString.split("\t")[1]
            shortcut_key = shortcut, self.language
            times_used = self.usedShortcuts.get(shortcut_key, 0)
            times_allowed = self.maxShortcuts.get(shortcut, 1)
            self.assertFalse(
                times_used > times_allowed,
                "Shortcut ('%s') used more "
                "than once in language %s." % shortcut_key,
            )
            self.usedShortcuts[shortcut_key] = times_used + 1

    def test_matching_short_cut(self):
        for shortcut_prefix in (
            "Ctrl+",
            "Ctrl-",
            "Shift+",
            "Shift-",
            "Alt+",
            "Alt-",
            "Shift+Ctrl+",
            "Shift-Ctrl-",
            "Shift+Alt+",
            "Shift-Alt-",
        ):
            self.assertEqual(
                self.englishString.count("\t" + shortcut_prefix),
                self.translatedString.count("\t" + shortcut_prefix),
                "Shortcut prefix ('%s') doesn't match for '%s' "
                "and '%s'"
                % (shortcut_prefix, self.englishString, self.translatedString),
            )

    def test_short_cut_is_ascii(self):
        """Test that the translated short cut key is using ASCII only."""
        if "\t" in self.translatedString:
            shortcut = set(self.translatedString.split("\t")[1])
            self.assertTrue(
                shortcut & set(string.ascii_letters + string.digits)
            )

    @staticmethod
    def ellipsisCount(text):
        return text.count("...") + text.count("…")

    def test_matching_ellipses(self):
        self.assertEqual(
            self.ellipsisCount(self.englishString),
            self.ellipsisCount(self.translatedString),
            "Ellipses ('...') don't match for '%s' and '%s'"
            % (self.englishString, self.translatedString),
        )

    umlautRE = re.compile(r"&[A-Za-z]uml;")

    @classmethod
    def removeUmlauts(cls, text):
        return re.sub(cls.umlautRE, "", text)


class TranslationCoverageTestsMixin(object):
    def setUp(self):
        super().setUp()
        if not self.strings:
            self.skipTest("no template: generate %s" % TEMPLATE)

    def test_not_complete(self):
        if self.enabled:
            percent_done = 100.0 * len(self.translation) / len(self.strings)
            self.assertGreaterEqual(
                percent_done,
                90.0,
                "Translation for %s is only %.2f%% complete"
                % (self.language, percent_done),
            )

    def test_complete(self):
        if not self.enabled:
            percent_done = 100.0 * len(self.translation) / len(self.strings)
            self.assertLess(
                percent_done,
                90.0,
                "Translation for %s is %.2f%% complete but disabled"
                % (self.language, percent_done),
            )


def install_all_test_case_classes():
    all_strings = template_strings()
    for language, enabled in getLanguages():
        install_test_case_classes(language, enabled, all_strings)


def template_strings():
    """Every translatable string: the template's msgids, or none when
    the template was not generated."""
    if not os.path.exists(TEMPLATE):
        return set()
    with tempfile.TemporaryDirectory() as folder:
        copy = os.path.join(folder, "messages.po")  # parse() reads .po
        shutil.copyfile(TEMPLATE, copy)
        po2dict.STRINGS.clear()
        po2dict.parse(copy)
    return po2dict.STRINGS - {""}  # Less the header


def getLanguages():
    return [
        (language, enabled)
        for language, enabled in list(meta.data.languages.values())
        if language is not None
    ]


def install_test_case_classes(language, enabled, all_strings):
    # The .po files are read at startup, as the app does
    translation, _encoding = po2dict.parse(
        os.path.join(LOCALES, language + ".po")
    )
    for english_string, translated_string in translation.items():
        installTranslationTestCaseClass(
            language, english_string, translated_string
        )
    installLanguageTestCaseClass(language, enabled, translation, all_strings)


def installTranslationTestCaseClass(
    language, english_string, translated_string
):
    test_case_class_name = translationTestCaseClassName(
        language, english_string
    )
    test_case_class = translationTestCaseClass(
        test_case_class_name, language, english_string, translated_string
    )
    globals()[test_case_class_name] = test_case_class


def installLanguageTestCaseClass(language, enabled, translation, all_strings):
    test_case_class_name = languageTestCaseClassName(language)
    test_case_class = languageTestCaseClass(
        test_case_class_name, language, enabled, translation, all_strings
    )
    globals()[test_case_class_name] = test_case_class


def translationTestCaseClassName(
    language, english_string, prefix="TranslationIntegrityTest"
):
    """Generate a class name for the test case class based on the language
    and the English string."""
    # Make sure we only use characters allowed in Python identifiers:
    english_string = english_string.replace(" ", "_")
    allowable_characters = string.ascii_letters + string.digits + "_"
    english_string = "".join(
        [char for char in english_string if char in allowable_characters]
    )
    class_name = "%s_%s_%s" % (prefix, language, english_string)
    count = 0
    while class_name in globals():  # Make sure className is unique
        count += 1
        class_name = "%s_%s_%s_%d" % (prefix, language, english_string, count)
    return class_name


def languageTestCaseClassName(language, prefix="TranslationCoverageTests"):
    class_name = "%s_%s" % (prefix, language)
    count = 0
    while class_name in globals():
        count += 1
        class_name = "%s_%s_%s" % (prefix, language, count)
    return class_name


def translationTestCaseClass(
    class_name, language, english_string, translated_string
):
    class_ = type(
        class_name, (TranslationIntegrityTestsMixin, test.TestCase), {}
    )
    class_.language = language
    class_.englishString = english_string
    class_.translatedString = translated_string
    return class_


def languageTestCaseClass(
    class_name, language, enabled, translation, all_strings
):
    class_ = type(
        class_name, (TranslationCoverageTestsMixin, test.TestCase), dict()
    )
    class_.translation = translation
    class_.enabled = enabled
    class_.strings = all_strings
    class_.language = language
    return class_


# Create all test cases and install them in the global name space:
install_all_test_case_classes()
