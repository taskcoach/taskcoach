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

import itertools
import random
from unittest import mock

import test
import wx
from taskcoachlib import config, patterns, persistence
from taskcoachlib.domain import attachment, base, category, date, effort
from taskcoachlib.domain.base import object as base_object
from taskcoachlib.domain import note, task
from taskcoachlib.gui import scheduler
from taskcoachlib.patterns.snapshot import Snapshot, Step

COLOURS = [wx.Colour(200, 0, 0), wx.Colour(0, 150, 0), wx.Colour(0, 0, 200)]
ICONS = ["nuvola_actions_edit", "nuvola_apps_korganizer", "nuvola_apps_clock"]


class IncrementalPassTest(test.wxTestCase):
    """After any change, the tick's pass leaves nothing for the full
    loop to change: it reached every object the change reaches
    (docs/MASTER_SCHEDULER_REFACTOR.md, Incremental Pass, Verification).
    Random changes of every kind on a random file, seeded, with a
    simulated clock. IDs count up and every pick is made in their
    order, so a seed replays a run: the task file's collections are
    sets, ordered by memory address."""

    SEED = 1
    STEPS = 150

    def setUp(self):
        super().setUp()
        task.Task.settings = config.Settings(load=False)
        self.now = date.DateTime(2026, 9, 29, 12, 0, 0)
        clock = mock.patch.object(date, "Now", lambda: self.now)
        clock.start()
        self.addCleanup(clock.stop)
        numbers = itertools.count()
        ids = mock.patch.object(
            base_object, "new_id", lambda: "%08d" % next(numbers)
        )
        ids.start()
        self.addCleanup(ids.stop)
        self.random = random.Random(self.SEED)
        self.task_file = persistence.TaskFile()
        self.master = scheduler.MasterScheduler(self.task_file)
        self.removed = []
        self.running = []
        self.build_file()
        self.tick()
        self.outputs = []
        for event_type in self.output_event_types():
            patterns.Publisher().registerObserver(
                self.on_output, eventType=event_type
            )

    def tearDown(self):
        self.master.shutdown()
        self.task_file.close()
        self.task_file.stop()
        super().tearDown()

    @staticmethod
    def output_event_types():
        types = [
            task.Task.statusChangedEventType(),
            task.Task.reminderChangedEventType(),
        ]
        for kind in ("derived", "effective"):
            for field in ("FgColor", "BgColor", "Icon", "Font"):
                name = "%s%sChangedEventType" % (kind, field)
                types.append(getattr(base.Object, name)())
        return types

    def on_output(self, event):
        self.outputs.extend(event.types())

    def tick(self):
        patterns.Event("timer.second", self, self.now).send()

    def left_for_the_full_loop(self):
        self.outputs = []
        self.master._run_full(self.now)
        return sorted(set(self.outputs))

    # The file

    def build_file(self):
        pick = self.random
        categories = []
        for index in range(8):
            parent = (
                pick.choice(categories)
                if categories and pick.random() < 0.5
                else None
            )
            each = category.Category("C%d" % index, parent=parent)
            if parent:
                parent.addChild(each)
            if pick.random() < 0.5:
                each.setForegroundColor(pick.choice(COLOURS))
            if pick.random() < 0.3:
                each.set_icon_id(pick.choice(ICONS))
            each.setStylePriority(pick.randint(0, 2))
            categories.append(each)
        self.task_file.categories().extend(
            [each for each in categories if each.parent() is None]
        )
        tasks = []
        for index in range(30):
            parent = (
                pick.choice(tasks) if tasks and pick.random() < 0.6 else None
            )
            dates = {}
            kind = pick.random()
            if kind < 0.2:
                dates["dueDateTime"] = self.now + date.TimeDelta(
                    hours=pick.randint(-5, 50)
                )
            elif kind < 0.4:
                dates["actualStartDateTime"] = self.now - date.ONE_HOUR
            elif kind < 0.5:
                dates["plannedStartDateTime"] = self.now + date.TimeDelta(
                    minutes=pick.randint(-60, 600)
                )
            if pick.random() < 0.2:
                dates["reminder"] = self.now + date.TimeDelta(
                    minutes=pick.randint(-5, 600)
                )
            each = task.Task("T%d" % index, parent=parent, **dates)
            if parent:
                parent.addChild(each)
            for linked in pick.sample(categories, pick.randint(0, 2)):
                each.addCategory(linked)
            if pick.random() < 0.2:
                each.setBackgroundColor(pick.choice(COLOURS))
            tasks.append(each)
        self.task_file.tasks().extend(
            [each for each in tasks if each.parent() is None]
        )
        notes = []
        for index in range(8):
            parent = (
                pick.choice(notes) if notes and pick.random() < 0.5 else None
            )
            each = note.Note(subject="N%d" % index, parent=parent)
            if parent:
                parent.addChild(each)
            for linked in pick.sample(categories, pick.randint(0, 1)):
                each.addCategory(linked)
            notes.append(each)
        self.task_file.notes().extend(
            [each for each in notes if each.parent() is None]
        )
        owners = (
            pick.sample(tasks, 8)
            + pick.sample(categories, 2)
            + pick.sample(notes, 2)
        )
        for owner in owners:
            self.add_owned(owner)

    def add_owned(self, owner):
        owned = note.Note(subject="owned by %s" % owner.subject())
        if self.random.random() < 0.5:
            owned.addCategory(self.random.choice(self.categories()))
        owned.addChild(note.Note(subject="under %s" % owned.subject()))
        if hasattr(owner, "addNote"):
            owner.addNote(owned)
        if hasattr(owner, "addAttachment"):
            file = attachment.FileAttachment("%s.txt" % owner.subject())
            file.addNote(note.Note(subject="attachment note"))
            owner.addAttachment(file)

    @staticmethod
    def ordered(items):
        return sorted(items, key=lambda each: each.id())

    def categories(self):
        return self.ordered(self.task_file.categories())

    def tasks(self):
        return self.ordered(self.task_file.tasks())

    def live(self, *kinds):
        found = []
        for collection in (
            self.task_file.categories(),
            self.task_file.tasks(),
            self.task_file.notes(),
        ):
            for each in collection:
                found.append(each)
                found.extend(scheduler._owned(each))
        return self.ordered(
            each for each in found if not kinds or isinstance(each, kinds)
        )

    # The changes, each returning what it did

    def override(self):
        item = self.random.choice(self.live())
        what = self.random.choice(["fg", "bg", "icon", "no fg", "no icon"])
        if what == "fg":
            item.setForegroundColor(self.random.choice(COLOURS))
        elif what == "bg":
            item.setBackgroundColor(self.random.choice(COLOURS))
        elif what == "icon":
            item.set_icon_id(self.random.choice(ICONS))
        elif what == "no fg":
            item.setForegroundColor(None)
        else:
            item.set_icon_id("")
        return "%s of %s" % (what, item.subject())

    def link(self):
        item = self.random.choice(self.live(task.Task, note.Note))
        linked = self.random.choice(self.categories())
        if linked in item.categories():
            item.removeCategory(linked)
            return "unlink %s" % item.subject()
        item.addCategory(linked)
        return "link %s" % item.subject()

    def priority(self):
        changed = self.random.choice(self.categories())
        changed.setStylePriority(self.random.randint(0, 3))
        return "priority of %s" % changed.subject()

    def rename(self):
        item = self.random.choice(
            self.live(task.Task, category.Category, note.Note)
        )
        item.setSubject(self.random.choice(["A", ""]) + item.subject() + "x")
        return "rename %s" % item.subject()

    def move_task(self):
        moved = self.random.choice(self.tasks())
        under = [
            each
            for each in self.tasks()
            if each is not moved and each not in moved.children(recursive=True)
        ]
        parent = self.random.choice(under + [None])
        self.task_file.tasks().removeItems([moved])
        moved.set_parent(parent)
        self.task_file.tasks().extend([moved])
        return "move %s" % moved.subject()

    def move_category(self):
        moved = self.random.choice(self.categories())
        under = [
            each
            for each in self.categories()
            if each is not moved and each not in moved.children(recursive=True)
        ]
        parent = self.random.choice(under + [None])
        self.task_file.categories().removeItems([moved])
        moved.set_parent(parent)
        self.task_file.categories().extend([moved])
        return "move %s" % moved.subject()

    def track(self):
        if self.running and self.random.random() < 0.5:
            stopped = self.running.pop()
            stopped.setStop()
            return "stop tracking"
        tracked = self.random.choice(self.tasks())
        running = effort.Effort(tracked)
        tracked.addEffort(running)
        self.running.append(running)
        return "track %s" % tracked.subject()

    def dates(self):
        changed = self.random.choice(self.tasks())
        what = self.random.choice(
            ["due", "actual", "planned", "complete", "reopen", "reminder"]
        )
        minutes = date.TimeDelta(minutes=self.random.randint(-120, 3000))
        if what == "due":
            changed.set_due_date_time(self.now + minutes)
        elif what == "actual":
            changed.set_actual_start_date_time(self.now + minutes)
        elif what == "planned":
            changed.set_planned_start_date_time(self.now + minutes)
        elif what == "complete":
            changed.set_completion_date_time(self.now)
        elif what == "reopen":
            changed.set_completion_date_time(changed.maxDateTime)
        else:
            changed.set_reminder(self.now + minutes)
        return "%s of %s" % (what, changed.subject())

    def prerequisite(self):
        first, second = self.random.sample(self.tasks(), 2)
        if second in first.prerequisites():
            first.remove_prerequisites([second])
            first.removeTaskAsDependencyOf([second])
            return "drop a prerequisite"
        if first in second.prerequisites(recursive=True, upwards=True):
            return "nothing"
        first.add_prerequisites([second])
        first.addTaskAsDependencyOf([second])
        return "add a prerequisite"

    def new_task(self):
        parent = self.random.choice(self.tasks() + [None])
        added = task.Task("new", parent=parent)
        if self.random.random() < 0.5:
            added.addCategory(self.random.choice(self.categories()))
        self.add_owned(added)
        self.task_file.tasks().extend([added])
        return "new task"

    def owned(self):
        owner = self.random.choice(
            self.live(
                task.Task, category.Category, note.Note, attachment.Attachment
            )
        )
        if isinstance(owner, attachment.Attachment):
            owner.addNote(note.Note(subject="late"))
        else:
            self.add_owned(owner)
        return "owned by %s" % owner.subject()

    def subnote(self):
        parent = self.random.choice(self.live(note.Note))
        added = note.Note(subject="late")
        if self.random.random() < 0.5:
            added.addCategory(self.random.choice(self.categories()))
        if parent in self.task_file.notes():
            added.set_parent(parent)
            self.task_file.notes().extend([added])
        else:
            parent.addChild(added)
        return "subnote of %s" % parent.subject()

    def delete_or_undelete(self):
        if self.removed and self.random.random() < 0.5:
            restored = self.removed.pop()
            self.task_file.tasks().extend([restored])
            return "undelete %s" % restored.subject()
        deleted = self.random.choice(self.tasks())
        self.task_file.tasks().removeItems([deleted])
        self.removed.append(deleted)
        return "delete %s" % deleted.subject()

    def undo(self):
        item = self.random.choice(self.live(task.Task, category.Category))
        before = Snapshot()
        item.setForegroundColor(self.random.choice(COLOURS))
        if isinstance(item, task.Task):
            item.set_due_date_time(self.now - date.ONE_HOUR)
        Step("change", before, Snapshot()).undo()
        return "undo %s" % item.subject()

    def clock(self):
        self.now += self.random.choice(
            [
                date.ONE_SECOND,
                date.TimeDelta(minutes=30),
                date.TimeDelta(hours=3),
                date.TimeDelta(hours=30),
            ]
        )
        return "clock to %s" % self.now

    def paste(self):
        copy = self.random.choice(self.tasks()).copy()
        copy.set_parent(None)
        self.task_file.tasks().extend([copy])
        return "paste %s" % copy.subject()

    CHANGES = (
        override,
        link,
        priority,
        rename,
        move_task,
        move_category,
        track,
        dates,
        prerequisite,
        new_task,
        owned,
        subnote,
        delete_or_undelete,
        undo,
        clock,
        paste,
    )

    def test_the_pass_leaves_nothing_for_the_full_loop(self):
        missed = []
        for step in range(self.STEPS):
            change = self.random.choice(self.CHANGES)(self)
            self.tick()
            left = self.left_for_the_full_loop()
            if left:
                missed.append((step, change, left))
        self.assertEqual([], missed)

    def test_the_pass_processes_only_what_the_change_reaches(self):
        # A task's colour: the task and its subtasks, up to a subtask
        # with a colour of its own, not the file
        parent = task.Task("parent")
        inheriting = task.Task("inheriting", parent=parent)
        own_colour = task.Task("own colour", parent=parent)
        own_colour.setForegroundColor(COLOURS[1])
        below = task.Task("below own colour", parent=own_colour)
        parent.addChild(inheriting)
        parent.addChild(own_colour)
        own_colour.addChild(below)
        self.task_file.tasks().extend([parent])
        self.tick()
        processed = []
        process = self.master._process

        def record(item, timestamp):
            processed.append(item.subject())
            process(item, timestamp)

        self.master._process = record
        parent.setForegroundColor(COLOURS[0])
        self.tick()
        self.assertEqual(
            ["inheriting", "own colour", "parent"], sorted(processed)
        )
