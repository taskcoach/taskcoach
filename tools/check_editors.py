#!/usr/bin/env python3
"""Open every kind of editor as the app does, and walk through it.

    python3 tools/check_editors.py

Each editor is opened on a sample task file and shown; each of its
pages is selected and its fields are tabbed through, forward and
back; then it is closed. Prints each problem (an error, an editor off
every display, the focus leaving the editor or moving on by itself)
and exits 1 if there is one. A hang prints every thread's stack and
ends the run.

Run from a checkout, it checks the checkout's taskcoachlib; copied
elsewhere, the one its Python brings. So the macOS and Windows builds
run a copy with the built app's own Python and files before packaging
(docs/TESTING.md, Editor check); the test suite runs the same checks
(tests/unittests/guiTests/EditorCheckTest.py).
"""

import faulthandler
import os
import shutil
import sys
import tempfile
import traceback

import wx

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if os.path.isdir(os.path.join(_ROOT, "taskcoachlib")):
    sys.path.insert(0, _ROOT)

# Longest one editor may take; past it every thread's stack is printed
# and the run ends, so a hang names where it hangs
TIME_LIMIT = 120

# Idle rounds after a step; the focus must stay put across them
SETTLE_ROUNDS = 10


def settle(rounds=3):
    """Run what wx leaves for idle time: deferred calls, focus
    changes, a top-level window's destroy."""
    for _ in range(rounds):
        wx.WakeUpIdle()
        wx.YieldIfNeeded()


def describe(window):
    if window is None:
        return "nothing"
    label = window.GetLabel() if hasattr(window, "GetLabel") else ""
    return "%s %r" % (type(window).__name__, label or window.GetName())


def inside(window, top_level):
    while window is not None:
        if window is top_level:
            return True
        window = window.GetParent()
    return False


class MainFrame(wx.Frame):
    """Stands in for the main window: shown, at a usual size and
    place, with what editors ask of it."""

    def __init__(self):
        super().__init__(None, title="Task Coach editor check")
        area = wx.Display(0).GetClientArea()
        self.SetSize(
            area.x + area.width // 8,
            area.y + area.height // 8,
            area.width * 3 // 4,
            area.height * 3 // 4,
        )
        self.list = wx.TextCtrl(self)  # Stands in for the task list
        self.Show()

    def getToolBarPerspective(self):  # noqa: N802 (main window's)
        return ""

    def AddBalloonTip(self, *args, **kwargs):  # noqa: N802
        pass


def sample_task_file():
    """A task file whose items fill every editor page."""
    from taskcoachlib import persistence
    from taskcoachlib.domain import (
        attachment,
        category,
        date,
        effort,
        note,
        task,
    )

    task_file = persistence.TaskFile()
    work = category.Category("Work", description="Paid *work*")
    task_file.categories().append(work)
    second = task.Task("Second")
    first = task.Task(
        "First",
        description="Some **Markdown**\n\n- one\n- [ ] two\n",
        categories={work},
        prerequisites=[second],
    )
    second.add_dependencies([first])
    first.addNote(note.Note(subject="Task note", description="Words"))
    first.addAttachments(
        attachment.URIAttachment("https://example.org", subject="Site")
    )
    first.addChild(task.Task("Child"))
    task_file.tasks().extend([first, second])
    now = date.Now()
    first.addEffort(effort.Effort(first, now - date.ONE_HOUR, now))
    task_file.notes().append(
        note.Note(subject="Note", description="A *note*", previewShown=True)
    )
    return task_file


def editors(parent, task_file):
    """(name, callable opening it, undo steps the opening makes) for
    each kind of editor, opened as the app opens it: from the main
    window, with the focus in its list."""
    from taskcoachlib import command
    from taskcoachlib.config import settings
    from taskcoachlib.domain import attachment
    from taskcoachlib.gui.dialog import editor

    tasks = task_file.tasks()
    first = next(item for item in tasks if item.subject() == "First")
    second = next(item for item in tasks if item.subject() == "Second")

    def task_editor():
        return editor.TaskEditor(parent, [first], tasks, task_file)

    def new_task():
        new = command.NewTaskCommand(tasks, subject="New")
        new.do()
        return editor.TaskEditor(
            parent, new.items, tasks, task_file, items_are_new=True
        )

    def attachment_editor():
        container = attachment.AttachmentList(first.attachments())
        return editor.AttachmentEditor(
            parent, first.attachments(), container, task_file
        )

    def unreadable_saved_tabs():
        """As a long-time user's settings may hold them (#487)."""
        probe = task_editor()
        section = probe._interior.settings_section()
        probe.Close()
        settle()
        settings.section(section).perspective = "x"
        return task_editor()

    def empty_toolbars():
        """Every button removed from the views' toolbars."""
        for view in ("effort", "category", "note", "attachment"):
            settings.section(
                "%sviewerintaskeditor" % view
            ).toolbarperspective = ""
        return task_editor()

    def from_the_list(open_editor):
        def opened():
            parent.list.SetFocus()
            settle()
            return open_editor()

        return opened

    return [
        (name, from_the_list(open_editor), own_steps)
        for name, open_editor, own_steps in [
            ("task", task_editor, 0),
            ("new task", new_task, 1),
            (
                "two tasks",
                lambda: editor.TaskEditor(
                    parent, [first, second], tasks, task_file
                ),
                0,
            ),
            (
                "category",
                lambda: editor.CategoryEditor(
                    parent,
                    list(task_file.categories()),
                    task_file.categories(),
                    task_file,
                ),
                0,
            ),
            (
                "note",
                lambda: editor.NoteEditor(
                    parent,
                    list(task_file.notes()),
                    task_file.notes(),
                    task_file,
                ),
                0,
            ),
            ("attachment", attachment_editor, 0),
            (
                "effort",
                lambda: editor.EffortEditor(
                    parent,
                    list(task_file.efforts()),
                    task_file.efforts(),
                    task_file,
                ),
                0,
            ),
            ("task, unreadable saved tabs", unreadable_saved_tabs, 0),
            ("task, empty toolbars", empty_toolbars, 0),
        ]
    ]


