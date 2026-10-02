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

from taskcoachlib import (
    gui,
    config,
    persistence,
    command,
    mailer,
    patterns,
    render,
    operating_system,
    widgets,
)
from taskcoachlib.gui import viewer  # noqa: F401 - make gui.viewer accessible
from taskcoachlib.gui.icons import image_list_cache
from taskcoachlib.domain import task, date, effort, category, attachment
from taskcoachlib.domain.date import dateandtime
from taskcoachlib.i18n import _
from taskcoachlib.thirdparty import wxScheduler
from unittest import mock
import locale
import os
import test
import wx


class TaskViewerUnderTest(gui.viewer.task.TaskViewer):  # pylint: disable=W0223
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.events = []

    def on_attribute_changed(self, event):
        super().on_attribute_changed(event)
        self.events.append(event)


class TaskViewerTestCase(test.wxTestCase):
    tree_mode = "Subclass responsibility"

    def setUp(self):
        super().setUp()
        task.Task.settings = self.settings = config.Settings(load=False)
        # Late: planned a second ago, dates being whole seconds
        started = date.Now() - date.ONE_SECOND
        self.task = task.Task(subject="task", plannedStartDateTime=started)
        self.child = task.Task(subject="child", plannedStartDateTime=started)
        self.child.set_parent(self.task)
        self.taskFile = persistence.TaskFile()
        self.taskList = self.taskFile.tasks()
        self.parentFrame = wx.Frame(self.frame, wx.ID_ANY, "")
        self.viewer = TaskViewerUnderTest(
            self.parentFrame, self.taskFile, self.settings
        )
        self.viewer.sortBy("subject")
        self.viewer.setSortOrderAscending()
        self.viewer.setSortByTaskStatusFirst(True)
        self.viewer.set_tree_mode(self.tree_mode)
        self.newColor = (100, 200, 100, 255)
        attachment.Attachment.attdir = os.getcwd()
        if not operating_system.isGTK():
            self.originalLocale = locale.getlocale(locale.LC_ALL)
            tmpLocale = (
                os.environ["LC_ALL"]
                if "LC_ALL" in os.environ
                else ("en_US" if operating_system.isMac() else "")
            )
            locale.setlocale(locale.LC_ALL, tmpLocale)

    def tearDown(self):
        # As when its pane closes, and before super() destroys the
        # frames: a viewer being destroyed tests false, and a frame is
        # deleted only at idle time, which never comes here. A viewer
        # left attached keeps its menu ids, and they run out.
        self.viewer.detach()
        self.viewer.Destroy()
        self.viewer = None
        super().tearDown()
        if not operating_system.isGTK():
            locale.setlocale(locale.LC_ALL, self.originalLocale)
        attachment.Attachment.attdir = None
        self.taskFile.close()
        self.taskFile.stop()

        for name in os.listdir("."):
            if os.path.isdir(name) and name.endswith("_attachments"):
                os.rmdir(name)  # pragma: no cover

        if self.parentFrame:
            self.parentFrame.Close()
            wx.Yield()

    def assertItems(self, *tasks):
        self.viewer.expand_all()  # pylint: disable=E1101
        self.assertEqual(self.viewer.size(), len(tasks))
        for index, eachTask in enumerate(tasks):
            self.assertItem(index, eachTask)

    def assertItem(self, index, aTask):
        if type(aTask) == type(
            (),
        ):
            aTask, nrChildren = aTask
        else:
            nrChildren = 0
        subject = aTask.subject(recursive=not self.viewer.is_tree_viewer())
        treeItem = self.viewer.widget.GetItemChildren(recursively=True)[index]
        self.assertEqual(subject, self.viewer.widget.GetItemText(treeItem))
        self.assertEqual(
            nrChildren,
            self.viewer.widget.GetChildrenCount(treeItem, recursively=False),
        )

    def firstItem(self):
        widget = self.viewer.widget
        return widget.GetFirstChild(widget.GetRootItem())[0]

    def getItemText(self, row, column):
        assert row == 0
        return self.viewer.widget.GetItemText(self.firstItem(), column)

    def getFirstItemTextColor(self):
        return self.viewer.widget.GetItemTextColour(self.firstItem())

    def getFirstItemBackgroundColor(self):
        return self.viewer.widget.GetItemBackgroundColour(self.firstItem())

    def getFirstItemFont(self):
        return self.viewer.widget.GetItemFont(self.firstItem())

    def getFirstItemIcon(self, column=0):
        return self.viewer.widget.GetItemImage(self.firstItem(), column=column)

    def showColumn(self, columnName, show=True):
        self.viewer.showColumnByName(columnName, show)

    def setColor(self, setting):
        self.settings.settuple("fgcolor", setting, self.newColor)

    def run_style_pass(self):
        # Rows show the styles of the master loop's pass
        for each in self.taskList:
            test.styled(each)

    def assertColor(self, expectedColor=None):
        expectedColor = expectedColor or wx.Colour(*self.newColor)
        self.run_style_pass()
        self.assertEqual(expectedColor, self.getFirstItemTextColor())

    def assertBackgroundColor(self):
        self.run_style_pass()
        self.assertEqual(
            wx.Colour(*self.newColor), self.getFirstItemBackgroundColor()
        )

    def assertIcon(self, icon, column=0):
        self.run_style_pass()
        self.assertEqual(
            image_list_cache.get_index(icon), self.getFirstItemIcon(column)
        )


class EscapeKey:
    """A key event for Escape."""

    @staticmethod
    def GetKeyCode():
        return wx.WXK_ESCAPE

    @staticmethod
    def ShiftDown():
        return False

    def Skip(self):
        pass


