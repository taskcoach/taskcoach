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
from taskcoachlib import gui, config
from taskcoachlib.domain import task, date


class DummyViewer(object):
    def __init__(self, presentation):
        self._presentation = presentation
        self._selection = []

    def presentation(self):
        return self._presentation

    def curselection(self):
        return self._selection

    def nrOfVisibleTasks(self):
        return len(self._presentation)


class TaskViewerStatusMessagesTest(test.TestCase):
    def setUp(self):
        super().setUp()
        task.Task.settings = config.Settings(load=False)
        self.taskList = task.filter.ViewFilter(task.TaskList())
        self.task = task.Task("Task")
        self.viewer = DummyViewer(self.taskList)
        self.status = gui.viewer.task.TaskViewerStatusMessages(self.viewer)
        self.template1 = "Tasks: %d selected, %d visible, %d total"
        self.template2 = (
            "Status: %d overdue, %d late, %d inactive, %d completed"
        )

    # Helper methods

    def assertMessages(
        self,
        selected=0,
        visible=0,
        total=0,
        overdue=0,
        late=0,
        inactive=0,
        completed=0,
    ):
        message1 = self.template1 % (selected, visible, total)
        message2 = self.template2 % (overdue, late, inactive, completed)
        self.assertEqual((message1, message2), self.status())

    def addActiveTask(self):
        self.task.setActualStartDateTime(date.Now())
        self.taskList.append(self.task)

    def addOverdueTask(self):
        self.task.setDueDateTime(date.Now() - date.ONE_HOUR)
        self.taskList.append(self.task)

    def addInactiveTask(self):
        self.taskList.append(self.task)

    def addCompletedTask(self):
        self.task.setCompletionDateTime(date.Now())
        self.taskList.append(self.task)

    def addLateTask(self):
        self.task.setPlannedStartDateTime(date.Yesterday())
        self.taskList.append(self.task)

    def removeTask(self):
        self.taskList.remove(self.task)

    def markTaskCompleted(self):
        self.task.setCompletionDateTime(date.Now())

    def markTaskUncompleted(self):
        self.task.setCompletionDateTime(date.DateTime())

    def makeTaskActive(self):
        self.task.setActualStartDateTime(date.Now())

    def makeTaskInactive(self):
        self.task.setActualStartDateTime(date.DateTime())

    def selectTask(self):
        self.viewer._selection = [self.task]

    def hideCompletedTasks(self):
        self.taskList.hide_task_status(task.status.completed)

    def showCompletedTasks(self):
        self.taskList.hide_task_status(task.status.completed, False)

    # Tests

    def testDefaultMessages(self):
        self.assertMessages()

    def testAddActiveTask(self):
        self.addActiveTask()
        self.assertMessages(visible=1, total=1)

    def testAddInactiveTask(self):
        self.addInactiveTask()
        self.assertMessages(visible=1, total=1, inactive=1)

    def testAddOverdueTask(self):
        self.addOverdueTask()
        self.assertMessages(visible=1, total=1, inactive=0, overdue=1)

    def testAddCompletedTask(self):
        self.addCompletedTask()
        self.assertMessages(visible=1, total=1, completed=1)

    def testAddLateTask(self):
        self.addLateTask()
        self.assertMessages(visible=1, late=1, total=1)

    def testRemoveActiveTask(self):
        self.addActiveTask()
        self.removeTask()
        self.assertMessages()

    def testRemoveInactiveTask(self):
        self.addInactiveTask()
        self.removeTask()
        self.assertMessages()

    def testRemoveOverdueTask(self):
        self.addOverdueTask()
        self.removeTask()
        self.assertMessages()

    def testRemoveCompletedTask(self):
        self.addCompletedTask()
        self.removeTask()
        self.assertMessages()

    def testMarkInactiveTaskCompleted(self):
        self.addInactiveTask()
        self.markTaskCompleted()
        self.assertMessages(visible=1, total=1, completed=1)

    def testMarkActiveTaskCompleted(self):
        self.addCompletedTask()
        self.markTaskCompleted()
        self.assertMessages(visible=1, total=1, completed=1)

    def testMarkCompletedTaskUncompleted(self):
        self.addCompletedTask()
        self.markTaskUncompleted()
        self.assertMessages(visible=1, total=1, inactive=1)

    def testMakeInactiveTaskActive(self):
        self.addInactiveTask()
        self.makeTaskActive()
        self.assertMessages(visible=1, total=1)

    def testMakeActiveTaskInactive(self):
        self.addActiveTask()
        self.makeTaskInactive()
        self.assertMessages(visible=1, total=1, inactive=1)

    def testMakeCompletedTaskInactive(self):
        self.addActiveTask()
        self.markTaskCompleted()
        self.makeTaskInactive()
        # Completed tasks are never considered to be inactive:
        self.assertMessages(visible=1, total=1, completed=1)

    def testMakeCompletedTaskActive(self):
        self.addInactiveTask()
        self.markTaskCompleted()
        self.makeTaskActive()
        # Completed tasks are never considered to be inactive:
        self.assertMessages(visible=1, total=1, completed=1)

    def testTotalWhenHidingCompletedTasks(self):
        self.addCompletedTask()
        self.hideCompletedTasks()
        self.assertMessages(total=1, completed=1)

    def testTotalWhenShowingCompletedTasks(self):
        self.hideCompletedTasks()
        self.addCompletedTask()
        self.showCompletedTasks()
        self.assertMessages(visible=1, total=1, completed=1)

    def testTotalWhenHidingCompletedTasksWithActiveTask(self):
        self.taskList.append(task.Task(actualStartDateTime=date.Now()))
        self.addCompletedTask()
        self.hideCompletedTasks()
        self.assertMessages(visible=1, total=2, completed=1)

    def testSelectedActiveTask(self):
        self.addActiveTask()
        self.selectTask()
        self.assertMessages(selected=1, visible=1, total=1)

    def testSelectedInactiveTask(self):
        self.addInactiveTask()
        self.selectTask()
        self.assertMessages(selected=1, visible=1, total=1, inactive=1)

    def testSelectedCompletedTask(self):
        self.addCompletedTask()
        self.selectTask()
        self.assertMessages(selected=1, visible=1, total=1, completed=1)

    def testSelectedOverdueTask(self):
        self.addOverdueTask()
        self.selectTask()
        self.assertMessages(
            selected=1, visible=1, total=1, overdue=1, inactive=0
        )
