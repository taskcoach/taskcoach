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

from taskcoachlib import gui, config, persistence, operating_system
from taskcoachlib.domain import task, effort, date, note, attachment
from taskcoachlib.gui import uicommand
from unittests import dummy
import test
import wx


class TaskEditorSetterMixin(object):
    def setSubject(self, newSubject):
        page = self.editor._interior[0]
        page._subjectEntry.SetFocus()
        page._subjectEntry.SetValue(newSubject)
        return page

    def setDescription(self, newDescription):
        page = self.editor._interior[0]
        page._descriptionEntry.SetFocus()
        page._descriptionEntry.SetValue(newDescription)
        return page

    def setPlannedStartDateTime(self, dateTime):
        self.setDateTime(
            self.editor._interior[1]._plannedStartDateTimeEntry, dateTime
        )

    def setDueDateTime(self, dateTime):
        self.setDateTime(self.editor._interior[1]._dueDateTimeEntry, dateTime)

    def setActualStartDateTime(self, dateTime):
        self.setDateTime(
            self.editor._interior[1]._actualStartDateTimeEntry, dateTime
        )

    def setCompletionDateTime(self, dateTime):
        self.setDateTime(
            self.editor._interior[1]._completionDateTimeEntry, dateTime
        )

    def setReminder(self, dateTime):
        self.setDateTime(
            self.editor._interior[1]._reminderDateTimeEntry, dateTime
        )

    def setDateTime(self, entry, dateTime):
        entry.SetValue(dateTime)
        entry.onDateTimeCtrlEdited()
        wx.YieldIfNeeded()

    def setRecurrence(self, newRecurrence):
        recurrenceEntry = self.editor._interior[1]._recurrenceEntry
        recurrenceEntry.SetValue(newRecurrence)
        recurrenceEntry.onRecurrenceEdited()
        wx.YieldIfNeeded()


class TaskEditorBySettingFocusMixin(TaskEditorSetterMixin):
    def setSubject(self, newSubject):
        page = super().setSubject(newSubject)
        if operating_system.isGTK():
            page._subjectSync.onAttributeEdited(
                dummy.Event()
            )  # pragma: no cover
        else:
            page._descriptionEntry.SetFocus()  # pragma: no cover

    def setDescription(self, newDescription):
        page = super().setDescription(newDescription)
        if operating_system.isGTK():
            page._descriptionSync.onAttributeEdited(
                dummy.Event()
            )  # pragma: no cover
        else:
            page._subjectEntry.SetFocus()  # pragma: no cover


class TaskEditBookWithPerspective(gui.dialog.editor.TaskEditBook):
    testPerspective = "503e3c7d0000018300000002=+0,1,2,3,4,5,6,7,8,9@layout2|name=dummy;caption=;state=67372030;dir=3;layer=0;row=0;pos=0;prop=100000;bestw=381;besth=173;minw=381;minh=173;maxw=-1;maxh=-1;floatx=-1;floaty=-1;floatw=-1;floath=-1;notebookid=-1;transparent=255|name=503e3c7d0000018300000002;caption=;state=67372028;dir=5;layer=0;row=0;pos=0;prop=100000;bestw=200;besth=200;minw=-1;minh=-1;maxw=-1;maxh=-1;floatx=-1;floaty=-1;floatw=-1;floath=-1;notebookid=-1;transparent=255|dock_size(5,0,0)=202|"

    def perspective(self):
        return self.testPerspective


class TaskEditorWithPerspective(gui.dialog.editor.TaskEditor):
    EditBookClass = TaskEditBookWithPerspective


class TaskEditorTestCase(test.wxTestCase):
    extraSettings = list()
    editorClass = gui.dialog.editor.TaskEditor

    def setUp(self):
        super().setUp()
        task.Task.settings = self.settings = config.Settings(load=False)
        for section, name, value in self.extraSettings:
            self.settings.set(section, name, value)
        self.today = date.Now()
        self.tomorrow = self.today + date.ONE_DAY
        self.yesterday = self.today - date.ONE_DAY
        self.twodaysago = self.yesterday - date.ONE_DAY
        self.taskFile = persistence.TaskFile()
        self.taskList = self.taskFile.tasks()
        self.taskList.extend(self.createTasks())
        self.editor = self.editorClass(
            self.frame,
            self.getItems(),
            self.settings,
            self.taskList,
            self.taskFile,
        )

    def tearDown(self):
        # TaskEditor uses CallAfter for setting the focus, make sure those
        # calls are dealt with, otherwise they'll turn up in other tests
        if operating_system.isGTK():
            wx.Yield()  # pragma: no cover
        super().tearDown()
        self.taskFile.close()
        self.taskFile.stop()

    def createTasks(self):
        raise NotImplementedError  # pragma: no cover

    def getItems(self):
        raise NotImplementedError  # pragma: no cover


