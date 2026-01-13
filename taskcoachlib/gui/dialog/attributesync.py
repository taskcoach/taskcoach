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
        widget.Bind(wx.EVT_SET_FOCUS, self.__onSetFocus)
        widget.Bind(wx.EVT_KILL_FOCUS, self.__onKillFocus)
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
        event.Skip()

        # Guard against destroyed widgets (e.g., when dialog is closing)
        try:
            if not self._entry:
                self.__editSessionValue = None
                self.__hasChanges = False
                return
        except RuntimeError:
            self.__editSessionValue = None
            self.__hasChanges = False
            return

        # Check if focus is moving to another child of the same parent widget
        new_focus = event.GetWindow()

        if new_focus is not None:
            try:
                # Check if new focus is within the same entry widget
                parent = new_focus
                while parent is not None:
                    if parent is self._entry:
                        return  # Still within the same widget, don't commit yet
                    parent = parent.GetParent()
            except RuntimeError:
                self.__editSessionValue = None
                self.__hasChanges = False
                return

        # If dialog is closing (new_focus is None), we still need to save any pending changes
        # to the domain model, but skip the callback to avoid UI updates on destroyed widgets.
        if new_focus is None:
            self.__stop_observing_attribute()
            # Still commit pending changes to domain model, but skip callback
            if self.__hasChanges and self.__editSessionValue is not None:
                try:
                    new_value = self.getValue()
                    if new_value != self.__editSessionValue:
                        self.__executeCommand(new_value, skip_callback=True)
                except RuntimeError:
                    pass  # Widget already destroyed
            self.__editSessionValue = None
            self.__hasChanges = False
            return

        # Focus is leaving the widget entirely - commit if there are changes
        if self.__hasChanges and self.__editSessionValue is not None:
            try:
                new_value = self.getValue()
                if new_value != self.__editSessionValue:
                    self.__executeCommand(new_value, skip_callback=False)
                    # Only reset edit session after successful commit
                    self.__editSessionValue = None
                    self.__hasChanges = False
            except RuntimeError:
                pass  # Widget deleted, can't get value or execute command
        # NOTE: Don't reset __editSessionValue if no changes committed.
        # This preserves the session state when focus goes to popup dropdowns.

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
        self._currentValue = new_value
        commandKwArgs = self.commandKwArgs(new_value)
        self._commandClass(
            None, self._items, **commandKwArgs
        ).do()  # pylint: disable=W0142
        if not skip_callback:
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
            # Check if widget is still valid (not destroyed)
            try:
                if not self._entry:
                    self.__stop_observing_attribute()
                    return
                # Additional check - try to access a property to verify widget is alive
                # On GTK, accessing a destroyed widget can segfault
                self._entry.GetId()
            except RuntimeError:
                self.__stop_observing_attribute()
                return

            if newValue != self._currentValue:
                self._currentValue = newValue
                self.__editSessionValue = None  # Cancel any pending edit session
                self.__hasChanges = False
                try:
                    self.setValue(newValue)
                    self.__invokeCallback(newValue)
                except RuntimeError:
                    self.__stop_observing_attribute()
                    return

    def commandKwArgs(self, new_value):
        self.__commandKwArgs["newValue"] = new_value
        return self.__commandKwArgs

    def setValue(self, new_value):
        try:
            if self._entry:
                self._entry.SetValue(new_value)
        except RuntimeError:
            raise

    def getValue(self):
        try:
            return self._entry.GetValue()
        except RuntimeError:
            raise

    def __invokeCallback(self, value):
        if self.__callback is not None:
            try:
                self.__callback(value)
            except RuntimeError:
                pass  # Widget has been deleted (e.g., dialog closing)
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
