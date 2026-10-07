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

from taskcoachlib.config import settings
from taskcoachlib.domain import task, date, effort
import test


class CommonTaskRelationshipManagerTestsMixin(object):
    def setUp(self):
        now = self.now = date.Now()
        self.yesterday = now - date.ONE_DAY
        self.tomorrow = now + date.ONE_DAY
        self.parent = task.Task("parent")
        self.child = task.Task("child")
        self.parent.addChild(self.child)
        self.child.set_parent(self.parent)
        self.child2 = task.Task("child2", plannedStartDateTime=now)
        self.grandchild = task.Task("grandchild", plannedStartDateTime=now)
        settings.set(
            "behavior",
            "markparentcompletedwhenallchildrencompleted",
            self.markParentCompletedWhenAllChildrenCompleted,
        )
        self.taskList = task.TaskList(
            [self.parent, self.child2, self.grandchild]
        )

    # completion date

    def test_completing_one_of_two_children_never_completes_parent(
        self,
    ):
        self.parent.addChild(self.child2)
        self.child.set_completion_date_time()
        self.assertFalse(self.parent.completed())

    def test_mark_parent_with_one_child_completed(self):
        self.parent.set_completion_date_time()
        self.assertTrue(self.child.completed())

    def test_mark_parent_with_two_children_completed(self):
        self.parent.addChild(self.child2)
        self.parent.set_completion_date_time()
        self.assertTrue(self.child.completed())
        self.assertTrue(self.child2.completed())

    def test_mark_parent_not_completed(self):
        self.parent.set_completion_date_time()
        self.assertTrue(self.child.completed())
        self.parent.set_completion_date_time(date.DateTime())
        self.assertTrue(self.child.completed())

    def test_mark_parent_completed_does_not_change_child_completion_date(self):
        self.parent.addChild(self.child2)
        self.child.set_completion_date_time(self.yesterday)
        self.parent.set_completion_date_time()
        self.assertEqual(self.yesterday, self.child.completionDateTime())

    def test_mark_child_not_completed(self):
        self.child.set_completion_date_time()
        self.child.set_completion_date_time(date.DateTime())
        self.assertFalse(self.parent.completed())

    def test_add_completed_child(self):
        self.child2.set_completion_date_time()
        self.parent.addChild(self.child2)
        self.assertFalse(self.parent.completed())

    def test_add_uncompleted_child(self):
        self.child.set_completion_date_time()
        self.parent.addChild(self.child2)
        self.assertFalse(self.parent.completed())

    def test_add_uncompleted_grandchild(self):
        self.parent.set_completion_date_time()
        self.child.addChild(self.grandchild)
        self.assertFalse(self.parent.completed())

    def test_mark_parent_completed_yesterday(self):
        self.parent.set_completion_date_time(self.yesterday)
        self.assertEqual(self.yesterday, self.child.completionDateTime())

    def test_mark_task_completed_stops_effort_tracking(self):
        self.child.addEffort(effort.Effort(self.child))
        self.child.set_completion_date_time()
        self.assertFalse(self.child.isBeingTracked())

    # recurrence

    def test_mark_parent_completed_stops_child_recurrence(self):
        self.child.set_recurrence(date.Recurrence("daily"))
        self.parent.set_completion_date_time()
        self.assertFalse(self.child.recurrence())

    def test_recurring_child_is_completed_when_parent_is_completed(self):
        self.child.set_recurrence(date.Recurrence("daily"))
        self.parent.set_completion_date_time()
        self.assertTrue(self.child.completed())

    def shouldMarkCompletedWhenAllChildrenCompleted(self, parent):
        return (
            parent.shouldMarkCompletedWhenAllChildrenCompleted() == True
            or (
                parent.shouldMarkCompletedWhenAllChildrenCompleted() == None
                and self.markParentCompletedWhenAllChildrenCompleted == True
            )
        )

    def test_mark_last_child_completed_makes_parent_recur(self):
        self.parent.set_planned_start_date_time(self.now)
        self.parent.set_recurrence(date.Recurrence("weekly"))
        self.child.set_completion_date_time(self.now)
        expected_planned_start_date_time = self.now
        if self.shouldMarkCompletedWhenAllChildrenCompleted(self.parent):
            expected_planned_start_date_time += date.TimeDelta(days=7)
        self.assertAlmostEqual(
            expected_planned_start_date_time.toordinal(),
            self.parent.plannedStartDateTime().toordinal(),
        )

    def test_mark_last_child_completed_makes_parent_recur_and_thus_child_too(
        self,
    ):
        self.child.set_planned_start_date_time(self.now)
        self.parent.set_recurrence(date.Recurrence("weekly"))
        self.parent.set_planned_start_date_time(self.now)
        self.child.set_completion_date_time(self.now)
        expected_planned_start_date_time = self.now
        if self.shouldMarkCompletedWhenAllChildrenCompleted(self.parent):
            expected_planned_start_date_time += date.TimeDelta(days=7)
        self.assertAlmostEqual(
            expected_planned_start_date_time.toordinal(),
            self.child.plannedStartDateTime().toordinal(),
        )

    def test_completing_last_child_makes_parent_recur_so_child_uncompleted(
        self,
    ):
        self.parent.set_recurrence(date.Recurrence("weekly"))
        self.child.set_completion_date_time()
        if self.shouldMarkCompletedWhenAllChildrenCompleted(self.parent):
            self.assertFalse(self.child.completed())
        else:
            self.assertTrue(self.child.completed())

    def test_mark_last_grand_child_completed_makes_parent_recur(self):
        self.parent.set_recurrence(date.Recurrence("weekly"))
        self.parent.set_planned_start_date_time(self.now)
        self.child.addChild(self.grandchild)
        self.grandchild.set_parent(self.child)
        self.grandchild.set_completion_date_time(self.now)
        expected_planned_start_date_time = self.now
        if self.shouldMarkCompletedWhenAllChildrenCompleted(self.parent):
            expected_planned_start_date_time += date.TimeDelta(days=7)
        self.assertAlmostEqual(
            expected_planned_start_date_time.toordinal(),
            self.parent.plannedStartDateTime().toordinal(),
        )

    def test_completing_last_grandchild_makes_parent_and_grandchild_recur(
        self,
    ):
        self.parent.set_recurrence(date.Recurrence("weekly"))
        self.child.addChild(self.grandchild)
        self.grandchild.set_parent(self.child)
        self.grandchild.set_completion_date_time(self.now)
        expected_planned_start_date_time = self.now
        if self.shouldMarkCompletedWhenAllChildrenCompleted(self.parent):
            expected_planned_start_date_time += date.TimeDelta(days=7)
        self.assertAlmostEqual(
            expected_planned_start_date_time.toordinal(),
            self.grandchild.plannedStartDateTime().toordinal(),
        )

    def test_last_child_completed_makes_parent_recur_grandchild_uncompleted(
        self,
    ):
        self.parent.set_recurrence(date.Recurrence("weekly"))
        self.child.addChild(self.grandchild)
        self.grandchild.set_parent(self.child)
        self.grandchild.set_completion_date_time()
        if self.shouldMarkCompletedWhenAllChildrenCompleted(self.parent):
            self.assertFalse(self.grandchild.completed())
        else:
            self.assertTrue(self.grandchild.completed())


