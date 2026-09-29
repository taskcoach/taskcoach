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

DESIGN NOTE (Scheduler Refactoring - 2024):
The old Scheduler class has been completely removed and replaced with a simpler
GlobalTimer architecture. See docs/SCHEDULERS.md for details.

GlobalTimer sends the Publisher event 'timer.second' every second
(source is the GlobalTimer, value is the tick timestamp).
"""

import test
import wx
from taskcoachlib import config, patterns
from taskcoachlib.domain import date, effort, task
from taskcoachlib.gui import scheduler


class GlobalTimerEventTest(test.wxTestCase):
    """Tests for the Publisher events published by GlobalTimer."""

    def setUp(self):
        super().setUp()
        self.timer = scheduler.GlobalTimer(self.frame)

    def tearDown(self):
        self.timer.stop()
        super().tearDown()

    def tick(self):
        self.timer._on_tick(None)  # pylint: disable=W0212

    def test_tick_sends_only_timer_second(self):
        # Date and minute changes come from MasterScheduler
        for event_type in ("timer.second", "timer.minute", "timer.date"):
            self.registerObserver(event_type)
        self.tick()
        self.assertEqual(
            ["timer.second"], [event.type() for event in self.events]
        )

    def test_event_source_is_the_timer_and_value_is_timestamp(self):
        self.registerObserver("timer.second")
        before = date.DateTime.now()
        self.tick()
        event = self.events[0]
        self.assertEqual(set([self.timer]), event.sources())
        self.assertTrue(before <= event.value() <= date.DateTime.now())

    def test_every_second_publishes_timer_second(self):
        self.registerObserver("timer.second")
        self.tick()
        self.tick()
        self.assertEqual(2, len(self.events))

    def test_multiple_subscribers(self):
        events1 = []
        events2 = []

        class Subscriber:
            def __init__(self, events):
                self.events = events

            def on_second(self, event):
                self.events.append(event)

        subscriber1 = Subscriber(events1)
        subscriber2 = Subscriber(events2)
        for subscriber in (subscriber1, subscriber2):
            patterns.Publisher().registerObserver(
                subscriber.on_second, eventType="timer.second"
            )
        self.tick()
        self.assertEqual(1, len(events1))
        self.assertEqual(1, len(events2))

    def test_remove_observer_stops_events(self):
        self.registerObserver("timer.second")
        patterns.Publisher().removeObserver(
            self.onEvent, eventType="timer.second"
        )
        self.tick()
        self.assertFalse(hasattr(self, "events") and self.events)


class MasterSchedulerEventTest(test.wxTestCase):
    """MasterScheduler sends scheduler.date and scheduler.minute after
    its tick's processing, as Publisher events."""

    def setUp(self):
        super().setUp()
        from taskcoachlib import persistence

        self.task_file = persistence.TaskFile()
        self.master = scheduler.MasterScheduler(self.task_file)

    def tearDown(self):
        self.master.shutdown()
        self.task_file.close()
        self.task_file.stop()
        super().tearDown()

    def second(self, timestamp):
        # The Publisher drops events without a source
        patterns.Event("timer.second", self, timestamp).send()

    def register_date_and_minute(self):
        for event_type in ("scheduler.date", "scheduler.minute"):
            self.registerObserver(event_type)

    @staticmethod
    def today_at(hour, minute=0, second=0, days=0):
        # The scheduler starts out on the real current day
        now = date.DateTime.now()
        day = date.DateTime(now.year, now.month, now.day, hour, minute)
        return day + date.TimeDelta(days=days, seconds=second)

    def test_first_second_sends_only_the_minute(self):
        # Viewers were just drawn for today
        self.register_date_and_minute()
        self.second(self.today_at(10))
        self.assertEqual(
            ["scheduler.minute"], [event.type() for event in self.events]
        )

    def test_first_second_on_the_next_day_sends_the_date(self):
        # Started just before midnight: the viewers show yesterday
        self.register_date_and_minute()
        self.second(self.today_at(0, second=1, days=1))
        self.assertIn("scheduler.date", [e.type() for e in self.events])

    def test_new_day_sends_date_and_minute(self):
        self.second(self.today_at(23, 59, 59))
        self.register_date_and_minute()
        self.second(self.today_at(0, days=1))
        self.assertEqual(
            set(["scheduler.date", "scheduler.minute"]),
            set(event.type() for event in self.events),
        )

    def test_same_minute_sends_nothing(self):
        self.second(self.today_at(10))
        self.registerObserver("scheduler.minute")
        self.second(self.today_at(10, 0, 30))
        self.assertEqual([], self.events)

    def test_failing_subscriber_does_not_stop_the_others(self):
        # Both fail: whichever runs first, the other still runs
        self.failed = []
        for observer in (self.on_minute_failing, self.on_minute_failing_too):
            patterns.Publisher().registerObserver(
                observer, eventType="scheduler.minute"
            )
        self.second(self.today_at(10))
        self.assertEqual(["first", "second"], sorted(self.failed))

    def on_minute_failing(self, event):
        self.failed.append("first")
        raise ValueError("subscriber bug")

    def on_minute_failing_too(self, event):
        self.failed.append("second")
        raise ValueError("subscriber bug")


