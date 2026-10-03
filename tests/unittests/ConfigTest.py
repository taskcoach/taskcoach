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
import gc
import shutil
import stat
import tempfile
import test, sys, os, configparser, io
import weakref
from unittest import mock
from taskcoachlib import config, meta


class SettingsTestCase(test.TestCase):
    def setUp(self):
        self.settings = config.Settings(load=False)

    def tearDown(self):
        super().tearDown()
        del self.settings


class SettingsTest(SettingsTestCase):
    def testDefaults(self):
        self.assertTrue(self.settings.has_section("view"))
        self.assertEqual(True, self.settings.get_typed("view", "statusbar"))

    def testSet(self):
        self.settings.set_typed("view", "toolbar", (16, 16))
        self.assertEqual((16, 16), self.settings.get_typed("view", "toolbar"))

    def testGetList_EmptyByDefault(self):
        self.assertEqual([], self.settings.get_typed("file", "recentfiles"))

    def testSetList_Empty(self):
        self.settings.set_typed("file", "recentfiles", [])
        self.assertEqual([], self.settings.get_typed("file", "recentfiles"))

    def testSetList_SimpleStrings(self):
        recentfiles = ["abc", r"C:\Documents And Settings\Whatever"]
        self.settings.set_typed("file", "recentfiles", recentfiles)
        self.assertEqual(
            recentfiles, self.settings.get_typed("file", "recentfiles")
        )

    def testSetList_UnicodeStrings(self):
        recentfiles = [
            "\u00fcmlaut",
            "\u03a3\u03bf\u03bc\u03b7 \u03c7\u03c1\u03b5\u03b5\u03ba",
        ]
        self.settings.set_typed("file", "recentfiles", recentfiles)
        self.assertEqual(
            recentfiles, self.settings.get_typed("file", "recentfiles")
        )

    def testGetNonExistingSettingFromSection1ReturnsDefault(self):
        self.settings.add_section("effortviewer1")
        self.settings.set_typed(
            "effortviewer", "columnwidths", {"subject": 10}
        )
        self.assertEqual(
            ast.literal_eval(
                config.defaults.defaults["effortviewer"]["columnwidths"]
            ),
            self.settings.get_typed("effortviewer1", "columnwidths"),
        )

    def testGetNonExistingSettingFromSection2ReturnsDefault(self):
        self.settings.add_section("effortviewer1")
        self.settings.add_section("effortviewer2")
        self.settings.set_typed(
            "effortviewer1", "columnwidths", {"subject": 10}
        )
        self.assertEqual(
            ast.literal_eval(
                config.defaults.defaults["effortviewer"]["columnwidths"]
            ),
            self.settings.get_typed("effortviewer2", "columnwidths"),
        )

    def testGetNonExistingSettingFromSection2RaisesException(self):
        self.settings.add_section("effortviewer1")
        self.settings.add_section("effortviewer2")
        self.assertRaises(
            KeyError, self.settings.get_typed, "effortviewer2", "nonexisting"
        )

    def testGetNonExistingSectionRaisesException(self):
        self.assertRaises(KeyError, self.settings.get_typed, "bla", "bla")

    def testAddSectionAndSkipOne(self):
        self.settings.set_typed(
            "effortviewer", "columnwidths", {"subject": 10}
        )
        self.settings.add_section("effortviewer2", copy_from="effortviewer")
        self.assertEqual(
            dict(subject=10),
            self.settings.get_typed("effortviewer2", "columnwidths"),
        )

    def assert_percentage_kept(self, text):
        # No interpolation: "%" is no syntax, in memory or in the file
        self.settings.set_typed("effortviewer", "searchfilterstring", text)
        file = io.StringIO()
        self.settings.write(file)
        self.assertEqual(
            text,
            self.settings.get_typed("effortviewer", "searchfilterstring"),
        )
        self.assertIn("searchfilterstring = %s\n" % text, file.getvalue())

    def test_single_percentage(self):
        self.assert_percentage_kept("%")

    def test_embedded_percentage(self):
        self.assert_percentage_kept("Bla%Bla")

    def test_double_percentage(self):
        self.assert_percentage_kept("%%")

    def test_a_value_not_of_its_type_is_shown_and_replaced(self):
        self.settings.read_file(io.StringIO("[view]\nstatusbar = maybe\n"))
        with mock.patch("wx.MessageBox") as message_box:
            self.assertEqual(
                True, self.settings.get_typed("view", "statusbar")
            )
        self.assertEqual(1, message_box.call_count)
        # Replaced: shown once
        with mock.patch("wx.MessageBox") as message_box:
            self.settings.get_typed("view", "statusbar")
        self.assertEqual(0, message_box.call_count)


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

    def test_sections_and_options_nothing_reads_are_kept(self):
        # An older release may read them
        self.settings.read_file(io.StringIO("[syncml]\nverbose = 1\n"))
        self.settings.write(self.fakeFile)
        self.assertIn("[syncml]\nverbose = 1\n", self.fakeFile.getvalue())

    def testIOErrorWhileSaving(self):
        def file_that_raises_ioerror(*args):  # pylint: disable=W0613,W0622
            raise IOError

        def showerror(*args, **kwargs):  # pylint: disable=W0613
            self.showerror_args = args  # pylint: disable=W0201

        settings = config.Settings()
        settings.save(showerror=showerror, file=file_that_raises_ioerror)
        self.assertTrue(self.showerror_args)

    def testIOErrorWhileReading(self):
        folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, folder)
        ini_file = os.path.join(folder, "TaskCoach.ini")
        with open(ini_file, "w", encoding="utf-8") as file:
            file.write("[file]\n")
        with mock.patch.object(
            configparser.ConfigParser,
            "read",
            side_effect=configparser.ParsingError("Testing"),
        ):
            settings = config.Settings(ini_file=ini_file)
        self.assertFalse(settings.get_typed("file", "inifileloaded"))

    def testFixOldColumnValues(self):
        section = "prerequisiteviewerintaskeditor1"
        self.fakeFile.write(
            "[%s]\ncolumns = ['dueDate']\ncolumnwidths = {'dueDate': 40}\n"
            % section
        )
        self.fakeFile.seek(0)
        self.settings.read_file(self.fakeFile)
        self.assertEqual(
            ["dueDateTime"], self.settings.get_typed(section, "columns")
        )
        self.assertEqual(
            dict(dueDateTime=40),
            self.settings.get_typed(section, "columnwidths"),
        )

    def test_an_old_sort_column_becomes_a_list(self):
        self.settings.read_file(
            io.StringIO(
                "[taskviewer]\nsortby = dueDate\nsortascending = False\n"
            )
        )
        self.assertEqual(
            ["-dueDateTime"], self.settings.get_typed("taskviewer", "sortby")
        )

    def test_options_nothing_reads_are_dropped(self):
        editor = "taskdialog_with_dates_subject"
        self.fakeFile.write(
            "[window]\nmonitor_index = 1\n"
            "[export]\nhtml_selectiononly = True\n"
            "[%s]\nparent_offset = (-1, -1)\nsize = (10, 10)\n" % editor
        )
        self.fakeFile.seek(0)
        self.settings.read_file(self.fakeFile)
        self.assertEqual(
            (False, False, False, True),
            (
                self.settings.has_option("window", "monitor_index"),
                self.settings.has_option("export", "html_selectiononly"),
                self.settings.has_option(editor, "parent_offset"),
                self.settings.has_option(editor, "size"),
            ),
        )

    def test_the_retired_dependency_graph_view_is_dropped(self):
        self.fakeFile.write(
            "[view]\ntaskinterdepsviewercount = 2\n"
            "[taskinterdepsviewer]\ntitle = Graph\n"
            "[taskinterdepsviewer1]\ntitle = Another\n"
        )
        self.fakeFile.seek(0)
        self.settings.read_file(self.fakeFile)
        self.assertEqual(
            (False, False, False, True),
            (
                self.settings.has_option("view", "taskinterdepsviewercount"),
                self.settings.has_section("taskinterdepsviewer"),
                self.settings.has_section("taskinterdepsviewer1"),
                self.settings.has_section("taskviewer"),
            ),
        )


