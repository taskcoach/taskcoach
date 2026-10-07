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

import subprocess
import wx
import test
from unittest import mock
from unittests import dummy
from taskcoachlib import gui, persistence
from taskcoachlib.domain import attachment, category, date, effort, note
from taskcoachlib.domain import task
from taskcoachlib.gui.dialog.editor import NoteEditor, TaskEditor
from taskcoachlib.gui.uicommand import base_uicommand
from taskcoachlib.tools import openfile
from taskcoachlib.config import settings


class UICommandTest(test.wxTestCase):
    def setUp(self):
        super().setUp()
        self.uicommand = dummy.DummyUICommand(menu_text="undo", bitmap="undo")
        self.menu = wx.Menu()
        self.frame = wx.Frame(None)
        self.frame.Show(False)
        self.frame.SetMenuBar(wx.MenuBar())
        self.frame.CreateToolBar()

    def activate(self, window, window_id):
        window.ProcessEvent(
            wx.CommandEvent(wx.wxEVT_COMMAND_MENU_SELECTED, window_id)
        )

    def test_append_to_menu(self):
        menu_id = self.uicommand.add_to_menu(self.menu, self.frame)
        self.assertEqual(menu_id, self.menu.FindItem(self.uicommand.menu_text))

    def test_append_to_tool_bar(self):
        tool_id = self.uicommand.append_to_toolbar(self.frame.GetToolBar())
        self.assertEqual(0, self.frame.GetToolBar().GetToolPos(tool_id))

    def test_activation_from_menu(self):
        menu_id = self.uicommand.add_to_menu(self.menu, self.frame)
        self.activate(self.frame, menu_id)
        self.assertTrue(self.uicommand.activated)

    def test_activation_from_tool_bar(self):
        menu_id = self.uicommand.append_to_toolbar(self.frame.GetToolBar())
        self.activate(self.frame.GetToolBar(), menu_id)
        self.assertTrue(self.uicommand.activated)

    def ask(self, item_id):
        """What wx asks when a menu opens or before a shortcut: the
        commands asked."""
        asked = []
        self.uicommand.enabled = lambda event: asked.append(event) or True
        self.frame.ProcessEvent(wx.UpdateUIEvent(item_id))
        return asked

    def test_a_menu_item_takes_its_state_from_its_command(self):
        menu_id = self.uicommand.add_to_menu(self.menu, self.frame)
        self.uicommand.enabled = lambda event: False
        self.menu.UpdateUI(self.frame)
        self.assertFalse(self.menu.IsEnabled(menu_id))
        self.uicommand.enabled = lambda event: True
        self.menu.UpdateUI(self.frame)
        self.assertTrue(self.menu.IsEnabled(menu_id))

    def test_a_menu_item_is_asked_until_removed(self):
        menu_id = self.uicommand.add_to_menu(self.menu, self.frame)
        self.assertEqual(1, len(self.ask(menu_id)))
        self.uicommand.remove_from_menu(self.menu, self.frame)
        self.assertEqual([], self.ask(menu_id))

    def test_a_toolbar_button_is_not_asked(self):
        tool_id = self.uicommand.append_to_toolbar(self.frame.GetToolBar())
        self.assertEqual([], self.ask(tool_id))


class wxTestCaseWithFrameAsTopLevelWindow(test.wxTestCase):
    def setUp(self):
        wx.GetApp().SetTopWindow(self.frame)
        self.taskFile = self.frame.taskFile = persistence.TaskFile()

    def tearDown(self):
        super().tearDown()
        self.taskFile.close()
        self.taskFile.stop()


class NewTaskWithSelectedCategoryTest(wxTestCaseWithFrameAsTopLevelWindow):
    def setUp(self):
        super().setUp()
        self.categories = self.taskFile.categories()
        self.categories.append(category.Category("cat"))
        self.viewer = gui.viewer.CategoryViewer(self.frame, self.taskFile)

    def createNewTask(self):
        task_new = gui.uicommand.NewTaskWithSelectedCategories(
            taskList=self.taskFile.tasks(),
            viewer=self.viewer,
            categories=self.categories,
        )
        dialog = task_new.do_command(None, show=False)
        self.assertTrue(isinstance(dialog, TaskEditor), dialog)
        dialog._interior[4].selected()
        tree = dialog._interior[4].viewer.widget
        return tree.GetFirstChild(tree.GetRootItem())[0]

    def selectFirstCategory(self):
        self.viewer.select([list(self.categories)[0]])

    def test_new_task_with_selected_category(self):
        self.selectFirstCategory()
        first_category_in_task_dialog = self.createNewTask()
        self.assertTrue(first_category_in_task_dialog.IsChecked())

    def test_new_task_without_selected_category(self):
        first_category_in_task_dialog = self.createNewTask()
        self.assertFalse(first_category_in_task_dialog.IsChecked())