class EditorDisplayTest(TaskEditorTestCase):
    """Does the editor display the task data correctly when opened?"""

    def getItems(self):
        return [self.task]

    def createTasks(self):
        # pylint: disable=W0201
        self.task = task.Task("Task to edit")
        self.stop_datetime = date.DateTime(2012, 12, 12, 12, 12)
        self.task.setRecurrence(
            date.Recurrence(
                "daily", amount=1, stop_datetime=self.stop_datetime
            )
        )
        return [self.task]

    def testSubject(self):
        self.assertEqual(
            "Task to edit", self.editor._interior[0]._subjectEntry.GetValue()
        )

    def testDueDateTime(self):
        self.assertEqual(
            date.DateTime(),
            self.editor._interior[1]._dueDateTimeEntry.GetValue(),
        )

    def testActualStartDateTime(self):
        self.assertEqual(
            date.DateTime(),
            self.editor._interior[1]._actualStartDateTimeEntry.GetValue(),
        )

    def testRecurrenceUnit(self):
        choice = self.editor._interior[
            1
        ]._recurrenceEntry._recurrencePeriodEntry
        self.assertEqual("Daily", choice.GetString(choice.GetSelection()))

    def testRecurrenceFrequency(self):
        freq = self.editor._interior[
            1
        ]._recurrenceEntry._recurrenceFrequencyEntry
        self.assertEqual(1, freq.GetValue())

    def testRecurrenceStopDateTime(self):
        stop = self.editor._interior[
            1
        ]._recurrenceEntry._recurrenceStopDateTimeEntry
        self.assertEqual(self.stop_datetime, stop.GetValue())


