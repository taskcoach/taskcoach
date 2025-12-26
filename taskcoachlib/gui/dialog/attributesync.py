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
import sys
import time

def _ts():
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
        self.__skipCallbacks = False  # Flag to suppress callbacks during close
        self.__syncId = "%s_%s" % (attributeGetterName, id(self))  # For logging
        sys.stderr.write("[%s][SYNC] Created AttributeSync id=%s, getter=%s\n" % (_ts(), self.__syncId, attributeGetterName))
        sys.stderr.flush()

        entry.Bind(editedEventType, self.onAttributeEdited)

        if commit_on_focus_loss:
            # For composite widgets like DateTimeEntry, we need to track focus
            # on the widget and all its children
            self.__bindFocusEvents(entry)

        if len(items) == 1:
            self.__start_observing_attribute(changedEventType, items[0])

    def __bindFocusEvents(self, widget):
        """Bind focus events to widget and all its children recursively."""
        widget.Bind(wx.EVT_SET_FOCUS, self.__onSetFocus)
        widget.Bind(wx.EVT_KILL_FOCUS, self.__onKillFocus)
        # Track bound widgets for cleanup
        if not hasattr(self, '_boundWidgets'):
            self._boundWidgets = []
        self._boundWidgets.append(widget)
        for child in widget.GetChildren():
            self.__bindFocusEvents(child)

    def unbindFocusEvents(self):
        """Unbind focus events from all tracked widgets."""
        sys.stderr.write("[%s][SYNC] unbindFocusEvents called, _boundWidgets=%s\n" % (_ts(), len(getattr(self, '_boundWidgets', []))))
        sys.stderr.flush()
        if hasattr(self, '_boundWidgets'):
            for widget in self._boundWidgets:
                try:
                    widget.Unbind(wx.EVT_SET_FOCUS)
                    widget.Unbind(wx.EVT_KILL_FOCUS)
                except (RuntimeError, AttributeError) as e:
                    sys.stderr.write("[%s][SYNC] unbindFocusEvents exception: %s\n" % (_ts(), e))
                    sys.stderr.flush()
            self._boundWidgets = []
        sys.stderr.write("[%s][SYNC] unbindFocusEvents complete\n" % _ts())
        sys.stderr.flush()

    def __onSetFocus(self, event):
        """Called when any part of the widget gains focus."""
        event.Skip()
        if self.__editSessionValue is None:
            # Starting a new edit session - remember the initial value
            self.__editSessionValue = self._currentValue
            self.__hasChanges = False

    def __onKillFocus(self, event):
        """Called when any part of the widget loses focus."""
        event.Skip()

        new_focus = event.GetWindow()
        sys.stderr.write("[%s][SYNC:%s] __onKillFocus called, new_focus=%s, hasChanges=%s, editSessionValue=%s\n" % (
            _ts(), self.__syncId, new_focus, self.__hasChanges, self.__editSessionValue))
        sys.stderr.flush()

        # Guard against destroyed widgets (e.g., when dialog is closing)
        try:
            if not self._entry:
                sys.stderr.write("[%s][SYNC] _entry is falsy, returning\n" % _ts())
                sys.stderr.flush()
                self.__editSessionValue = None
                self.__hasChanges = False
                return
        except RuntimeError as e:
            sys.stderr.write("[%s][SYNC] RuntimeError checking _entry: %s\n" % (_ts(), e))
            sys.stderr.flush()
            self.__editSessionValue = None
            self.__hasChanges = False
            return

        if new_focus is not None:
            try:
                # Check if new focus is within the same entry widget
                parent = new_focus
                while parent is not None:
                    if parent is self._entry:
                        sys.stderr.write("[%s][SYNC] new_focus is within same widget, returning\n" % _ts())
                        sys.stderr.flush()
                        return  # Still within the same widget, don't commit yet
                    parent = parent.GetParent()
            except RuntimeError as e:
                sys.stderr.write("[%s][SYNC] RuntimeError traversing parents: %s\n" % (_ts(), e))
                sys.stderr.flush()
                self.__editSessionValue = None
                self.__hasChanges = False
                return

        # Focus is leaving the widget entirely - commit if there are changes
        sys.stderr.write("[%s][SYNC] Focus leaving widget, hasChanges=%s, editSessionValue=%s\n" % (
            _ts(), self.__hasChanges, self.__editSessionValue))
        sys.stderr.flush()

        if self.__hasChanges and self.__editSessionValue is not None:
            try:
                new_value = self.getValue()
                sys.stderr.write("[%s][SYNC] new_value=%s, editSessionValue=%s\n" % (_ts(), new_value, self.__editSessionValue))
                sys.stderr.flush()
                if new_value != self.__editSessionValue:
                    # Skip callback if focus is going to None (dialog closing)
                    # The callback updates UI which can queue events that crash
                    # after the dialog is destroyed
                    skip_callback = (new_focus is None)
                    sys.stderr.write("[%s][SYNC] About to executeCommand, skip_callback=%s\n" % (_ts(), skip_callback))
                    sys.stderr.flush()
                    if skip_callback:
                        self.__skipCallbacks = True  # Suppress callbacks from pubsub too
                    self.__executeCommand(new_value, skip_callback=skip_callback)
                    self.__skipCallbacks = False
                    sys.stderr.write("[%s][SYNC] executeCommand complete\n" % _ts())
                    sys.stderr.flush()
            except RuntimeError as e:
                sys.stderr.write("[%s][SYNC] RuntimeError in commit: %s\n" % (_ts(), e))
                sys.stderr.flush()

        # Reset edit session
        self.__editSessionValue = None
        self.__hasChanges = False
        sys.stderr.write("[%s][SYNC] __onKillFocus complete\n" % _ts())
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

    def __executeCommand(self, new_value, skip_callback=False):
        """Execute the command to update the model.

        Args:
            new_value: The new value to set
            skip_callback: If True, skip the callback invocation. This is used
                when the dialog is closing to avoid queuing UI events that would
                crash after the dialog is destroyed.
        """
        sys.stderr.write("[%s][SYNC] __executeCommand called, new_value=%s, skip_callback=%s\n" % (_ts(), new_value, skip_callback))
        sys.stderr.flush()
        self._currentValue = new_value
        commandKwArgs = self.commandKwArgs(new_value)
        sys.stderr.write("[%s][SYNC] About to call command.do()\n" % _ts())
        sys.stderr.flush()
        self._commandClass(
            None, self._items, **commandKwArgs
        ).do()  # pylint: disable=W0142
        sys.stderr.write("[%s][SYNC] command.do() complete\n" % _ts())
        sys.stderr.flush()
        if not skip_callback:
            sys.stderr.write("[%s][SYNC] About to invokeCallback\n" % _ts())
            sys.stderr.flush()
            self.__invokeCallback(new_value)
            sys.stderr.write("[%s][SYNC] invokeCallback complete\n" % _ts())
            sys.stderr.flush()
        else:
            sys.stderr.write("[%s][SYNC] Skipping callback\n" % _ts())
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
        sys.stderr.write("[%s][SYNC:%s] onAttributeChanged called, newValue=%s, sender=%s, skipCallbacks=%s\n" % (
            _ts(), self.__syncId, newValue, sender, self.__skipCallbacks))
        sys.stderr.flush()
        if sender in self._items:
            if self._entry:
                if newValue != self._currentValue:
                    sys.stderr.write("[%s][SYNC:%s] Value changed, about to setValue and invokeCallback\n" % (_ts(), self.__syncId))
                    sys.stderr.flush()
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
        sys.stderr.write("[%s][SYNC:%s] __invokeCallback called, callback=%s, skipCallbacks=%s\n" % (_ts(), self.__syncId, self.__callback, self.__skipCallbacks))
        sys.stderr.flush()
        if self.__skipCallbacks:
            sys.stderr.write("[%s][SYNC] Skipping callback due to __skipCallbacks flag\n" % _ts())
            sys.stderr.flush()
            return
        if self.__callback is not None:
            try:
                self.__callback(value)
                sys.stderr.write("[%s][SYNC] callback executed successfully\n" % _ts())
                sys.stderr.flush()
            except RuntimeError as e:
                sys.stderr.write("[%s][SYNC] RuntimeError in callback: %s\n" % (_ts(), e))
                sys.stderr.flush()
            except Exception as e:
                sys.stderr.write("[%s][SYNC] Exception in callback: %s\n" % (_ts(), e))
                sys.stderr.flush()
                wx.MessageBox(str(e), _("Error"), wx.OK)

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
