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
        self.__changedEventType = changedEventType
        self.__callback = callback
        self.__syncId = "%s_%s" % (attributeGetterName, id(self))  # For logging
        sys.stderr.write("[%s][SYNC] Created AttributeSync id=%s, getter=%s, items=[%s]\n" % (
            _ts(), self.__syncId, attributeGetterName,
            ", ".join("%s (id=%s)" % (i, id(i)) for i in items)))
        sys.stderr.flush()

        entry.Bind(editedEventType, self.onAttributeEdited)

        if len(items) == 1:
            self.__start_observing_attribute(changedEventType, items[0])

    def onAttributeEdited(self, event):
        event.Skip()
        new_value = self.getValue()
        if new_value != self._currentValue:
            self.__executeCommand(new_value)

    def __executeCommand(self, new_value):
        """Execute the command to update the model."""
        sys.stderr.write("[%s][SYNC] __executeCommand called, new_value=%s\n" % (_ts(), new_value))
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
        sys.stderr.write("[%s][SYNC] About to invokeCallback\n" % _ts())
        sys.stderr.flush()
        self.__invokeCallback(new_value)
        sys.stderr.write("[%s][SYNC] invokeCallback complete\n" % _ts())
        sys.stderr.flush()

    def onAttributeChanged_Deprecated(self, event):  # pylint: disable=W0613
        if self._entry:
            new_value = getattr(self._items[0], self._getter)()
            if new_value != self._currentValue:
                self._currentValue = new_value
                self.setValue(new_value)
                self.__invokeCallback(new_value)
        else:
            self.__stop_observing_attribute()

    def onAttributeChanged(self, newValue, sender):
        sender_in_items = sender in self._items
        sys.stderr.write("[%s][SYNC:%s] onAttributeChanged: sender=%s (id=%s), _items=[%s], match=%s\n" % (
            _ts(), self.__syncId, sender, id(sender),
            ", ".join("%s (id=%s)" % (i, id(i)) for i in self._items),
            sender_in_items))
        sys.stderr.flush()
        if sender_in_items:
            if self._entry:
                if newValue != self._currentValue:
                    sys.stderr.write("[%s][SYNC:%s] Value changed, about to setValue and invokeCallback\n" % (_ts(), self.__syncId))
                    sys.stderr.flush()
                    self._currentValue = newValue
                    self.setValue(newValue)
                    self.__invokeCallback(newValue)
            else:
                self.__stop_observing_attribute()

    def commandKwArgs(self, new_value):
        self.__commandKwArgs["newValue"] = new_value
        return self.__commandKwArgs

    def setValue(self, new_value):
        sys.stderr.write("[%s][SYNC:%s] setValue called, new_value=%s, entry=%s\n" % (
            _ts(), self.__syncId, new_value, self._entry))
        sys.stderr.flush()
        self._entry.SetValue(new_value)
        sys.stderr.write("[%s][SYNC:%s] setValue complete\n" % (_ts(), self.__syncId))
        sys.stderr.flush()

    def getValue(self):
        return self._entry.GetValue()

    def __invokeCallback(self, value):
        sys.stderr.write("[%s][SYNC:%s] __invokeCallback called, callback=%s\n" % (_ts(), self.__syncId, self.__callback))
        sys.stderr.flush()
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