class NewNoteWithSelectedCategoryTest(wxTestCaseWithFrameAsTopLevelWindow):
    def setUp(self):
        super().setUp()
        self.categories = self.taskFile.categories()
        self.categories.append(category.Category("cat"))
        self.viewer = gui.viewer.CategoryViewer(self.frame, self.taskFile)

    def createNewNote(self):
        note_new = gui.uicommand.NewNoteWithSelectedCategories(
            notes=self.taskFile.notes(),
            viewer=self.viewer,
            categories=self.categories,
        )
        dialog = note_new.do_command(None, show=False)
        self.assertTrue(isinstance(dialog, NoteEditor), dialog)
        dialog._interior[1].selected()
        tree = dialog._interior[1].viewer.widget
        return tree.GetFirstChild(tree.GetRootItem())[0]

    def selectFirstCategory(self):
        self.viewer.select([list(self.categories)[0]])

    def test_new_note_with_selected_category(self):
        self.selectFirstCategory()
        first_category_in_note_dialog = self.createNewNote()
        self.assertTrue(first_category_in_note_dialog.IsChecked())

    def test_new_note_without_selected_category(self):
        first_category_in_note_dialog = self.createNewNote()
        self.assertFalse(first_category_in_note_dialog.IsChecked())


class DummyTask(object):
    def subject(self, *args, **kwargs):  # pylint: disable=W0613
        return "subject"

    def customAttributes(self, section_name):
        return set()

    def description(self):
        return "description"


class DummyViewer(object):
    def __init__(
        self,
        selection=None,
        showing_effort=False,
        domain_objects_to_view=None,
        core_object_type="tasks",
    ):
        self.selection = selection or []
        self.showingEffort = showing_effort
        self.domainObjects = domain_objects_to_view
        self.coreObjectType = core_object_type

    @property
    def is_task(self):
        return self.coreObjectType == "tasks"

    @property
    def is_note(self):
        return self.coreObjectType == "notes"

    @property
    def is_category(self):
        return self.coreObjectType == "categories"

    @property
    def is_effort(self):
        return self.coreObjectType == "efforts"

    @property
    def is_attachment(self):
        return self.coreObjectType == "attachments"

    def curselection(self):
        return self.selection

    def is_showing_categories(self):
        return self.selection and isinstance(
            self.selection[0], category.Category
        )

    def is_showing_tasks(self):
        return False

    def is_showing_effort(self):
        return self.showingEffort


class MailTaskTest(test.TestCase):
    def test_exception(self):
        failures = iter(["first failure", "second failure"])

        def mail(*args, **kwargs):  # pylint: disable=W0613
            raise RuntimeError(next(failures))

        def showerror(*args, **kwargs):  # pylint: disable=W0613
            self.showerror = args  # pylint: disable=W0201

        # No recipient: the placeholder tried too; the first failure
        # tells more
        mail_task = gui.uicommand.Mail(viewer=DummyViewer([DummyTask()]))
        mail_task.do_command(None, mail=mail, showerror=showerror)
        self.assertEqual(
            "Cannot send email:\nfirst failure", self.showerror[0]
        )

    def mail_refusing(self, refused, items):
        """Mail the items with a mail program refusing the recipients
        in refused; return the recipients and copies it was given."""
        given = []
        self.shown = []  # pylint: disable=W0201

        def mail(to, subject, body, cc=None):
            given.append((to, cc))
            if to in refused:
                raise RuntimeError("refused")

        mail_task = gui.uicommand.Mail(viewer=DummyViewer(items))
        mail_task.do_command(
            None, mail=mail, showerror=lambda *a, **k: self.shown.append(a)
        )
        return given

    def test_no_recipient_refused_opens_again_to_the_placeholder(self):
        given = self.mail_refusing([set()], [DummyTask()])
        self.assertEqual(
            [(set(), set()), ("recipient@example.com", set())], given
        )

    def test_a_message_with_recipients_is_not_opened_again(self):
        task_with_recipient = DummyTask()
        task_with_recipient.customAttributes = lambda section: {
            "to=bob@example.org"
        }
        given = self.mail_refusing(
            [{"bob@example.org"}], [task_with_recipient]
        )
        self.assertEqual([({"bob@example.org"}, set())], given)
        self.assertEqual(1, len(self.shown))

    def test_body_formatting(self):
        a_task = task.Task("subject", description="line1\nline2\n")
        self.assertEqual(
            "line1\r\nline2",
            gui.uicommand.Mail(viewer=DummyViewer()).body([a_task]),
        )

    def test_body_of_several_tasks(self):
        first = task.Task("first", description="line1")
        second = task.Task("second")
        self.assertEqual(
            "first\r\nline1\r\n\r\nsecond",
            gui.uicommand.Mail(viewer=DummyViewer()).body([first, second]),
        )


