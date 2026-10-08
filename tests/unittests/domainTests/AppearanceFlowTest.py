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
import wx
from taskcoachlib.config import settings
from taskcoachlib.domain import category, effort, note, task
from taskcoachlib.domain.base import NO_ICON


def child_of(parent, child):
    parent.addChild(child)
    child.set_parent(parent)
    return child


class AppearanceFlowTest(test.TestCase):
    """Where an item's style starts, by the "Appearance flow"
    preference (docs/APPEARANCE_STYLES.md, Appearance Flow): a red
    category with a subcategory, a task in it with a subtask, and a
    green note with a subnote."""

    def setUp(self):
        self.category = category.Category("Errands")
        self.category.setBackgroundColor(wx.RED)
        self.subcategory = child_of(self.category, category.Category("Shops"))
        self.task = task.Task(subject="Shopping")
        self.task.addCategory(self.category)
        self.subtask = child_of(self.task, task.Task(subject="Bread"))
        self.note = note.Note(subject="List")
        self.note.setBackgroundColor(wx.GREEN)
        self.subnote = child_of(self.note, note.Note(subject="Dairy"))

    def backgrounds(self, flow):
        """What the task, subtask, subcategory and subnote show."""
        settings.set("appearance", "flow", flow)
        return [
            test.styled(item).shown_bg_color()
            for item in (self.task, self.subtask, self.subcategory)
        ] + [test.styled(self.subnote).shown_bg_color()]

    def own_status(self, a_task):
        return a_task.statusBgColor()

    def test_from_categories_and_tasks_by_default(self):
        self.assertEqual(
            [wx.RED, wx.RED, wx.RED, wx.GREEN], self.backgrounds("all")
        )

    def test_from_categories_only(self):
        self.assertEqual(
            [wx.RED, self.own_status(self.subtask), wx.RED, None],
            self.backgrounds("categories"),
        )

    def test_from_tasks_only(self):
        self.assertEqual(
            [
                self.own_status(self.task),
                self.own_status(self.subtask),
                None,
                wx.GREEN,
            ],
            self.backgrounds("tasks"),
        )

    def test_from_tasks_only_passes_a_task_own_style(self):
        self.task.setBackgroundColor(wx.BLUE)
        self.assertEqual(wx.BLUE, self.backgrounds("tasks")[1])

    def test_none_shows_only_what_each_item_has(self):
        self.task.setBackgroundColor(wx.BLUE)
        self.assertEqual(
            [wx.BLUE, self.own_status(self.subtask), None, None],
            self.backgrounds("none"),
        )

    def test_icons_flow_alike(self):
        self.category.set_icon_id("nuvola_apps_kpackage")
        settings.set("appearance", "flow", "tasks")
        self.assertEqual(
            self.task.status_icon_id(),
            test.styled(self.task).shown_icon_id(),
        )


class NoIconTest(test.TestCase):
    """The "No icon" override: the item shows none, and what flows from
    above stops at it (docs/APPEARANCE_STYLES.md, No Icon)."""

    def setUp(self):
        self.category = category.Category("Errands")
        self.category.set_icon_id("nuvola_apps_kpackage")
        self.task = task.Task(subject="Shopping")
        self.task.addCategory(self.category)
        self.subtask = child_of(self.task, task.Task(subject="Bread"))

    def test_hides_the_category_icon(self):
        self.task.set_icon_id(NO_ICON)
        self.assertEqual("", test.styled(self.task).shown_icon_id())

    def test_says_it_is_the_override(self):
        self.task.set_icon_id(NO_ICON)
        self.assertEqual(
            "[Override]", test.styled(self.task).effectiveIconSource()
        )

    def test_subtask_shows_its_own_status_icon(self):
        self.task.set_icon_id(NO_ICON)
        self.assertEqual(
            self.subtask.status_icon_id(),
            test.styled(self.subtask).shown_icon_id(),
        )

    def test_subtask_own_category_icon_still_shows(self):
        self.task.set_icon_id(NO_ICON)
        own = category.Category("Bakery")
        own.set_icon_id("nuvola_apps_knotes")
        self.subtask.addCategory(own)
        self.assertEqual(
            "nuvola_apps_knotes", test.styled(self.subtask).shown_icon_id()
        )

    def test_nothing_below_is_forced_to_no_icon(self):
        # Two levels down, each task shows its own status icon
        self.task.set_icon_id(NO_ICON)
        grandchild = child_of(self.subtask, task.Task(subject="Rye"))
        self.assertEqual(
            grandchild.status_icon_id(),
            test.styled(grandchild).shown_icon_id(),
        )

    def test_a_category_icon_below_starts_a_new_flow(self):
        self.task.set_icon_id(NO_ICON)
        own = category.Category("Bakery")
        own.set_icon_id("nuvola_apps_knotes")
        self.subtask.addCategory(own)
        grandchild = child_of(self.subtask, task.Task(subject="Rye"))
        self.assertEqual(
            "nuvola_apps_knotes", test.styled(grandchild).shown_icon_id()
        )

    def test_an_own_icon_below_starts_a_new_flow(self):
        self.task.set_icon_id(NO_ICON)
        self.subtask.set_icon_id("nuvola_apps_korganizer")
        grandchild = child_of(self.subtask, task.Task(subject="Rye"))
        self.assertEqual(
            "nuvola_apps_korganizer", test.styled(grandchild).shown_icon_id()
        )

    def test_a_subnote_shows_the_note_icon(self):
        parent = note.Note(subject="List")
        parent.set_icon_id(NO_ICON)
        subnote = child_of(parent, note.Note(subject="Dairy"))
        self.assertEqual(
            "nuvola_apps_knotes", test.styled(subnote).shown_icon_id()
        )

    def test_a_no_icon_category_passes_nothing(self):
        # Its items take their next category's icon, its subcategories
        # none, as categories without an icon
        self.category.set_icon_id(NO_ICON)
        other = category.Category("Zoo")
        other.set_icon_id("nuvola_apps_korganizer")
        self.task.addCategory(other)
        subcategory = child_of(self.category, category.Category("Shops"))
        self.assertEqual(
            ["nuvola_apps_korganizer", ""],
            [
                test.styled(self.task).shown_icon_id(),
                test.styled(subcategory).shown_icon_id(),
            ],
        )

    def test_unset_still_takes_the_category_icon(self):
        self.assertEqual(
            "nuvola_apps_kpackage", test.styled(self.task).shown_icon_id()
        )

    def test_tracking_clock_still_shows(self):
        self.task.set_icon_id(NO_ICON)
        self.task.addEffort(effort.Effort(self.task))
        self.assertEqual(
            "nuvola_apps_clock", test.styled(self.task).shown_icon_id()
        )
