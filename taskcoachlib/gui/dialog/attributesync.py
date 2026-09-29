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
from taskcoachlib.i18n import _
import wx


class AttributeSync(object):
    """Class used for keeping an attribute of a domain object synchronized with
    a control in a dialog. If the user edits the value using the control,
    the domain object is changed, using the appropriate command. If the
    attribute of the domain object is changed (e.g. in another dialog) the
    value of the control is updated."""

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
        **kwargs
    ):
        self._getter = attributeGetterName
        self._entry = entry
        self._currentValue = currentValue
        self._items = items
        self._commandClass = commandClass
        self.__commandKwArgs = kwargs
        self.__callback = callback

        entry.Bind(editedEventType, self.onAttributeEdited)

        if len(items) == 1:
            self.__start_observing_attribute(changedEventType, items[0])

    def onAttributeEdited(self, event):
        event.Skip()
        new_value = self.get_value()
        if new_value != self._currentValue:
            self.__executeCommand(new_value)

    def __executeCommand(self, new_value):
        self._currentValue = new_value
        command_kw_args = self.command_kw_args(new_value)
        self._commandClass(
            None, self._items, **command_kw_args
        ).do()  # pylint: disable=W0142
        self.__invokeCallback(new_value)

    def on_attribute_changed(self, event):  # pylint: disable=W0613
        if self._entry:
            new_value = getattr(self._items[0], self._getter)()
            if new_value != self._currentValue:
                self._currentValue = new_value
                self.set_value(new_value)
                self.__invokeCallback(new_value)
        else:
            self.__stop_observing_attribute()

    def command_kw_args(self, new_value):
        self.__commandKwArgs["newValue"] = new_value
        return self.__commandKwArgs

    def set_value(self, new_value):
        if self._entry:
            self._entry.SetValue(new_value)

    def get_value(self):
        return self._entry.GetValue()

    def __invokeCallback(self, value):
        if self.__callback is not None:
            try:
                self.__callback(value)
            except RuntimeError:
                pass  # Widget has been deleted (e.g., dialog closing)
            except Exception as e:
                wx.MessageBox(str(e), _("Error"), wx.OK)

    def __start_observing_attribute(self, eventType, eventSource):
        patterns.Publisher().registerObserver(
            self.on_attribute_changed,
            eventType=eventType,
            eventSource=eventSource,
        )

    def __stop_observing_attribute(self):
        patterns.Publisher().removeObserver(self.on_attribute_changed)


class FontColorSync(AttributeSync):
    def set_value(self, new_value):
        self._entry.SetColor(new_value)

    def get_value(self):
        return self._entry.GetColor()
