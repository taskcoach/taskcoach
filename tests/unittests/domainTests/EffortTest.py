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
from unittests import asserts
import test
import wx


class EffortTest(test.TestCase, asserts.Mixin):
    def setUp(self):
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

    def test_id(self):
        self.assertTrue(self.effort.id() is not None)

    def test_create(self):
        self.assertEqual(self.task, self.effort.task())
        self.assertEqual("", self.effort.description())

    def test_str(self):
        self.assertEqual(
            "Effort(%s, %s, %s)"
            % (
                self.effort.task(),
                self.effort.getStart(),
                self.effort.getStop(),
            ),
            str(self.effort),
        )

    def test_duration(self):
        self.assertEqual(date.TimeDelta(days=1), self.effort.timeSpent())

    def test_foreground_color_is_the_task_color(self):
        self.task.setForegroundColor(wx.RED)
        test.styled(self.task)
        self.assertEqual(wx.RED, self.effort.shown_fg_color())

    def test_background_color_is_the_task_color(self):
        self.task.setBackgroundColor(wx.RED)
        test.styled(self.task)
        self.assertEqual(wx.RED, self.effort.shown_bg_color())

    def test_font_is_the_task_font(self):
        self.task.setFont(wx.SWISS_FONT)
        test.styled(self.task)
        self.assertEqual(wx.SWISS_FONT, self.effort.shown_font())

    def changes(self):
        return [
            (event.value(source), source)
            for event in self.events
            for source in event.sources()
        ]

    def test_notification_for_set_start(self):
        self.registerObserver(effort.Effort.startChangedEventType())
        start = date.DateTime.now()
        self.effort.setStart(start)
        self.assertEqual([(start, self.effort)], self.changes())

    def test_notification_for_set_stop(self):
        self.registerObserver(effort.Effort.stopChangedEventType())
        stop = date.DateTime.now()
        self.effort.setStop(stop)
        self.assertEqual([(stop, self.effort)], self.changes())

    def test_no_notification_for_an_unchanged_stop(self):
        self.registerObserver(effort.Effort.stopChangedEventType())
        self.effort.setStop(self.effort.getStop())
        self.assertFalse(self.events)

    def test_effort_change_sets_its_modification_date(self):
        before = date.Now()
        self.effort.setStart(date.DateTime(2004, 1, 1, 12, 0, 0))
        self.assertTrue(before <= self.effort.modificationDateTime())

    def test_duration_notification_for_set_duration(self):
        events = test.ChangeRecorder(effort.Effort.durationChangedEventType())
        self.effort.setDuration(date.TimeDelta(hours=2))
        self.assertEqual([(date.TimeDelta(hours=2), self.effort)], events)

    def test_start_and_stop_changes_keep_the_stored_duration(self):
        # The effort editor recalculates it by entry mode
        # (docs/DURATION_CALCULATIONS.md)
        events = test.ChangeRecorder(effort.Effort.durationChangedEventType())
        self.effort.setStart(date.DateTime(2004, 1, 1, 12, 0, 0))
        self.effort.setStop(date.DateTime(2004, 1, 3))
        self.assertEqual(
            ([], date.TimeDelta(hours=24)),
            (events, self.effort.stored_duration()),
        )

    def test_start_change_sends_the_tasks_time_spent(self):
        events = test.ChangeRecorder(task.Task.timeSpentChangedEventType())
        self.effort.setStart(date.DateTime(2004, 1, 1, 12, 0, 0))
        self.assertEqual([(date.TimeDelta(hours=12), self.task)], events)

    def test_stop_change_sends_the_tasks_time_spent(self):
        events = test.ChangeRecorder(task.Task.timeSpentChangedEventType())
        self.effort.setStop(date.DateTime(2004, 1, 3))
        self.assertEqual([(date.TimeDelta(hours=48), self.task)], events)

    def test_notification_for_set_description(self):
        patterns.Publisher().registerObserver(
            self.onEvent, eventType=effort.Effort.descriptionChangedEventType()
        )
        self.effort.setDescription("description")
        self.assertEqual("description", self.events[0].value())

    def test_notification_for_set_task(self):
        self.registerObserver(effort.Effort.taskChangedEventType())
        task2 = task.Task()
        self.effort.set_task(task2)
        self.assertEqual([(task2, self.effort)], self.changes())

    def test_moving_to_another_task_sets_the_modification_date(self):
        self.effort.set_modification_datetime(date.DateTime.min)
        before = date.Now()
        self.effort.set_task(task.Task())
        self.assertTrue(before <= self.effort.modificationDateTime())

    def test_notification_for_start_tracking(self):
        events = test.ChangeRecorder(self.effort.trackingChangedEventType())
        self.effort.setStop(date.DateTime())
        self.assertEqual([(True, self.effort)], events)

    def test_notification_for_stop_tracking(self):
        self.effort.setStop(date.DateTime())
        events = test.ChangeRecorder(self.effort.trackingChangedEventType())
        self.effort.setStop(date.DateTime.now())
        self.assertEqual([(False, self.effort)], events)

    def test_revenue_notification_for_task_hourly_fee_change(self):
        events = test.ChangeRecorder(effort.Effort.revenueChangedEventType())
        self.task.set_hourly_fee(100)
        self.assertEqual([(2400.0, self.effort)], events)

    def test_revenue_notification_for_a_duration_change(self):
        self.task.set_hourly_fee(100)
        events = test.ChangeRecorder(effort.Effort.revenueChangedEventType())
        self.effort.setDuration(date.TimeDelta(hours=2))
        self.assertEqual([(2400.0, self.effort)], events)

    def test_default_start_and_stop(self):
        effort_period = effort.Effort(self.task)
        current_time = date.DateTime.now()

        def now():
            return current_time

        self.assertEqual(
            now() - effort_period.getStart(), effort_period.timeSpent(now=now)
        )

    def test_copy(self):
        copy_effort = self.effort.copy()
        self.assertEqualEfforts(copy_effort, self.effort)
        self.assertEqual(copy_effort.description(), self.effort.description())

    def test_copy_has_different_id(self):
        copy_effort = self.effort.copy()
        self.assertNotEqual(copy_effort.id(), self.effort.id())

    def test_description(self):
        self.effort.setDescription("description")
        self.assertEqual("description", self.effort.description())

    def test_description_constructor(self):
        new_effort = effort.Effort(self.task, description="description")
        self.assertEqual("description", new_effort.description())

    def test_set_stop_none(self):
        self.effort.setStop()
        now = date.Now()
        self.assertTrue(
            now - date.ONE_SECOND
            <= self.effort.getStop()
            < now + date.ONE_SECOND
        )

    def test_set_stop_infinite(self):
        self.effort.setStop(date.DateTime.max)
        self.assertEqual(None, self.effort.getStop())

    def test_set_stop_specific_date_time(self):
        self.effort.setStop(date.DateTime(2005, 1, 1))
        self.assertEqual(date.DateTime(2005, 1, 1), self.effort.getStop())

    def test_is_not_being_tracked_(self):
        self.assertFalse(self.effort.isBeingTracked())

    def test_is_being_tracked(self):
        self.effort.setStop(date.DateTime.max)
        self.assertTrue(self.effort.isBeingTracked())

    def test_set_task_to_new_task_will_add_it_to_new_task(self):
        task2 = task.Task()
        self.effort.set_task(task2)
        self.assertEqual([self.effort], task2.efforts())

    def test_set_task_to_new_task_will_remove_it_from_old_task(self):
        self.task.addEffort(self.effort)
        task2 = task.Task()
        self.effort.set_task(task2)
        self.assertEqual([self.effort], task2.efforts())
        self.assertFalse(self.effort in self.task.efforts())

    def test_set_task_to_old_task_twice(self):
        self.task.addEffort(self.effort)
        self.effort.set_task(self.task)
        self.assertEqual([self.effort], self.task.efforts())

    def test_revenue_without_fee(self):
        self.task.addEffort(self.effort)
        self.assertEqual(0, self.effort.revenue())

    def test_revenue_hourly_fee(self):
        self.task.set_hourly_fee(100)
        self.task.addEffort(self.effort)
        self.assertEqual(
            self.effort.timeSpent().hours() * 100, self.effort.revenue()
        )

    def test_revenue_fixed_fee_one_effort(self):
        self.task.set_fixed_fee(1000)
        self.task.addEffort(self.effort)
        self.assertEqual(0, self.effort.revenue())

    def test_revenue_fixed_fee_one_small_effort(self):
        self.task.set_fixed_fee(1000)
        self.effort.setStop(self.effort.getStart())
        self.assertEqual(0, self.effort.revenue())

    def test_revenue_fixed_fee_two_efforts(self):
        self.task.set_fixed_fee(1000)
        self.task.addEffort(self.effort)
        self.task.addEffort(
            effort.Effort(
                self.task,
                date.DateTime(2005, 1, 1, 10, 0),
                date.DateTime(2005, 1, 1, 22, 0),
            )
        )
        self.assertEqual(0, self.effort.revenue())

    def test_subject(self):
        self.assertEqual(self.task.subject(), self.effort.subject())

    def test_no_categories(self):
        self.assertEqual(self.task.categories(), self.effort.categories())

    def test_categories(self):
        self.task.addCategory(category.Category("C"))
        self.assertEqual(self.task.categories(), self.effort.categories())

    def test_modification_event_types(self):  # pylint: disable=E1003
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

    def test_creating_an_effort_without_task(self):
        self.assertEqual(None, self.effort.task())

    def test_setting_task(self):
        self.effort.set_task(self.task)
        self.assertEqual(self.task, self.effort.task())

    def test_setting_task_causes_no_notification(self):
        patterns.Publisher().registerObserver(
            self.onEvent, self.effort.taskChangedEventType()
        )
        self.effort.set_task(self.task)
        self.assertFalse(self.events)


class TrackedEffortCopyTest(test.TestCase):
    def test_a_copy_of_a_tracked_effort_is_stopped(self):
        # It holds the time spent so far; one task tracked at a time
        # (docs/EFFORTS.md, Tracking)
        tracked = effort.Effort(task.Task(), date.DateTime(2026, 1, 1))
        self.assertFalse(tracked.copy().isBeingTracked())