class EditTaskTestMixin(object):
    def getItems(self):
        return [self.task]

    def createTasks(self):
        # pylint: disable=W0201
        self.task = task.Task("Task to edit")
        self.attachment = attachment.FileAttachment("some attachment")
        self.task.addAttachments(self.attachment)  # pylint: disable=E1101
        return [self.task]

    def testEditSubject(self):
        self.setSubject("Done")
        self.assertEqual("Done", self.task.subject())

    def testEditDescription(self):
        self.setDescription("Description")
        self.assertEqual("Description", self.task.description())

    # pylint: disable=W0212

    def testSetPlannedStartDateTime(self):
        self.setPlannedStartDateTime(self.tomorrow)
        self.assertAlmostEqual(
            self.tomorrow.toordinal(),
            self.task.plannedStartDateTime().toordinal(),
            places=2,
        )

    def testSetDueDateTime(self):
        self.setDueDateTime(self.tomorrow)
        self.assertAlmostEqual(
            self.tomorrow.toordinal(),
            self.task.dueDateTime().toordinal(),
            places=2,
        )

    def testSetActualStartDateTime(self):
        self.setActualStartDateTime(self.tomorrow)
        self.assertAlmostEqual(
            self.tomorrow.toordinal(),
            self.task.actualStartDateTime().toordinal(),
            places=2,
        )

    def testSetCompletionDateTime(self):
        self.setCompletionDateTime(self.tomorrow)
        self.assertAlmostEqual(
            self.tomorrow.toordinal(),
            self.task.completionDateTime().toordinal(),
            places=2,
        )

    def testSetUncompleted(self):
        self.setCompletionDateTime(date.Now())
        self.setCompletionDateTime(date.DateTime())
        self.assertEqual(date.DateTime(), self.task.completionDateTime())

    def testSetReminder(self):
        reminderDateTime = date.DateTime(2005, 1, 1)
        self.setReminder(reminderDateTime)
        self.assertEqual(reminderDateTime, self.task.reminder())

    def testSetRecurrence(self):
        self.setRecurrence(date.Recurrence("weekly"))
        self.assertEqual("weekly", self.task.recurrence().unit)

    def testSetDailyRecurrence(self):
        self.setRecurrence(date.Recurrence("daily", amount=1))
        self.assertEqual("daily", self.task.recurrence().unit)
        self.assertEqual(1, self.task.recurrence().amount)

    def testSetYearlyRecurrence(self):
        self.setRecurrence(date.Recurrence("yearly"))
        self.assertEqual("yearly", self.task.recurrence().unit)

    def testSetMaxRecurrence(self):
        self.setRecurrence(date.Recurrence("weekly", maximum=10))
        self.assertEqual(10, self.task.recurrence().max)

    def testSetRecurrenceStopDateTime(self):
        stop = date.DateTime(2012, 3, 4, 10, 0)
        self.setRecurrence(date.Recurrence("weekly", stop_datetime=stop))
        self.assertEqual(stop, self.task.recurrence().stop_datetime)

    def testSetRecurrenceFrequency(self):
        self.setRecurrence(date.Recurrence("weekly", amount=3))
        self.assertEqual(3, self.task.recurrence().amount)

    def testSetRecurrenceSameWeekday(self):
        self.setRecurrence(date.Recurrence("monthly", sameWeekday=True))
        self.assertTrue(self.task.recurrence().sameWeekday)

    def testPriority(self):
        self.editor._interior[0]._priorityEntry.SetValue(45)
        self.assertEqual(
            45, self.editor._interior[0]._priorityEntry.GetValue()
        )

    def testSetNegativePriority(self):
        self.editor._interior[0]._priorityEntry.SetValue(-1)
        self.editor._interior[0]._prioritySync.onAttributeEdited(dummy.Event())
        self.assertEqual(-1, self.task.priority())

    def testSetHourlyFee(self):
        self.editor._interior[5]._hourlyFeeEntry.SetValue(100)
        self.editor._interior[5]._hourlyFeeSync.onAttributeEdited(
            dummy.Event()
        )
        self.assertEqual(100, self.task.hourlyFee())

    def testSetFixedFee(self):
        self.editor._interior[5]._fixedFeeEntry.SetValue(100.5)
        self.editor._interior[5]._fixedFeeSync.onAttributeEdited(dummy.Event())
        self.assertEqual(100.5, self.task.fixedFee())

    def testBehaviorMarkCompleted(self):
        page = self.editor._interior[3]
        page._shouldMarkCompletedEntry.SetStringSelection("Yes")
        page._shouldMarkCompletedSync.onAttributeEdited(dummy.Event())
        self.assertEqual(
            True, self.task.shouldMarkCompletedWhenAllChildrenCompleted()
        )

    def testAddAttachment(self):
        self.editor._interior[8].viewer.onDropFiles(self.task, ["filename"])
        # pylint: disable=E1101
        self.assertTrue(
            "filename" in [att.location() for att in self.task.attachments()]
        )
        self.assertTrue(
            "filename" in [att.subject() for att in self.task.attachments()]
        )

    def testRemoveAttachment(self):
        self.editor._interior[8].viewer.select(self.task.attachments())
        self.editor._interior[8].viewer.deleteItemCommand().do()
        self.assertEqual([], self.task.attachments())  # pylint: disable=E1101

    def testOpenAttachmentWithNonAsciiFileName(self):
        self.errorMessage = ""  # pylint: disable=W0201

        def onError(*args, **kwargs):  # pylint: disable=W0613
            self.errorMessage = args[0]  # pragma: no cover

        att = attachment.FileAttachment("tÃƒÂ©st.ÃƒÂ©")
        openAttachment = uicommand.AttachmentOpen(
            viewer=self.editor._interior[6].viewer,
            attachments=attachment.AttachmentList([att]),
            settings=self.settings,
        )
        openAttachment.do_command(None, showerror=onError)
        self.assertFalse(self.errorMessage)

    def testAddNote(self):
        viewer = self.editor._interior[7].viewer
        viewer.newItemCommand(viewer.presentation()).do()
        self.assertEqual(1, len(self.task.notes()))

    def testAddNoteWithSubnote(self):
        parent = note.Note(subject="New note")
        child = note.Note(subject="Child")
        parent.addChild(child)
        child.setParent(parent)
        viewer = self.editor._interior[7].viewer
        viewer.newItemCommand(viewer.presentation()).do()
        viewer.newSubItemCommandClass()(
            list=viewer.presentation(), items=viewer.presentation()
        ).do()
        # Only the parent note should be added to the notes list:
        self.assertEqual(1, len(self.task.notes()))

    def testNewNote(self):
        viewer = self.editor._interior[7].viewer
        wx.GetApp().TopWindow.taskFile = self.taskFile
        command = gui.uicommand.NoteNew(
            notes=viewer.presentation(), settings=self.settings, viewer=viewer
        )
        dialog = command.do_command(None, show=False)
        dialog.ok()
        self.assertEqual(1, len(self.task.notes()))