class CommonTestsMixin(object):
    def fix_the_clock(self):
        """Noon today, for the test and the rendering alike: neither a
        run crossing midnight nor a test at 00:00 or 23:59, which render
        without the time, changes what "Today" shows (P115)."""
        noon = date.DateTime.now().replace(
            hour=12, minute=0, second=0, microsecond=0
        )
        for module in (date, dateandtime):
            patcher = mock.patch.object(module, "Now", lambda: noon)
            patcher.start()
            self.addCleanup(patcher.stop)

    def testCreate(self):
        self.assertItems()

    ## def testCollected(self):
    ##     filterRef = weakref.ref(self.viewer.presentation())
    ##     self.viewer.detach()
    ##     self.viewer = None
    ##     self.parentFrame.Close()
    ##     wx.Yield()
    ##     self.parentFrame = None

    ##     ## import gc
    ##     ## def printRef(obj, indent=0):
    ##     ##     if indent == 3:
    ##     ##         return
    ##     ##     if obj.__class__.__name__ in ['frame']:
    ##     ##         return
    ##     ##     print (' ' * indent), obj.__class__.__name__
    ##     ##     for ref in gc.get_referrers(obj):
    ##     ##         printRef(ref, indent + 1)
    ##     ## print
    ##     ## printRef(filterRef())
    ##     ## print '===', len(gc.get_referrers(filterRef()))

    ##     self.failUnless(filterRef() is None)

    def testAddTask(self):
        self.taskList.append(self.task)
        self.assertItems(self.task)

    def testRemoveTask(self):
        self.taskList.append(self.task)
        self.taskList.remove(self.task)
        self.assertItems()

    def testUndoRemoveTaskWithSubtask(self):
        self.task.addChild(self.child)
        self.taskList.append(self.task)
        self.viewer.select([self.task])
        self.viewer.updateSelection()
        self.viewer.deleteItemCommand().do()
        patterns.CommandHistory().undo()
        if self.viewer.is_tree_viewer():
            self.assertItems((self.task, 1), self.child)
        else:
            self.assertItems(self.child, self.task)

    def testDeleteSelectedTask(self):
        self.taskList.append(self.task)
        self.viewer.widget.select_all()
        self.viewer.updateSelection()
        self.taskList.removeItems(self.viewer.curselection())
        self.assertItems()

    def testSelectedTaskStaysSelectedWhenStartingEffortTracking(self):
        self.taskList.append(self.task)
        self.viewer.select([self.task])
        self.assertEqual([self.task], self.viewer.curselection())
        self.task.addEffort(effort.Effort(self.task))
        self.assertEqual([self.task], self.viewer.curselection())

    def testChildOrder(self):
        child1 = task.Task(
            subject="1", plannedStartDateTime=date.Now() - date.ONE_SECOND
        )
        self.task.addChild(child1)
        child2 = task.Task(
            subject="2", plannedStartDateTime=date.Now() - date.ONE_SECOND
        )
        self.task.addChild(child2)
        self.taskList.append(self.task)
        if self.viewer.is_tree_viewer():
            self.assertItems((self.task, 2), child1, child2)
        else:
            self.assertItems(child1, child2, self.task)

    def testChildSubjectRendering(self):
        self.task.addChild(self.child)
        self.taskList.append(self.task)
        if self.viewer.is_tree_viewer():
            self.assertItems((self.task, 1), self.child)
        else:
            self.assertItems(self.child, self.task)

    def testSortOrder(self):
        self.task.addChild(self.child)
        task2 = task.Task(subject="zzz")
        self.taskList.extend([self.task, task2])
        if self.viewer.is_tree_viewer():
            self.assertItems((self.task, 1), self.child, task2)
        else:
            self.assertItems(self.child, self.task, task2)

    def testMarkCompleted(self):
        task2 = task.Task(subject="task2")
        self.taskList.extend([self.task, task2])
        self.assertItems(self.task, task2)
        self.task.set_completion_date_time()
        self.assertItems(task2, self.task)

    def testMakeInactive(self):
        task2 = task.Task(
            subject="task2", plannedStartDateTime=date.Now() - date.ONE_SECOND
        )
        self.taskList.extend([self.task, task2])
        self.assertItems(self.task, task2)
        self.task.set_planned_start_date_time(date.Tomorrow())
        self.assertItems(task2, self.task)

    def testFilterCompletedTasks(self):
        self.viewer.hide_task_status(task.status.completed)
        completedChild = task.Task(
            completionDateTime=date.Now() - date.ONE_HOUR
        )
        notCompletedChild = task.Task(
            plannedStartDateTime=date.Now() - date.ONE_SECOND
        )
        self.task.addChild(notCompletedChild)
        self.task.addChild(completedChild)
        self.taskList.append(self.task)
        if self.viewer.is_tree_viewer():
            self.assertItems((self.task, 1), notCompletedChild)
        else:
            self.assertItems(notCompletedChild, self.task)

    def testUndoMarkCompletedWhenFilteringCompletedTasks(self):
        self.settings.setboolean(
            "behavior", "markparentcompletedwhenallchildrencompleted", True
        )
        self.viewer.hide_task_status(task.status.completed)
        child1 = task.Task("child1")
        child2 = task.Task("child2")
        grandChild = task.Task("grandChild")
        self.task.addChild(child1)
        self.task.addChild(child2)
        child2.addChild(grandChild)
        self.taskList.append(self.task)
        self.viewer.expand_all()
        self.assertEqual(4, self.viewer.size())
        markCompletedCommand = command.MarkCompletedCommand(
            self.taskList, [grandChild]
        )
        markCompletedCommand.do()
        self.assertEqual(2, self.viewer.size())
        patterns.CommandHistory().undo()
        self.assertEqual(4, self.viewer.size())

    def testFilterOnAllCategories(self):
        self.settings.setboolean("view", "categoryfiltermatchall", False)
        self.taskList.append(self.task)
        cat1 = category.Category("category 1")
        cat2 = category.Category("category 2")
        self.task.addCategory(cat1)
        self.taskFile.categories().extend([cat1, cat2])
        cat1.setFiltered(True)
        cat2.setFiltered(True)
        self.assertEqual(1, self.viewer.size())
        self.settings.setboolean("view", "categoryfiltermatchall", True)
        self.assertEqual(0, self.viewer.size())

    def testFilterOnAnyCategory(self):
        self.settings.setboolean("view", "categoryfiltermatchall", True)
        self.taskList.append(self.task)
        cat1 = category.Category("category 1")
        cat2 = category.Category("category 2")
        self.task.addCategory(cat1)
        self.taskFile.categories().extend([cat1, cat2])
        cat1.setFiltered(True)
        cat2.setFiltered(True)
        self.assertEqual(0, self.viewer.size())
        self.settings.setboolean("view", "categoryfiltermatchall", False)
        self.assertEqual(1, self.viewer.size())

    def testDefaultVisibleColumns(self):
        self.assertEqual(
            _("Subject"), self.viewer.widget.GetColumn(0).GetText()
        )
        self.assertEqual(
            _("Planned start date"), self.viewer.widget.GetColumn(1).GetText()
        )
        self.assertEqual(
            _("Due date"), self.viewer.widget.GetColumn(2).GetText()
        )
        self.assertEqual(3, self.viewer.widget.GetColumnCount())

    def testTurnOffPlannedStartDateColumn(self):
        self.showColumn("plannedStartDateTime", False)
        self.assertEqual(
            _("Due date"), self.viewer.widget.GetColumn(1).GetText()
        )
        self.assertEqual(2, self.viewer.widget.GetColumnCount())

    def testShowSort_Subject(self):
        self.assertNotEqual(-1, self.viewer.widget.GetColumn(0).GetImage())
        self.assertEqual(-1, self.viewer.widget.GetColumn(1).GetImage())

    def testForegroundColorWhenTaskIsCompleted(self):
        self.taskList.append(self.task)
        self.task.set_completion_date_time()
        newColor = self.task.statusFgColor()
        newColor = wx.Colour(newColor.Red(), newColor.Green(), newColor.Blue())
        self.assertColor(newColor)

    def testTurnColumnsOnAndOff(self):
        columns = dict(
            actualStartDateTime=(3, _("Actual start date")),
            hourlyFee=(3, _("Hourly fee")),
            fixedFee=(3, _("Fixed fee")),
            revenue=(3, _("Revenue")),
            priority=(3, _("Priority")),
            prerequisites=(1, _("Prerequisites")),
            dependencies=(1, _("Dependents")),
            categories=(1, _("Categories")),
            percentageComplete=(3, _("% complete")),
            recurrence=(3, _("Recurrence")),
            notes=(1, ""),
            attachments=(1, ""),
        )
        for column in columns:
            columnIndex, expectedHeader = columns[column]
            self.showColumn(column)
            actualHeader = self.viewer.widget.GetColumn(columnIndex).GetText()
            self.assertEqual(expectedHeader, actualHeader)
            self.showColumn(column, False)
            self.assertEqual(3, self.viewer.widget.GetColumnCount())

    def testRenderFixedFee(self):
        taskWithFixedFee = task.Task(fixedFee=100)
        self.taskList.append(taskWithFixedFee)
        self.showColumn("fixedFee")
        self.assertEqual(locale.currency(100, False), self.getItemText(0, 3))
        self.assertEqual(
            _("Fixed fee"), self.viewer.widget.GetColumn(3).GetText()
        )

    def testRenderPercentageComplete_0(self):
        uncompletedTask = task.Task()
        self.taskList.append(uncompletedTask)
        self.showColumn("percentageComplete")
        self.assertEqual("", self.getItemText(0, 3))

    def testRenderPercentageComplete_100(self):
        completedTask = task.Task(
            completionDateTime=date.Now() - date.ONE_HOUR
        )
        self.taskList.append(completedTask)
        self.showColumn("percentageComplete")
        self.assertEqual("100%", self.getItemText(0, 3))

    def testRenderSingleCategory(self):
        cat = category.Category(subject="Category")
        self.task.addCategory(cat)
        self.assertEqual("Category", self.viewer.renderCategories(self.task))

    def testRenderMultipleCategories(self):
        for index in range(1, 3):
            cat = category.Category(subject="Category %d" % index)
            self.task.addCategory(cat)
        self.assertEqual(
            "Category 1, Category 2", self.viewer.renderCategories(self.task)
        )

    def testRenderSingleChildCategory(self):
        self.task.addChild(self.child)
        self.taskList.append(self.task)
        cat = category.Category(subject="Category")
        self.child.addCategory(cat)
        expectedCategory = "(Category)" if self.viewer.is_tree_viewer() else ""
        self.assertEqual(
            expectedCategory, self.viewer.renderCategories(self.task)
        )

    def testRenderMultipleChildCategories(self):
        self.task.addChild(self.child)
        self.taskList.append(self.task)
        for index in range(1, 3):
            cat = category.Category(subject="Category %d" % index)
            self.child.addCategory(cat)
        expectedCategory = (
            "(Category 1, Category 2)" if self.viewer.is_tree_viewer() else ""
        )
        self.assertEqual(
            expectedCategory, self.viewer.renderCategories(self.task)
        )

    def testRenderDifferentParentAndChildCategories(self):
        self.task.addChild(self.child)
        self.taskList.append(self.task)
        for index, eachTask in enumerate([self.task, self.child]):
            cat = category.Category(subject="Category %d" % index)
            eachTask.addCategory(cat)
        expectedCategory = (
            "Category 0 (Category 1)"
            if self.viewer.is_tree_viewer()
            else "Category 0"
        )
        self.assertEqual(
            expectedCategory, self.viewer.renderCategories(self.task)
        )

    def testRenderSameParentAndChildCategory(self):
        self.task.addChild(self.child)
        self.taskList.append(self.task)
        cat = category.Category(subject="Category")
        for eachTask in (self.task, self.child):
            eachTask.addCategory(cat)
        expectedCategory = "Category"
        self.assertEqual(
            expectedCategory, self.viewer.renderCategories(self.task)
        )

    def testRenderRecurrence(self):
        taskWithRecurrence = task.Task(
            recurrence=date.Recurrence("weekly", amount=2)
        )
        self.showColumn("recurrence")
        self.taskList.append(taskWithRecurrence)
        self.assertEqual("Every other week", self.getItemText(0, 3))

    def testRenderAttachment(self):
        att = attachment.FileAttachment("whatever")
        self.task.addAttachment(att)
        self.taskList.append(self.task)
        self.showColumn("attachments")
        names = [column.name() for column in self.viewer.visibleColumns()]
        self.assertIcon(
            "nuvola_status_mail-attachment", column=names.index("attachments")
        )

    def testOneDayLeft(self):
        self.showColumn("timeLeft")
        timeLeft = date.TimeDelta(hours=25, seconds=30)
        self.taskList.append(self.task)
        self.task.set_due_date_time(date.Now() + timeLeft)
        self.assertEqual(
            render.timeLeft(timeLeft, False), self.getItemText(0, 3)
        )

    def testReverseSortOrderWithGrandchildren(self):
        self.task.addChild(self.child)
        grandchild = task.Task(
            subject="grandchild",
            plannedStartDateTime=date.Now() - date.ONE_SECOND,
        )
        self.child.addChild(grandchild)
        task2 = task.Task(
            subject="zzz", plannedStartDateTime=date.Now() - date.ONE_SECOND
        )
        self.taskList.extend([self.task, task2])
        self.viewer.setSortOrderAscending(False)
        if self.viewer.is_tree_viewer():
            self.assertItems(
                task2, (self.task, 1), (self.child, 1), grandchild
            )
        else:
            self.assertItems(task2, self.task, grandchild, self.child)

    def testReverseSortOrder(self):
        self.task.addChild(self.child)
        task2 = task.Task(
            subject="zzz", plannedStartDateTime=date.Now() - date.ONE_SECOND
        )
        self.taskList.extend([self.task, task2])
        self.viewer.setSortOrderAscending(False)
        if self.viewer.is_tree_viewer():
            self.assertItems(task2, (self.task, 1), self.child)
        else:
            self.assertItems(task2, self.task, self.child)

    def testSortByDueDate(self):
        self.task.addChild(self.child)
        task2 = task.Task(
            subject="zzz", plannedStartDateTime=date.Now() - date.ONE_SECOND
        )
        child2 = task.Task(
            subject="child 2",
            plannedStartDateTime=date.Now() - date.ONE_SECOND,
        )
        task2.addChild(child2)
        child2.set_parent(task2)
        self.taskList.extend([self.task, task2])
        if self.viewer.is_tree_viewer():
            self.assertItems((self.task, 1), self.child, (task2, 1), child2)
        else:
            self.assertItems(self.child, child2, self.task, task2)
        child2.set_due_date_time(date.Now().endOfDay())
        self.viewer.sortBy("dueDateTime")
        if self.viewer.is_tree_viewer():
            self.assertItems((task2, 1), child2, (self.task, 1), self.child)
        else:
            self.assertItems(child2, self.child, self.task, task2)

    def testSortByPrerequisite_OnePrerequisite(self):
        self.viewer.sortBy("prerequisites")
        prerequisite = task.Task()
        self.task.add_prerequisites([prerequisite])
        self.taskList.extend([prerequisite, self.task])
        self.assertItems(prerequisite, self.task)

    def testSortByPrerequisite_TwoPrerequisites(self):
        self.viewer.sortBy("prerequisites")
        prerequisite1 = task.Task(subject="1")
        prerequisite2 = task.Task(subject="2")
        self.task.add_prerequisites([prerequisite1, prerequisite2])
        self.taskList.extend([prerequisite1, prerequisite2, self.task])
        try:
            self.assertItems(prerequisite1, prerequisite2, self.task)
        except AssertionError:  # pragma: no cover
            self.assertItems(prerequisite2, prerequisite1, self.task)

    def testSortByPrerequisite_ChainedPrerequisites(self):
        self.viewer.sortBy("prerequisites")
        task0 = task.Task(subject="0")
        task1 = task.Task(subject="1")
        task2 = task.Task(subject="2")
        task2.add_prerequisites([task1])
        task1.add_prerequisites([task0])
        self.taskList.extend([task0, task1, task2])
        self.assertItems(task0, task1, task2)  # Prerequisites = '', '0', '1'
        self.viewer.setSortOrderAscending(False)
        self.assertItems(task2, task1, task0)  # Prerequisites = '1', '0', ''

    def testSortBySubject_AddPrerequisite(self):
        task0 = task.Task(
            subject="0", plannedStartDateTime=date.DateTime(2000, 1, 1)
        )
        task1 = task.Task(
            subject="1", plannedStartDateTime=date.DateTime(2000, 1, 1)
        )
        self.taskList.extend([task0, task1])
        self.assertItems(task0, task1)
        task0.add_prerequisites([task1])
        self.assertItems(task1, task0)

    def testSortByCategories(self):
        cat0 = category.Category(subject="Category 0")
        cat1 = category.Category(subject="Category 1")
        task0 = task.Task(subject="0")
        task1 = task.Task(subject="1")
        task0.addCategory(cat1)
        task1.addCategory(cat0)
        self.taskList.extend([task0, task1])
        self.assertItems(task0, task1)
        self.viewer.sortBy("categories")
        self.assertItems(task1, task0)

    def testSortByChildCategories(self):
        cat0 = category.Category(subject="Category 0")
        cat1 = category.Category(subject="Category 1")
        task0 = task.Task(subject="0")
        task1 = task.Task(subject="1")
        task1_1 = task.Task(subject="1.1")
        task1.addChild(task1_1)
        task0.addCategory(cat1)
        task1_1.addCategory(cat0)
        self.taskList.extend([task0, task1])
        if self.viewer.is_tree_viewer():
            self.assertItems(task0, (task1, 1), task1_1)
        else:
            self.assertItems(task0, task1, task1_1)
        self.viewer.sortBy("categories")
        if self.viewer.is_tree_viewer():
            self.assertItems((task1, 1), task1_1, task0)
        else:
            self.assertItems(task1, task1_1, task0)

    def testChangeActiveTaskForegroundColor(self):
        self.setColor("activetasks")
        self.taskList.append(
            task.Task(subject="test", actualStartDateTime=date.Now())
        )
        self.assertColor()

    def testChangeInactiveTaskForegroundColor(self):
        self.setColor("inactivetasks")
        self.taskList.append(task.Task())
        self.assertColor()

    def testChangeCompletedTaskForegroundColor(self):
        self.setColor("completedtasks")
        self.taskList.append(task.Task(completionDateTime=date.Now()))
        self.assertColor()

    def testChangeDueSoonTaskForegroundColor(self):
        self.setColor("duesoontasks")
        self.taskList.append(task.Task(dueDateTime=date.Now().endOfDay()))
        self.assertColor()

    def testChangeOverDueTaskForegroundColor(self):
        self.setColor("overduetasks")
        self.taskList.append(task.Task(dueDateTime=date.Yesterday()))
        self.assertColor()

    def testStatusMessage_EmptyTaskList(self):
        self.assertEqual(
            (
                "Tasks: 0 selected, 0 visible, 0 total",
                "Status: 0 overdue, 0 late, 0 inactive, 0 completed",
            ),
            self.viewer.statusMessages(),
        )

    def test_on_drop_files(self):
        aTask = task.Task()
        self.taskList.append(aTask)
        self.viewer.on_drop_files(aTask, ["filename"])
        self.assertEqual(
            ["filename"],
            [
                a.location()
                for a in self.viewer.presentation()[0].attachments()
            ],
        )

    def test_on_drop_url(self):
        aTask = task.Task()
        self.taskList.append(aTask)
        self.viewer.on_drop_url(aTask, "http://www.example.com/")
        self.assertEqual(
            ["http://www.example.com/"],
            [
                a.location()
                for a in self.viewer.presentation()[0].attachments()
            ],
        )

    def test_on_drop_mail(self):
        aTask = task.Task()
        self.taskList.append(aTask)
        self.viewer.on_drop_mail(
            aTask,
            [
                mailer.parse_mail(
                    b"Subject: foo\r\nMessage-ID: <1@example.com>\r\n\r\n"
                )
            ],
        )
        self.assertEqual(
            [("mid:1@example.com", "foo", "")],
            [
                (a.location(), a.subject(), a.description())
                for a in self.viewer.presentation()[0].attachments()
            ],
        )

    def testCategoryBackgroundColor(self):
        cat = category.Category(
            "category with background color", bgColor=self.newColor
        )
        self.task.addCategory(cat)
        self.taskList.append(self.task)
        self.assertBackgroundColor()

    def testNewItem(self):
        self.taskFile.categories().append(
            category.Category("cat", filtered=True)
        )
        dialog = self.viewer.newItemDialog(
            icon_id="nuvola_actions_document-new"
        )
        dialog._interior[4].selected()
        tree = dialog._interior[4].viewer.widget  # pylint: disable=W0212
        firstChild = tree.GetFirstChild(tree.GetRootItem())[0]
        self.assertTrue(firstChild.IsChecked())

    def test_category_icons_in_the_order_their_styles_apply(self):
        # Highest style priority first, equal ones by name
        icons = {
            "b": "nuvola_apps_clanbomber",
            "a": "nuvola_actions_document-new",
            "c": "nuvola_apps_kcmsystem",
        }
        categories = {}
        for subject, icon_id in icons.items():
            each = categories[subject] = category.Category(
                subject, icon=icon_id
            )
            each.setStylePriority(1 if subject == "c" else 0)
            self.task.addCategory(each)
            test.styled(each)
        self.assertEqual(
            [
                image_list_cache.get_index(categories[subject].icon_id())
                for subject in "cab"
            ],
            self.viewer.categoryIconsImageIndices(self.task),
        )

    def testFont(self):
        self.taskList.append(task.Task(font=wx.SWISS_FONT))
        self.assertEqual(wx.SWISS_FONT, self.getFirstItemFont())

    def testIconUpdatesWhenPlannedStartDateTimeChanges(self):
        self.taskList.append(self.task)
        self.task.set_planned_start_date_time(date.Now() + date.ONE_DAY)
        self.assertIcon(task.inactive.icon_id(self.settings))

    def testIconUpdatesWhenDueDateTimeChanges(self):
        self.taskList.append(self.task)
        self.task.set_due_date_time(date.Now() + date.ONE_HOUR)
        self.assertIcon(task.duesoon.icon_id(self.settings))

    def testIconUpdatesWhenCompletionDateTimeChanges(self):
        self.taskList.append(self.task)
        self.task.set_completion_date_time(date.Now())
        self.assertIcon(task.completed.icon_id(self.settings))

    def testIconUpdatesWhenPrerequisiteIsAdded(self):
        prerequisite = task.Task("zzz")
        self.taskList.extend([prerequisite, self.task])
        self.task.add_prerequisites([prerequisite])
        prerequisite.add_dependencies([self.task])
        self.assertIcon(task.inactive.icon_id(self.settings))

    def testIconUpdatesWhenPrerequisiteIsCompleted(self):
        prerequisite = task.Task(subject="zzz")
        self.taskList.extend([prerequisite, self.task])
        self.task.add_prerequisites([prerequisite])
        prerequisite.add_dependencies([self.task])
        prerequisite.set_completion_date_time(date.Now())
        self.assertIcon(task.late.icon_id(self.settings))

    def testIconUpdatesWhenEffortTrackingStarts(self):
        self.taskList.append(self.task)
        self.task.addEffort(effort.Effort(self.task))
        self.assertIcon("nuvola_apps_clock")

    def testIconUpdatesWhenEffortTrackingStops(self):
        self.taskList.append(self.task)
        self.task.addEffort(effort.Effort(self.task))
        self.task.stopTracking()
        self.assertIcon(task.active.icon_id(self.settings))

    def testIconUpdatesWhenTaskBecomesOverdue(self):
        dueDateTime = date.Now() + date.TimeDelta(seconds=10)
        self.task.set_due_date_time(dueDateTime)
        self.taskList.append(self.task)
        self.assertIcon(task.duesoon.icon_id(self.settings))
        now = dueDateTime + date.ONE_SECOND
        oldNow = date.Now
        date.Now = lambda: now
        self.task.compute_stored_status()
        self.assertIcon(task.overdue.icon_id(self.settings))
        date.Now = oldNow

    def testModeIsSavedInSettings(self):
        self.assertEqual(
            self.tree_mode,
            self.settings.getboolean(
                self.viewer.settingsSection(), "treemode"
            ),
        )

    def testRenderSubject(self):
        self.task.addChild(self.child)
        expectedSubject = "child" if self.tree_mode else "task -> child"
        self.assertEqual(
            expectedSubject, self.viewer.renderSubject(self.child)
        )

    def testItemOrder(self):
        self.task.addChild(self.child)
        self.taskList.append(self.task)
        if self.tree_mode:
            self.assertItems((self.task, 1), self.child)
        else:
            self.assertItems(self.child, self.task)

    def testItemOrderAfterSwitch(self):
        self.task.addChild(self.child)
        self.taskList.append(self.task)
        self.viewer.set_tree_mode(not self.tree_mode)
        if self.tree_mode:
            self.assertItems(self.child, self.task)
        else:
            self.assertItems((self.task, 1), self.child)

    def testItemOrderAfterSwitchWhenOrderDoesNotChange(self):
        self.task.addChild(self.child)
        self.taskList.append(self.task)
        self.task.setSubject("a")  # task comes before child
        self.viewer.set_tree_mode(not self.tree_mode)
        if self.tree_mode:
            self.assertItems(self.task, self.child)
        else:
            self.assertItems((self.task, 1), self.child)

    def assert_event_fired(self, type_):
        types = []
        for event in self.viewer.events:
            types.extend(event.types())
        self.assertTrue(
            type_ in types,
            '"%s" not in %s' % (type_, self.viewer.events),
        )

    def assert_change_received(self, event_type, value, source):
        received = [
            event.value(source, type=event_type)
            for event in self.viewer.events
            if source in event.sources(event_type)
        ]
        self.assertIn(value, received)

    def testGetTimeSpent(self):
        self.taskList.append(self.task)
        self.task.addEffort(
            effort.Effort(
                self.task, date.DateTime(2000, 1, 1), date.DateTime(2000, 1, 2)
            )
        )
        self.showColumn("timeSpent")
        timeSpent = self.getItemText(0, 3)
        self.assertEqual("24:00:00", timeSpent)

    def testGetTotalTimeSpent(self):
        self.task.addChild(self.child)
        self.taskList.append(self.task)
        self.task.expand(False, context=self.viewer.settingsSection())
        self.task.addEffort(
            effort.Effort(
                self.task, date.DateTime(2000, 1, 1), date.DateTime(2000, 1, 2)
            )
        )
        self.child.addEffort(
            effort.Effort(
                self.child,
                date.DateTime(2000, 1, 1),
                date.DateTime(2000, 1, 2),
            )
        )
        self.showColumn("timeSpent")
        timeSpent = self.getItemText(0, 3)
        expectedTimeSpent = "(48:00:00)" if self.tree_mode else "24:00:00"
        self.assertEqual(expectedTimeSpent, timeSpent)

    def testGetSelection(self):
        taskA = task.Task("a")
        taskB = task.Task("b")
        self.viewer.presentation().extend([taskA, taskB])
        self.viewer.select([taskA])
        self.viewer.updateSelection()
        self.assertEqual([taskA], self.viewer.curselection())

    def testGetSelection_AfterResort(self):
        taskA = task.Task("a")
        taskB = task.Task("b")
        self.viewer.presentation().extend([taskA, taskB])
        self.viewer.widget.select([taskA])
        self.viewer.updateSelection()
        self.viewer.setSortOrderAscending(False)
        self.assertEqual([taskA], self.viewer.curselection())

    def testChangeSubject(self):
        self.taskList.append(self.task)
        self.task.setSubject("New subject")
        self.assertEqual(
            task.Task.subjectChangedEventType(),
            self.viewer.events[0].type(),
        )

    def testChangePlannedStartDateTimeWhileColumnShown(self):
        self.taskList.append(self.task)
        newValue = date.Now() - date.ONE_DAY
        self.task.set_planned_start_date_time(newValue)
        self.assert_change_received(
            task.Task.plannedStartDateTimeChangedEventType(),
            newValue,
            self.task,
        )

    def test_a_status_changed_by_the_clock_is_no_viewer_status(self):
        # The viewer status means a selection change to its followers
        # (Effort for selected tasks); the status bar follows the
        # task statuses itself
        self.taskList.append(self.task)
        self.task.set_due_date_time(date.Now() + date.ONE_HOUR)
        statuses = test.ChangeRecorder(self.viewer.viewer_status_event_type())
        # The master loop, a day later: the task is overdue
        self.task.compute_stored_status(now=date.Now() + date.ONE_DAY)
        self.assertEqual([], statuses)

    def testStartTracking(self):
        self.taskList.append(self.task)
        self.task.addEffort(effort.Effort(self.task))
        self.assert_change_received(
            task.Task.trackingChangedEventType(), True, self.task
        )

    def test_change_planned_start_date_time_while_column_not_shown(self):
        self.taskList.append(self.task)
        self.showColumn("plannedStartDate", False)
        self.task.set_planned_start_date_time(date.Yesterday())
        # Still received once, for the subject column
        event_type = task.Task.plannedStartDateTimeChangedEventType()
        received = [
            event
            for event in self.viewer.events
            if event_type in event.types()
        ]
        self.assertEqual(1, len(received))

    def hide_this_column(self, column_name):
        # The menu records the right-clicked column when it opens;
        # where the pointer is at the click does not matter
        menu = gui.menu.ColumnPopupMenu(self.viewer)
        names = [column.name() for column in self.viewer.visibleColumns()]
        menu.columnIndex = names.index(column_name)
        return gui.uicommand.HideCurrentColumn(viewer=self.viewer, menu=menu)

    def test_hide_this_column_hides_the_column_right_clicked(self):
        self.showColumn("priority")
        hide = self.hide_this_column("priority")
        self.assertTrue(hide.enabled(None))
        hide.do_command(None)
        names = [column.name() for column in self.viewer.visibleColumns()]
        self.assertNotIn("priority", names)

    def test_hide_this_column_is_off_for_a_column_always_shown(self):
        self.assertFalse(self.hide_this_column("subject").enabled(None))

    def test_hiding_a_column_keeps_what_the_viewer_observes(self):
        # The viewer observes prerequisites for every row, the
        # prerequisites column too; hiding it drops only its own
        self.taskList.append(self.task)
        self.showColumn("prerequisites")
        self.showColumn("prerequisites", False)
        prerequisite = task.Task()
        self.taskList.append(prerequisite)
        self.task.add_prerequisites([prerequisite])
        event_type = task.Task.prerequisitesChangedEventType()
        self.assertTrue(
            [
                event
                for event in self.viewer.events
                if self.task in event.sources(event_type)
            ]
        )

    def testChangeDueDate(self):
        self.taskList.append(self.task)
        newValue = date.Now().endOfDay()
        self.task.set_due_date_time(newValue)
        self.assert_change_received(
            task.Task.dueDateTimeChangedEventType(), newValue, self.task
        )

    def test_change_shows_the_new_modification_date(self):
        self.taskList.append(self.task)
        self.showColumn("modificationDateTime")
        self.task.setSubject("New subject")
        self.assert_change_received(
            task.Task.modification_datetime_changed_event_type(),
            self.task.modificationDateTime(),
            self.task,
        )

    def testChangeCompletionDateWhileColumnNotShown(self):
        self.taskList.append(self.task)
        now = date.Now()
        self.task.set_completion_date_time(now)
        # We still get an event for the subject column:
        self.assert_change_received(
            task.Task.completionDateTimeChangedEventType(), now, self.task
        )

    def testChangeCompletionDateWhileColumnShown(self):
        self.taskList.append(self.task)
        self.showColumn("completionDate")
        now = date.Now()
        self.task.set_completion_date_time(now)
        self.assert_change_received(
            task.Task.completionDateTimeChangedEventType(), now, self.task
        )

    def test_change_percentage_complete_while_column_not_shown(self):
        self.taskList.append(self.task)
        self.task.setPercentageComplete(50)
        event_type = task.Task.percentageCompleteChangedEventType()
        self.assertFalse(
            [
                event
                for event in self.viewer.events
                if event_type in event.types()
            ]
        )

    def testChangePercentageCompleteWhileColumnShown(self):
        self.taskList.append(self.task)
        self.showColumn("percentageComplete")
        self.task.setPercentageComplete(50)
        self.assert_change_received(
            task.Task.percentageCompleteChangedEventType(), 50, self.task
        )

    def testChangePriorityWhileColumnNotShown(self):
        self.taskList.append(self.task)
        self.task.setPriority(10)
        # Priority changes are Publisher events
        self.assertFalse(self.viewer.events)

    def testChangePriorityWhileColumnShown(self):
        self.taskList.append(self.task)
        self.showColumn("priority")
        self.task.setPriority(10)
        # Priority changes are Publisher events
        self.assert_event_fired(task.Task.priorityChangedEventType())

    def testChangePriorityOfSubtask(self):
        self.showColumn("priority")
        self.task.addChild(self.child)
        self.taskList.append(self.task)
        self.child.setPriority(10)
        # The parent is a source of the child's Publisher event
        self.assertIn(
            self.task,
            self.viewer.events[-1].sources(
                task.Task.priorityChangedEventType()
            ),
        )

    def testChangeHourlyFeeWhileColumnShown(self):
        self.showColumn("hourlyFee")
        self.taskList.append(self.task)
        self.task.set_hourly_fee(100)
        self.assertEqual(render.monetaryAmount(100.0), self.getItemText(0, 3))

    def testChangeFixedFeeWhileColumnShown(self):
        self.showColumn("fixedFee")
        self.taskList.append(self.task)
        self.task.set_fixed_fee(200)
        self.assertEqual(render.monetaryAmount(200.0), self.getItemText(0, 3))

    def test_a_fee_typed_in_its_cell_is_stored_as_typed(self):
        self.showColumn("hourlyFee")
        self.taskList.append(self.task)
        main_window = self.viewer.widget.GetMainWindow()
        main_window.EditLabel(self.firstItem(), 3)
        editor = main_window._editCtrl
        amount = [
            child
            for child in editor.GetChildren()
            if isinstance(child, widgets.CurrencyCtrl)
        ][0]
        amount.ChangeValue("12.5")
        editor.AcceptChanges()
        self.assertEqual(12.5, self.task.hourlyFee())

    def edit_percentage_in_its_cell(self, percentage):
        self.showColumn("percentageComplete")
        self.taskList.append(self.task)
        main_window = self.viewer.widget.GetMainWindow()
        main_window.EditLabel(self.firstItem(), 3)
        editor = main_window._editCtrl
        editor.SetValue(percentage)
        return editor

    def test_a_cell_keeps_its_value_when_the_editing_stops(self):
        # The tree stops the editing at a click elsewhere
        self.edit_percentage_in_its_cell(60).StopEditing()
        self.assertEqual(60, self.task.percentageComplete())

    def test_escape_in_a_cell_cancels(self):
        editor = self.edit_percentage_in_its_cell(60)
        editor.OnKeyDown(EscapeKey())
        self.assertEqual(0, self.task.percentageComplete())

    def test_a_budget_entered_in_its_cell_is_stored(self):
        self.showColumn("budget")
        self.taskList.append(self.task)
        main_window = self.viewer.widget.GetMainWindow()
        main_window.EditLabel(self.firstItem(), 3)
        editor = main_window._editCtrl
        duration = [
            child
            for child in editor.GetChildren()
            if isinstance(child, widgets.MaskedDurationCtrl)
        ][0]
        duration.SetDuration(date.TimeDelta(hours=2, minutes=30))
        editor.AcceptChanges()
        self.assertEqual(
            date.TimeDelta(hours=2, minutes=30), self.task.budget()
        )

    def testCollapsedCompositeTaskShowsRecursiveFixedFee(self):
        self.showColumn("fixedFee")
        self.taskList.extend([self.task, self.child])
        self.task.addChild(self.child)
        self.task.set_fixed_fee(100)
        self.child.set_fixed_fee(200)
        self.viewer.setSortOrderAscending(False)
        expectedAmount = (
            "(%s)" % locale.currency(300, False)
            if self.tree_mode
            else locale.currency(100, False)
        )
        self.task.expand(False, context=self.viewer.settingsSection())
        self.assertEqual(expectedAmount, self.getItemText(0, 3))

    def testCollapsedCompositeTaskShowsRecursivePlannedStartDateTime(self):
        self.taskList.extend([self.task, self.child])
        self.task.addChild(self.child)
        now = date.Now()
        self.child.set_planned_start_date_time(now)
        self.task.set_planned_start_date_time(date.DateTime())
        self.viewer.setSortByTaskStatusFirst(False)
        self.viewer.setSortOrderAscending(False)
        expectedDateTime = (
            "(%s)" % render.dateTime(now, human_readable=True)
            if self.tree_mode
            else ""
        )
        self.task.expand(False, context=self.viewer.settingsSection())
        self.assertEqual(expectedDateTime, self.getItemText(0, 1))

    def testChangePrerequisiteSubject(self):
        self.showColumn("prerequisites")
        self.viewer.setSortOrderAscending(False)
        prerequisite = task.Task(subject="prerequisite")
        self.taskList.extend([self.task, prerequisite])
        self.task.add_prerequisites([prerequisite])
        prerequisite.add_dependencies([self.task])
        self.assertEqual("prerequisite", self.getItemText(0, 1))
        prerequisite.setSubject("new")
        self.assertEqual("new", self.getItemText(0, 1))

    def testChangeDependencySubject(self):
        self.showColumn("dependencies")
        self.viewer.setSortOrderAscending(False)
        dependency = task.Task(subject="dependency")
        self.taskList.extend([self.task, dependency])
        dependency.add_prerequisites([self.task])
        self.task.add_dependencies([dependency])
        self.assertEqual("dependency", self.getItemText(0, 1))
        dependency.setSubject("new")
        self.assertEqual("new", self.getItemText(0, 1))

    def testPlannedStartDateTimeToday(self):
        self.fix_the_clock()
        today = date.Now()
        self.task.set_planned_start_date_time(today)
        self.taskList.append(self.task)
        self.showColumn("plannedStartDateTime")
        self.assertEqual(
            _("Today %s") % render.time(today.time()), self.getItemText(0, 1)
        )

    def testPlannedStartDateTimeYesterday(self):
        self.fix_the_clock()
        yesterday = date.Yesterday()
        self.task.set_planned_start_date_time(yesterday)
        self.taskList.append(self.task)
        self.showColumn("plannedStartDateTime")
        self.assertEqual(
            _("Yesterday %s") % render.time(yesterday.time()),
            self.getItemText(0, 1),
        )

    def testPlannedStartDateTimeTomorrow(self):
        self.fix_the_clock()
        tomorrow = date.Tomorrow()
        self.task.set_planned_start_date_time(tomorrow)
        self.taskList.append(self.task)
        self.showColumn("plannedStartDateTime")
        self.assertEqual(
            _("Tomorrow %s") % render.time(tomorrow.time()),
            self.getItemText(0, 1),
        )

    def testPlannedStartDateToday(self):
        self.fix_the_clock()
        today = date.Now().startOfDay()
        self.task.set_planned_start_date_time(today)
        self.taskList.append(self.task)
        self.showColumn("plannedStartDateTime")
        self.assertEqual(_("Today"), self.getItemText(0, 1))

    def testPlannedStartDateYesterday(self):
        self.fix_the_clock()
        yesterday = date.Yesterday().startOfDay()
        self.task.set_planned_start_date_time(yesterday)
        self.taskList.append(self.task)
        self.showColumn("plannedStartDateTime")
        self.assertEqual(_("Yesterday"), self.getItemText(0, 1))

    def testPlannedStartDateTomorrow(self):
        self.fix_the_clock()
        tomorrow = date.Tomorrow().startOfDay()
        self.task.set_planned_start_date_time(tomorrow)
        self.taskList.append(self.task)
        self.showColumn("plannedStartDateTime")
        self.assertEqual(_("Tomorrow"), self.getItemText(0, 1))

    def testDueDateTimeToday(self):
        self.fix_the_clock()
        today = date.Now()
        self.task.set_due_date_time(today)
        self.taskList.append(self.task)
        self.showColumn("dueDateTime")
        self.assertEqual(
            _("Today %s") % render.time(today.time()), self.getItemText(0, 2)
        )

    def testDueDateTimeYesterday(self):
        self.fix_the_clock()
        yesterday = date.Yesterday()
        self.task.set_due_date_time(yesterday)
        self.taskList.append(self.task)
        self.showColumn("dueDateTime")
        self.assertEqual(
            _("Yesterday %s") % render.time(yesterday.time()),
            self.getItemText(0, 2),
        )

    def testDueDateTimeTomorrow(self):
        self.fix_the_clock()
        tomorrow = date.Tomorrow()
        self.task.set_due_date_time(tomorrow)
        self.taskList.append(self.task)
        self.showColumn("dueDateTime")
        self.assertEqual(
            _("Tomorrow %s") % render.time(tomorrow.time()),
            self.getItemText(0, 2),
        )

    def testDueDateToday(self):
        self.fix_the_clock()
        today = date.Now().startOfDay()
        self.task.set_due_date_time(today)
        self.taskList.append(self.task)
        self.showColumn("dueDateTime")
        self.assertEqual(_("Today"), self.getItemText(0, 2))

    def testDueDateYesterday(self):
        self.fix_the_clock()
        yesterday = date.Yesterday().startOfDay()
        self.task.set_due_date_time(yesterday)
        self.taskList.append(self.task)
        self.showColumn("dueDateTime")
        self.assertEqual(_("Yesterday"), self.getItemText(0, 2))

    def testDueDateTomorrow(self):
        self.fix_the_clock()
        tomorrow = date.Tomorrow().startOfDay()
        self.task.set_due_date_time(tomorrow)
        self.taskList.append(self.task)
        self.showColumn("dueDateTime")
        self.assertEqual(_("Tomorrow"), self.getItemText(0, 2))

    def testActualStartDateTimeToday(self):
        self.fix_the_clock()
        today = date.Now()
        self.task.set_actual_start_date_time(today)
        self.taskList.append(self.task)
        self.showColumn("actualStartDateTime")
        self.assertEqual(
            _("Today %s") % render.time(today.time()), self.getItemText(0, 3)
        )

    def testActualStartDateTimeYesterday(self):
        self.fix_the_clock()
        yesterday = date.Yesterday()
        self.task.set_actual_start_date_time(yesterday)
        self.taskList.append(self.task)
        self.showColumn("actualStartDateTime")
        self.assertEqual(
            _("Yesterday %s") % render.time(yesterday.time()),
            self.getItemText(0, 3),
        )

    def testActualStartDateTimeTomorrow(self):
        self.fix_the_clock()
        tomorrow = date.Tomorrow()
        self.task.set_actual_start_date_time(tomorrow)
        self.taskList.append(self.task)
        self.showColumn("actualStartDateTime")
        self.assertEqual(
            _("Tomorrow %s") % render.time(tomorrow.time()),
            self.getItemText(0, 3),
        )

    def testActualStartDateToday(self):
        self.fix_the_clock()
        today = date.Now().startOfDay()
        self.task.set_actual_start_date_time(today)
        self.taskList.append(self.task)
        self.showColumn("actualStartDateTime")
        self.assertEqual(_("Today"), self.getItemText(0, 3))

    def testActualStartDateYesterday(self):
        self.fix_the_clock()
        yesterday = date.Yesterday().startOfDay()
        self.task.set_actual_start_date_time(yesterday)
        self.taskList.append(self.task)
        self.showColumn("actualStartDateTime")
        self.assertEqual(_("Yesterday"), self.getItemText(0, 3))

    def testActualStartDateTomorrow(self):
        self.fix_the_clock()
        tomorrow = date.Tomorrow().startOfDay()
        self.task.set_actual_start_date_time(tomorrow)
        self.taskList.append(self.task)
        self.showColumn("actualStartDateTime")
        self.assertEqual(_("Tomorrow"), self.getItemText(0, 3))

    def testCompletionDateTimeToday(self):
        self.fix_the_clock()
        today = date.Now()
        self.task.set_completion_date_time(today)
        self.taskList.append(self.task)
        self.showColumn("completionDateTime")
        self.assertEqual(
            _("Today %s") % render.time(today.time()), self.getItemText(0, 3)
        )

    def testCompletionDateTimeYesterday(self):
        self.fix_the_clock()
        yesterday = date.Yesterday()
        self.task.set_completion_date_time(yesterday)
        self.taskList.append(self.task)
        self.showColumn("completionDateTime")
        self.assertEqual(
            _("Yesterday %s") % render.time(yesterday.time()),
            self.getItemText(0, 3),
        )

    def testCompletionDateTimeTomorrow(self):
        self.fix_the_clock()
        tomorrow = date.Tomorrow()
        self.task.set_completion_date_time(tomorrow)
        self.taskList.append(self.task)
        self.showColumn("completionDateTime")
        self.assertEqual(
            _("Tomorrow %s") % render.time(tomorrow.time()),
            self.getItemText(0, 3),
        )

    def testCompletionDateToday(self):
        self.fix_the_clock()
        today = date.Now().startOfDay()
        self.task.set_completion_date_time(today)
        self.taskList.append(self.task)
        self.showColumn("completionDateTime")
        self.assertEqual(_("Today"), self.getItemText(0, 3))

    def testCompletionDateYesterday(self):
        self.fix_the_clock()
        yesterday = date.Yesterday().startOfDay()
        self.task.set_completion_date_time(yesterday)
        self.taskList.append(self.task)
        self.showColumn("completionDateTime")
        self.assertEqual(_("Yesterday"), self.getItemText(0, 3))

    def testCompletionDateTomorrow(self):
        self.fix_the_clock()
        tomorrow = date.Tomorrow().startOfDay()
        self.task.set_completion_date_time(tomorrow)
        self.taskList.append(self.task)
        self.showColumn("completionDateTime")
        self.assertEqual(_("Tomorrow"), self.getItemText(0, 3))

    # Test all attributes...


