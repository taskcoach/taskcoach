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
import shutil
import tempfile
import types
import unittest
from unittest import mock
from taskcoachlib import meta, gui, operating_system, patterns, persistence
from taskcoachlib.gui import appindicator
from taskcoachlib.gui.icons.icon_library import icon_catalog, LIST_ICON_SIZE
from taskcoachlib.domain import task, effort, date
from taskcoachlib.config import settings
from taskcoachlib.gui import uicommand
import test
import wx


class TaskFileMock(object):
    def filename(self):
        return "filename"


class MainWindowMock(object):
    taskFile = TaskFileMock()

    def __init__(self):
        self.__cb = None

    def restore(self):
        pass  # pragma: no cover

    def Bind(self, evt, cb):
        self.__cb = cb

    def Unbind(self, evt, handler=None):  # TaskBarIcon.Destroy unbinds
        self.__cb = None

    def ProcessIdle(self):
        if self.__cb is not None:
            self.__cb(None)


class TaskBarIconTestCase(test.TestCase):
    def setUp(self):
        self.taskList = task.TaskList()
        self.window = MainWindowMock()
        self.icon = gui.taskbaricon.TaskBarIcon(self.window, self.taskList)

    def tearDown(self):  # pragma: no cover
        if operating_system.isWindows():
            self.icon.Destroy()
        else:
            self.icon.RemoveIcon()
        super().tearDown()


class TaskBarIconTest(TaskBarIconTestCase):
    def test_icon_no_tasks(self):
        self.window.ProcessIdle()
        self.assertTrue(self.icon.IsIconInstalled())

    def test_start_tracking(self):
        active_task = task.Task()
        self.taskList.append(active_task)
        active_task.addEffort(effort.Effort(active_task))
        self.assertEqual("nuvola_apps_clock", self.icon.icon_id())

    def test_stop_tracking(self):
        active_task = task.Task()
        self.taskList.append(active_task)
        active_effort = effort.Effort(active_task)
        active_task.addEffort(active_effort)
        active_task.removeEffort(active_effort)
        self.assertEqual(self.icon.default_icon_id(), self.icon.icon_id())


class TaskBarIconTooltipTestCase(TaskBarIconTestCase):
    def assertTooltip(self, text):
        expected_tooltip = "%s - %s" % (meta.name, TaskFileMock().filename())
        if text:
            expected_tooltip += "\n%s" % text
        self.assertEqual(expected_tooltip, self.icon.tooltip())


class TaskBarIconTooltipTest(TaskBarIconTooltipTestCase):
    def test_no_tasks(self):
        self.assertTooltip("")

    def test_one_task_no_due_date_time(self):
        self.taskList.append(task.Task())
        self.assertTooltip("")

    def test_one_task_due_soon(self):
        self.taskList.append(task.Task(dueDateTime=date.Now() + date.ONE_HOUR))
        self.assertTooltip("one task due soon")

    def test_one_task_no_longer_due_soon_after_changing_due_soon_setting(self):
        self.taskList.append(task.Task(dueDateTime=date.Now() + date.ONE_HOUR))
        settings.set("behavior", "duesoonhours", 0)
        self.assertTooltip("")

    def test_two_tasks_due_soon(self):
        self.taskList.append(task.Task(dueDateTime=date.Now() + date.ONE_HOUR))
        self.taskList.append(task.Task(dueDateTime=date.Now() + date.ONE_HOUR))
        self.assertTooltip("2 tasks due soon")

    def test_one_tasks_overdue(self):
        self.taskList.append(task.Task(dueDateTime=date.Yesterday()))
        self.assertTooltip("one task overdue")

    def test_a_file_read_counts_the_statuses_anew(self):
        # A read sets them quietly
        due = date.Now() + date.ONE_HOUR
        each = task.Task(dueDateTime=due)
        self.taskList.append(each)
        with patterns.computed_values_quietly():
            each.compute_stored_status(due + date.ONE_HOUR)
        patterns.Event("taskfile.justRead", self.window.taskFile).send()
        self.assertTooltip("one task overdue")

    def test_two_tasks_overdue(self):
        self.taskList.append(task.Task(dueDateTime=date.Yesterday()))
        self.taskList.append(task.Task(dueDateTime=date.Yesterday()))
        self.assertTooltip("2 tasks overdue")

    def test_one_task_due_soon_and_one_task_overdue(self):
        self.taskList.append(task.Task(dueDateTime=date.Yesterday()))
        self.taskList.append(task.Task(dueDateTime=date.Now() + date.ONE_HOUR))
        self.assertTooltip("one task overdue, one task due soon")

    def test_remove_task(self):
        new_task = task.Task()
        self.taskList.append(new_task)
        self.taskList.remove(new_task)
        self.assertTooltip("")

    def test_remove_overdue_task(self):
        overdue_task = task.Task(dueDateTime=date.Yesterday())
        self.taskList.append(overdue_task)
        self.taskList.remove(overdue_task)
        self.assertTooltip("")

    def assert_counted_once_after(self, begin, end):
        # The tool tip counts every task: once for a burst of changes
        tasks = [task.Task(), task.Task()]
        self.taskList.extend(tasks)
        patterns.Event(begin, self).send()
        for each in tasks:
            each.set_due_date_time(date.Yesterday())
        self.assertTooltip("")
        patterns.Event(end, self).send()
        self.assertTooltip("2 tasks overdue")

    def test_counted_once_after_a_bulk_command(self):
        self.assert_counted_once_after(
            "command.aboutToBulkModify", "command.justBulkModified"
        )

    def test_counted_once_after_a_scheduler_pass(self):
        self.assert_counted_once_after(
            "scheduler.aboutToPass", "scheduler.pass"
        )