class MarkActiveTest(test.TestCase):
    def assertMarkActiveIsEnabled(self, selection, should_be_enabled=True):
        viewer = DummyViewer(selection)
        mark_active = gui.uicommand.TaskMarkActive(viewer=viewer)
        is_enabled = mark_active.enabled(None)
        if should_be_enabled:
            self.assertTrue(is_enabled)
        else:
            self.assertFalse(is_enabled)

    def test_not_enabled_when_selection_is_empty(self):
        self.assertMarkActiveIsEnabled(selection=[], should_be_enabled=False)

    def test_enabled_when_selected_task_is_not_active(self):
        self.assertMarkActiveIsEnabled(selection=[task.Task()])

    def test_enabled_when_selected_task_is_active(self):
        self.assertMarkActiveIsEnabled(
            selection=[task.Task(actualStartDateTime=date.Now())],
            should_be_enabled=False,
        )

    def test_enabled_when_selected_tasks_are_both_active_and_inactive(self):
        self.assertMarkActiveIsEnabled(
            selection=[task.Task(actualStartDateTime=date.Now()), task.Task()]
        )


class MarkInactiveTest(test.TestCase):
    def assertMarkInactiveIsEnabled(self, selection, should_be_enabled=True):
        viewer = DummyViewer(selection)
        mark_inactive = gui.uicommand.TaskMarkInactive(viewer=viewer)
        is_enabled = mark_inactive.enabled(None)
        if should_be_enabled:
            self.assertTrue(is_enabled)
        else:
            self.assertFalse(is_enabled)

    def test_not_enabled_when_selection_is_empty(self):
        self.assertMarkInactiveIsEnabled(selection=[], should_be_enabled=False)

    def test_enabled_when_selected_task_is_not_inactive(self):
        self.assertMarkInactiveIsEnabled(
            selection=[task.Task(actualStartDateTime=date.Now())]
        )

    def test_enabled_when_selected_task_is_inactive(self):
        self.assertMarkInactiveIsEnabled(
            selection=[task.Task()], should_be_enabled=False
        )

    def test_enabled_when_selected_tasks_are_both_active_and_inactive(self):
        self.assertMarkInactiveIsEnabled(
            selection=[task.Task(actualStartDateTime=date.Now()), task.Task()]
        )


class MarkCompletedTest(test.TestCase):
    def assertMarkCompletedIsEnabled(self, selection, should_be_enabled=True):
        viewer = DummyViewer(selection)
        mark_completed = gui.uicommand.TaskMarkCompleted(viewer=viewer)
        is_enabled = mark_completed.enabled(None)
        if should_be_enabled:
            self.assertTrue(is_enabled)
        else:
            self.assertFalse(is_enabled)

    def test_not_enabled_when_selection_is_empty(self):
        self.assertMarkCompletedIsEnabled(
            selection=[], should_be_enabled=False
        )

    def test_enabled_when_selected_task_is_not_completed(self):
        self.assertMarkCompletedIsEnabled(selection=[task.Task()])

    def test_enabled_when_selected_task_is_completed(self):
        self.assertMarkCompletedIsEnabled(
            selection=[task.Task(completionDateTime=date.Now())],
            should_be_enabled=False,
        )

    def test_enabled_when_selected_tasks_are_both_completed_and_uncompleted(
        self,
    ):
        self.assertMarkCompletedIsEnabled(
            selection=[task.Task(completionDateTime=date.Now()), task.Task()]
        )