class EditTaskTestBySettingFocus(
    TaskEditorBySettingFocusMixin, EditTaskTestMixin, TaskEditorTestCase
):
    pass


class EditTaskWithChildrenMixin(object):
    def getItems(self):
        return [self.parent]

    def createTasks(self):
        # pylint: disable=W0201
        self.parent = task.Task("Parent", plannedStartDateTime=date.Now())
        self.child = task.Task("Child", plannedStartDateTime=date.Now())
        self.parent.addChild(self.child)
        return [self.parent]  # self.child is added to tasklist automatically

    def testEditSubject(self):
        self.setSubject("New Parent Subject")
        self.assertEqual("New Parent Subject", self.parent.subject())


class EditTaskWithChildrenTestBySettingFocus(
    TaskEditorBySettingFocusMixin,
    EditTaskWithChildrenMixin,
    TaskEditorTestCase,
):
    pass


class EditTaskWithEffortTest(TaskEditorTestCase):
    def getItems(self):
        return [self.task]

    def createTasks(self):
        self.task = task.Task("task")  # pylint: disable=W0201
        self.task.addEffort(effort.Effort(self.task))
        return [self.task]

    def testEffortIsShown(self):
        self.assertEqual(
            1, self.editor._interior[6].viewer.widget.GetItemCount()
        )


class FocusTest(TaskEditorTestCase):
    def createTasks(self):
        self.task = task.Task("Task to edit")
        return [self.task]

    def getItems(self):
        return [self.task]

    def testFocus(self):
        # pylint: disable=W0212
        self.assertEqual(
            self.editor._interior[0]._subjectEntry, wx.Window_FindFocus()
        )

    def testSelection(self):
        # pylint: disable=W0212
        self.assertEqual(
            self.editor._interior[0]._subjectEntry.GetStringSelection(),
            self.editor._interior[0]._subjectEntry.GetValue(),
        )


class FocusTestWithPerspective(FocusTest):
    editorClass = TaskEditorWithPerspective


class DatesTestBase(TaskEditorSetterMixin, TaskEditorTestCase):
    def createTasks(self):
        # pylint: disable=W0201
        self.task = task.Task("Task to edit")
        return [self.task]

    def getItems(self):
        return [self.task]


class DatesStartDueTest(DatesTestBase):
    extraSettings = [("view", "datestied", "startdue")]

    def testChangePlannedStartDateChangesDueDate(self):
        self.setPlannedStartDateTime(self.yesterday)
        self.setDueDateTime(self.today)
        self.setPlannedStartDateTime(self.today)
        self.assertAlmostEqual(
            self.editor._interior[1]._dueDateTimeEntry.GetValue().toordinal(),
            self.tomorrow.toordinal(),
            places=2,
        )


class DatesDueStartBase(DatesTestBase):
    extraSettings = [("view", "datestied", "duestart")]

    def testChangeDueDateChangesPlannedStartDate(self):
        self.setPlannedStartDateTime(self.yesterday)
        self.setDueDateTime(self.today)
        self.setDueDateTime(self.yesterday)
        self.assertAlmostEqual(
            self.editor._interior[1]
            ._plannedStartDateTimeEntry.GetValue()
            .toordinal(),
            self.twodaysago.toordinal(),
            places=2,
        )


class DatesTest(DatesTestBase):
    def testChangePlannedStartDateDoesNotChangeDueDate(self):
        self.setPlannedStartDateTime(self.yesterday)
        self.setDueDateTime(self.today)
        self.setPlannedStartDateTime(self.today)
        self.assertAlmostEqual(
            self.editor._interior[1]._dueDateTimeEntry.GetValue().toordinal(),
            self.today.toordinal(),
            places=2,
        )

    def testChangeDueDateDoesNotChangePlannedStartDate(self):
        self.setPlannedStartDateTime(self.yesterday)
        self.setDueDateTime(self.today)
        self.setDueDateTime(self.yesterday)
        self.assertAlmostEqual(
            self.editor._interior[1]
            ._plannedStartDateTimeEntry.GetValue()
            .toordinal(),
            self.yesterday.toordinal(),
            places=2,
        )
