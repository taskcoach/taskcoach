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

from taskcoachlib import patterns, config
from taskcoachlib.domain import task, effort, date
import test


class EffortAggregatorTestCase(test.TestCase):
    aggregation = "One of: day, week, or month (override in subclass)"

    def setUp(self):
        task.Task.settings = config.Settings(load=False)
        self.taskList = task.TaskList()
        self.effortAggregator = effort.EffortAggregator(
            self.taskList, aggregation=self.aggregation
        )
        patterns.Publisher().registerObserver(
            self.onEvent,
            eventType=self.effortAggregator.addItemEventType(),
            eventSource=self.effortAggregator,
        )
        patterns.Publisher().registerObserver(
            self.onEvent,
            eventType=self.effortAggregator.removeItemEventType(),
            eventSource=self.effortAggregator,
        )
        self.task1 = task.Task(subject="task 1")
        self.task2 = task.Task(subject="task 2")
        self.task3 = task.Task(subject="child")
        self.task1.addChild(self.task3)
        self.task3.setParent(self.task1)
        self.effort1period1a = effort.Effort(
            self.task1,
            date.DateTime(2004, 1, 1, 11, 0, 0),
            date.DateTime(2004, 1, 1, 12, 0, 0),
        )
        self.effort2period1a = effort.Effort(
            self.task2,
            date.DateTime(2004, 1, 1, 11, 0, 0),
            date.DateTime(2004, 1, 1, 12, 0, 0),
        )
        self.effort1period1b = effort.Effort(
            self.task1,
            date.DateTime(2004, 1, 1, 13, 0, 0),
            date.DateTime(2004, 1, 1, 14, 0, 0),
        )
        self.effort2period1b = effort.Effort(
            self.task2,
            date.DateTime(2004, 1, 1, 13, 0, 0),
            date.DateTime(2004, 1, 1, 14, 0, 0),
        )
        self.effort1period2 = effort.Effort(
            self.task1,
            date.DateTime(2004, 2, 2, 13, 0, 0),
            date.DateTime(2004, 2, 2, 14, 0, 0),
        )
        self.effort1period3 = effort.Effort(
            self.task1,
            date.DateTime(2004, 1, 1, 10, 0, 0),
            date.DateTime(2005, 1, 1, 10, 0, 0),
        )
        self.effort3period1a = effort.Effort(
            self.task3,
            date.DateTime(2004, 1, 1, 14, 0, 0),
            date.DateTime(2004, 1, 1, 15, 0, 0),
        )
        self.events = []

    def onEvent(self, event):
        self.events.append(event)