class TaskNewTest(wxTestCaseWithFrameAsTopLevelWindow):
    def test_new_task_with_categories(self):
        cat = category.Category("cat", filtered=True)
        self.taskFile.categories().append(cat)
        task_new = gui.uicommand.TaskNew(taskList=self.taskFile.tasks())
        dialog = task_new.do_command(None, show=False)
        dialog._interior[4].selected()
        tree = dialog._interior[4].viewer.widget
        first_child = tree.GetFirstChild(tree.GetRootItem())[0]
        self.assertTrue(first_child.IsChecked())

    def test_new_task_with_preset_planned_start_date_time(self):
        settings.set(
            "view",
            "defaultplannedstartdatetime",
            "preset_tomorrow_endofworkingday",
        )
        task_new = gui.uicommand.TaskNew(taskList=self.taskFile.tasks())
        task_new.do_command(None, show=False)
        self.assertFalse(
            date.DateTime()
            == list(self.taskFile.tasks())[0].plannedStartDateTime()
        )

    def test_new_task_with_proposed_planned_start_date_time(self):
        settings.set(
            "view",
            "defaultplannedstartdatetime",
            "propose_tomorrow_endofworkingday",
        )
        task_new = gui.uicommand.TaskNew(taskList=self.taskFile.tasks())
        task_new.do_command(None, show=False)
        self.assertEqual(
            date.DateTime(),
            list(self.taskFile.tasks())[0].plannedStartDateTime(),
        )

    def test_new_task_with_preset_due_date_time(self):
        settings.set(
            "view", "defaultduedatetime", "preset_tomorrow_endofworkingday"
        )
        task_new = gui.uicommand.TaskNew(taskList=self.taskFile.tasks())
        task_new.do_command(None, show=False)
        self.assertFalse(
            date.DateTime() == list(self.taskFile.tasks())[0].dueDateTime()
        )

    def test_new_task_with_preset_reminder_date_time(self):
        settings.set(
            "view",
            "defaultreminderdatetime",
            "preset_tomorrow_endofworkingday",
        )
        task_new = gui.uicommand.TaskNew(taskList=self.taskFile.tasks())
        task_new.do_command(None, show=False)
        self.assertFalse(
            date.DateTime() == list(self.taskFile.tasks())[0].reminder()
        )


class NoteNewTest(wxTestCaseWithFrameAsTopLevelWindow):
    def test_new_note_with_categories(self):
        cat = category.Category("cat", filtered=True)
        self.taskFile.categories().append(cat)
        note_new = gui.uicommand.NoteNew(notes=self.taskFile.notes())
        dialog = note_new.do_command(None, show=False)
        dialog._interior[1].selected()
        tree = dialog._interior[1].viewer.widget
        first_child = tree.GetFirstChild(tree.GetRootItem())[0]
        self.assertTrue(first_child.IsChecked())


class EffortNewTest(wxTestCaseWithFrameAsTopLevelWindow):
    def test_new_effort_uses_task_of_selected_effort(self):
        task1 = task.Task("task 1")
        task2 = task.Task("task 2")
        effort_task2 = effort.Effort(task2)
        task2.addEffort(effort_task2)
        self.taskFile.tasks().extend([task1, task2])
        viewer = DummyViewer(
            task2.efforts(),
            showing_effort=True,
            domain_objects_to_view=self.taskFile.tasks(),
        )
        effort_new = gui.uicommand.EffortNew(
            effortList=self.taskFile.efforts(),
            taskList=self.taskFile.tasks(),
            viewer=viewer,
        )
        dialog = effort_new.do_command(None, show=False)
        for each_effort in dialog._items:
            self.assertEqual(task2, each_effort.task())


class EditPreferencesTest(test.TestCase):
    def test_edit_preferences(self):
        self.set_main_window_task_file()
        edit_preferences = gui.uicommand.EditPreferences()
        edit_preferences.do_command(None, show=False)
        # No assert, just checking whether it works without exceptions


