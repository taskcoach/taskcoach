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
from taskcoachlib.domain import task, effort, date, category
from pubsub import pub
from unittests import asserts
import test
import wx


class EffortTest(test.TestCase, asserts.Mixin):
    def setUp(self):
        task.Task.settings = config.Settings(load=False)
        self.task = task.Task()
        self.effort = effort.Effort(
            self.task,
            start=date.DateTime(2004, 1, 1),
            stop=date.DateTime(2004, 1, 2),
        )
        self.task.addEffort(self.effort)
        self.events = []

    def onEvent(self, event):
        self.events.append(event)

    def testId(self):
        self.assertTrue(self.effort.id() is not None)

    def testStatus(self):
        self.assertEqual(self.effort.getStatus(), self.effort.STATUS_NEW)

    def testCreate(self):
        self.assertEqual(self.task, self.effort.task())
        self.assertEqual("", self.effort.description())

    def testStr(self):
        self.assertEqual(
            "Effort(%s, %s, %s)"
            % (
                self.effort.task(),
                self.effort.getStart(),
                self.effort.getStop(),
            ),
            str(self.effort),
        )

    def testDuration(self):
        self.assertEqual(date.TimeDelta(days=1), self.effort.duration())

    def testForegroundColor(self):
        self.task.setForegroundColor(wx.RED)
        self.assertEqual(wx.RED, self.effort.foregroundColor())

    def testBackgroundColor(self):
        self.task.setBackgroundColor(wx.RED)
        self.assertEqual(wx.RED, self.effort.backgroundColor())

    def testFont(self):
        self.task.setFont(wx.SWISS_FONT)
        self.assertEqual(wx.SWISS_FONT, self.effort.font())

    def testNotificationForSetStart(self):
        events = []

        def onEvent(newValue, sender):
            events.append((newValue, sender))

        pub.subscribe(onEvent, effort.Effort.startChangedEventType())
        start = date.DateTime.now()
        self.effort.setStart(start)
        self.assertEqual([(start, self.effort)], events)

    def testNotificationForSetStop(self):
        events = []

        def onEvent(newValue, sender):
            events.append((newValue, sender))

        pub.subscribe(onEvent, effort.Effort.stopChangedEventType())
        stop = date.DateTime.now()
        self.effort.setStop(stop)
        self.assertEqual([(stop, self.effort)], events)

    def testNoNotificationForSetStopWhenNewStopEqualsOldStop(self):
        events = []

        def onEvent(newValue, sender):
            events.append((newValue, sender))

        pub.subscribe(onEvent, effort.Effort.stopChangedEventType())
        self.effort.setStop(self.effort.getStop())
        self.assertFalse(events)

    def testDurationNotificationForSetStart(self):
        events = []

        def onEvent(newValue, sender):
            events.append((newValue, sender))

        pub.subscribe(onEvent, effort.Effort.durationChangedEventType())
        start = date.DateTime.now()
        self.effort.setStart(start)
        self.assertEqual([(self.effort.duration(), self.effort)], events)

    def testDurationNotificationForSetStop(self):
        events = []

        def onEvent(newValue, sender):
            events.append((newValue, sender))

        pub.subscribe(onEvent, effort.Effort.durationChangedEventType())
        self.effort.setStop(date.DateTime.now())
        self.assertEqual([(self.effort.duration(), self.effort)], events)

    def testNotificationForSetDescription(self):
        patterns.Publisher().registerObserver(
            self.onEvent, eventType=effort.Effort.descriptionChangedEventType()
        )
        self.effort.setDescription("description")
        self.assertEqual("description", self.events[0].value())

    def testNotificationForSetTask(self):
        events = []

        def onEvent(newValue, sender):
            events.append((newValue, sender))

        pub.subscribe(onEvent, effort.Effort.taskChangedEventType())
        task2 = task.Task()
        self.effort.setTask(task2)
        self.assertEqual([(task2, self.effort)], events)

    def testNotificationForStartTracking(self):
        events = []

        def onEvent(newValue, sender):
            events.append((newValue, sender))

        pub.subscribe(onEvent, self.effort.trackingChangedEventType())
        self.effort.setStop(date.DateTime())
        self.assertEqual([(True, self.effort)], events)

    def testNotificationForStopTracking(self):
        self.effort.setStop(date.DateTime())
        events = []

        def onEvent(newValue, sender):
            events.append((newValue, sender))

        pub.subscribe(onEvent, self.effort.trackingChangedEventType())
        self.effort.setStop(date.DateTime.now())
        self.assertEqual([(False, self.effort)], events)

    def testRevenueNotificationForTaskHourlyFeeChange(self):
        events = []

        def onEvent(newValue, sender):
            events.append((newValue, sender))

        pub.subscribe(onEvent, effort.Effort.revenueChangedEventType())
        self.task.setHourlyFee(100)
        self.assertEqual([(2400.0, self.effort)], events)

    def testRevenueNotificationForEffortDurationChange_ChangeStop(self):
        self.task.setHourlyFee(100)
        events = []

        def onEvent(newValue, sender):
            events.append((newValue, sender))

        pub.subscribe(onEvent, effort.Effort.revenueChangedEventType())
        self.effort.setStop(date.DateTime(2004, 1, 3))
        self.assertEqual([(4800.0, self.effort)], events)

    def testRevenueNotificationForEffortDurationChange_ChangeStart(self):
        self.task.setHourlyFee(100)
        events = []

        def onEvent(newValue, sender):
            events.append((newValue, sender))

        pub.subscribe(onEvent, effort.Effort.revenueChangedEventType())
        self.effort.setStart(date.DateTime(2004, 1, 1, 12, 0, 0))
        self.assertEqual([(1200.0, self.effort)], events)

    def testDefaultStartAndStop(self):
        effortPeriod = effort.Effort(self.task)
        currentTime = date.DateTime.now()
        now = lambda: currentTime
        self.assertEqual(
            now() - effortPeriod.getStart(), effortPeriod.duration(now=now)
        )

    def testState(self):
        state = self.effort.__getstate__()
        theTask = task.Task()
        newEffort = effort.Effort(theTask)
        newEffort.__setstate__(state)
        self.assertEqualEfforts(newEffort, self.effort)

    def testCopy(self):
        copyEffort = self.effort.copy()
        self.assertEqualEfforts(copyEffort, self.effort)
        self.assertEqual(copyEffort.description(), self.effort.description())

    def testCopyHasDifferentId(self):
        copyEffort = self.effort.copy()
        self.assertNotEqual(copyEffort.id(), self.effort.id())

    def testCopyHasStatusNew(self):
        self.effort.markDeleted()
        copyEffort = self.effort.copy()
        self.assertEqual(copyEffort.getStatus(), copyEffort.STATUS_NEW)

    def testDescription(self):
        self.effort.setDescription("description")
        self.assertEqual("description", self.effort.description())

    def testDescription_Constructor(self):
        newEffort = effort.Effort(self.task, description="description")
        self.assertEqual("description", newEffort.description())

    def testSetStop_None(self):
        self.effort.setStop()
        now = date.Now()
        self.assertTrue(
            now - date.ONE_SECOND
            < self.effort.getStop()
            < now + date.ONE_SECOND
        )

    def testSetStop_Infinite(self):
        self.effort.setStop(date.DateTime.max)
        self.assertEqual(None, self.effort.getStop())

    def testSetStop_SpecificDateTime(self):
        self.effort.setStop(date.DateTime(2005, 1, 1))
        self.assertEqual(date.DateTime(2005, 1, 1), self.effort.getStop())

    def testIsNotBeingTracked_(self):
        self.assertFalse(self.effort.isBeingTracked())

    def testIsBeingTracked(self):
        self.effort.setStop(date.DateTime.max)
        self.assertTrue(self.effort.isBeingTracked())

    def testSetTaskToNewTaskWillAddItToNewTask(self):
        task2 = task.Task()
        self.effort.setTask(task2)
        self.assertEqual([self.effort], task2.efforts())

    def testSetTaskToNewTaskWillRemoveItFromOldTask(self):
        self.task.addEffort(self.effort)
        task2 = task.Task()
        self.effort.setTask(task2)
        self.assertEqual([self.effort], task2.efforts())
        self.assertFalse(self.effort in self.task.efforts())

    def testSetTaskToOldTaskTwice(self):
        self.task.addEffort(self.effort)
        self.effort.setTask(self.task)
        self.assertEqual([self.effort], self.task.efforts())

    def testRevenueWithoutFee(self):
        self.task.addEffort(self.effort)
        self.assertEqual(0, self.effort.revenue())

    def testRevenue_HourlyFee(self):
        self.task.setHourlyFee(100)
        self.task.addEffort(self.effort)
        self.assertEqual(
            self.effort.duration().hours() * 100, self.effort.revenue()
        )

    def testRevenue_FixedFee_OneEffort(self):
        self.task.setFixedFee(1000)
        self.task.addEffort(self.effort)
        self.assertEqual(0, self.effort.revenue())

    def testRevenue_FixedFee_OneSmallEffort(self):
        self.task.setFixedFee(1000)
        self.effort.setStop(self.effort.getStart())
        self.assertEqual(0, self.effort.revenue())

    def testRevenue_FixedFee_TwoEfforts(self):
        self.task.setFixedFee(1000)
        self.task.addEffort(self.effort)
        self.task.addEffort(
            effort.Effort(
                self.task,
                date.DateTime(2005, 1, 1, 10, 0),
                date.DateTime(2005, 1, 1, 22, 0),
            )
        )
        self.assertEqual(0, self.effort.revenue())

    def testSubject(self):
        self.assertEqual(self.task.subject(), self.effort.subject())

    def testNoCategories(self):
        self.assertEqual(self.task.categories(), self.effort.categories())

    def testCategories(self):
        self.task.addCategory(category.Category("C"))
        self.assertEqual(self.task.categories(), self.effort.categories())

    def testModificationEventTypes(self):  # pylint: disable=E1003
        self.assertEqual(
            super(effort.Effort, self.effort).modificationEventTypes()
            + [
                self.effort.taskChangedEventType(),
                self.effort.startChangedEventType(),
                self.effort.stopChangedEventType(),
                self.effort.entryModeChangedEventType(),
            ],
            self.effort.modificationEventTypes(),
        )


class EffortWithoutTaskTest(test.TestCase):
    def setUp(self):
        self.effort = effort.Effort(None, start=date.DateTime(2005, 1, 1))
        self.task = task.Task()
        self.events = []

    def onEvent(self, event):
        self.events.append(event)  # pragma: no cover

    def testCreatingAnEffortWithoutTask(self):
        self.assertEqual(None, self.effort.task())

    def testSettingTask(self):
        self.effort.setTask(self.task)
        self.assertEqual(self.task, self.effort.task())

    def testSettingTask_CausesNoNotification(self):
        patterns.Publisher().registerObserver(
            self.onEvent, self.effort.taskChangedEventType()
        )
        self.effort.setTask(self.task)
        self.assertFalse(self.events)
