# -*- coding: utf-8 -*-

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

import ast
import test, sys, os, configparser, io
from taskcoachlib import config, meta
from pubsub import pub


class SettingsTestCase(test.TestCase):
    def setUp(self):
        self.settings = config.Settings(load=False)

    def tearDown(self):
        super().tearDown()
        del self.settings


class SettingsTest(SettingsTestCase):
    def testDefaults(self):
        self.assertTrue(self.settings.has_section("view"))
        self.assertEqual(True, self.settings.getboolean("view", "statusbar"))

    def testSet(self):
        self.settings.setvalue("view", "toolbar", (16, 16))
        self.assertEqual((16, 16), self.settings.gettuple("view", "toolbar"))

    def testGetList_EmptyByDefault(self):
        self.assertEqual([], self.settings.getlist("file", "recentfiles"))

    def testSetList_Empty(self):
        self.settings.setlist("file", "recentfiles", [])
        self.assertEqual([], self.settings.getlist("file", "recentfiles"))

    def testSetList_SimpleStrings(self):
        recentfiles = ["abc", "C:\Documents And Settings\Whatever"]
        self.settings.setlist("file", "recentfiles", recentfiles)
        self.assertEqual(
            recentfiles, self.settings.getlist("file", "recentfiles")
        )

    def testSetList_UnicodeStrings(self):
        recentfiles = ["√É¬ºmlaut", "√é¬£√é¬ø√é¬º√é¬∑ √è‚Ä°√èÔøΩ√é¬µ√é¬µ√é¬∫"]
        self.settings.setlist("file", "recentfiles", recentfiles)
        self.assertEqual(
            recentfiles, self.settings.getlist("file", "recentfiles")
        )

    def testGetNonExistingSettingFromSection1ReturnsDefault(self):
        self.settings.add_section("effortviewer1")
        self.settings.set("effortviewer", "columnwidths", "dict(subject=10)")
        self.assertEqual(
            ast.literal_eval(config.defaults.defaults["effortviewer"]["columnwidths"]),
            self.settings.getdict("effortviewer1", "columnwidths"),
        )

    def testGetNonExistingSettingFromSection2ReturnsDefault(self):
        self.settings.add_section("effortviewer1")
        self.settings.add_section("effortviewer2")
        self.settings.set("effortviewer1", "columnwidths", "dict(subject=10)")
        self.assertEqual(
            ast.literal_eval(config.defaults.defaults["effortviewer"]["columnwidths"]),
            self.settings.getdict("effortviewer2", "columnwidths"),
        )

    def testGetNonExistingSettingFromSection2RaisesException(self):
        self.settings.add_section("effortviewer1")
        self.settings.add_section("effortviewer2")
        self.assertRaises(
            configparser.NoOptionError,
            self.settings.get,
            "effortviewer2",
            "nonexisting",
        )

    def testGetNonExistingSectionRaisesException(self):
        self.assertRaises(
            configparser.NoSectionError, self.settings.get, "bla", "bla"
        )

    def testAddSectionAndSkipOne(self):
        self.settings.set("effortviewer", "columnwidths", "dict(subject=10)")
        self.settings.add_section(
            "effortviewer2", copyFromSection="effortviewer"
        )
        self.assertEqual(
            dict(subject=10),
            self.settings.getdict("effortviewer2", "columnwidths"),
        )

    def testSinglePercentage(self):
        # Prevent ValueError: invalid interpolation syntax in '%' at position 0:
        self.settings.set("effortviewer", "searchfilterstring", "%")
        self.assertEqual(
            "%", self.settings.get("effortviewer", "searchfilterstring")
        )

    def testEmbeddedPercentage(self):
        # Prevent ValueError: invalid interpolation syntax in '%' at position 0
        self.settings.set("effortviewer", "searchfilterstring", "Bla%Bla")
        self.assertEqual(
            "Bla%Bla", self.settings.get("effortviewer", "searchfilterstring")
        )

    def testDoublePercentage(self):
        # Prevent ValueError: invalid interpolation syntax in '%' at position 0
        self.settings.set("effortviewer", "searchfilterstring", "%%")
        self.assertEqual(
            "%%", self.settings.get("effortviewer", "searchfilterstring")
        )

    def testFixInvalidValuesFromOldIniFile(self):
        self.settings.set("feature", "notifier", "Native")
        self.assertEqual(
            "Task Coach", self.settings.get("feature", "notifier")
        )
        self.assertEqual(
            "Task Coach", self.settings.getRawValue("feature", "notifier")
        )