class EffortViewerAggregationChoiceTest(test.TestCase):
    def setUp(self):
        self.choice = gui.uicommand.EffortViewerAggregationChoice(viewer=self)
        self.choice.currentChoice = 0

        class DummyEvent(object):
            def __init__(self, selection):
                self.selection = selection

            def GetInt(self):
                return self.selection

        self.DummyEvent = DummyEvent

    def settingsSection(self):
        return "effortviewer"

    # The viewer interface EffortViewerAggregationChoice uses:

    aggregation = "details"

    def set_aggregation(self, aggregation):
        settings.set(self.settingsSection(), "aggregation", aggregation)

    def registerObserver(self, *args, **kwargs):
        pass

    def view_settings_changed_event_type(self):
        return "view.settings"

    def test_user_picks_effort_per_day(self):
        self.choice.onChoice(self.DummyEvent(1))
        self.assertEqual(
            "day", settings.get(self.settingsSection(), "aggregation")
        )

    def test_user_picks_effort_per_week(self):
        self.choice.onChoice(self.DummyEvent(2))
        self.assertEqual(
            "week",
            settings.get(self.settingsSection(), "aggregation"),
        )

    def test_user_picks_effort_per_month(self):
        self.choice.onChoice(self.DummyEvent(3))
        self.assertEqual(
            "month",
            settings.get(self.settingsSection(), "aggregation"),
        )

    def test_set_choice(self):
        class DummyToolBar(wx.Frame):
            def AddControl(self, *args, **kwargs):
                pass

        self.choice.append_to_toolbar(DummyToolBar(None))
        self.choice.set_choice("week")
        self.assertEqual(
            "Effort per week", self.choice.choiceCtrl.GetStringSelection()
        )
        self.assertEqual(2, self.choice.currentChoice)


class OpenAllAttachmentsTest(test.TestCase):
    def setUp(self):
        self.viewer = DummyViewer([task.Task("Task")])
        self.openAll = gui.uicommand.OpenAllAttachments(viewer=self.viewer)
        self.errorArgs = self.errorKwargs = None

    def showerror(self, *args, **kwargs):  # pragma: no cover
        self.errorArgs = args
        self.errorKwargs = kwargs

    def test_no_attachments(self):
        self.openAll.do_command(None)

    @test.skipOnPlatform("__WXMAC__")
    def test_nonexisting_attachment(self):  # pragma: no cover
        self.viewer.selection[0].addAttachment(
            attachment.FileAttachment("Attachment")
        )
        # xdg-open's status for a missing file; running it would open a
        # file manager on some desktops
        missing = subprocess.CompletedProcess([], returncode=2)
        with mock.patch.object(
            openfile.subprocess, "run", return_value=missing
        ):
            self.openAll.do_command(None, showerror=self.showerror)
        # Don't test the error message itself, it differs per platform
        self.assertEqual(
            dict(caption="Error opening attachment", style=wx.ICON_ERROR),
            self.errorKwargs,
        )

    def test_multiple_attachments(self):
        class DummyAttachment(object):
            def __init__(self):
                self.openCalled = False

            def open(self, attachment_base):  # pylint: disable=W0613
                self.openCalled = True

            def modified_now(self, event=None):
                pass  # Adding it dates it, as an attachment's

        dummy_attachment_1 = DummyAttachment()
        dummy_attachment_2 = DummyAttachment()
        self.viewer.selection[0].addAttachment(dummy_attachment_1)
        self.viewer.selection[0].addAttachment(dummy_attachment_2)
        self.openAll.do_command(None)
        self.assertTrue(
            dummy_attachment_1.openCalled and dummy_attachment_2.openCalled
        )