class TaskViewerInTreeModeTest(CommonTestsMixin, TaskViewerTestCase):
    tree_mode = True


class TaskViewerInListModeTest(CommonTestsMixin, TaskViewerTestCase):
    tree_mode = False


class TaskCalendarViewerTest(test.wxTestCase):
    def setUp(self):
        super().setUp()
        task.Task.settings = self.settings = config.Settings(load=False)
        self.taskFile = persistence.TaskFile()
        self.frame.taskFile = self.taskFile
        self.viewer = gui.viewer.task.CalendarViewer(
            self.frame, self.taskFile, self.settings
        )
        self.originalTopWindow = wx.GetApp().TopWindow
        wx.GetApp().TopWindow = (
            self.frame
        )  # uiCommands use TopWindow to get the main window

    def tearDown(self):
        super().tearDown()
        wx.GetApp().TopWindow = self.originalTopWindow
        self.taskFile.close()
        self.taskFile.stop()

    def openDialogAndAssertDateTimes(
        self, dateTime, expectedPlannedStartDateTime, expectedDueDateTime
    ):
        self.viewer.onCreate(dateTime, show=False)
        newTask = list(self.taskFile.tasks())[0]
        self.assertEqual(
            expectedPlannedStartDateTime, newTask.plannedStartDateTime()
        )
        self.assertEqual(expectedDueDateTime, newTask.dueDateTime())

    def testOnCreateSetsPlannedStartAndDueDateTime(self):
        dateTime = date.DateTime(2010, 10, 10, 16, 0, 0)
        self.openDialogAndAssertDateTimes(dateTime, dateTime, dateTime)

    def test_week_start_applies_at_once(self):
        self.settings.settext("view", "weekstart", "sunday")
        self.assertEqual(
            wxScheduler.wxSCHEDULER_WEEKSTART_SUNDAY,
            self.viewer.widget.GetWeekStart(),
        )

    def test_gradient_applies_at_once(self):
        self.settings.setboolean("calendarviewer", "gradient", True)
        self.assertIs(
            wxScheduler.wxFancyDrawer, self.viewer.widget.GetDrawer()
        )

    def testOnCreateKeepsPlannedStartDateTimeAndMakesDueDateTimeEndOfDayWhenDateTimeIsStartOfDay(
        self,
    ):
        dateTime = date.DateTime(2010, 10, 1, 0, 0, 0)
        self.openDialogAndAssertDateTimes(
            dateTime, dateTime, dateTime.endOfDay()
        )

    def test_colours_follow_preferences(self):
        for section in ("calendar_light", "calendar_dark"):
            self.settings.setboolean(section, "other_month_bg_system", False)
            self.settings.setvalue(section, "other_month_bg", (1, 2, 3))
        patterns.Event("calendar.colours.changed", self.settings).send()
        self.assertEqual(
            wx.Colour(1, 2, 3), self.viewer.widget.GetOtherMonthColor()
        )


