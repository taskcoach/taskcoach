"""Category membership (P28, P29 in docs/MASTER_SCHEDULER_REFACTOR.md).
It was held twice, the item's categories and the category's members,
and the file was written from the category's side, so a change that
filled only the item's side was lost on save. Now the item's side is
the only data, in memory and in the file (tskversion 38), and the
category's members its index. Each scenario prints the item's
categories, whether the index lists it, then the categories after a
save and reload: all keep Home.

Run from the repository root:

    PYTHONPATH=. xvfb-run -a .venv/bin/python \\
        docs/scripts/category_membership_probe.py
"""

import os
import tempfile

import wx

app = wx.App(False)
from taskcoachlib import command, config, persistence  # noqa: E402
from taskcoachlib.domain import category, note, task  # noqa: E402

task.Task.settings = config.Settings(load=False)


def new_file():
    task_file = persistence.TaskFile()
    home = category.Category("Home")
    task_file.categories().append(home)
    return task_file, home


def save_and_reload(task_file):
    filename = os.path.join(tempfile.mkdtemp(), "probe.tsk")
    task_file.setFilename(filename)
    task_file.save()
    task_file.close()
    task_file.stop()
    reloaded = persistence.TaskFile()
    reloaded.load(filename)
    return reloaded


def names(categories):
    return sorted(each.subject() for each in categories)


def check_all():
    """P28: the editor's Check all linked the item side only."""
    task_file, home = new_file()
    paint = task.Task(subject="Paint")
    task_file.tasks().append(paint)
    command.LinkCategoriesCommand(None, [paint], categories=[home]).do()
    print(
        "check all:", names(paint.categories()), paint in home.categorizables()
    )
    reloaded = save_and_reload(task_file)
    print("  after reload:", names(list(reloaded.tasks())[0].categories()))


def paste_task_with_note():
    """P29: a pasted task's notes kept their categories on their side
    only; the task list linked the category side for tasks only."""
    task_file, home = new_file()
    paint = task.Task(subject="Paint")
    colours = note.Note(subject="Colours")
    paint.addNote(colours)
    task_file.tasks().append(paint)
    command.ToggleCategoryCommand(None, [colours], category=home).do()
    command.CopyCommand(task_file.tasks(), [paint]).do()
    command.PasteCommand(task_file.tasks()).do()
    copy = [each for each in task_file.tasks() if each is not paint][0]
    pasted = copy.notes()[0]
    print(
        "paste task:",
        names(pasted.categories()),
        pasted in home.categorizables(),
    )
    reloaded = save_and_reload(task_file)
    for each in reloaded.tasks():
        print("  after reload:", [names(n.categories()) for n in each.notes()])


def paste_note_in_editor():
    """P29: a note pasted in the task editor (AddNoteCommand) kept its
    categories on its side only."""
    task_file, home = new_file()
    first, second = task.Task(subject="A"), task.Task(subject="B")
    colours = note.Note(subject="Colours")
    first.addNote(colours)
    task_file.tasks().extend([first, second])
    command.ToggleCategoryCommand(None, [colours], category=home).do()
    command.CopyCommand(None, [colours]).do()
    pasted = command.Clipboard().items_to_paste()
    command.AddNoteCommand(None, [second], notes=pasted).do()
    print(
        "paste note:",
        names(pasted[0].categories()),
        pasted[0] in home.categorizables(),
    )
    reloaded = save_and_reload(task_file)
    for each in reloaded.tasks():
        print("  after reload:", [names(n.categories()) for n in each.notes()])


check_all()
paste_task_with_note()
paste_note_in_editor()