class _Check:
    """One editor's run: each problem is named by the editor and the
    step it happened in."""

    def __init__(self, name):
        self.name = name
        self.problems = []
        self.__errors = []

    def __enter__(self):
        self.__hook = sys.excepthook
        # An error in an event handler: wx prints it and goes on
        sys.excepthook = lambda *error: self.__errors.append(error)
        # A message box waits for a click no one makes here
        self.__message_box = wx.MessageBox
        wx.MessageBox = self.__message
        faulthandler.dump_traceback_later(TIME_LIMIT, exit=True)
        return self

    def __exit__(self, kind, error, trace):
        faulthandler.cancel_dump_traceback_later()
        wx.MessageBox = self.__message_box
        sys.excepthook = self.__hook
        if not isinstance(error, Exception):
            return False
        self.report("error", "".join(traceback.format_exception(error)))
        return True

    def __message(self, message, caption="", *args, **kwargs):
        self.report("message box", "%s: %s" % (caption, message))
        return wx.OK

    def report(self, step, text):
        self.problems.append("%s editor, %s: %s" % (self.name, step, text))

    def errors(self, step):
        """Report the errors raised in event handlers so far."""
        for kind, error, trace in self.__errors:
            self.report(
                step,
                "".join(traceback.format_exception(kind, error, trace)),
            )
        del self.__errors[:]