class TaskSquareMapViewerTest(test.wxTestCase):
    def testCreate(self):
        task.Task.settings = settings = config.Settings(load=False)
        self.taskFile = persistence.TaskFile()
        gui.viewer.task.SquareTaskViewer(self.frame, self.taskFile, settings)

    def tearDown(self):
        super().tearDown()
        self.taskFile.close()
        self.taskFile.stop()


class TaskTimelineViewerTest(test.wxTestCase):
    def testCreate(self):
        # pylint: disable-msg=W0201
        task.Task.settings = settings = config.Settings(load=False)
        self.taskFile = persistence.TaskFile()
        self.viewer = gui.viewer.task.TimelineViewer(
            self.frame, self.taskFile, settings
        )

    def test_no_icon_until_the_loop_styles_the_task(self):
        self.testCreate()
        self.assertIsNone(self.viewer.get_wx_icon(task.Task()))

    def tearDown(self):
        super().tearDown()
        self.taskFile.close()
        self.taskFile.stop()


class TaskStatisticsViewerTest(test.wxTestCase):
    def create_viewer(self):
        task.Task.settings = settings = config.Settings(load=False)
        self.taskFile = persistence.TaskFile()
        return gui.viewer.task.TaskStatsViewer(
            self.frame, self.taskFile, settings
        )

    def test_create(self):
        self.create_viewer()

    def record_redraws(self):
        stats_viewer = self.create_viewer()
        self.task = task.Task("task")
        self.taskFile.tasks().append(self.task)
        redraws = []
        stats_viewer.refresh = lambda: redraws.append(True)
        return redraws

    def test_the_pie_is_redrawn_once_after_a_pass(self):
        redraws = self.record_redraws()
        patterns.Event("scheduler.aboutToPass", self).send()
        for event_type in (
            task.Task.statusChangedEventType(),
            task.Task.effectiveFgColorChangedEventType(),
        ):
            patterns.Event(event_type, self.task, None).send()
        self.assertEqual([], redraws)
        patterns.Event("scheduler.pass", self).send()
        self.assertEqual([True], redraws)

    def test_the_pie_is_redrawn_after_a_bulk_change(self):
        # The pie has no rows to refresh: the viewer redraws it
        redraws = self.record_redraws()
        patterns.Event("command.aboutToBulkModify", self).send()
        patterns.Event(
            task.Task.effectiveFgColorChangedEventType(), self.task, None
        ).send()
        patterns.Event("command.justBulkModified", self).send()
        self.assertEqual([True], redraws)

    def tearDown(self):
        super().tearDown()
        self.taskFile.close()
        self.taskFile.stop()