class SettingsIOTest(SettingsTestCase):
    def setUp(self):
        super().setUp()
        self.fakeFile = io.StringIO()

    def testSave(self):
        self.settings.write(self.fakeFile)
        self.fakeFile.seek(0)
        self.assertEqual(
            "[%s]\n" % self.settings.sections()[0], self.fakeFile.readline()
        )

    def testRead(self):
        self.fakeFile.write("[testing]\n")
        self.fakeFile.seek(0)
        self.settings.read_file(self.fakeFile)
        self.assertTrue(self.settings.has_section("testing"))

    def testIOErrorWhileSaving(self):
        def file_that_raises_ioerror(*args):  # pylint: disable=W0613,W0622
            raise IOError

        def showerror(*args, **kwargs):  # pylint: disable=W0613
            self.showerror_args = args  # pylint: disable=W0201

        settings = config.Settings()
        settings.save(showerror=showerror, file=file_that_raises_ioerror)
        self.assertTrue(self.showerror_args)

    def testIOErrorWhileReading(self):
        class SettingsThatThrowsParsingError(config.Settings):
            def read(self, *args, **kwargs):  # pylint: disable=W0613
                self.remove_section("file")
                raise configparser.ParsingError("Testing")

        self.assertFalse(
            SettingsThatThrowsParsingError().getboolean(
                "file", "inifileloaded"
            )
        )

    def testFixOldColumnValues(self):
        section = "prerequisiteviewerintaskeditor1"
        self.fakeFile.write(
            "[%s]\ncolumns = ['dueDate']\ncolumnwidths = {'dueDate': 40}\n"
            % section
        )
        self.fakeFile.seek(0)
        self.settings.read_file(self.fakeFile)
        self.assertTrue(
            ["dueDateTime"], self.settings.getlist(section, "columns")
        )
        self.assertEqual(
            dict(dueDateTime=40),
            self.settings.getdict(section, "columnwidths"),
        )


class SettingsObservableTest(SettingsTestCase):
    def setUp(self):
        super().setUp()
        self.events = []
        pub.subscribe(self.onEvent, "settings.view.toolbar")

    def tearDown(self):
        pub.clearNotificationHandlers()

    def onEvent(self, value):
        self.events.append(value)

    def testChangingTheSettingCausesNotification(self):
        self.settings.settuple("view", "toolbar", (16, 16))
        self.assertEqual((16, 16), self.events[0])

    def testChangingAnotherSettingDoesNotCauseANotification(self):
        self.settings.set("view", "statusbar", "True")
        self.assertFalse(self.events)


class SpecificSettingsTest(SettingsTestCase):
    def testDefaultWindowPosition(self):
        self.assertEqual("(-1, -1)", self.settings.get("window", "position"))

    def testSetCurrentVersionAtSave(self):
        self.settings.set("version", "current", "0.0")
        self.settings.save()
        self.assertEqual(
            meta.data.version, self.settings.get("version", "current")
        )


class SettingsFileLocationTest(SettingsTestCase):
    def testDefaultSetting(self):
        self.assertEqual(
            False, self.settings.getboolean("file", "saveinifileinprogramdir")
        )

    def testPathWhenNotSavingIniFileInProgramDir(self):
        self.assertNotEqual(sys.argv[0], self.settings.path())

    def testPathWhenSavingIniFileInProgramDir(self):
        self.settings.setboolean("file", "saveinifileinprogramdir", True)
        self.assertEqual(os.path.dirname(sys.argv[0]), self.settings.path())

    def testPathWhenSavingIniFileInProgramDirAndRunFromZipFile(self):
        self.settings.setboolean("file", "saveinifileinprogramdir", True)
        sys.argv.insert(0, os.path.join("d:", "TaskCoach", "library.zip"))
        self.assertEqual(os.path.join("d:", "TaskCoach"), self.settings.path())
        del sys.argv[0]

    def testSettingSaveIniFileInProgramDirToFalseRemovesIniFile(self):
        class SettingsUnderTest(config.Settings):
            def onSettingsFileLocationChanged(self, value):
                self.onSettingsFileLocationChangedCalled = (
                    value  # pylint: disable=W0201
                )

        settings = SettingsUnderTest(load=False)
        settings.setboolean("file", "saveinifileinprogramdir", True)
        settings.setboolean("file", "saveinifileinprogramdir", False)
        self.assertFalse(settings.onSettingsFileLocationChangedCalled)


class MinimumSettingsTest(SettingsTestCase):
    def testAtLeastOneTaskTreeListViewer(self):
        self.assertEqual(1, self.settings.getint("view", "taskviewercount"))

    def testTwoTaskTreeListViewers(self):
        self.settings.set("view", "taskviewercount", "2")
        self.assertEqual(2, self.settings.getint("view", "taskviewercount"))

    def testAtLeastOneTaskTreeListViewer_EvenWhenSetToZero(self):
        self.settings.set("view", "taskviewercount", "0")
        self.assertEqual(1, self.settings.getint("view", "taskviewercount"))


class ApplicationOptionsTest(test.TestCase):
    def setUp(self):
        super().setUp()
        self.parser = config.ApplicationOptionParser()

    def parse(self, *args):
        return self.parser.parse_args(list(args))[0]

    def testUsage(self):
        self.assertEqual("%prog [options] [.tsk file]", self.parser.usage)

    def testLanguage(self):
        options = self.parse("-l", "nl")
        self.assertEqual("nl", options.language)

    def testLanguageWhenNotChanged(self):
        options = self.parse()
        self.assertEqual(None, options.language)

    def testPoFile(self):
        options = self.parse("-p", "test.po")
        self.assertEqual("test.po", options.pofile)

    def testIniFile(self):
        options = self.parse("-i", "test.ini")
        self.assertEqual("test.ini", options.inifile)

    def testProfile(self):
        options = self.parse("--profile")
        self.assertTrue(options.profile)
