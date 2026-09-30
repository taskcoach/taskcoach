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

import contextlib
import time

from taskcoachlib.meta.debug import log_step
from . import singleton as patterns
from .observer import Event
from .snapshot import Snapshot, Step, is_restoring


class Command(object):
    """A user action's change. Its undo is generic: the step records
    what it changed (docs/UNDO_REDO.md, Architecture)."""

    def __init__(self, *args, **kwargs):
        super().__init__()  # object.__init__ takes no arguments

    def do(self):
        if is_restoring():
            return  # A view reacting to undo or redo changes nothing
        with CommandHistory().action(str(self)):
            self.do_command()

    def do_command(self):
        pass

    def __str__(self):
        return "command"


class CommandHistory(object, metaclass=patterns.Singleton):
    """The undo log: one step per user action, what it changed in the
    stored data (docs/UNDO_REDO.md, Architecture)."""

    def __init__(self):
        self.__history = []
        self.__future = []
        self.__running = 0
        self.__depth = 0
        self.__open = None  # (label, snapshot before) of the open step
        self.__closing = False  # Waiting for the application's idle

    def _notify(self):
        Event("commandhistory.changed", self).send()

    @contextlib.contextmanager
    def action(self, label):
        """A user action: what it changes, whatever commands it runs, is
        one step, named label. The step stays open until the events the
        action posted have run, so what they change joins it (an
        editor's derived adjustments), as undo managers group by event.
        A failed action is rolled back."""
        if self.__depth or is_restoring():
            yield  # Part of the running action, or of undo or redo
            return
        start = Snapshot()
        if self.__open is None:
            self.__open = (label, start)
        self.__depth += 1
        try:
            with self.running():
                yield
        except BaseException:
            step = Step(label, start, Snapshot())
            log_step("rolled back", step.summary(), prefix="UNDO")
            step.undo()
            if self.__open is not None and self.__open[1] is start:
                self.__open = None
            raise
        finally:
            self.__depth -= 1
        self.__close_soon()

    def __close_soon(self):
        """Close the step when the application is next idle: the
        events the action posted, and theirs, have run. At once
        without an event loop (tests, loading)."""
        import wx

        app = wx.GetApp()
        if app is None or not app.IsMainLoopRunning():
            self.flush()
        elif not self.__closing:
            self.__closing = True
            app.Bind(wx.EVT_IDLE, self.__on_idle)
            wx.WakeUpIdle()

    def __on_idle(self, event):
        import wx

        event.Skip()
        event.GetEventObject().Unbind(wx.EVT_IDLE, handler=self.__on_idle)
        self.__closing = False
        self.flush()

    def flush(self):
        """Close the open step, before the steps are read."""
        if self.__open is None or self.__depth:
            return
        label, before = self.__open
        self.__open = None
        started = time.perf_counter()
        step = Step(label, before, Snapshot())
        if step:
            log_step(
                "step",
                step.summary(),
                "(%d ms)" % ((time.perf_counter() - started) * 1000),
                prefix="UNDO",
            )
            self.__history.append(step)
            del self.__future[:]
            self._notify()

    @contextlib.contextmanager
    def running(self):
        """While an action runs or a step is undone or redone: changes
        made meanwhile are the step's."""
        self.__running += 1
        try:
            yield
        finally:
            self.__running -= 1

    def is_running(self):
        """Whether changes made now are a step's: an action, undo or
        redo runs, or a step is open."""
        return self.__running > 0 or self.__open is not None

    def current(self):
        """The last step done, which undo would undo; None if none."""
        self.flush()
        return self.__history[-1] if self.__history else None

    def undo(self):
        self.flush()
        if self.__history:
            step = self.__history.pop()
            log_step("undo", step.summary(), prefix="UNDO")
            with self.running():
                step.undo()
            self.__future.append(step)
            self._notify()

    def redo(self):
        self.flush()
        if self.__future:
            step = self.__future.pop()
            log_step("redo", step.summary(), prefix="UNDO")
            with self.running():
                step.redo()
            self.__history.append(step)
            self._notify()

    def clear(self):
        self.__open = None
        del self.__history[:]
        del self.__future[:]
        self._notify()

    def has_history(self):
        self.flush()
        return self.__history

    def get_history(self):
        self.flush()
        return self.__history

    def has_future(self):
        self.flush()
        return self.__future

    def get_future(self):
        self.flush()
        return self.__future

    def _extend_label(self, label, steps):
        if steps:
            label += (" %s" % steps[-1]).lower()
        return label

    def undostr(self, label="Undo"):
        self.flush()
        return self._extend_label(label, self.__history)

    def redostr(self, label="Redo"):
        self.flush()
        return self._extend_label(label, self.__future)
