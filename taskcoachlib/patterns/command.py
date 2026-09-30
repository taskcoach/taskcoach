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
        self.__open = 0

    def _notify(self):
        Event("commandhistory.changed", self).send()

    @contextlib.contextmanager
    def action(self, label):
        """A user action: what it changes, whatever commands it runs, is
        one step, named label. A failed action is rolled back."""
        if self.__open:
            self.__open += 1  # Joins the open action
            try:
                yield
            finally:
                self.__open -= 1
            return
        before = Snapshot()
        self.__open = 1
        try:
            with self.running():
                yield
        except BaseException:
            Step(label, before, Snapshot()).undo()
            raise
        finally:
            self.__open = 0
        step = Step(label, before, Snapshot())
        if step:
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
        return self.__running > 0

    def current(self):
        """The last step done, which undo would undo; None if none."""
        return self.__history[-1] if self.__history else None

    def undo(self):
        if self.__history:
            step = self.__history.pop()
            with self.running():
                step.undo()
            self.__future.append(step)
            self._notify()

    def redo(self):
        if self.__future:
            step = self.__future.pop()
            with self.running():
                step.redo()
            self.__history.append(step)
            self._notify()

    def clear(self):
        del self.__history[:]
        del self.__future[:]
        self._notify()

    def hasHistory(self):
        return self.__history

    def getHistory(self):
        return self.__history

    def hasFuture(self):
        return self.__future

    def getFuture(self):
        return self.__future

    def _extendLabel(self, label, commandList):
        if commandList:
            commandName = " %s" % commandList[-1]
            label += commandName.lower()
        return label

    def undostr(self, label="Undo"):
        return self._extendLabel(label, self.__history)

    def redostr(self, label="Redo"):
        return self._extendLabel(label, self.__future)
