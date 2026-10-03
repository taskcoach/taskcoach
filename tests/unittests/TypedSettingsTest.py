"""
Task Coach - Your friendly task manager
Copyright (C) 2004-2026 Task Coach developers <developers@taskcoach.org>

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

from unittest import mock

import test
from taskcoachlib import config
from taskcoachlib.config import settings


class TypedSettingsTest(test.TestCase):
    """Any module reads and writes the one Settings object by
    attribute, each option as its type (docs/SETTINGS.md, One Settings
    Object)."""

    def setUp(self):
        super().setUp()
        self.settings = config.Settings(load=False)
        self.addCleanup(settings.use, settings.current())
        settings.use(self.settings)

    def test_true_or_false_reads_as_bool(self):
        self.assertIs(True, settings.view.statusbar)

    def test_whole_number_reads_as_int(self):
        self.assertEqual(1, settings.window.hoverlinewidth)

    def test_python_literal_reads_as_its_value(self):
        self.assertEqual((22, 22), settings.view.toolbar)

    def test_text_reads_as_text(self):
        self.assertEqual("monday", settings.view.weekstart)

    def test_a_time_format_is_text(self):
        # "24", "12" or "" for the system's
        self.assertEqual("24", settings.view.timeformat)

    def test_a_viewer_instance_has_its_templates_types(self):
        self.settings.add_section("taskviewer1", copyFromSection="taskviewer")
        self.assertEqual(
            ["dueDateTime"], settings.section("taskviewer1").sortby
        )

    def test_an_editor_window_has_the_editor_windows_types(self):
        name = "taskdialog_with_dates_subject"
        settings.add_section(name)
        self.assertEqual(
            (False, (-1, -1)),
            (settings.section(name).maximized, settings.section(name).size),
        )

    def test_computed_names(self):
        self.assertIs(True, settings.get("view", "statusbar"))

    def test_write_by_computed_names(self):
        settings.set("view", "statusbar", False)
        self.assertIs(False, settings.view.statusbar)

    def test_write_by_computed_names_checks_the_type(self):
        with self.assertRaises(TypeError):
            settings.set("view", "statusbar", "False")

    def test_send_changed_tells_the_listeners(self):
        self.registerObserver("window.theme")
        settings.send_changed("window", "theme")
        self.assertEqual(["automatic"], [e.value() for e in self.events])

    def test_from_text_whole_number(self):
        self.assertEqual(
            15, settings.from_text("view", "defaultsnoozetime", "15")
        )

    def test_from_text_text(self):
        self.assertEqual(
            "sunday", settings.from_text("view", "weekstart", "sunday")
        )

    def test_write_stores_the_text_form(self):
        settings.view.statusbar = False
        self.assertEqual("False", self.settings.get("view", "statusbar"))

    def test_write_tells_the_listeners(self):
        self.registerObserver("view.statusbar")
        settings.view.statusbar = False
        self.assertEqual(["False"], [e.value() for e in self.events])

    def test_a_value_of_another_type_is_refused(self):
        with self.assertRaises(TypeError):
            settings.view.statusbar = "False"

    def test_text_for_a_list_is_refused(self):
        with self.assertRaises(TypeError):
            settings.taskviewer.sortby = "subject"

    def test_an_option_no_defaults_name(self):
        with self.assertRaises(AttributeError):
            settings.view.no_such_option

    def test_a_section_no_defaults_name(self):
        with self.assertRaises(AttributeError):
            settings.no_such_section

    def test_reads_the_object_in_use(self):
        other = config.Settings(load=False)
        other.setboolean("view", "statusbar", False)
        settings.use(other)
        self.assertIs(False, settings.view.statusbar)


class FoldersTest(test.TestCase):
    """The folders come from the Settings object in use: on Windows a
    settings file named on the command line moves them."""

    def setUp(self):
        super().setUp()
        self.addCleanup(settings.use, settings.current())
        settings.use(
            mock.Mock(
                pathToTemplatesDir=lambda: "templates here",
                pathToBackupsDir=lambda: "backups here",
            )
        )

    def test_templates(self):
        self.assertEqual("templates here", settings.templates_dir())

    def test_backups(self):
        self.assertEqual("backups here", settings.backups_dir())


class SectionsMadeWhileRunningTest(test.TestCase):
    """A viewer instance's section copies the previous viewer's; an
    editor window's starts from the editor window defaults."""

    def setUp(self):
        super().setUp()
        self.settings = config.Settings(load=False)
        self.addCleanup(settings.use, settings.current())
        settings.use(self.settings)

    def test_a_declared_section_exists(self):
        self.assertTrue(settings.has_section("taskviewer"))

    def test_a_section_not_made_yet(self):
        self.assertFalse(settings.has_section("taskviewer1"))

    def test_a_copy_of_the_previous_viewers(self):
        settings.taskviewer.title = "Mine"
        settings.add_section("taskviewer1", copy_from="taskviewer")
        self.assertEqual("Mine", settings.section("taskviewer1").title)

    def test_an_editor_window_starts_from_its_defaults(self):
        name = "notedialog_with_subject"
        settings.add_section(name)
        self.assertEqual([], settings.section(name).pages)

    def test_no_listener_is_told(self):
        self.registerObserver("notedialog_with_subject.pages")
        settings.add_section("notedialog_with_subject")
        self.assertEqual([], self.events)


class ResetTest(test.TestCase):
    """Each test starts from the defaults: the harness resets the one
    Settings object after every test."""

    def setUp(self):
        super().setUp()
        self.settings = config.Settings(load=False)

    def test_back_to_the_defaults(self):
        self.settings.setboolean("view", "statusbar", False)
        self.settings.reset()
        self.assertIs(True, self.settings.getboolean("view", "statusbar"))

    def test_sections_made_while_running_go(self):
        self.settings.add_section("taskviewer1", copyFromSection="taskviewer")
        self.settings.settext("taskviewer1", "title", "Mine")
        self.settings.reset()
        self.assertFalse(self.settings.has_section("taskviewer1"))

    def test_no_listener_is_told(self):
        self.settings.setboolean("view", "statusbar", False)
        self.registerObserver("view.statusbar")
        self.settings.reset()
        self.assertEqual([], self.events)

    def test_quiet_as_when_made(self):
        self.settings.reset()
        self.assertIs(False, self.settings.getboolean("window", "tips"))


class ThemeIsDarkTest(test.wxTestCase):
    """window.theme_is_dark: the theme chosen, or the system's."""

    def test_dark_chosen(self):
        settings.window.theme = "dark"
        self.assertIs(True, settings.window.theme_is_dark)

    def test_light_chosen(self):
        settings.window.theme = "light"
        self.assertIs(False, settings.window.theme_is_dark)

    def test_automatic_follows_the_system(self):
        settings.window.theme = "automatic"
        from taskcoachlib.application.application import detect_dark_theme

        self.assertEqual(detect_dark_theme(), settings.window.theme_is_dark)

    def test_not_written(self):
        with self.assertRaises(AttributeError):
            settings.window.theme_is_dark = True


class BeforeTheApplicationTest(test.TestCase):
    """A module that reads while it loads, before the application has
    its settings, gets the defaults."""

    def setUp(self):
        super().setUp()
        self.addCleanup(settings.use, settings.current())
        settings.use(None)

    def test_the_default_as_its_type(self):
        self.assertEqual(
            (True, 1, (22, 22), "24"),
            (
                settings.view.statusbar,
                settings.window.hoverlinewidth,
                settings.view.toolbar,
                settings.view.timeformat,
            ),
        )
