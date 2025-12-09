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

# Enable debug logging for AttributeSync
_log = logging.getLogger('AttributeSync')
_log.setLevel(logging.DEBUG)
# Add console handler if not already present
if not _log.handlers:
    _handler = logging.StreamHandler()
    _handler.setLevel(logging.DEBUG)
    _handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    _log.addHandler(_handler)


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

        _log.debug("AttributeSync.__init__: getter=%s, entry=%s (%s), commit_on_focus_loss=%s, editedEventType=%s",
                   attributeGetterName, entry, type(entry).__name__, commit_on_focus_loss, editedEventType)

        entry.Bind(editedEventType, self.onAttributeEdited)
        _log.debug("AttributeSync.__init__: Bound %s to onAttributeEdited", editedEventType)

        if commit_on_focus_loss:
            # For composite widgets like DateTimeEntry, we need to track focus
            # on the widget and all its children
            self.__bindFocusEvents(entry)
            _log.debug("AttributeSync.__init__: Bound focus events for commit_on_focus_loss mode")

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
            _log.debug("__onSetFocus: Starting edit session, initial value=%s", self.__editSessionValue)

    def __onKillFocus(self, event):
        """Called when any part of the widget loses focus."""
        event.Skip()
        # Check if focus is moving to another child of the same parent widget
        # If so, we're still in the same edit session
        new_focus = event.GetWindow()
        _log.debug("__onKillFocus: Focus leaving, new_focus=%s", new_focus)

        if new_focus is not None:
            # Check if new focus is within the same entry widget
            parent = new_focus
            while parent is not None:
                if parent is self._entry:
                    _log.debug("__onKillFocus: Focus moving within same widget, not committing")
                    return  # Still within the same widget, don't commit yet
                parent = parent.GetParent()

        # Focus is leaving the widget entirely - commit if there are changes
        if self.__hasChanges and self.__editSessionValue is not None:
            new_value = self.getValue()
            _log.debug("__onKillFocus: Focus left widget, committing. old=%s, new=%s",
                       self.__editSessionValue, new_value)
            if new_value != self.__editSessionValue:
                self.__executeCommand(new_value)

        # Reset edit session
        self.__editSessionValue = None
        self.__hasChanges = False

    def onAttributeEdited(self, event):
        _log.debug("onAttributeEdited: event=%s, event.GetEventType()=%s", event, event.GetEventType())
        event.Skip()
        new_value = self.getValue()
        _log.debug("onAttributeEdited: new_value=%s, current_value=%s, changed=%s",
                   new_value, self._currentValue, new_value != self._currentValue)

        if new_value != self._currentValue:
            if self.__commit_on_focus_loss:
                # Just track that we have changes, don't commit yet
                self.__hasChanges = True
                # Update internal state but don't execute command
                self._currentValue = new_value
                _log.debug("onAttributeEdited: commit_on_focus_loss mode - tracking change, not committing")
            else:
                # Immediate: execute command now
                _log.debug("onAttributeEdited: executing command immediately")
                self.__executeCommand(new_value)

    def __executeCommand(self, new_value):
        """Execute the command to update the model."""
        _log.debug("__executeCommand: executing command with new_value=%s", new_value)
        self._currentValue = new_value
        commandKwArgs = self.commandKwArgs(new_value)
        _log.debug("__executeCommand: commandClass=%s, items=%s, kwargs=%s",
                   self._commandClass, self._items, commandKwArgs)
        self._commandClass(
            None, self._items, **commandKwArgs
        ).do()  # pylint: disable=W0142
        _log.debug("__executeCommand: command executed successfully")
        self.__invokeCallback(new_value)

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
        if self.__callback is not None:
            try:
                self.__callback(value)
            except Exception as e:
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