class TaskBarIconTooltipWithTrackedTaskTest(TaskBarIconTooltipTestCase):
    def setUp(self):
        super().setUp()
        self.task = task.Task(subject="Subject")
        self.taskList.append(self.task)
        self.task.addEffort(effort.Effort(self.task))

    def test_start_tracking(self):
        self.assertTooltip('tracking "Subject"')

    def test_stop_tracking(self):
        self.task.efforts()[0].setStop(date.DateTime(2000, 1, 1, 10, 0, 0))
        self.assertTooltip("")

    def test_tracking_two_tasks(self):
        active_task = task.Task()
        self.taskList.append(active_task)
        active_task.addEffort(effort.Effort(active_task))
        self.assertTooltip("tracking effort for 2 tasks")

    def test_changing_subject_of_tracked_task(self):
        self.task.setSubject("New subject")
        self.assertTooltip('tracking "New subject"')

    def test_changing_subject_of_task_that_is_not_tracked_anymore(self):
        self.task.efforts()[0].setStop(date.DateTime(2000, 1, 1, 10, 0, 0))
        self.task.setSubject("New subject")
        self.assertTooltip("")


class AppIndicatorMenuCommandTest(test.TestCase):
    """The New commands of the Linux tray menu (AppIndicator), with a
    stand-in indicator: no tray icon registers on the session bus."""

    def setUp(self):
        super().setUp()
        self.window = MainWindowMock()
        self.window.taskFile = persistence.TaskFile()
        with mock.patch.object(gui.taskbaricon, "_APPINDICATOR_MODULE"):
            self.icon = gui.taskbaricon.AppIndicatorTaskBarIcon(
                self.window, self.window.taskFile.tasks()
            )

    def assert_runs(self, command_class, menu_item):
        with mock.patch.object(command_class, "do_command") as do_command:
            menu_item()
        do_command.assert_called_once_with(None)

    def test_new_effort(self):
        self.assert_runs(uicommand.EffortNew, self.icon._do_new_effort)

    def test_new_task(self):
        self.assert_runs(uicommand.TaskNew, self.icon._do_new_task)

    def test_new_category(self):
        self.assert_runs(uicommand.CategoryNew, self.icon._do_new_category)

    def test_new_note(self):
        self.assert_runs(uicommand.NoteNew, self.icon._do_new_note)