class ToggleCategoryTest(test.TestCase):
    def setUp(self):
        self.category = category.Category("Category")

    def test_enable_when_viewer_is_showing_categorizables(self):
        viewer = DummyViewer(selection=[task.Task("Task")])
        ui_command = gui.uicommand.ToggleCategory(
            viewer=viewer, category=self.category
        )
        self.assertTrue(ui_command.enabled(None))

    def test_disable_when_viewer_is_showing_categories(self):
        viewer = DummyViewer(selection=[self.category])
        ui_command = gui.uicommand.ToggleCategory(
            viewer=viewer, category=self.category
        )
        self.assertFalse(ui_command.enabled(None))

    def test_disable_when_selection_is_empty(self):
        viewer = DummyViewer(selection=[])
        ui_command = gui.uicommand.ToggleCategory(
            viewer=viewer, category=self.category
        )
        self.assertFalse(ui_command.enabled(None))

    def test_disabled_when_category_has_unchecked_exclusive_ancestor(
        self,
    ):
        parent_category = category.Category(
            "Parent of mutual exclusive categories",
            exclusiveSubcategories=True,
        )
        child_category = category.Category("Mutual exclusive category")
        parent_category.addChild(child_category)
        child_category.set_parent(parent_category)
        child_category.addChild(self.category)
        self.category.set_parent(child_category)
        task_with_category = task.Task("Task")
        task_with_category.addCategory(self.category)
        viewer = DummyViewer(selection=[task_with_category])
        ui_command = gui.uicommand.ToggleCategory(
            viewer=viewer, category=self.category
        )
        self.assertFalse(ui_command.enabled(None))


class EffortStopTest(test.TestCase):
    def setUp(self):
        super().setUp()
        self.taskList = task.TaskList()
        self.task = task.Task("Task")
        self.task2 = task.Task("Task 2")
        self.effort1 = effort.Effort(self.task)
        self.effort2 = effort.Effort(self.task)
        self.taskList.append(self.task)
        self.effortList = effort.EffortList(self.taskList)
        self.viewer = DummyViewer()
        self.effortStop = gui.uicommand.EffortStop(
            viewer=self.viewer,
            effortList=self.effortList,
            taskList=self.taskList,
        )

    # Tests of EffortStop.enabled()

    def test_stop_is_not_enabled_by_default(self):
        self.assertFalse(self.effortStop.enabled())

    def test_stop_is_enabled_when_effort_is_tracked(self):
        self.task.addEffort(self.effort1)
        self.assertTrue(self.effortStop.enabled())

    def test_stop_resume_is_enabled_when_effort_is_tracked(self):
        self.task.addEffort(self.effort1)
        self.effort1.setStop(date.Now())
        self.assertTrue(self.effortStop.enabled())

    def test_stop_is_disabled_when_efforts_is_deleted(self):
        self.task.addEffort(self.effort1)
        self.task.removeEffort(self.effort1)
        self.assertFalse(self.effortStop.enabled())

    def test_stop_is_enabled_when_two_efforts_are_tracked(self):
        self.task.addEffort(self.effort1)
        self.task.addEffort(self.effort2)
        self.assertTrue(self.effortStop.enabled())

    def test_stop_is_enabled_when_one_of_two_efforts_is_stopped(self):
        self.task.addEffort(self.effort1)
        self.task.addEffort(self.effort2)
        self.effort1.setStop(date.Now())
        self.assertTrue(self.effortStop.enabled())

    def test_stop_is_enabled_when_one_of_two_efforts_is_deleted(self):
        self.task.addEffort(self.effort1)
        self.task.addEffort(self.effort2)
        self.task.removeEffort(self.effort1)
        self.assertTrue(self.effortStop.enabled())

    def test_pause_is_enabled_when_both_efforts_are_stopped(self):
        self.task.addEffort(self.effort1)
        self.task.addEffort(self.effort2)
        self.effort1.setStop(date.Now())
        self.effort2.setStop(date.Now())
        self.assertTrue(self.effortStop.enabled())

    def test_stop_is_disabled_when_both_efforts_are_deleted(self):
        self.task.addEffort(self.effort1)
        self.task.addEffort(self.effort2)
        self.task.removeEffort(self.effort1)
        self.task.removeEffort(self.effort2)
        self.assertFalse(self.effortStop.enabled())

    def test_stop_is_disabled_when_task_is_deleted(self):
        self.task.addEffort(self.effort1)
        self.taskList.remove(self.task)
        self.assertFalse(self.effortStop.enabled())

    def test_stop_enabled_after_deleting_one_of_two_tracked_tasks(
        self,
    ):
        self.task.addEffort(self.effort1)
        self.task2.addEffort(effort.Effort(self.task2))
        self.taskList.append(self.task2)
        self.taskList.remove(self.task)
        self.assertTrue(self.effortStop.enabled())

    def test_stop_is_enabled_when_a_task_with_tracked_effort_is_added(self):
        self.task2.addEffort(effort.Effort(self.task2))
        self.taskList.append(self.task2)
        self.assertTrue(self.effortStop.enabled())

    def test_stop_is_enabled_when_a_tracked_effort_is_moved(self):
        self.task.addEffort(self.effort1)
        self.taskList.append(self.task2)
        self.effort1.set_task(self.task2)
        self.assertTrue(self.effortStop.enabled())

    def test_ignore_composite_efforts(self):
        effort.reducer.EffortAggregator(self.taskList, aggregation="day")
        self.task.addEffort(self.effort1)
        self.assertFalse("multiple tasks" in self.effortStop.get_menu_text())

    # Tests of EffortStop.do_command()

    def test_do_command_stops_tracked_effort(self):
        self.task.addEffort(self.effort1)
        self.effortStop.do_command()
        self.assertFalse(self.effort1.isBeingTracked())

    def test_do_command_stops_all_tracked_effort(self):
        self.task.addEffort(self.effort1)
        self.task.addEffort(self.effort2)
        self.effortStop.do_command()
        self.assertFalse(self.task.isBeingTracked())


