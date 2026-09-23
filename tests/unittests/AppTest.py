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

import test
import wx
from taskcoachlib import meta, application, config


class DummyOptions(object):
    pofile = None
    language = None


class DummyLocale(object):
    def __init__(self, language="C"):
        self.language = language

    def getdefaultlocale(self):
        return self.language, None


class AppTests(test.TestCase):
    def setUp(self):
        super().setUp()
        self.settings = config.Settings(load=False)
        self.options = DummyOptions()

    def testAppProperties(self):
        import locale

        if locale.getdefaultlocale()[0] != "en_US":
            # Somehow wx displays an error dialog box if en_US is not installed, when
            # quit_application() calls ProcessIdle and I don't know how to get rid of it.
            # I don't know how to find out if en_US is installed either, so skip if
            # it's not the default.
            self.skipTest("Locale is not en_US")
        else:
            # Normally I prefer one assert per test, but creating the app is
            # expensive, so we do all the queries in one test method.
            app = application.Application(
                load_settings=False, load_task_file=False
            )
            wxApp = wx.GetApp()
            self.assertEqual(meta.name, wxApp.GetAppName())
            self.assertEqual(meta.author, wxApp.GetVendorName())
            app.mainwindow._idleController.stop()
            app.quit_application()
            app.mainwindow.Destroy()
            application.Application.deleteInstance()

    def assertLanguage(self, expectedLanguage, locale=None):
        args = [self.options, self.settings]
        if locale:
            args.append(locale)
        self.assertEqual(
            expectedLanguage, application.Application.determine_language(*args)
        )  # pylint: disable=W0142

    def testLanguageViaCommandLineOption(self):
        self.options.language = "fi_FI"
        self.assertLanguage("fi_FI")

    def testLanguageViaCommandLinePoFile(self):
        self.options.pofile = "nl_NL"
        self.assertLanguage("nl_NL")

    def testLanguageViaExternallySetLanguage(self):
        self.settings.set("view", "language", "de_DE")
        self.assertLanguage("de_DE")

    def testLanguageSetByUser(self):
        self.settings.set("view", "language_set_by_user", "de_DE")
        self.assertLanguage("de_DE")

    def testLanguageSetByUser_OverridesExternallySetLanguage(self):
        self.settings.set("view", "language", "nl_NL")
        self.settings.set("view", "language_set_by_user", "de_DE")
        self.assertLanguage("de_DE")

    def testLanguageViaLocale(self):
        self.assertLanguage("en_GB", DummyLocale("en_GB"))

    def testLanguageViaCLocale(self):
        self.assertLanguage("en_US", DummyLocale())
