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

from taskcoachlib import patterns
from pubsub import pub
from taskcoachlib.i18n import _
import wx
import logging
import sys
import time

# Set up logging for crash debugging
_logger = logging.getLogger(__name__)

def _ts():
    """Return timestamp with millisecond precision."""
    return "%.3f" % time.time()


class AttributeSync(object):
    """Class used for keeping an attribute of a domain object synchronized with
    a control in a dialog. If the user edits the value using the control,
    the domain object is changed, using the appropriate command. If the
    attribute of the domain object is changed (e.g. in another dialog) the
    value of the control is updated.

    When commit_on_focus_loss=True, command execution is delayed until focus
    leaves the control. This creates a single undo entry for the entire edit
    session (e.g., typing a complete date)."""

    def __init__(
        self,
        attributeGetterName,
        entry,
        currentValue,
        items,
        commandClass,
        editedEventType,
        changedEventType,
        callback=None,
        commit_on_focus_loss=False,
        **kwargs
    ):
        self._getter = attributeGetterName
        self._entry = entry
        self._currentValue = currentValue
        self._items = items
        self._commandClass = commandClass
        self.__commandKwArgs = kwargs
        self.__changedEventType = changedEventType
        self.__callback = callback
        self.__commit_on_focus_loss = commit_on_focus_loss
        self.__editSessionValue = None  # Value at start of edit session
        self.__hasChanges = False  # Track if any changes during this focus session

        entry.Bind(editedEventType, self.onAttributeEdited)

        if commit_on_focus_loss:
            # For composite widgets like DateTimeEntry, we need to track focus
            # on the widget and all its children
            self.__bindFocusEvents(entry)

        if len(items) == 1:
            self.__start_observing_attribute(changedEventType, items[0])

    def __bindFocusEvents(self, widget):
        """Bind focus events to widget and all its children recursively."""
        # Bind to the widget itself
        widget.Bind(wx.EVT_SET_FOCUS, self.__onSetFocus)
        widget.Bind(wx.EVT_KILL_FOCUS, self.__onKillFocus)
        # Bind to all children (for composite widgets)
        for child in widget.GetChildren():
            self.__bindFocusEvents(child)

    def __onSetFocus(self, event):
        """Called when any part of the widget gains focus."""
        event.Skip()
        if self.__editSessionValue is None:
            # Starting a new edit session - remember the initial value
            self.__editSessionValue = self._currentValue
            self.__hasChanges = False

    def __onKillFocus(self, event):
        """Called when any part of the widget loses focus."""
        sys.stderr.write("[%s][KILLFOCUS] __onKillFocus called, hasChanges=%s\n" % (_ts(), self.__hasChanges))
        sys.stderr.flush()
        event.Skip()

        # Guard against destroyed widgets (e.g., when dialog is closing)
        try:
            # Check if the entry widget is still valid
            if not self._entry:
                sys.stderr.write("[%s][KILLFOCUS] Entry is invalid, returning\n" % _ts())
                sys.stderr.flush()
                self.__editSessionValue = None
                self.__hasChanges = False
                return
        except RuntimeError as e:
            # Widget has been deleted (wrapped C/C++ object deleted)
            sys.stderr.write("[%s][KILLFOCUS] RuntimeError checking entry: %s\n" % (_ts(), e))
            sys.stderr.flush()
            self.__editSessionValue = None
            self.__hasChanges = False
            return

        # Check if focus is moving to another child of the same parent widget
        # If so, we're still in the same edit session
        new_focus = event.GetWindow()
        sys.stderr.write("[%s][KILLFOCUS] new_focus=%s\n" % (_ts(), new_focus))
        sys.stderr.flush()

        if new_focus is not None:
            try:
                # Check if new focus is within the same entry widget
                parent = new_focus
                while parent is not None:
                    if parent is self._entry:
                        sys.stderr.write("[%s][KILLFOCUS] Focus still within same widget, returning\n" % _ts())
                        sys.stderr.flush()
                        return  # Still within the same widget, don't commit yet
                    parent = parent.GetParent()
            except RuntimeError as e:
                # Widget has been deleted during parent traversal
                sys.stderr.write("[%s][KILLFOCUS] RuntimeError during parent traversal: %s\n" % (_ts(), e))
                sys.stderr.flush()
                self.__editSessionValue = None
                self.__hasChanges = False
                return

        # Focus is leaving the widget entirely - commit if there are changes
        sys.stderr.write("[%s][KILLFOCUS] Focus leaving widget, hasChanges=%s, editSessionValue=%s\n" %
                        (_ts(), self.__hasChanges, self.__editSessionValue))
        sys.stderr.flush()
        if self.__hasChanges and self.__editSessionValue is not None:
            try:
                new_value = self.getValue()
                sys.stderr.write("[%s][KILLFOCUS] new_value=%s\n" % (_ts(), new_value))
                sys.stderr.flush()
                if new_value != self.__editSessionValue:
                    sys.stderr.write("[%s][KILLFOCUS] Values differ, executing command\n" % _ts())
                    sys.stderr.flush()
                    self.__executeCommand(new_value)
                    sys.stderr.write("[%s][KILLFOCUS] Command executed\n" % _ts())
                    sys.stderr.flush()
            except RuntimeError as e:
                # Widget has been deleted, can't get value or execute command
                sys.stderr.write("[%s][KILLFOCUS] RuntimeError during command execution: %s\n" % (_ts(), e))
                sys.stderr.flush()

        # Reset edit session
        self.__editSessionValue = None
        self.__hasChanges = False
        sys.stderr.write("[%s][KILLFOCUS] __onKillFocus complete\n" % _ts())
        sys.stderr.flush()

    def flushPendingChanges(self):
        """Commit any pending changes immediately.

        Call this before closing a dialog to ensure any uncommitted edits
        from commit_on_focus_loss mode are saved.
        """
        sys.stderr.write("[%s][FLUSH] flushPendingChanges called, hasChanges=%s, editSessionValue=%s\n" %
                        (_ts(), self.__hasChanges, self.__editSessionValue))
        sys.stderr.flush()
        if self.__hasChanges and self.__editSessionValue is not None:
            try:
                new_value = self.getValue()
                sys.stderr.write("[%s][FLUSH] new_value=%s, editSessionValue=%s\n" % (_ts(), new_value, self.__editSessionValue))
                sys.stderr.flush()
                if new_value != self.__editSessionValue:
                    sys.stderr.write("[%s][FLUSH] About to execute command\n" % _ts())
                    sys.stderr.flush()
                    self.__executeCommand(new_value)
                    sys.stderr.write("[%s][FLUSH] Command executed successfully\n" % _ts())
                    sys.stderr.flush()
            except RuntimeError as e:
                # Widget has been deleted
                sys.stderr.write("[%s][FLUSH] RuntimeError: %s\n" % (_ts(), e))
                sys.stderr.flush()
        # Reset edit session
        self.__editSessionValue = None
        self.__hasChanges = False
        sys.stderr.write("[%s][FLUSH] flushPendingChanges complete\n" % _ts())
        sys.stderr.flush()

    def onAttributeEdited(self, event):
        event.Skip()
        new_value = self.getValue()
        if new_value != self._currentValue:
            if self.__commit_on_focus_loss:
                # Just track that we have changes, don't commit yet
                self.__hasChanges = True
                # Update internal state but don't execute command
                self._currentValue = new_value
            else:
                # Immediate: execute command now
                self.__executeCommand(new_value)

    def __executeCommand(self, new_value):
        """Execute the command to update the model."""
        sys.stderr.write("[%s][EXEC] __executeCommand called with new_value=%s\n" % (_ts(), new_value))
        sys.stderr.flush()
        # Guard against destroyed widgets
        try:
            if not self._entry:
                sys.stderr.write("[%s][EXEC] Entry is invalid, returning\n" % _ts())
                sys.stderr.flush()
                return
        except RuntimeError as e:
            sys.stderr.write("[%s][EXEC] RuntimeError checking entry: %s\n" % (_ts(), e))
            sys.stderr.flush()
            return

        self._currentValue = new_value
        commandKwArgs = self.commandKwArgs(new_value)
        sys.stderr.write("[%s][EXEC] About to call command.do(), commandClass=%s\n" % (_ts(), self._commandClass.__name__))
        sys.stderr.flush()
        self._commandClass(
            None, self._items, **commandKwArgs
        ).do()  # pylint: disable=W0142
        sys.stderr.write("[%s][EXEC] command.do() completed, about to invoke callback\n" % _ts())
        sys.stderr.flush()
        self.__invokeCallback(new_value)
        sys.stderr.write("[%s][EXEC] __executeCommand complete\n" % _ts())
        sys.stderr.flush()

    def onAttributeChanged_Deprecated(self, event):  # pylint: disable=W0613
        if self._entry:
            new_value = getattr(self._items[0], self._getter)()
            if new_value != self._currentValue:
                self._currentValue = new_value
                self.__editSessionValue = None  # Cancel any pending edit session
                self.__hasChanges = False
                self.setValue(new_value)
                self.__invokeCallback(new_value)
        else:
            self.__stop_observing_attribute()

    def onAttributeChanged(self, newValue, sender):
        if sender in self._items:
            if self._entry:
                if newValue != self._currentValue:
                    self._currentValue = newValue
                    self.__editSessionValue = None  # Cancel any pending edit session
                    self.__hasChanges = False
                    self.setValue(newValue)
                    self.__invokeCallback(newValue)
            else:
                self.__stop_observing_attribute()

    def commandKwArgs(self, new_value):
        self.__commandKwArgs["newValue"] = new_value
        return self.__commandKwArgs

    def setValue(self, new_value):
        self._entry.SetValue(new_value)

    def getValue(self):
        return self._entry.GetValue()

    def __invokeCallback(self, value):
        sys.stderr.write("[%s][CALLBACK] __invokeCallback called, callback=%s\n" % (_ts(), self.__callback))
        sys.stderr.flush()
        if self.__callback is not None:
            try:
                sys.stderr.write("[%s][CALLBACK] About to call callback\n" % _ts())
                sys.stderr.flush()
                self.__callback(value)
                sys.stderr.write("[%s][CALLBACK] Callback completed successfully\n" % _ts())
                sys.stderr.flush()
            except RuntimeError as e:
                # Widget has been deleted (e.g., dialog closing)
                sys.stderr.write("[%s][CALLBACK] RuntimeError: %s\n" % (_ts(), e))
                sys.stderr.flush()
            except Exception as e:
                sys.stderr.write("[%s][CALLBACK] Exception: %s\n" % (_ts(), e))
                sys.stderr.flush()
                wx.MessageBox(str(e), _("Error"), wx.OK)
        sys.stderr.write("[%s][CALLBACK] __invokeCallback complete\n" % _ts())
        sys.stderr.flush()

    def __start_observing_attribute(self, eventType, eventSource):
        if eventType.startswith("pubsub"):
            pub.subscribe(self.onAttributeChanged, eventType)
        else:
            patterns.Publisher().registerObserver(
                self.onAttributeChanged_Deprecated,
                eventType=eventType,
                eventSource=eventSource,
            )

    def __stop_observing_attribute(self):
        try:
            pub.unsubscribe(self.onAttributeChanged, self.__changedEventType)
        except pub.TopicNameError:
            pass
        patterns.Publisher().removeObserver(self.onAttributeChanged_Deprecated)


class FontColorSync(AttributeSync):
    def setValue(self, newValue):
        self._entry.SetColor(newValue)

    def getValue(self):
        return self._entry.GetColor()
