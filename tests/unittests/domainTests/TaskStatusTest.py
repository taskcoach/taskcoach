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

    def assertTaskStatus(self, status, **taskKwArgs):
        self.assertEqual(status, task.Task(**taskKwArgs).computedStatus())

    # No dates/times

    def testDefaultTaskIsInactive(self):
        self.assertTaskStatus(task.status.inactive)

    # One date/time

    def testTaskWithCompletionInThePastIsCompleted(self):
        self.assertTaskStatus(
            task.status.completed, completionDateTime=self.yesterday
        )

    def testTaskWithCompletionInTheFutureIsCompleted(self):
        # Maybe keep the task inactive until the completion date passes?
        # That would be more consistent with the other date/times
        self.assertTaskStatus(
            task.status.completed, completionDateTime=self.nearFuture
        )

    def testTaskWithPlannedStartInThePastIsLate(self):
        self.assertTaskStatus(
            task.status.late, plannedStartDateTime=self.yesterday
        )

    def testTaskWithPlannedStartInTheFutureIsInactive(self):
        self.assertTaskStatus(
            task.status.inactive, plannedStartDateTime=self.nearFuture
        )

    def testTaskWithActualStartInThePastIsActive(self):
        self.assertTaskStatus(
            task.status.active, actualStartDateTime=self.yesterday
        )

    def testTaskWithActualStartInTheFutureIsInactive(self):
        self.assertTaskStatus(
            task.status.inactive, actualStartDateTime=self.nearFuture
        )

    def testTaskWithDueInThePastIsOverdue(self):
        self.assertTaskStatus(task.status.overdue, dueDateTime=self.yesterday)

    def testTaskWithDueInTheFutureIsInactive(self):
        self.assertTaskStatus(task.status.inactive, dueDateTime=self.farFuture)

    def testTaskWithDueInTheNearFutureIsDueSoon(self):
        self.assertTaskStatus(task.status.duesoon, dueDateTime=self.nearFuture)

    # Two dates/times

    # planned start date/time and actual start date/time

    def testTaskWithPlannedAndActualStartInThePastIsActive(self):
        self.assertTaskStatus(
            task.status.active,
            plannedStartDateTime=self.yesterday,
            actualStartDateTime=self.yesterday,
        )

    def testTaskWithPlannedStartInThePastAndActualStartInTheFutureIsLate(self):
        self.assertTaskStatus(
            task.status.late,
            plannedStartDateTime=self.yesterday,
            actualStartDateTime=self.nearFuture,
        )

    def testTaskWithPlannedStartInTheFutureAndActualStartInThePastIsActive(
        self,
    ):
        self.assertTaskStatus(
            task.status.active,
            plannedStartDateTime=self.nearFuture,
            actualStartDateTime=self.yesterday,
        )

    def testTaskWithPlannedAndActualStartInTheFutureIsInactive(self):
        self.assertTaskStatus(
            task.status.inactive,
            plannedStartDateTime=self.nearFuture,
            actualStartDateTime=self.nearFuture,
        )

    # planned start date/time and due date/time

    def testTaskWithPlannedStartAndDueInThePastIsOverdue(self):
        self.assertTaskStatus(
            task.status.overdue,
            plannedStartDateTime=self.yesterday,
            dueDateTime=self.yesterday,
        )

    def testTaskWithPlannedStartInThePastAndDueInTheFutureIsLate(self):
        self.assertTaskStatus(
            task.status.late,
            plannedStartDateTime=self.yesterday,
            dueDateTime=self.farFuture,
        )

    def testTaskWithPlannedStartInThePastAndDueInTheNearFutureIsDueSoon(self):
        self.assertTaskStatus(
            task.status.duesoon,
            plannedStartDateTime=self.yesterday,
            dueDateTime=self.nearFuture,
        )

    def testTaskWithPlannedStartInTheFutureAndDueInThePastIsOverdue(self):
        self.assertTaskStatus(
            task.status.overdue,
            plannedStartDateTime=self.nearFuture,
            dueDateTime=self.yesterday,
        )

    def testTaskWithPlannedStartInTheFutureAndDueInTheFutureIsLate(self):
        self.assertTaskStatus(
            task.status.inactive,
            plannedStartDateTime=self.nearFuture,
            dueDateTime=self.farFuture,
        )

    def testTaskWithPlannedStartInTheFutureAndDueInTheNearFutureIsDueSoon(
        self,
    ):
        self.assertTaskStatus(
            task.status.duesoon,
            plannedStartDateTime=self.nearFuture,
            dueDateTime=self.nearFuture,
        )

    # planned start date/time and completion date/time

    def testTaskWithPlannedStartAndCompletionInThePastIsCompleted(self):
        self.assertTaskStatus(
            task.status.completed,
            plannedStartDateTime=self.yesterday,
            completionDateTime=self.yesterday,
        )

    def testTaskWithPlannedStartInThePastAndCompletionInTheFutureIsCompleted(
        self,
    ):
        self.assertTaskStatus(
            task.status.completed,
            plannedStartDateTime=self.yesterday,
            completionDateTime=self.nearFuture,
        )

    def testTaskWithPlannedStartInTheFutureAndCompletionInThePastIsCompleted(
        self,
    ):
        self.assertTaskStatus(
            task.status.completed,
            plannedStartDateTime=self.nearFuture,
            completionDateTime=self.yesterday,
        )

    def testTaskWithPlannedStartInTheFutureAndCompletionInTheFutureIsComplete(
        self,
    ):
        self.assertTaskStatus(
            task.status.completed,
            plannedStartDateTime=self.nearFuture,
            completionDateTime=self.nearFuture,
        )

    # actual start date/time and due date/time

    def testTaskWithActualStartAndDueInThePastIsOverdue(self):
        self.assertTaskStatus(
            task.status.overdue,
            actualStartDateTime=self.yesterday,
            dueDateTime=self.yesterday,
        )

    def testTaskWithActualStartInThePastAndDueInTheFutureIsActive(self):
        self.assertTaskStatus(
            task.status.active,
            actualStartDateTime=self.yesterday,
            dueDateTime=self.farFuture,
        )

    def testTaskWithActualStartInThePastAndDueInTheNearFutureIsDueSoon(self):
        self.assertTaskStatus(
            task.status.duesoon,
            actualStartDateTime=self.yesterday,
            dueDateTime=self.nearFuture,
        )

    def testTaskWithActualStartInTheFutureAndDueInThePastIsOverdue(self):
        self.assertTaskStatus(
            task.status.overdue,
            actualStartDateTime=self.nearFuture,
            dueDateTime=self.yesterday,
        )

    def testTaskWithActualStartInTheFutureAndDueInTheFutureIsActive(self):
        self.assertTaskStatus(
            task.status.inactive,
            actualStartDateTime=self.nearFuture,
            dueDateTime=self.farFuture,
        )

    def testTaskWithActualStartInTheFutureAndDueInTheNearFutureIsDueSoon(self):
        self.assertTaskStatus(
            task.status.duesoon,
            actualStartDateTime=self.nearFuture,
            dueDateTime=self.nearFuture,
        )

    # actual start date/time and completion date/time

    def testTaskWithActualStartAndCompletionInThePastIsCompleted(self):
        self.assertTaskStatus(
            task.status.completed,
            actualStartDateTime=self.yesterday,
            completionDateTime=self.yesterday,
        )

    def testTaskWithActualStartInThePastAndCompletionInTheFutureIsCompleted(
        self,
    ):
        self.assertTaskStatus(
            task.status.completed,
            actualStartDateTime=self.yesterday,
            completionDateTime=self.nearFuture,
        )

    def testTaskWithActualStartInTheFutureAndCompletionInThePastIsCompleted(
        self,
    ):
        self.assertTaskStatus(
            task.status.completed,
            actualStartDateTime=self.nearFuture,
            completionDateTime=self.yesterday,
        )

    def testTaskWithActualStartInTheFutureAndCompletionInTheFutureIsComplete(
        self,
    ):
        self.assertTaskStatus(
            task.status.completed,
            actualStartDateTime=self.nearFuture,
            completionDateTime=self.nearFuture,
        )

    # due date/time and completion date/time

    def testTaskWithDueAndCompletionInThePastIsCompleted(self):
        self.assertTaskStatus(
            task.status.completed,
            dueDateTime=self.yesterday,
            completionDateTime=self.yesterday,
        )

    def testTaskWithDueInThePastAndCompletionInTheFutureIsCompleted(self):
        self.assertTaskStatus(
            task.status.completed,
            dueDateTime=self.yesterday,
            completionDateTime=self.nearFuture,
        )

    def testTaskWithDueInTheFutureAndCompletionInThePastIsCompleted(self):
        self.assertTaskStatus(
            task.status.completed,
            dueDateTime=self.nearFuture,
            completionDateTime=self.yesterday,
        )

    def testTaskWithDueInTheFutureAndCompletionInTheFutureIsComplete(self):
        self.assertTaskStatus(
            task.status.completed,
            dueDateTime=self.nearFuture,
            completionDateTime=self.nearFuture,
        )

    # Three dates/times

    # planned start date/time, actual start date/time and due date/time
    # (Other combinations are not interesting since they are always completed)

    def testTaskIsOverdueWheneverDueIsInThePast(self):
        for planned in self.dates:
            for actual in self.dates:
                self.assertTaskStatus(
                    task.status.overdue,
                    plannedStartDateTime=planned,
                    actualStartDateTime=actual,
                    dueDateTime=self.yesterday,
                )

    def testTaskIsDuesoonWheneverDueIsInTheNearFuture(self):
        for planned in self.dates:
            for actual in self.dates:
                self.assertTaskStatus(
                    task.status.duesoon,
                    plannedStartDateTime=planned,
                    actualStartDateTime=actual,
                    dueDateTime=self.nearFuture,
                )

    def testTaskIsOverdueWheneverDueIsInTheFuture(self):
        for planned in self.dates:
            expectedStatusBasedOnPlannedStart = (
                task.status.late
                if planned < self.now
                else task.status.inactive
            )
            for actual in self.dates:
                expectedStatus = (
                    task.status.active
                    if actual < self.now
                    else expectedStatusBasedOnPlannedStart
                )
                self.assertTaskStatus(
                    expectedStatus,
                    plannedStartDateTime=planned,
                    actualStartDateTime=actual,
                    dueDateTime=self.farFuture,
                )

    # Four date/times (always completed)

    def testTaskWithCompletionDateTimeIsAlwaysCompleted(self):
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

    def testTaskWithUncompletedPrerequisiteIsNeverLate(self):
        prerequisite = task.Task()
        for planned in self.dates:
            self.assertTaskStatus(
                task.status.inactive,
                plannedStartDateTime=planned,
                prerequisites=[prerequisite],
            )

    def testTaskWithCompletedPrerequisiteIsLateWhenPlannedStartIsInThePast(
        self,
    ):
        prerequisite = task.Task(completionDateTime=self.yesterday)
        for planned in self.dates:
            expectedStatus = (
                task.status.late
                if planned < self.now
                else task.status.inactive
            )
            self.assertTaskStatus(
                expectedStatus,
                plannedStartDateTime=planned,
                prerequisites=[prerequisite],
            )

    def testMutualPrerequisites(self):
        taskA = task.Task()
        taskB = task.Task(prerequisites=[taskA])
        taskA.add_prerequisites([taskB])
        for eachTask in (taskA, taskB):
            self.assertEqual(task.status.inactive, eachTask.computedStatus())
