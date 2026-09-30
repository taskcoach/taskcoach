"""
Generate a task file for measuring the per-second processing.

Usage: python3 tools/generate_task_file.py TASKS FILE [MINUTES]

Parents with 9 subtasks each, 20 categories and 50 notes. Planned
start, due and completion dates are spread 20 days around now and
reminders 2 days, so every status occurs; with MINUTES, all within
that many minutes, so statuses change and reminders fire while the
file is open. The same arguments give the same file, with dates
relative to the moment it is generated. See docs/SCHEDULERS.md.
"""

import os
import random
import sys

import wx

APP = wx.AppConsole()  # taskcoachlib sets the locale when imported

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from taskcoachlib import config, persistence  # noqa: E402
from taskcoachlib.domain import category, date, note, task  # noqa: E402

SUBTASKS = 9
CATEGORIES = 20
NOTES = 50


DAY = 86400  # Seconds


def spread(rng, now, seconds):
    """A moment within the given seconds around now, or None."""
    if rng.random() < 0.3:
        return None
    return now + date.TimeDelta(seconds=rng.uniform(-seconds, seconds))


def new_task(rng, now, subject, minutes):
    dates = minutes * 60 if minutes else 20 * DAY
    planned_start = spread(rng, now, dates)
    due = spread(rng, now, dates)
    if planned_start and due and due < planned_start:
        planned_start, due = due, planned_start
    actual_start = planned_start if rng.random() < 0.2 else None
    if actual_start and actual_start > now:
        actual_start = None
    completion = now if rng.random() < 0.1 else None
    reminders = minutes * 60 if minutes else 2 * DAY
    reminder = spread(rng, now, reminders) if rng.random() < 0.2 else None
    return task.Task(
        subject=subject,
        plannedStartDateTime=planned_start or date.DateTime(),
        dueDateTime=due or date.DateTime(),
        actualStartDateTime=actual_start or date.DateTime(),
        completionDateTime=completion or date.DateTime(),
        reminder=reminder,
        priority=rng.randint(0, 5),
    )


def generate(count, filename, minutes=None):
    settings = config.Settings(load=False)  # Defaults
    task.Task.settings = settings
    rng = random.Random(count)
    now = date.DateTime.now()
    task_file = persistence.TaskFile()
    categories = [
        category.Category("Category %d" % i) for i in range(CATEGORIES)
    ]
    task_file.categories().extend(categories)
    parents = []
    for number in range(0, count, SUBTASKS + 1):
        parent = new_task(rng, now, "Task %d" % number, minutes)
        for child in range(1, min(SUBTASKS + 1, count - number)):
            subject = "Task %d" % (number + child)
            parent.addChild(new_task(rng, now, subject, minutes))
        parents.append(parent)
    task_file.tasks().extend(parents)
    for item in task_file.tasks():
        for chosen in rng.sample(categories, rng.randint(0, 2)):
            item.addCategory(chosen)
    task_file.notes().extend(
        note.Note(subject="Note %d" % i) for i in range(NOTES)
    )
    task_file.setFilename(filename)
    task_file.save()
    count = len(task_file.tasks())
    task_file.close()
    return count


if __name__ == "__main__":
    if len(sys.argv) not in (3, 4):
        sys.exit(__doc__)
    minutes = float(sys.argv[3]) if len(sys.argv) == 4 else None
    print("%d tasks" % generate(int(sys.argv[1]), sys.argv[2], minutes))