class LegacyStatusIconsTest(SettingsTestCase):
    """With the legacy status icons on, the file names the status icons
    as releases before 2.0.1.72 know them; the settings keep today's
    names."""

    def written(self):
        file = io.StringIO()
        self.settings.write(file)
        return file.getvalue()

    def test_on_the_old_names_in_the_file(self):
        self.settings.set_typed("icon", "legacystatusicons", True)
        self.assertIn("\nactivetasks = led_blue_icon\n", self.written())
        self.assertEqual(
            "nuvola_actions_ledblue",
            self.settings.get_typed("icon", "activetasks"),
        )

    def test_off_todays_names(self):
        self.assertIn(
            "\nactivetasks = nuvola_actions_ledblue\n", self.written()
        )
        self.assertNotIn("led_blue_icon", self.written())


class SettingsObservableTest(SettingsTestCase):
    def setUp(self):
        super().setUp()
        self.events = test.ChangeRecorder("view.toolbar")

    def test_changing_the_setting_causes_notification(self):
        self.settings.set_typed("view", "toolbar", (16, 16))
        self.assertEqual([("(16, 16)", self.settings)], self.events)

    def test_changing_another_setting_does_not_cause_a_notification(self):
        self.settings.set_typed("view", "statusbar", True)
        self.assertFalse(self.events)

    def test_the_section_is_told_which_option_changed(self):
        section = test.ChangeRecorder(
            self.settings.section_changed_event_type("view")
        )
        self.settings.set_typed("view", "toolbar", (16, 16))
        self.assertEqual([("toolbar", self.settings)], section)