class MarkParentTaskCompletedTestsMixin(object):
    """Tests where we expect to parent task to be marked completed, based on
    the fact that all children are completed. This happens when the global
    setting is on and task is indifferent or the task specific setting is
    on."""

    def test_mark_only_child_completed(self):
        self.child.set_completion_date_time()
        self.assertTrue(self.parent.completed())

    def test_mark_only_grandchild_completed(self):
        self.child.addChild(self.grandchild)
        self.grandchild.set_completion_date_time()
        self.assertTrue(self.parent.completed())

    def test_add_completed_child_as_only_child(self):
        self.grandchild.set_completion_date_time()
        self.child.addChild(self.grandchild)
        self.assertTrue(self.child.completed())

    def test_mark_child_completed_yesterday(self):
        self.child.set_completion_date_time(self.yesterday)
        self.assertEqual(self.yesterday, self.parent.completionDateTime())

    def test_remove_last_uncompleted_child(self):
        self.parent.addChild(self.child2)
        self.child.set_completion_date_time()
        self.parent.removeChild(self.child2)
        self.assertTrue(self.parent.completed())


class DontMarkParentTaskCompletedTestsMixin(object):
    """Tests where we expect the parent task not to be marked completed when
    all children are completed. This should be the case when the global
    setting is off and task is indifferent or when the task specific
    setting is off."""

    def test_mark_only_child_completed_does_not_mark_parent_completed(self):
        self.child.set_completion_date_time()
        self.assertFalse(self.parent.completed())

    def test_mark_only_grandchild_completed_does_not_mark_parent_completed(
        self,
    ):
        self.child.addChild(self.grandchild)
        self.grandchild.set_completion_date_time()
        self.assertFalse(self.parent.completed())

    def test_add_completed_child_as_only_child_does_not_mark_parent_completed(
        self,
    ):
        self.grandchild.set_completion_date_time()
        self.child.addChild(self.grandchild)
        self.assertFalse(self.child.completed())

    def test_child_completed_yesterday_keeps_parent_completion_date(
        self,
    ):
        self.child.set_completion_date_time(self.yesterday)
        self.assertEqual(date.DateTime(), self.parent.completionDateTime())

    def test_remove_last_uncompleted_child_does_not_mark_parent_completed(
        self,
    ):
        self.parent.addChild(self.child2)
        self.child.set_completion_date_time()
        self.parent.removeChild(self.child2)
        self.assertFalse(self.parent.completed())


class MarkParentCompletedAutomaticallyIsOn(
    CommonTaskRelationshipManagerTestsMixin,
    MarkParentTaskCompletedTestsMixin,
    test.TestCase,
):
    markParentCompletedWhenAllChildrenCompleted = True


class MarkParentCompletedAutomaticallyIsOff(
    CommonTaskRelationshipManagerTestsMixin,
    DontMarkParentTaskCompletedTestsMixin,
    test.TestCase,
):
    markParentCompletedWhenAllChildrenCompleted = False


class MarkParentCompletedAutomaticallyIsOnButTaskSettingIsOff(
    CommonTaskRelationshipManagerTestsMixin,
    test.TestCase,
    DontMarkParentTaskCompletedTestsMixin,
):
    markParentCompletedWhenAllChildrenCompleted = True

    def setUp(self):
        super(
            MarkParentCompletedAutomaticallyIsOnButTaskSettingIsOff, self
        ).setUp()
        for each_task in self.parent, self.child:
            each_task.set_should_mark_completed_when_all_children_completed(
                False
            )


class MarkParentCompletedAutomaticallyIsOffButTaskSettingIsOn(
    CommonTaskRelationshipManagerTestsMixin,
    test.TestCase,
    MarkParentTaskCompletedTestsMixin,
):
    markParentCompletedWhenAllChildrenCompleted = False

    def setUp(self):
        super(
            MarkParentCompletedAutomaticallyIsOffButTaskSettingIsOn, self
        ).setUp()
        for each_task in self.parent, self.child:
            each_task.set_should_mark_completed_when_all_children_completed(
                True
            )