class AttachmentTest(test.wxTestCase):
    def setUp(self):
        super().setUp()

        task_file = persistence.TaskFile()
        self.task = task.Task()
        task_file.tasks().extend([self.task])
        self.attachment = attachment.FileAttachment("Test")
        self.task.addAttachment(self.attachment)
        self.viewer = gui.dialog.editor.LocalAttachmentViewer(
            self.frame,
            task_file,
            owner=self.task,
            settingsSection="attachmentviewer",
        )

    def select(self):
        self.viewer.widget.select_all()
        self.viewer.updateSelection()
        # Without this tests fail on Fedora 14
        self.viewer.SetFocus()

    def test_delete(self):
        self.select()
        cmd = gui.uicommand.Delete(viewer=self.viewer)
        cmd.do_command(None)
        self.assertEqual(self.task.attachments(), [])

    def test_cut(self):
        self.select()
        cmd = gui.uicommand.EditCut(viewer=self.viewer)
        cmd.do_command(None)
        self.assertEqual(self.task.attachments(), [])

    def test_cutpaste(self):
        self.test_cut()
        cmd = gui.uicommand.EditPaste(viewer=self.viewer)
        cmd.do_command(None)
        # A pasted attachment is a copy: compare locations
        self.assertEqual(
            [self.attachment.location()],
            [each.location() for each in self.task.attachments()],
        )


class CategoryInUseTextTest(wxTestCaseWithFrameAsTopLevelWindow):
    def test_a_note_shows_its_owners_from_the_top(self):
        garden = task.Task(subject="Garden")
        plan = attachment.FileAttachment("plan.txt")
        tools = note.Note(subject="Tools")
        plan.addNote(tools)
        garden.addAttachments(plan)
        self.taskFile.tasks().append(garden)
        self.assertEqual(
            "[Task] Garden -> [Attachment] plan -> [Note] Tools",
            gui.uicommand.Delete._get_object_display_path(
                tools, self.taskFile.owner_chains()
            ),
        )


class Selection:
    """A viewer, as far as a viewer command asks it what it acts on."""

    def __init__(self, *items):
        self.items = list(items)

    def curselection(self):
        return self.items


class OpenWindow(gui.uicommand.ViewerCommand):
    """Opens a window for the selected items, as Edit does."""

    def __init__(self, *args, **kwargs):
        self.windows = []
        super().__init__(menu_text="open", *args, **kwargs)

    def do_command(self, event):
        window = wx.Frame(None)
        self.windows.append(window)


class Count(gui.uicommand.ViewerCommand):
    """Opens no window, as a priority + button."""

    def __init__(self, *args, **kwargs):
        self.runs = 0
        super().__init__(menu_text="count", *args, **kwargs)

    def do_command(self, event):
        self.runs += 1