class MasterTimerListTest(test.wxTestCase):
    """The full loop runs only when the heap holds a due second
    (docs/MASTER_SCHEDULER_REFACTOR.md)."""

    start = date.DateTime(2026, 9, 27, 12, 0, 0)

    def setUp(self):
        super().setUp()
        from taskcoachlib import persistence

        task.Task.settings = config.Settings(load=False)
        self.task_file = persistence.TaskFile()
        self.master = scheduler.MasterScheduler(self.task_file)
        self.passes = []
        run_pass = self.master._run_pass

        def record_pass(timestamp, due):
            self.passes.append(timestamp)
            run_pass(timestamp, due)

        self.master._run_pass = record_pass
        self.task = task.Task(subject="task")
        self.task_file.tasks().append(self.task)
        self.now = self.start

    def tearDown(self):
        self.master.shutdown()
        self.task_file.close()
        self.task_file.stop()
        super().tearDown()

    def tick(self, seconds=1):
        self.now += date.TimeDelta(seconds=seconds)
        before = len(self.passes)
        patterns.Event("timer.second", self, self.now).send()
        return len(self.passes) > before

    def settle(self):
        """Tick until a tick runs no pass; return the passes run."""
        for count in range(10):
            if not self.tick():
                return count
        self.fail("the cascade does not settle")

    def test_first_tick_runs_the_loop(self):
        self.assertTrue(self.tick(0))

    def test_the_cascade_settles(self):
        self.assertGreater(self.settle(), 0)
        self.assertFalse(self.tick())

    def test_the_second_after_the_due_runs_the_loop(self):
        self.task.set_due_date_time(self.start + date.ONE_HOUR)
        self.settle()
        self.now = self.start + date.ONE_HOUR - date.ONE_SECOND
        self.assertFalse(self.tick())  # At the due: not overdue yet
        self.assertTrue(self.tick())
        self.assertEqual(task.status.overdue, self.task.computedStatus())

    def test_one_pass_takes_every_due_second_and_leaves_the_next(self):
        self.settle()
        dues = [
            self.now + date.TimeDelta(seconds=seconds)
            for seconds in (-20, -10, 1)
        ]
        later = self.now + date.ONE_MINUTE
        added = [
            task.Task(subject="due", dueDateTime=due) for due in dues + [later]
        ]
        self.task_file.tasks().extend(added)
        # One tick takes the past overdue seconds and this second's
        self.assertTrue(self.tick(2))
        self.assertEqual(
            [task.status.overdue] * 3,
            [each.computedStatus() for each in added[:3]],
        )
        self.assertEqual(task.status.duesoon, added[3].computedStatus())
        # The later second stays until its time
        self.settle()
        self.now = later - date.ONE_SECOND
        self.assertFalse(self.tick())
        self.assertTrue(self.tick())
        self.assertEqual(task.status.overdue, added[3].computedStatus())

    def test_a_colour_change_runs_the_loop_at_the_next_tick(self):
        self.settle()
        self.task.setForegroundColor(wx.RED)
        self.assertTrue(self.tick())

    def test_a_subject_change_runs_nothing(self):
        self.settle()
        self.task.setSubject("new subject")
        self.assertFalse(self.tick())

    def test_a_fee_change_runs_nothing(self):
        # Nor the revenue it changes: the loop reads neither
        self.task.addEffort(
            effort.Effort(self.task, self.start - date.ONE_HOUR, self.start)
        )
        self.settle()
        self.task.set_hourly_fee(100)
        self.assertFalse(self.tick())

    def test_a_priority_change_runs_nothing(self):
        # Nor for the ancestors it names: the loop reads no priority
        self.settle()
        self.task.setPriority(5)
        self.assertFalse(self.tick())

    def test_a_blocked_tasks_subtask_looks_and_counts_inactive(self):
        # The ancestors' prerequisites count, in the styles and the
        # status bar as in the status column and the filters
        prerequisite = task.Task(subject="prerequisite")
        parent = task.Task(subject="parent", prerequisites=[prerequisite])
        child = task.Task(
            subject="child", plannedStartDateTime=self.start - date.ONE_HOUR
        )
        parent.addChild(child)
        self.task_file.tasks().extend([prerequisite, parent])
        self.settle()
        counts = self.task_file.tasks().nr_of_tasks_per_status()
        self.assertEqual(
            (
                task.status.inactive,
                child.fgColorForStatus(task.status.inactive),
                0,
            ),
            (
                child.computedStatus(),
                child.statusFgColor(),
                counts[task.status.late],
            ),
        )

    def test_expanding_runs_nothing(self):
        self.settle()
        self.task.expand()
        self.assertFalse(self.tick())

    def test_a_reminder_set_in_the_past_fires_at_the_next_tick(self):
        self.settle()
        self.registerObserver("task.reminder.trigger")
        self.task.set_reminder(self.now - date.ONE_HOUR)
        self.tick()
        self.assertEqual(1, len(self.events))

    def test_an_added_task_runs_the_loop_at_its_due(self):
        self.settle()
        due = self.now + date.ONE_HOUR
        added = task.Task(subject="added", dueDateTime=due)
        self.task_file.tasks().append(added)
        self.settle()
        self.now = due
        self.assertTrue(self.tick())
        self.assertEqual(task.status.overdue, added.computedStatus())

    def test_setting_the_clock_back_runs_the_loop(self):
        self.settle()
        self.assertTrue(self.tick(-3600))