@unittest.skipUnless(appindicator.APPINDICATOR_AVAILABLE, "no AppIndicator")
class MenuImagesTest(test.wxTestCase):
    """The Linux tray menu's icons are each read once; where GTK draws
    the menu, items name them, so the tray library hands over a name,
    not each item's picture as image data (docs/SYSTEM_TRAY.md, Menu
    Icons)."""

    def setUp(self):
        super().setUp()
        self.images = appindicator._MenuImages()
        self.path = icon_catalog.get_path(
            "taskcoach_actions_arrow_down_right", LIST_ICON_SIZE
        )
        self.gtk = appindicator._Gtk

    def test_each_icon_file_is_read_once(self):
        read = appindicator._GdkPixbuf.Pixbuf.new_from_file
        with mock.patch.object(
            appindicator, "_GdkPixbuf", mock.Mock()
        ) as gdk_pixbuf:
            gdk_pixbuf.Pixbuf.new_from_file.side_effect = read
            for by_name in (True, True, False, False):
                self.images.image(self.path, by_name)
        self.assertEqual(1, gdk_pixbuf.Pixbuf.new_from_file.call_count)

    def test_where_gtk_draws_the_menu_items_name_their_icon(self):
        first = self.images.image(self.path, by_name=True)
        second = self.images.image(self.path, by_name=True)
        self.assertEqual(
            (self.gtk.ImageType.ICON_NAME, first.get_icon_name()[0]),
            (second.get_storage_type(), second.get_icon_name()[0]),
        )
        self.assertTrue(
            self.gtk.IconTheme.get_default().has_icon(first.get_icon_name()[0])
        )

    def test_for_a_tray_host_items_share_the_picture(self):
        first = self.images.image(self.path, by_name=False)
        second = self.images.image(self.path, by_name=False)
        self.assertEqual(
            (self.gtk.ImageType.PIXBUF, first.get_pixbuf()),
            (second.get_storage_type(), second.get_pixbuf()),
        )

    def test_an_unreadable_file_gives_no_icon(self):
        self.assertIsNone(self.images.image("/nonexistent.png", True))


