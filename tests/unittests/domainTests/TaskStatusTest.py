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
from taskcoachlib.domain import task, date


class TaskStatusTest(test.TestCase):
    def setUp(self):
        self.now = date.Now()
        self.yesterday = self.now - date.ONE_DAY
        self.nearFuture = self.now + date.ONE_DAY - date.ONE_HOUR
        self.dates = (self.yesterday, self.nearFuture)
        self.farFuture = self.now + date.ONE_DAY + date.ONE_DAY

    def assertTaskStatus(self, status, **task_kw_args):
        self.assertEqual(status, task.Task(**task_kw_args).computedStatus())

    # No dates/times

    def test_default_task_is_inactive(self):
        self.assertTaskStatus(task.status.inactive)

    # One date/time

    def test_task_with_completion_in_the_past_is_completed(self):
        self.assertTaskStatus(
            task.status.completed, completionDateTime=self.yesterday
        )

    def test_task_with_completion_in_the_future_is_completed(self):
        # Maybe keep the task inactive until the completion date passes?
        # That would be more consistent with the other date/times
        self.assertTaskStatus(
            task.status.completed, completionDateTime=self.nearFuture
        )

    def test_task_with_planned_start_in_the_past_is_late(self):
        self.assertTaskStatus(
            task.status.late, plannedStartDateTime=self.yesterday
        )

    def test_task_with_planned_start_in_the_future_is_inactive(self):
        self.assertTaskStatus(
            task.status.inactive, plannedStartDateTime=self.nearFuture
        )

    def test_task_with_actual_start_in_the_past_is_active(self):
        self.assertTaskStatus(
            task.status.active, actualStartDateTime=self.yesterday
        )

    def test_task_with_actual_start_in_the_future_is_inactive(self):
        self.assertTaskStatus(
            task.status.inactive, actualStartDateTime=self.nearFuture
        )

    def test_task_with_due_in_the_past_is_overdue(self):
        self.assertTaskStatus(task.status.overdue, dueDateTime=self.yesterday)

    def test_task_with_due_in_the_future_is_inactive(self):
        self.assertTaskStatus(task.status.inactive, dueDateTime=self.farFuture)

    def test_task_with_due_in_the_near_future_is_due_soon(self):
        self.assertTaskStatus(task.status.duesoon, dueDateTime=self.nearFuture)

    # Two dates/times

    # planned start date/time and actual start date/time

    def test_task_with_planned_and_actual_start_in_the_past_is_active(self):
        self.assertTaskStatus(
            task.status.active,
            plannedStartDateTime=self.yesterday,
            actualStartDateTime=self.yesterday,
        )

    def test_task_planned_start_in_past_actual_start_in_future_is_late(
        self,
    ):
        self.assertTaskStatus(
            task.status.late,
            plannedStartDateTime=self.yesterday,
            actualStartDateTime=self.nearFuture,
        )

    def test_task_planned_start_in_future_actual_start_in_past_is_active(
        self,
    ):
        self.assertTaskStatus(
            task.status.active,
            plannedStartDateTime=self.nearFuture,
            actualStartDateTime=self.yesterday,
        )

    def test_task_with_planned_and_actual_start_in_the_future_is_inactive(
        self,
    ):
        self.assertTaskStatus(
            task.status.inactive,
            plannedStartDateTime=self.nearFuture,
            actualStartDateTime=self.nearFuture,
        )

    # planned start date/time and due date/time

    def test_task_with_planned_start_and_due_in_the_past_is_overdue(self):
        self.assertTaskStatus(
            task.status.overdue,
            plannedStartDateTime=self.yesterday,
            dueDateTime=self.yesterday,
        )

    def test_task_with_planned_start_in_the_past_and_due_in_the_future_is_late(
        self,
    ):
        self.assertTaskStatus(
            task.status.late,
            plannedStartDateTime=self.yesterday,
            dueDateTime=self.farFuture,
        )

    def test_task_planned_start_in_past_due_in_near_future_is_due_soon(
        self,
    ):
        self.assertTaskStatus(
            task.status.duesoon,
            plannedStartDateTime=self.yesterday,
            dueDateTime=self.nearFuture,
        )

    def test_task_with_planned_start_in_future_and_due_in_past_is_overdue(
        self,
    ):
        self.assertTaskStatus(
            task.status.overdue,
            plannedStartDateTime=self.nearFuture,
            dueDateTime=self.yesterday,
        )

    def test_task_with_planned_start_in_future_and_due_in_future_is_late(
        self,
    ):
        self.assertTaskStatus(
            task.status.inactive,
            plannedStartDateTime=self.nearFuture,
            dueDateTime=self.farFuture,
        )

    def test_task_planned_start_in_future_due_in_near_future_is_due_soon(
        self,
    ):
        self.assertTaskStatus(
            task.status.duesoon,
            plannedStartDateTime=self.nearFuture,
            dueDateTime=self.nearFuture,
        )

    # planned start date/time and completion date/time

    def test_task_with_planned_start_and_completion_in_the_past_is_completed(
        self,
    ):
        self.assertTaskStatus(
            task.status.completed,
            plannedStartDateTime=self.yesterday,
            completionDateTime=self.yesterday,
        )

    def test_task_planned_start_in_past_completion_in_future_is_completed(
        self,
    ):
        self.assertTaskStatus(
            task.status.completed,
            plannedStartDateTime=self.yesterday,
            completionDateTime=self.nearFuture,
        )

    def test_task_planned_start_in_future_completion_in_past_is_completed(
        self,
    ):
        self.assertTaskStatus(
            task.status.completed,
            plannedStartDateTime=self.nearFuture,
            completionDateTime=self.yesterday,
        )

    def test_task_planned_start_in_future_completion_in_future_is_complete(
        self,
    ):
        self.assertTaskStatus(
            task.status.completed,
            plannedStartDateTime=self.nearFuture,
            completionDateTime=self.nearFuture,
        )

    # actual start date/time and due date/time

    def test_task_with_actual_start_and_due_in_the_past_is_overdue(self):
        self.assertTaskStatus(
            task.status.overdue,
            actualStartDateTime=self.yesterday,
            dueDateTime=self.yesterday,
        )

    def test_task_with_actual_start_in_past_and_due_in_future_is_active(
        self,
    ):
        self.assertTaskStatus(
            task.status.active,
            actualStartDateTime=self.yesterday,
            dueDateTime=self.farFuture,
        )

    def test_task_with_actual_start_in_past_and_due_in_near_future_is_due_soon(
        self,
    ):
        self.assertTaskStatus(
            task.status.duesoon,
            actualStartDateTime=self.yesterday,
            dueDateTime=self.nearFuture,
        )

    def test_task_with_actual_start_in_future_and_due_in_past_is_overdue(
        self,
    ):
        self.assertTaskStatus(
            task.status.overdue,
            actualStartDateTime=self.nearFuture,
            dueDateTime=self.yesterday,
        )

    def test_task_with_actual_start_in_future_and_due_in_future_is_active(
        self,
    ):
        self.assertTaskStatus(
            task.status.inactive,
            actualStartDateTime=self.nearFuture,
            dueDateTime=self.farFuture,
        )

    def test_task_actual_start_in_future_due_in_near_future_is_due_soon(
        self,
    ):
        self.assertTaskStatus(
            task.status.duesoon,
            actualStartDateTime=self.nearFuture,
            dueDateTime=self.nearFuture,
        )

    # actual start date/time and completion date/time

    def test_task_with_actual_start_and_completion_in_the_past_is_completed(
        self,
    ):
        self.assertTaskStatus(
            task.status.completed,
            actualStartDateTime=self.yesterday,
            completionDateTime=self.yesterday,
        )

    def test_task_actual_start_in_past_completion_in_future_is_completed(
        self,
    ):
        self.assertTaskStatus(
            task.status.completed,
            actualStartDateTime=self.yesterday,
            completionDateTime=self.nearFuture,
        )

    def test_task_actual_start_in_future_completion_in_past_is_completed(
        self,
    ):
        self.assertTaskStatus(
            task.status.completed,
            actualStartDateTime=self.nearFuture,
            completionDateTime=self.yesterday,
        )

    def test_task_actual_start_in_future_completion_in_future_is_complete(
        self,
    ):
        self.assertTaskStatus(
            task.status.completed,
            actualStartDateTime=self.nearFuture,
            completionDateTime=self.nearFuture,
        )

    # due date/time and completion date/time

    def test_task_with_due_and_completion_in_the_past_is_completed(self):
        self.assertTaskStatus(
            task.status.completed,
            dueDateTime=self.yesterday,
            completionDateTime=self.yesterday,
        )

    def test_task_with_due_in_past_and_completion_in_future_is_completed(
        self,
    ):
        self.assertTaskStatus(
            task.status.completed,
            dueDateTime=self.yesterday,
            completionDateTime=self.nearFuture,
        )

    def test_task_with_due_in_future_and_completion_in_past_is_completed(
        self,
    ):
        self.assertTaskStatus(
            task.status.completed,
            dueDateTime=self.nearFuture,
            completionDateTime=self.yesterday,
        )

    def test_task_with_due_in_future_and_completion_in_future_is_complete(
        self,
    ):
        self.assertTaskStatus(
            task.status.completed,
            dueDateTime=self.nearFuture,
            completionDateTime=self.nearFuture,
        )

    # Three dates/times

    # planned start date/time, actual start date/time and due date/time
    # (Other combinations are not interesting since they are always completed)

    def test_task_is_overdue_whenever_due_is_in_the_past(self):
        for planned in self.dates:
            for actual in self.dates:
                self.assertTaskStatus(
                    task.status.overdue,
                    plannedStartDateTime=planned,
                    actualStartDateTime=actual,
                    dueDateTime=self.yesterday,
                )

    def test_task_is_duesoon_whenever_due_is_in_the_near_future(self):
        for planned in self.dates:
            for actual in self.dates:
                self.assertTaskStatus(
                    task.status.duesoon,
                    plannedStartDateTime=planned,
                    actualStartDateTime=actual,
                    dueDateTime=self.nearFuture,
                )

    def test_task_is_overdue_whenever_due_is_in_the_future(self):
        for planned in self.dates:
            expected_status_based_on_planned_start = (
                task.status.late
                if planned < self.now
                else task.status.inactive
            )
            for actual in self.dates:
                expected_status = (
                    task.status.active
                    if actual < self.now
                    else expected_status_based_on_planned_start
                )
                self.assertTaskStatus(
                    expected_status,
                    plannedStartDateTime=planned,
                    actualStartDateTime=actual,
                    dueDateTime=self.farFuture,
                )

    # Four date/times (always completed)

    def test_task_with_completion_date_time_is_always_completed(self):
        for planned in self.dates:
            for actual in self.dates:
                for due in self.dates + (self.farFuture,):
                    for completion in self.dates:
                        self.assertTaskStatus(
                            task.status.completed,
                            plannedStartDateTime=planned,
                            actualStartDateTime=actual,
                            dueDateTime=due,
                            completionDateTime=completion,
                        )

    # Prerequisites

    def test_task_with_uncompleted_prerequisite_is_never_late(self):
        prerequisite = task.Task()
        for planned in self.dates:
            self.assertTaskStatus(
                task.status.inactive,
                plannedStartDateTime=planned,
                prerequisites=[prerequisite],
            )

    def test_task_with_completed_prerequisite_late_when_planned_start_past(
        self,
    ):
        prerequisite = task.Task(completionDateTime=self.yesterday)
        for planned in self.dates:
            expected_status = (
                task.status.late
                if planned < self.now
                else task.status.inactive
            )
            self.assertTaskStatus(
                expected_status,
                plannedStartDateTime=planned,
                prerequisites=[prerequisite],
            )

    def test_mutual_prerequisites(self):
        task_a = task.Task()
        task_b = task.Task(prerequisites=[task_a])
        task_a.add_prerequisites([task_b])
        for each_task in (task_a, task_b):
            self.assertEqual(task.status.inactive, each_task.computedStatus())