class CommonTestsMixin(object):
    def testEmptyTaskList(self):
        self.assertEqual(0, len(self.effortAggregator))

    def testAddTaskWithoutEffort(self):
        self.taskList.append(self.task1)
        self.assertEqual(0, len(self.effortAggregator))

    def testAddTaskWithEffort(self):
        self.task1.addEffort(self.effort1period1a)
        self.taskList.append(self.task1)
        self.assertEqual(2, len(self.effortAggregator))

    def testAddEffort(self):
        self.taskList.append(self.task1)
        self.task1.addEffort(effort.Effort(self.task1))
        self.assertEqual(2, len(self.effortAggregator))

    def testAddTwoEffortsOnSameDay(self):
        self.taskList.append(self.task1)
        self.task1.addEffort(self.effort1period1a)
        self.task1.addEffort(self.effort1period1b)
        self.assertEqual(2, len(self.effortAggregator))

    def testAddTaskWithTwoEffortsOnSameDay(self):
        self.task1.addEffort(self.effort1period1a)
        self.task1.addEffort(self.effort1period1b)
        self.taskList.append(self.task1)
        self.assertEqual(2, len(self.effortAggregator))

    def testAddTaskWithTwoEffortsOnSameDayAndCheckTotalEffort(self):
        self.task1.addEffort(self.effort1period1a)
        self.task1.addEffort(self.effort1period1b)
        self.taskList.append(self.task1)
        expectedDuration = (
            self.effort1period1a.duration() + self.effort1period1b.duration()
        )
        self.assertEqual(
            expectedDuration, list(self.effortAggregator)[0].duration()
        )

    def testAddTwoEffortsInDifferentPeriods(self):
        self.taskList.append(self.task1)
        self.task1.addEffort(self.effort1period1a)
        self.task1.addEffort(self.effort1period2)
        self.assertEqual(4, len(self.effortAggregator))

    def testAddTwoEffortsOnTheSameDayToTwoDifferentTasks(self):
        self.taskList.extend([self.task1, self.task2])
        self.task1.addEffort(self.effort1period1a)
        self.task2.addEffort(self.effort2period1a)
        self.assertEqual(3, len(self.effortAggregator))

    def testAddEffortToChild(self):
        self.taskList.extend([self.task1, self.task2])
        self.task1.addChild(self.task2)
        self.task2.addEffort(self.effort2period1a)
        self.assertEqual(3, len(self.effortAggregator))

    def testAddChildWithEffort(self):
        self.taskList.extend([self.task1, self.task2])
        self.task2.addEffort(self.effort2period1a)
        self.task1.addChild(self.task2)
        self.assertEqual(3, len(self.effortAggregator))

    def testAddParentAndChildWithEffortToTaskList(self):
        self.task3.addEffort(self.effort3period1a)
        self.taskList.append(self.task1)
        self.assertEqual(3, len(self.effortAggregator))

    def testAddEffortToGrandChild(self):
        self.taskList.extend([self.task1, self.task2])
        self.task3.addChild(self.task2)
        self.task2.addEffort(self.effort2period1a)
        self.assertEqual(4, len(self.effortAggregator))

    def testAddGrandChildWithEffort(self):
        self.taskList.extend([self.task1, self.task2])
        self.task2.addEffort(self.effort2period1a)
        self.task3.addChild(self.task2)
        self.assertEqual(4, len(self.effortAggregator))

    def testRemoveChildWithEffortFromParent(self):
        self.taskList.extend([self.task1, self.task2])
        self.task1.addChild(self.task2)
        self.task2.addEffort(self.effort2period1a)
        self.task2.setParent(None)
        self.task1.removeChild(self.task2)
        self.assertEqual(2, len(self.effortAggregator))

    def testRemoveEffort(self):
        self.taskList.append(self.task1)
        self.task1.addEffort(self.effort1period1a)
        self.task1.removeEffort(self.effort1period1a)
        self.assertEqual(0, len(self.effortAggregator))

    def testRemoveOneOfTwoEfforts(self):
        self.taskList.append(self.task1)
        self.task1.addEffort(self.effort1period1a)
        self.task1.addEffort(self.effort1period1b)
        self.task1.removeEffort(self.effort1period1a)
        self.assertEqual(2, len(self.effortAggregator))

    def testRemoveOneOfTwoEffortsOfDifferentTasks(self):
        self.taskList.extend([self.task1, self.task2])
        self.task1.addEffort(self.effort1period1a)
        self.task2.addEffort(self.effort2period1a)
        self.task1.removeEffort(self.effort1period1a)
        self.assertEqual(2, len(self.effortAggregator))

    def testRemoveTwoOfTwoEfforts(self):
        self.taskList.append(self.task1)
        self.task1.addEffort(self.effort1period1a)
        self.task1.addEffort(self.effort1period1b)
        self.task1.removeEffort(self.effort1period1a)
        self.task1.removeEffort(self.effort1period1b)
        self.assertEqual(0, len(self.effortAggregator))

    def testRemoveEffortFromChild(self):
        self.taskList.extend([self.task1, self.task2])
        self.task2.addEffort(self.effort2period1a)
        self.task1.addChild(self.task2)
        self.task2.removeEffort(self.effort2period1a)
        self.assertEqual(0, len(self.effortAggregator))

    def testRemoveTasks(self):
        self.taskList.extend([self.task1, self.task3])
        self.task3.addEffort(self.effort3period1a)
        self.taskList.removeItems([self.task1, self.task3])
        self.assertEqual(0, len(self.effortAggregator))

    def testRemoveTasksWithOverlappingEffort(self):
        self.taskList.extend([self.task1, self.task3])
        self.task3.addEffort(self.effort3period1a)
        self.task1.addEffort(self.effort1period1a)
        self.taskList.removeItems([self.task1, self.task3])
        self.assertEqual(0, len(self.effortAggregator))

    def testRemoveAllTasks(self):
        self.taskList.extend([self.task1, self.task2, self.task3])
        self.task3.addEffort(self.effort3period1a)
        self.taskList.removeItems([self.task1, self.task2, self.task3])
        self.assertEqual(0, len(self.effortAggregator))

    def testRemoveChildTask(self):
        self.taskList.extend([self.task1])
        self.task3.addEffort(self.effort3period1a)
        self.taskList.removeItems([self.task3])
        self.assertEqual(0, len(self.effortAggregator))

    def testChangeStart(self):
        self.taskList.append(self.task1)
        self.task1.addEffort(self.effort1period1a)
        self.effort1period1a.setStart(date.DateTime.now())
        self.assertEqual(2, len(self.effortAggregator))

    def testChangeStartOfOneOfTwoEfforts(self):
        self.taskList.append(self.task1)
        self.task1.addEffort(self.effort1period1a)
        self.task1.addEffort(self.effort1period1b)
        self.effort1period1a.setStart(date.DateTime.now())
        self.assertEqual(4, len(self.effortAggregator))

    def testChangeStart_WithinPeriod(self):
        self.taskList.append(self.task1)
        self.task1.addEffort(self.effort1period1a)
        self.effort1period1a.setStart(
            self.effort1period1a.getStart() + date.ONE_SECOND
        )
        self.assertEqual(2, len(self.effortAggregator))

    def testChangeStopDoesNotAffectPeriod(self):
        self.taskList.append(self.task1)
        self.task1.addEffort(self.effort1period1a)
        composite = list(self.effortAggregator)[0]
        start = composite.getStart()
        self.effort1period1a.setStop(date.DateTime.now())
        self.assertEqual(start, composite.getStart())

    def testChangeStartOfOneOfTwoEffortsToOneYearLater(self):
        self.taskList.append(self.task1)
        self.task1.addEffort(self.effort1period1a)
        self.task1.addEffort(self.effort1period1b)
        self.effort1period1a.setStart(date.DateTime(2005, 1, 1, 11, 0, 0))
        self.assertEqual(4, len(self.effortAggregator))

    def testNotification_Add(self):
        self.taskList.append(self.task1)
        self.task1.addEffort(self.effort1period1a)
        self.assertEqual(1, len(self.events))
        self.assertTrue(self.events[0].value() in self.effortAggregator)

    def testNotification_Remove(self):
        self.taskList.append(self.task1)
        self.task1.addEffort(self.effort1period1a)
        self.task1.removeEffort(self.effort1period1a)
        self.assertEqual(3, len(self.events))

    def testCreateWithInitialEffort(self):
        self.taskList.append(self.task1)
        self.task1.addEffort(self.effort1period1a)
        aggregator = effort.EffortAggregator(
            self.taskList, aggregation=self.aggregation
        )
        self.assertEqual(2, len(aggregator))

    def testLongEffortIsStillOneCompositeEffort(self):
        self.taskList.append(self.task1)
        self.task1.addEffort(self.effort1period3)
        self.assertEqual(2, len(self.effortAggregator))

    def testChangeTask(self):
        self.taskList.extend([self.task1, self.task2])
        self.task1.addEffort(self.effort1period1a)
        self.effort1period1a.setTask(self.task2)
        self.assertEqual(2, len(self.effortAggregator))
        self.assertTrue(
            self.task2 in [item.task() for item in self.effortAggregator]
        )

    def testChangeTaskOfChildEffort(self):
        self.taskList.extend([self.task1, self.task2])
        self.task3.addEffort(self.effort3period1a)
        self.effort3period1a.setTask(self.task2)
        self.assertEqual(2, len(self.effortAggregator))
        self.assertTrue(
            self.task2 in [item.task() for item in self.effortAggregator]
        )

    def testRemoveTaskAfterChangeTaskOfEffort(self):
        self.taskList.extend([self.task1, self.task2])
        self.task1.addEffort(self.effort1period1a)
        self.effort1period1a.setTask(self.task2)
        self.taskList.remove(self.task1)
        self.assertEqual(2, len(self.effortAggregator))
        self.assertTrue(
            self.task2 in [item.task() for item in self.effortAggregator]
        )

    def testRemoveAndAddEffortToSamePeriod(self):
        self.taskList.append(self.task1)
        self.task1.addEffort(self.effort1period1a)
        self.task1.removeEffort(self.effort1period1a)
        self.task1.addEffort(self.effort1period1a)
        self.assertEqual(2, len(self.effortAggregator))
        self.assertEqual(
            self.effort1period1a, list(self.effortAggregator)[0][0]
        )

    def testMaxDateTime(self):
        self.assertEqual(None, self.effortAggregator.maxDateTime())

    def testMaxDateTime_OneEffort(self):
        self.taskList.append(self.task1)
        self.task1.addEffort(self.effort1period1a)
        self.assertEqual(
            self.effort1period1a.getStop(), self.effortAggregator.maxDateTime()
        )

    def testMaxDateTime_OneTrackingEffort(self):
        self.taskList.append(self.task1)
        self.task1.addEffort(effort.Effort(self.task1))
        self.assertEqual(None, self.effortAggregator.maxDateTime())

    def testMaxDateTime_TwoEfforts(self):
        self.taskList.append(self.task1)
        self.task1.addEffort(self.effort1period1a)
        now = date.DateTime.now()
        self.task1.addEffort(
            effort.Effort(self.task1, self.effort1period1a.getStart(), now)
        )
        self.assertEqual(now, self.effortAggregator.maxDateTime())

    def testNrTracking(self):
        self.assertEqual(0, self.effortAggregator.nr_being_tracked())

    def testOriginalLength(self):
        self.assertEqual(0, self.effortAggregator.original_length())


class EffortPerDayTest(EffortAggregatorTestCase, CommonTestsMixin):
    aggregation = "day"


class EffortPerWeekTest(EffortAggregatorTestCase, CommonTestsMixin):
    aggregation = "week"


class EffortPerMonthTest(EffortAggregatorTestCase, CommonTestsMixin):
    aggregation = "month"


class MultipleAggregatorsTest(test.TestCase):
    def setUp(self):
        self.taskList = task.TaskList()
        self.effortPerDay = effort.EffortSorter(
            effort.EffortAggregator(self.taskList, aggregation="day")
        )
        self.effortPerWeek = effort.EffortSorter(
            effort.EffortAggregator(self.taskList, aggregation="week")
        )

    def testDeleteEffort_StartOfBothPeriods(self):
        aTask = task.Task()
        self.taskList.append(aTask)
        # Make sure the start of the day and week are the same,
        # in other words, use a Monday
        anEffort = effort.Effort(
            aTask, date.DateTime(2006, 8, 28), date.DateTime(2006, 8, 29)
        )
        aTask.addEffort(anEffort)
        aTask.removeEffort(anEffort)
        self.assertFalse(self.effortPerDay)