class SpecificSettingsTest(SettingsTestCase):
    def testDefaultWindowPosition(self):
        self.assertEqual(
            (-1, -1), self.settings.get_typed("window", "position")
        )

    def testSetCurrentVersionAtSave(self):
        self.settings.set_typed("version", "current", "0.0")
        self.settings.save()
        self.assertEqual(
            meta.data.version, self.settings.get_typed("version", "current")
        )


class SettingsFileLocationTest(SettingsTestCase):
    def testDefaultSetting(self):
        self.assertEqual(
            False,
            self.settings.get_typed("file", "saveinifileinprogramdir"),
        )

    def testPathWhenNotSavingIniFileInProgramDir(self):
        self.assertNotEqual(sys.argv[0], self.settings.path())

    def testPathWhenSavingIniFileInProgramDir(self):
        self.settings.set_typed("file", "saveinifileinprogramdir", True)
        self.assertEqual(
            os.path.abspath(os.path.dirname(sys.argv[0])), self.settings.path()
        )

    def testPathWhenSavingIniFileInProgramDirAndRunFromZipFile(self):
        self.settings.set_typed("file", "saveinifileinprogramdir", True)
        sys.argv.insert(0, os.path.join("d:", "TaskCoach", "library.zip"))
        self.assertEqual(
            os.path.abspath(os.path.join("d:", "TaskCoach")),
            self.settings.path(),
        )
        del sys.argv[0]

    def test_setting_save_ini_file_in_program_dir_to_false_is_heard(self):
        class SettingsUnderTest(config.Settings):
            def on_settings_file_location_changed(self):
                # pylint: disable=W0201
                self.in_program_dir = self.get_typed(
                    "file", "saveinifileinprogramdir"
                )

        settings = SettingsUnderTest(load=False)
        settings.set_typed("file", "saveinifileinprogramdir", True)
        settings.set_typed("file", "saveinifileinprogramdir", False)
        self.assertFalse(settings.in_program_dir)


class XdgFoldersTest(SettingsTestCase):
    """The settings and data folders on Linux: in the XDG base
    directories, ~/.config and ~/.local/share when unset."""

    def environment(self, **variables):
        home = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, home)
        patcher = mock.patch.dict(os.environ, HOME=home, **variables)
        patcher.start()
        self.addCleanup(patcher.stop)
        return home

    def test_settings_folder_in_xdg_config_home(self):
        home = self.environment(XDG_CONFIG_HOME="")
        os.environ["XDG_CONFIG_HOME"] = os.path.join(home, "settings")
        path = self.settings.pathToConfigDir(os.environ)
        self.assertEqual(os.path.join(home, "settings", meta.name), path)
        # Readable by the user only
        self.assertEqual(0o700, stat.S_IMODE(os.stat(path).st_mode))

    def test_settings_folder_without_xdg_config_home(self):
        home = self.environment(XDG_CONFIG_HOME="")
        self.assertEqual(
            os.path.join(home, ".config", meta.name),
            self.settings.pathToConfigDir(os.environ),
        )

    def test_data_folder_in_xdg_data_home(self):
        home = self.environment(XDG_DATA_HOME="")
        os.environ["XDG_DATA_HOME"] = os.path.join(home, "data")
        self.assertEqual(
            os.path.join(home, "data", meta.name, "templates"),
            self.settings.pathToTemplatesDir(),
        )

    def test_data_folder_without_xdg_data_home(self):
        home = self.environment(XDG_DATA_HOME="")
        path = self.settings.pathToTemplatesDir()
        self.assertEqual(
            os.path.join(home, ".local", "share", meta.name, "templates"),
            path,
        )
        self.assertTrue(os.path.isdir(path))


class SettingsLifetimeTest(test.TestCase):
    def test_settings_read_and_dropped_are_freed(self):
        # Date, time and amount controls each read a Settings object
        # of their own and drop it
        reference = weakref.ref(config.Settings(load=False))
        gc.collect()
        self.assertIsNone(reference())


class MinimumSettingsTest(SettingsTestCase):
    def testAtLeastOneTaskTreeListViewer(self):
        self.assertEqual(1, self.settings.get_typed("view", "taskviewercount"))

    def testTwoTaskTreeListViewers(self):
        self.settings.set_typed("view", "taskviewercount", 2)
        self.assertEqual(2, self.settings.get_typed("view", "taskviewercount"))

    def testAtLeastOneTaskTreeListViewer_EvenWhenSetToZero(self):
        self.settings.set_typed("view", "taskviewercount", 0)
        self.assertEqual(1, self.settings.get_typed("view", "taskviewercount"))


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