def placement_problems(window):
    """Why the window cannot be seen, if it cannot."""
    if not window.IsShownOnScreen():
        return ["not shown"]
    rect = window.GetScreenRect()
    if rect.width < 100 or rect.height < 100:
        return ["too small to use: %s" % (tuple(rect),)]
    index = wx.Display.GetFromWindow(window)
    if index == wx.NOT_FOUND:
        return ["on no display: %s" % (tuple(rect),)]
    area = wx.Display(index).GetClientArea()
    if not area.Contains(wx.Point(rect.x + rect.width // 2, rect.y)):
        return [
            "its top is off the display's work area %s: %s"
            % (tuple(area), tuple(rect))
        ]
    return []


def walk_focus(check, editor, step, forward):
    """Tab through the editor's fields. Returns False when nothing has
    the focus to start from (an app in the background)."""
    if not inside(wx.Window.FindFocus(), editor):
        editor.SetFocus()
        settle()
    if not inside(wx.Window.FindFocus(), editor):
        return False
    from taskcoachlib.tools.wxhelper import descendants

    steps = min(300, 10 + sum(1 for _ in descendants(editor)))
    focus = wx.Window.FindFocus()
    for _ in range(steps):
        focus.Navigate(forward)
        settle()
        check.errors(step)
        previous, focus = focus, wx.Window.FindFocus()
        if focus is None:
            # wxGTK loses track of a choice tabbed into inside a panel:
            # GTK focuses the choice's own button, which wx does not map
            # back; the next Tab key still reaches the choice
            print(
                "%s editor, %s: from %s the focus went where wx does"
                " not see it; walk ended"
                % (check.name, step, describe(previous))
            )
            break
        if not inside(focus, editor):
            check.report(
                step,
                "from %s the focus went to %s, out of the editor"
                % (describe(previous), describe(focus)),
            )
            break
    return True


def focus_keeps_moving(rounds=SETTLE_ROUNDS):
    """The windows the focus moves between with nothing done, if it
    does not settle."""
    seen = []
    for _ in range(rounds):
        settle(1)
        seen.append(wx.Window.FindFocus())
    moves = sum(1 for a, b in zip(seen, seen[1:]) if a is not b)
    if moves < rounds // 2:
        return []
    return sorted(set(describe(window) for window in seen))


def click_focus(check, editor, step):
    """Give the focus to each field shown, as a click does: a field
    that refuses it hands it on, and the focus must then settle inside
    the editor."""
    from taskcoachlib.tools.wxhelper import descendants

    for window in list(descendants(editor)):
        if not (window and window.IsShownOnScreen() and window.AcceptsFocus()):
            continue
        window.SetFocus()
        settle()
        check.errors(step)
        focus = wx.Window.FindFocus()
        if focus is not None and not inside(focus, editor):
            check.report(
                step,
                "focusing %s sent the focus to %s, out of the editor"
                % (describe(window), describe(focus)),
            )
        moving = focus_keeps_moving(4)
        if moving:
            check.report(
                step,
                "focusing %s, the focus keeps moving by itself between %s"
                % (describe(window), ", ".join(moving)),
            )


def check_editor(name, open_editor, own_steps=0):
    """The problems found opening, using and closing one editor.
    Looking through an editor changes nothing: the undo steps after it
    are the ones its opening makes (a new task's)."""
    from taskcoachlib import patterns

    history = patterns.CommandHistory().get_history()
    steps_before = len(history)
    editor = None
    with _Check(name) as check:
        editor = open_editor()
        editor.Show()
        settle()
        check.errors("open")
        for problem in placement_problems(editor):
            check.report("placement", problem)
        book = editor._interior
        pages = (
            range(book.GetPageCount())
            if isinstance(book, wx.BookCtrlBase)
            else [None]
        )
        for index in pages:
            if index is None:
                step = "page"
            else:
                book.SetSelection(index)
                step = "page %r" % book.GetPageText(index)
                settle()
                check.errors(step)
            click_focus(check, editor, step + ", click")
            for forward in (True, False):
                walk = step + (", Tab" if forward else ", Shift+Tab")
                if not walk_focus(check, editor, walk, forward):
                    print(
                        "%s editor, %s: skipped, the app has no focus"
                        % (name, walk)
                    )
                    break
                moving = focus_keeps_moving()
                if moving:
                    check.report(
                        walk,
                        "the focus keeps moving by itself between %s"
                        % ", ".join(moving),
                    )
                check.errors(walk)
        editor.Close()
        settle()
        check.errors("close")
        editor = None
        changes = patterns.CommandHistory().get_history()[
            steps_before + own_steps :
        ]
        if changes:
            check.report(
                "close",
                "looking through it changed the item: %s"
                % ", ".join(str(step) for step in changes),
            )
    if editor:  # Left open by an error
        editor.Destroy()
        settle()
    return check.problems


def check_all(parent, task_file):
    problems = []
    for name, open_editor, own_steps in editors(parent, task_file):
        print("Checking the %s editor" % name, flush=True)
        problems.extend(check_editor(name, open_editor, own_steps))
    return problems


def _set_up():
    """The app's own start, as taskcoach.py and application.py make
    it, with settings that are never saved."""
    import taskcoachlib.workarounds.monkeypatches  # noqa: F401
    from taskcoachlib import config, gui, i18n

    app = wx.App(False)
    app.quitting = False
    app.settings = config.Settings(load=False)
    config.settings.use(app.settings)
    i18n.Translator("en_US")
    gui.init()
    from taskcoachlib.gui.dialog import editor  # noqa: F401

    return app


def annotate(problem):
    """On GitHub Actions, the problem as an error on the run's page,
    which anyone can read; the log needs a sign-in."""
    if os.environ.get("GITHUB_ACTIONS") == "true":
        for plain, coded in (("%", "%25"), ("\r", "%0D"), ("\n", "%0A")):
            problem = problem.replace(plain, coded)
        print("::error title=Editor check::" + problem)


def main():
    # Each line out at once: a hang ends the run with os._exit(),
    # which drops what is buffered (the app's log of the error)
    sys.stdout.reconfigure(line_buffering=True)
    faulthandler.enable(all_threads=True)
    # Never the user's own settings, data or session bus
    folders = tempfile.mkdtemp(prefix="taskcoach-editor-check-")
    for variable in ("XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_CACHE_HOME"):
        os.environ[variable] = os.path.join(folders, variable)
        os.makedirs(os.environ[variable])
    os.environ["DBUS_SESSION_BUS_ADDRESS"] = "unix:path=" + os.path.join(
        folders, "no-session-bus"
    )
    try:
        app = _set_up()
        import taskcoachlib

        print(
            "wxPython %s, Python %s, %s"
            % (
                wx.version(),
                sys.version.split()[0],
                os.path.dirname(taskcoachlib.__file__),
            )
        )
        parent = MainFrame()
        task_file = sample_task_file()
        problems = check_all(parent, task_file)
        task_file.close()
        task_file.stop()
        parent.Destroy()
        settle()
        del app
    finally:
        shutil.rmtree(folders, ignore_errors=True)
    for problem in problems:
        print(problem, file=sys.stderr)
        annotate(problem)
    print("%d problem(s)" % len(problems))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