class SameWindowThrottleTest(test.wxTestCase):
    """The same window opens at most once a second: a held key, or
    presses queued while the system is busy, would open one per press
    (docs/MENUS.md#the-same-window-once-a-second)."""

    def setUp(self):
        super().setUp()
        throttle = mock.patch.object(
            base_uicommand,
            "_same_window",
            base_uicommand._SameWindowThrottle(),
        )
        throttle.start()
        self.addCleanup(throttle.stop)
        self.now = 100.0
        clock = mock.patch.object(
            base_uicommand, "time", mock.Mock(monotonic=lambda: self.now)
        )
        clock.start()
        self.addCleanup(clock.stop)
        self.task = task.Task()

    def open_window(self, *items):
        command = OpenWindow(viewer=Selection(*items))
        self.addCleanup(
            lambda: [window.Destroy() for window in command.windows]
        )
        return command

    def test_the_same_window_opens_once(self):
        command = self.open_window(self.task)
        for _ in range(5):
            command(None)
        self.assertEqual(1, len(command.windows))

    def test_the_same_window_opens_again_a_second_later(self):
        command = self.open_window(self.task)
        command(None)
        self.now += 1.0
        command(None)
        self.assertEqual(2, len(command.windows))

    def test_within_the_second_it_stays_held_back(self):
        command = self.open_window(self.task)
        command(None)
        self.now += 0.9
        command(None)
        self.assertEqual(1, len(command.windows))

    def test_another_items_window_opens(self):
        command = self.open_window(self.task)
        command(None)
        command.viewer.items = [task.Task()]
        command(None)
        self.assertEqual(2, len(command.windows))

    def test_a_new_command_for_the_same_items_is_held_back(self):
        # The calendar makes a new Edit for each edit
        first = self.open_window(self.task)
        second = self.open_window(self.task)
        first(None)
        second(None)
        self.assertEqual(0, len(second.windows))

    def new_task_key(self, **keywords):
        command = gui.uicommand.TaskNew(
            taskList=task.TaskList(),
            taskKeywords=keywords,
        )
        return command.same_window_key()

    def test_a_new_task_for_another_calendar_slot_is_another_window(self):
        self.assertNotEqual(
            self.new_task_key(dueDateTime=date.DateTime(2026, 10, 2, 9)),
            self.new_task_key(dueDateTime=date.DateTime(2026, 10, 2, 10)),
        )

    def test_a_new_task_for_the_same_slot_is_the_same_window(self):
        self.assertEqual(
            self.new_task_key(dueDateTime=date.DateTime(2026, 10, 2, 9)),
            self.new_task_key(dueDateTime=date.DateTime(2026, 10, 2, 9)),
        )

    def test_a_command_opening_no_window_is_not_held_back(self):
        command = Count(viewer=Selection(self.task))
        for _ in range(5):
            command(None)
        self.assertEqual(5, command.runs)


class TaskViewerStub(DummyViewer):
    def is_showing_tasks(self):
        return True


class TrackingOneTaskTest(test.TestCase):
    """Start tracking and New effort take one task
    (docs/EFFORTS.md, Tracking)."""

    def setUp(self):
        super().setUp()
        self.task_list = task.TaskList()
        self.tasks = [task.Task("A"), task.Task("B")]
        self.task_list.extend(self.tasks)
        self.effort_list = effort.EffortList(self.task_list)

    def test_start_takes_one_task(self):
        for selection, enabled in (
            (self.tasks[:1], True),
            (self.tasks, False),
        ):
            with self.subTest(selection=len(selection)):
                start = gui.uicommand.EffortStart(
                    viewer=DummyViewer(selection), taskList=self.task_list
                )
                self.assertEqual(enabled, start.enabled(None))

    def test_start_from_efforts_of_one_task(self):
        efforts = [
            effort.Effort(
                each, date.DateTime(2026, 1, 1), date.DateTime(2026, 1, 2)
            )
            for each in self.tasks
        ]
        for each, an_effort in zip(self.tasks, efforts):
            each.addEffort(an_effort)
        for selection, enabled in ((efforts[:1], True), (efforts, False)):
            with self.subTest(selection=len(selection)):
                start = gui.uicommand.EffortStartForEffort(
                    viewer=DummyViewer(
                        selection,
                        showing_effort=True,
                        core_object_type="efforts",
                    ),
                    taskList=self.task_list,
                )
                self.assertEqual(enabled, start.enabled(None))

    def test_new_effort_takes_one_task(self):
        for selection, enabled in (
            (self.tasks[:1], True),
            (self.tasks, False),
        ):
            with self.subTest(selection=len(selection)):
                new = gui.uicommand.EffortNew(
                    viewer=TaskViewerStub(selection),
                    effortList=self.effort_list,
                    taskList=self.task_list,
                )
                self.assertEqual(enabled, new.enabled(None))