@unittest.skipUnless(appindicator.APPINDICATOR_AVAILABLE, "no AppIndicator")
class AppIndicatorMenuUpdateTest(test.wxTestCase):
    """The Linux tray menu is updated in place: after each change it is
    the menu a fresh build gives, and only the changed items are
    touched (docs/SYSTEM_TRAY.md, Menu Updates). A stand-in indicator
    with real GTK menus: no tray icon registers on the session bus."""

    def setUp(self):
        super().setUp()
        self.gtk = appindicator._Gtk
        self.indicator = mock.Mock()
        self.indicator.is_connected.return_value = False
        self.indicator.menu_image.side_effect = (
            lambda path: self.gtk.Image.new_from_icon_name(
                path, self.gtk.IconSize.MENU
            )
        )
        module = types.SimpleNamespace(
            _Gtk=self.gtk, AppIndicatorIcon=lambda **kwargs: self.indicator
        )
        self.templates = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.templates)
        for patcher in (
            mock.patch.object(gui.taskbaricon, "_APPINDICATOR_MODULE", module),
            mock.patch.object(
                gui.taskbaricon.settings,
                "templates_dir",
                return_value=self.templates,
            ),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)
        self.window = MainWindowMock()
        self.window.taskFile = persistence.TaskFile()
        self.addCleanup(self.window.taskFile.stop)
        self.tasks = self.window.taskFile.tasks()
        self.icon = gui.taskbaricon.AppIndicatorTaskBarIcon(
            self.window, self.tasks
        )
        self.alpha = task.Task(subject="Alpha")
        self.bravo = task.Task(subject="Bravo")
        self.charlie = task.Task(subject="Charlie")
        self.bravo.addChild(self.charlie)
        self.tasks.extend([self.alpha, self.bravo])
        self.icon._update_gtk_menu()
        wx.GetApp().ProcessPendingEvents()  # The update the adds asked

    def menu(self):
        return self.indicator.set_gtk_menu.call_args[0][0]

    def dump(self, menu):
        lines = []
        for item in menu.get_children():
            if isinstance(item, self.gtk.SeparatorMenuItem):
                lines.append("-")
                continue
            image = None
            if isinstance(item, self.gtk.ImageMenuItem) and item.get_image():
                image = item.get_image().get_icon_name()[0]
            submenu = item.get_submenu()
            lines.append(
                (
                    item.get_label(),
                    image,
                    self.dump(submenu) if submenu else None,
                    item.get_visible(),
                )
            )
        return lines

    def fresh_menu(self):
        level = gui.taskbaricon._MenuLevel(self.gtk)
        level.update(
            self.icon._menu_lines(),
            self.icon._AppIndicatorTaskBarIcon__menu_image,
        )
        return self.dump(level.menu)

    def assert_updated(self):
        self.icon._update_gtk_menu()
        self.assertEqual(self.fresh_menu(), self.dump(self.menu()))

    def tracking_items(self):
        tracking = [
            item
            for item in self.menu().get_children()
            if item.get_label() == "Start tracking effort"
        ][0]
        return tracking.get_submenu().get_children()

    def write_template(self, subject):
        with open(
            os.path.join(self.templates, "%s.tsktmpl" % subject), "wb"
        ) as fd:
            persistence.TemplateXMLWriter(fd).write(task.Task(subject=subject))

    def test_the_menu_is_handed_over_once(self):
        self.alpha.setSubject("Alpha 2")
        self.icon._update_gtk_menu()
        self.assertEqual(1, self.indicator.set_gtk_menu.call_count)

    def test_tasks_renamed_completed_reopened_and_removed(self):
        self.alpha.setSubject("Zulu")  # Sorts after Bravo now
        self.assert_updated()
        self.charlie.set_completion_date_time(date.Now())
        self.assert_updated()
        self.charlie.set_completion_date_time(date.DateTime())
        self.assert_updated()
        self.bravo.set_completion_date_time(date.Now())  # Holds Charlie
        self.assert_updated()
        self.tasks.remove(self.alpha)
        self.assert_updated()
        self.tasks.append(task.Task(subject="Delta"))
        self.assert_updated()

    def test_icons_follow_the_tasks(self):
        # The first menu after a load has none: the first pass sets them
        for each in (self.alpha, self.bravo, self.charlie):
            gui.scheduler.MasterScheduler._process_task(each, date.Now())
        self.assert_updated()
        self.assertTrue(self.tracking_items()[0].get_image())

    def test_an_icon_the_clock_changes_follows(self):
        # Due soon, then overdue: the pass gives the status icon
        due = date.Now() + date.ONE_HOUR
        self.alpha.set_due_date_time(due)
        gui.scheduler.MasterScheduler._process_task(self.alpha, date.Now())
        self.icon._update_gtk_menu()
        wx.GetApp().ProcessPendingEvents()
        before = self.tracking_items()[0].get_image().get_icon_name()[0]
        gui.scheduler.MasterScheduler._process_task(
            self.alpha, due + date.ONE_HOUR
        )
        wx.GetApp().ProcessPendingEvents()  # The update it schedules
        after = self.tracking_items()[0].get_image().get_icon_name()[0]
        self.assertNotEqual(before, after)
        self.assertEqual(self.fresh_menu(), self.dump(self.menu()))

    def test_tracking_stopping_and_resuming(self):
        self.alpha.addEffort(effort.Effort(self.alpha))
        self.assert_updated()
        self.alpha.efforts()[0].setStop(date.Now())
        self.assert_updated()

    def test_templates(self):
        self.write_template("Weekly review")
        self.assert_updated()
        self.write_template("Annual review")
        self.assert_updated()

    def test_only_the_changed_item_is_touched(self):
        before = self.tracking_items()
        self.alpha.setSubject("Alpha 2")  # Still first
        self.icon._update_gtk_menu()
        after = self.tracking_items()
        self.assertEqual(
            ([True] * len(before), "Alpha 2"),
            ([a is b for a, b in zip(before, after)], after[0].get_label()),
        )

    def test_a_reloaded_task_is_not_the_old_one(self):
        # Same subject and id after a reload, another object
        self.tasks.remove(self.alpha)
        again = task.Task(subject="Alpha", id=self.alpha.id())
        self.tasks.append(again)
        self.icon._update_gtk_menu()
        with mock.patch.object(gui.taskbaricon.patterns.later, "soon") as soon:
            self.tracking_items()[0].activate()
        self.assertIs(again, soon.call_args[0][2])

    def test_a_tray_host_coming_makes_the_menu_anew(self):
        callback = self.indicator.on_connection_changed.call_args[0][0]
        self.indicator.is_connected.return_value = True
        with mock.patch.object(gui.taskbaricon.patterns.later, "soon"):
            callback()
        self.icon._update_gtk_menu()
        self.assertEqual(2, self.indicator.set_gtk_menu.call_count)

    def test_a_connection_notice_changing_nothing_keeps_the_menu(self):
        # Sent at the start too
        callback = self.indicator.on_connection_changed.call_args[0][0]
        callback()
        wx.GetApp().ProcessPendingEvents()
        self.assertEqual(1, self.indicator.set_gtk_menu.call_count)
