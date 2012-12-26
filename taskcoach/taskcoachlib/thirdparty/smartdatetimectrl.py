#!/usr/bin/python-32

# This file is part of smartdatetimectrl.

#    smartdatetimectrl is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.

#    smartdatetimectrl is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.

#    You should have received a copy of the GNU General Public License
#    along with smartdatetimectrl.  If not, see <http://www.gnu.org/licenses/>.

import wx, math, time, re, datetime, calendar
import wx.lib.platebtn as pbtn


# We expect the user application to inject _ into __builtins__
try:
    _
except NameError:
    _ = lambda x: x


def defaultEncodingName():
    return wx.Locale.GetSystemEncodingName() or 'utf-8'


def decodeSystemString(s):
    if isinstance(s, unicode):
        return s
    encoding = defaultEncodingName()
    # Python does not define the windows_XXX aliases for every code page...
    if encoding.startswith('windows-'):
        encoding = 'cp' + encoding[8:]
    if not encoding:
        encoding = 'utf-8'
    return s.decode(encoding, 'ignore')


class NullField(object):
    def __getattr__(self, name):
        return self
    def __call__(self, *args, **kwargs):
        return self
    def GetValue(self):
        return 0
NullField = NullField()


class FormatCharacter(object):
    valueName = None

    def __init__(self, c):
        pass

    @classmethod
    def matches(self, c):
        raise NotImplementedError

    @classmethod
    def keywordArgs(klass, kwargs):
        if klass.valueName is not None:
            return dict(value=kwargs.pop(klass.valueName))
        try:
            return dict(value=kwargs['values'].pop(0))
        except KeyError:
            return KeyError('No values defined for unnamed field %s' % klass)

    def append(self, c):
        raise NotImplementedError

    def createField(self, *args, **kwargs):
        raise NotImplementedError


class SingleFormatCharacter(FormatCharacter):
    character = None

    @classmethod
    def matches(self, c):
        return c == self.character

    def append(self, c):
        pass


class AnyFormatCharacter(FormatCharacter):
    def __init__(self, c):
        self.__value = c

    @classmethod
    def matches(self, c):
        return True

    def append(self, c):
        self.__value += c

    @classmethod
    def keywordArgs(klass, kwargs):
        return dict()

    def createField(self, *args, **kwargs):
        return self.__value


class Field(object):
    def __init__(self, *args, **kwargs):
        self.__value = kwargs.pop('value')
        self.__observer = kwargs.pop('observer')
        self.__choices = kwargs.pop('choices', None)

        super(Field, self).__init__(*args, **kwargs)

    def Observer(self):
        return self.__observer

    def GetValue(self):
        return self.__value

    def SetValue(self, value, notify=False):
        if notify:
            value = self.Observer().ValidateChange(self, value)
            if value is None:
                return

        self.__value = value
        self.Observer().Refresh()

    def GetChoices(self):
        return self.__choices

    def SetChoices(self, choices):
        self.__choices = choices

    def GetCurrentChoice(self):
        for idx, choice in enumerate(self.__choices):
            if choice == self.GetValue():
                return idx
        return None

    def SetCurrentChoice(self, value):
        self.SetValue(value, notify=True)

    # Methods to override

    def GetExtent(self, dc):
        raise NotImplementedError

    def PaintValue(self, dc, x, y, w, h):
        raise NotImplementedError

    def ResetState(self):
        pass

    def HandleKey(self, key):
        raise NotImplementedError

    def OnClick(self):
        pass


class FieldValueChangeEvent(wx.PyCommandEvent):
    type_ = None

    def __init__(self, owner, newValue, *args, **kwargs):
        super(FieldValueChangeEvent, self).__init__(self.type_)
        self.__newValue = newValue
        self.__vetoed = False
        self.SetEventObject(owner)

    def Clone(self):
        event = self.__class__(self.GetEventObject(), self.__newValue)
        event.__vetoed = self.__vetoed
        return event

    def GetValue(self):
        return self.__newValue

    def Veto(self):
        self.__vetoed = True

    def IsVetoed(self):
        return self.__vetoed


wxEVT_ENTRY_CHOICE_SELECTED = wx.NewEventType()
EVT_ENTRY_CHOICE_SELECTED = wx.PyEventBinder(wxEVT_ENTRY_CHOICE_SELECTED)

class EntryChoiceSelectedEvent(FieldValueChangeEvent):
    type_ = wxEVT_ENTRY_CHOICE_SELECTED

    def __init__(self, owner, value, field=None, **kwargs):
        super(EntryChoiceSelectedEvent, self).__init__(owner, value, **kwargs)
        self.__field = field

    def GetField(self):
        return self.__field


class Entry(wx.Panel):
    MARGIN = 3
    formats = [AnyFormatCharacter]

    def __init__(self, *args, **kwargs):
        fmt = kwargs.pop('format')

        format = list()
        state = None

        for c in fmt:
            for klass in self.formats:
                if klass.matches(c):
                    break
            if state is not None and state.__class__ is klass:
                state.append(c)
            elif state is None:
                state = klass(c)
            else:
                format.append((state, state.keywordArgs(kwargs)))
                state = klass(c)
        format.append((state, state.keywordArgs(kwargs)))

        kwargs.pop('values', None)
        for aFormat in self.formats:
            if aFormat.valueName is not None:
                kwargs.pop(aFormat.valueName, 0)

        if '__WXMSW__' in wx.PlatformInfo:
            kwargs['style'] = wx.WANTS_CHARS
        super(Entry, self).__init__(*args, **kwargs)

        dc = wx.ClientDC(self)

        self.__focus = None
        self.__forceFocus = False
        self.__fields = list()
        self.__widgets = list()
        self.__namedFields = dict()
        self.__popup = None
        self.__focusStamp = time.time()

        minW = 0
        minH = 0
        curX = self.MARGIN

        for state, keywords in format:
            field = state.createField(observer=self, **keywords)
            if state.valueName is not None:
                self.__namedFields[state.valueName] = field

            if isinstance(field, (str, unicode)):
                tw, th = dc.GetTextExtent(field)
                self.__widgets.append((field, curX, self.MARGIN, tw, th))
                minW += tw
                minH = max(minH, th)
                curX += tw + self.MARGIN
            else:
                self.__fields.append(field)
                w, h = field.GetExtent(dc)
                self.__widgets.append((field, curX, self.MARGIN, w, h))
                minW += w
                minH = max(minH, h)
                curX += w + self.MARGIN

        self.__SetFocus(self.__widgets[0][0])

        self.SetMinSize(wx.Size(minW + (len(self.__widgets) + 1) * self.MARGIN, minH + 2 * self.MARGIN))

        timerId = wx.NewId()
        self.__timer = wx.Timer(self, timerId)
        wx.EVT_TIMER(self, timerId, self.OnTimer)

        wx.EVT_PAINT(self, self.OnPaint)
        wx.EVT_KEY_DOWN(self, self.OnKeyDown)
        wx.EVT_LEFT_UP(self, self.OnLeftUp)
        wx.EVT_KILL_FOCUS(self, self.OnKillFocus)
        wx.EVT_SET_FOCUS(self, self.OnSetFocus)

    def Cleanup(self):
        # It's complicated.
        try:
            self.DismissPopup()
        except wx.PyDeadObjectError:
            pass

    def ForceFocus(self, force=True):
        self.__forceFocus = force
        self.Refresh()

    def OnTimer(self, event):
        if self.__focus is not None:
            self.__focus.ResetState()

    def StartTimer(self):
        self.__timer.Start(750, True)

    def __SetFocus(self, field):
        if self.__popup is not None:
            self.__popup[0].Dismiss()

        if self.__focus is not None:
            self.__timer.Stop()
            self.__focus.ResetState()

        self.__focus = field
        self.Refresh()

    def DismissPopup(self):
        if self.__popup is not None:
            self.__popup[0].Dismiss()

    def OnPopupDismiss(self, event):
        self.__popup = None
        self.ForceFocus(False)
        event.Skip()

    def OnKillFocus(self, event):
        self.Refresh()
        event.Skip()

    def OnSetFocus(self, event):
        self.__focusStamp = time.time()
        self.Refresh()
        event.Skip()

    @classmethod
    def addFormat(klass, format):
        klass.formats.insert(0, format)

    def Fields(self):
        return self.__fields[:]

    def Field(self, name):
        return self.__namedFields.get(name, NullField)

    def Position(self, field):
        for widget, x, y, w, h in self.__widgets:
            if widget == field:
                return x, y, w, h

    def GetValue(self):
        value = list()
        for field in self.__fields:
            value.append(field.GetValue())
        return tuple(value)

    def SetValue(self, value):
        value = list(value)
        for index, field in enumerate(self.__fields):
            field.SetValue(value[index])

    def ValidateChange(self, field, value):
        return value

    def ValidateIncrement(self, field, value):
        return value

    def ValidateDecrement(self, field, value):
        return value

    def OnPaint(self, event):
        dc = wx.PaintDC(self)
        dc.SetBackground(wx.WHITE_BRUSH)
        dc.Clear()
        dc.SetBrush(wx.TRANSPARENT_BRUSH)
        w, h = self.GetClientSizeTuple()
        dc.SetPen(wx.Pen(wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNFACE), width=3))
        dc.DrawLine(0, 0, w, 0)
        dc.DrawLine(0, 0, 0, h)
        dc.SetPen(wx.Pen(wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNSHADOW), width=3))
        dc.DrawLine(w, 0, w, h)
        dc.DrawLine(0, h, w, h)

        if self.IsEnabled():
            for widget, x, y, w, h in self.__widgets:
                if isinstance(widget, (str, unicode)):
                    dc.SetTextForeground(wx.BLACK)
                    dc.DrawText(widget, x, y)
                else:
                    if widget == self.__focus and (self.FindFocus() == self or self.__forceFocus):
                        color = wx.SystemSettings.GetColour(wx.SYS_COLOUR_HIGHLIGHT)
                        dc.SetPen(wx.Pen(color))
                        dc.SetBrush(wx.Brush(color))
                        dc.DrawRoundedRectangle(x, y, w, h, 3)
                        dc.SetTextForeground(wx.SystemSettings.GetColour(wx.SYS_COLOUR_HIGHLIGHTTEXT))
                    else:
                        dc.SetTextForeground(wx.BLACK)
                    widget.PaintValue(dc, x, y, w, h)
        else:
            text = u'N/A'
            tw, th = dc.GetTextExtent(text)
            dc.SetTextForeground(wx.LIGHT_GREY)
            dc.DrawText(text, (w - tw) / 2, (h - th) / 2)

    def FocusNext(self):
        if self.__focus is not None:
            self.__SetFocus(self.__fields[(self.__fields.index(self.__focus) + 1) % len(self.__fields)])

    def OnKeyDown(self, event):
        if event.GetKeyCode() == wx.WXK_TAB:
            self.DismissPopup()
            self.Navigate(not event.ShiftDown())
            return

        if event.GetKeyCode() in [wx.WXK_RIGHT, wx.WXK_DECIMAL, wx.WXK_NUMPAD_DECIMAL] or event.GetUnicodeKey() == ord('.'):
            self.FocusNext()
        elif event.GetKeyCode() == wx.WXK_LEFT:
            if self.__focus is not None:
                self.__SetFocus(self.__fields[(self.__fields.index(self.__focus) + len(self.__fields) - 1) % len(self.__fields)])
        elif event.GetKeyCode() == wx.WXK_ESCAPE and self.__popup is not None:
            self.__popup[0].Dismiss()
        elif event.GetKeyCode() == wx.WXK_RETURN and self.__popup is None and \
            self.__focus is not None:
            self.PopupChoices(self.__focus)
            self.ForceFocus()
        else:
            if self.__focus is not None and self.__focus.HandleKey(event):
                self.StartTimer()
                return
            if not self.GetParent().HandleKey(event):
                event.Skip()

    def OnLeftUp(self, event):
        for widget, x, y, w, h in self.__widgets:
            if event.GetX() >= x and event.GetX() < x + w and event.GetY() >= y and event.GetY() < y + h:
                if not isinstance(widget, (str, unicode)):
                    oldFocus = self.__focus
                    self.__SetFocus(widget)
                    # the __focusStamp stuff is there so that choices don't show when clicking to set focus to
                    # the whole control
                    if oldFocus == widget and time.time() - self.__focusStamp >= 0.05:
                        self.PopupChoices(widget)
                        self.ForceFocus()
                    widget.OnClick()
                    break
        else:
            self.__SetFocus(None)
        self.Refresh()

    def PopupChoices(self, widget):
        if widget.GetChoices() is not None:
            x, y, w, h = self.Position(widget)
            self.__popup = (_MultipleChoicesPopup(widget.GetChoices(),
                                                  widget.GetCurrentChoice(),
                self), widget)
            self.__popup[0].Popup(self.ClientToScreen(wx.Point(x, y + h)))
            EVT_POPUP_DISMISS(self.__popup[0], self.OnPopupDismiss)
            EVT_ENTRY_CHOICE_SELECTED(self.__popup[0], self.__OnChoiceSelected)

    def __OnChoiceSelected(self, event):
        popup, field = self.__popup
        evt = EntryChoiceSelectedEvent(self, event.GetValue(), field=field)
        self.ProcessEvent(evt)
        if not evt.IsVetoed():
            field.SetCurrentChoice(evt.GetValue())
        popup.Dismiss()


class NumericField(Field):
    class NumericFormatCharacter(FormatCharacter):
        def __init__(self, c):
            self.__width = 1

        @classmethod
        def matches(self, c):
            return c == '#'

        def append(self, c):
            self.__width += 1

        def createField(self, *args, **kwargs):
            kwargs['width'] = self.__width
            return NumericField(*args, **kwargs)

    Entry.addFormat(NumericFormatCharacter)

    def __init__(self, *args, **kwargs):
        self.__width = kwargs.pop('width')
        self.__state = 0

        super(NumericField, self).__init__(*args, **kwargs)

    def GetExtent(self, dc):
        return dc.GetTextExtent('0' * self.__width)

    def SetCurrentChoice(self, choice):
        super(NumericField, self).SetCurrentChoice(int(choice))

    def PaintValue(self, dc, x, y, w, h):
        dc.DrawText(('%%0%dd' % self.__width) % self.GetValue(), x, y)

    def ResetState(self):
        self.__state = 0

    def HandleKey(self, event):
        if event.GetKeyCode() == wx.WXK_UP:
            value = self.Observer().ValidateIncrement(self, self.GetValue() + 1)
            if value is None:
                return False
            self.SetValue(value)
            return True

        if event.GetKeyCode() == wx.WXK_DOWN:
            value = self.Observer().ValidateDecrement(self, self.GetValue() - 1)
            if value is None:
                return False
            self.SetValue(value)
            return True

        if event.GetKeyCode() >= wx.WXK_NUMPAD0 and event.GetKeyCode() <= wx.WXK_NUMPAD9:
            number = event.GetKeyCode() - wx.WXK_NUMPAD0
        else:
            number = event.GetUnicodeKey() - ord('0')

        if number >= 0 and number <= 9:
            if self.__state == 0:
                self.__state = 1
                self.SetValue(number, notify=True)
            elif self.__state == 1:
                self.SetValue((self.GetValue() * 10 + number) % int(math.pow(10, self.__width)), notify=True)
            return True

        return False


class EnumerationField(Field):
    def __init__(self, *args, **kwargs):
        self.__choices = kwargs['choices']
        super(EnumerationField, self).__init__(*args, **kwargs)

    def SetCurrentChoice(self, value):
        super(EnumerationField, self).SetCurrentChoice(['AM', 'PM'].index(value))

    def GetCurrentChoice(self):
        return self.GetValue()

    def GetExtent(self, dc):
        maxW = maxH = 0
        for choice in self.__choices:
            tw, th = dc.GetTextExtent(choice)
            maxW = max(maxW, tw)
            maxH = max(maxH, th)
        return maxW, maxH

    def PaintValue(self, dc, x, y, w, h):
        dc.DrawText(self.__choices[self.GetValue()], x, y)

    def HandleKey(self, event):
        if event.GetKeyCode() == wx.WXK_UP:
            self.SetValue((self.GetValue() - 1 + len(self.__choices)) % len(self.__choices), notify=True)
            return True
        if event.GetKeyCode() == wx.WXK_DOWN:
            self.SetValue((self.GetValue() + 1) % len(self.__choices), notify=True)
            return True
        return False


#=======================================
#{ Time

def Convert24To12(hour):
    if hour == 0:
        value = (12, 0)
    elif hour < 12:
        value = (hour, 0)
    elif hour == 12:
        value = (hour, 1)
    else:
        value = (hour - 12, 1)
    return value


def Convert12To24(hour, ampm):
    if hour == 12:
        if ampm:
            value = 12
        else:
            value = 0
    else:
        value = hour + ampm * 12
    return value


class AMPMField(EnumerationField):
    class AMPMFormatCharacter(SingleFormatCharacter):
        character = 'p'
        valueName = 'ampm'

        def createField(self, *args, **kwargs):
            kwargs['choices'] = ['AM', 'PM']
            return AMPMField(*args, **kwargs)

    Entry.addFormat(AMPMFormatCharacter)


class HourField(NumericField):
    pass


class MinuteField(NumericField):
    pass


class SecondField(NumericField):
    pass


wxEVT_TIME_CHANGE = wx.NewEventType()
EVT_TIME_CHANGE = wx.PyEventBinder(wxEVT_TIME_CHANGE)
wxEVT_TIME_NEXT_DAY = wx.NewEventType()
EVT_TIME_NEXT_DAY = wx.PyEventBinder(wxEVT_TIME_NEXT_DAY)
wxEVT_TIME_PREV_DAY = wx.NewEventType()
EVT_TIME_PREV_DAY = wx.PyEventBinder(wxEVT_TIME_PREV_DAY)
wxEVT_TIME_CHOICES_CHANGE = wx.NewEventType()
EVT_TIME_CHOICES_CHANGE = wx.PyEventBinder(wxEVT_TIME_CHOICES_CHANGE)


class TimeChangeEvent(FieldValueChangeEvent):
    type_ = wxEVT_TIME_CHANGE

class TimeNextDayEvent(FieldValueChangeEvent):
    type_ = wxEVT_TIME_NEXT_DAY

class TimePrevDayEvent(FieldValueChangeEvent):
    type_ = wxEVT_TIME_PREV_DAY

class TimeChoicesChangedEvent(FieldValueChangeEvent):
    type_ = wxEVT_TIME_CHOICES_CHANGE


class TimeEntry(Entry):
    class HourFormatCharacter(SingleFormatCharacter):
        character = 'H'
        valueName = 'hour'

        def createField(self, *args, **kwargs):
            kwargs['width'] = 2
            return HourField(*args, **kwargs)

    class MinuteFormatCharacter(SingleFormatCharacter):
        character = 'M'
        valueName = 'minute'

        def createField(self, *args, **kwargs):
            kwargs['width'] = 2
            return MinuteField(*args, **kwargs)

    class SecondFormatCharacter(SingleFormatCharacter):
        character = 'S'
        valueName = 'second'

        def createField(self, *args, **kwargs):
            kwargs['width'] = 2
            return SecondField(*args, **kwargs)

    Entry.addFormat(HourFormatCharacter)
    Entry.addFormat(MinuteFormatCharacter)
    Entry.addFormat(SecondFormatCharacter)

    def __init__(self, *args, **kwargs):
        fmt = kwargs.pop('format', lambda x: x.strftime('%H:%M:%S'))
        pattern = fmt(datetime.time(hour=11, minute=33, second=44))
        pattern = re.sub('3+', 'M', pattern)
        pattern = re.sub('1+', 'H', pattern)
        pattern = re.sub('4+', 'S', pattern)

        # Work around a bug in wx...
        if time.strftime('%p') == '' and fmt(datetime.time(hour=1, minute=0)) == fmt(datetime.time(hour=13, minute=0)):
            ampm = True
            # We can't actually guess where it should be so put it at the end.
            if not pattern.endswith(' '):
                pattern += ' '
            pattern += 'p'
        else:
            ampm = pattern.lower().find('am') != -1
            pattern = re.sub('(?i)am', 'p', pattern)

        self.__value = datetime.time(hour=kwargs.get('hour', 0), minute=kwargs.get('minute', 0), second=kwargs.get('second', 0))
        self.__minuteDelta = kwargs.pop('minuteDelta', 10)
        self.__secondDelta = kwargs.pop('secondDelta', 10)
        self.__startHour = kwargs.pop('startHour', 0)
        self.__endHour = kwargs.pop('endHour', 24)

        self.__relChoices = '60,120,180'
        self.__choiceStart = None
        self.__choicePopup = None

        if ampm:
            kwargs['hour'], kwargs['ampm'] = Convert24To12(kwargs['hour'])

        kwargs['format'] = pattern
        super(TimeEntry, self).__init__(*args, **kwargs)

        EVT_ENTRY_CHOICE_SELECTED(self, self.__OnHourSelected)

    def OnKeyDown(self, event):
        if event.GetUnicodeKey() == ord(':'):
            self.FocusNext()
            event.Skip()
        else:
            return super(TimeEntry, self).OnKeyDown(event)

    def DismissPopup(self):
        super(TimeEntry, self).DismissPopup()
        if self.__choicePopup is not None:
            self.__choicePopup.Dismiss()

    def EnableChoices(self, enabled=True):
        if enabled:
            if self.Field('ampm') is NullField:
                hours = range(self.__startHour, min(self.__endHour + 1, 24))
            else:
                hours = list()
                for hour in xrange(self.__startHour, min(self.__endHour + 1, 24)):
                    hr, ampm = Convert24To12(hour)
                    hours.append('%02d %s' % (hr, ['AM', 'PM'][ampm]))
            self.Field('hour').SetChoices(hours)
            self.Field('minute').SetChoices(range(0, 60, self.__minuteDelta))
            self.Field('second').SetChoices(range(0, 60, self.__secondDelta))
        else:
            self.Field('hour').SetChoices(None)
            self.Field('minute').SetChoices(None)
            self.Field('second').SetChoices(None)
            self.DismissPopup()

    def __OnHourSelected(self, event):
        if self.Field('ampm') is not NullField and event.GetField() is self.Field('hour'):
            hour, ampm = event.GetValue().split()
            self.Field('hour').SetValue(int(hour))
            self.Field('ampm').SetValue(dict(am=0, pm=1)[ampm.lower()])
            event.Veto()

    def LoadChoices(self, choices):
        self.__relChoices = choices

    def SetRelativeChoicesStart(self, start=None):
        self.__choiceStart = start

    def GetRelativeChoicesStart(self):
        return self.__choiceStart

    def PopupRelativeChoices(self):
        self.__choicePopup = _RelativeChoicePopup(self.__choiceStart, self, wx.ID_ANY, choices=self.__relChoices)
        w, h = self.GetClientSizeTuple()
        self.__choicePopup.Popup(self.ClientToScreen(wx.Point(0, h)))
        EVT_POPUP_DISMISS(self.__choicePopup, self.OnRelativePopupDismiss)

    def OnRelativePopupDismiss(self, event):
        self.__choicePopup = None
        event.Skip()

    def OnChoicesChanged(self, sender):
        self.__relChoices = sender.SaveChoices()
        self.ProcessEvent(TimeChoicesChangedEvent(self, self.__relChoices))

    def SetDateTime(self, dateTime, notify=False):
        self.GetParent().SetDateTime(dateTime, notify=notify)

    def GetTime(self):
        hour = self.Field('hour').GetValue()
        minute = self.Field('minute').GetValue()
        second = self.Field('second').GetValue()

        if self.Field('ampm') is not NullField:
            hour = Convert12To24(hour, self.Field('ampm').GetValue())

        return datetime.time(hour=hour, minute=minute, second=second)

    def SetTime(self, value):
        hour = value.hour
        if self.Field('ampm') is not NullField:
            hour, ampm = Convert24To12(value.hour)
            self.Field('ampm').SetValue(ampm)
        self.Field('hour').SetValue(hour)
        self.Field('minute').SetValue(value.minute)
        self.Field('second').SetValue(value.second)

    def __NewValue(self, **kwargs):
        keywords = dict(hour=self.Field('hour').GetValue(), minute=self.Field('minute').GetValue(), second=self.Field('second').GetValue())
        if self.Field('ampm') is not NullField:
            keywords['hour'] = Convert12To24(keywords['hour'], kwargs.pop('ampm', self.Field('ampm').GetValue()))
        keywords.update(kwargs)
        return datetime.time(**keywords)

    def ValidateChange(self, field, value):
        if field == self.Field('hour'):
            return self.ValidateHourChange(value)
        elif field == self.Field('minute'):
            return self.ValidateMinuteChange(value)
        elif field == self.Field('second'):
            return self.ValidateSecondChange(value)
        elif field == self.Field('ampm'):
            return self.ValidateAMPMChange(value)
        return None

    def ValidateIncrement(self, field, value):
        if field == self.Field('hour'):
            return self.ValidateHourIncrement(value)
        elif field == self.Field('minute'):
            return self.ValidateMinuteIncrement(value)
        elif field == self.Field('second'):
            return self.ValidateSecondIncrement(value)
        elif field == self.Field('ampm'):
            return self.ValidateAMPMChange(value)
        return None

    def ValidateDecrement(self, field, value):
        if field == self.Field('hour'):
            return self.ValidateHourDecrement(value)
        elif field == self.Field('minute'):
            return self.ValidateMinuteDecrement(value)
        elif field == self.Field('second'):
            return self.ValidateSecondDecrement(value)
        elif field == self.Field('ampm'):
            return self.ValidateAMPMChange(value)
        return None

    def ValidateHourChange(self, value):
        if self.Field('ampm') is NullField:
            if value < 0 or value > 23:
                wx.Bell()
                return None
        else:
            if value < 1 or value > 12:
                wx.Bell()
                return None
            value = Convert12To24(value, self.Field('ampm').GetValue())

        evt = TimeChangeEvent(self, self.__NewValue(hour=value))
        self.ProcessEvent(evt)
        if evt.IsVetoed():
            wx.Bell()
        else:
            self.SetTime(evt.GetValue())
        return None

    def __ValidateIncrementDecrement(self, delta, evtClass):
        oldTime = self.GetTime()
        oldDate = datetime.date(2012, 10, 10) # Dummy
        newDateTime = datetime.datetime.combine(oldDate, oldTime) + delta
        if oldDate != newDateTime.date():
            evt = evtClass(self, newDateTime.time())
        else:
            evt = TimeChangeEvent(self, newDateTime.time())

        self.ProcessEvent(evt)
        if evt.IsVetoed():
            wx.Bell()
        else:
            self.SetTime(evt.GetValue())

    def ValidateHourIncrement(self, value):
        self.__ValidateIncrementDecrement(datetime.timedelta(hours=1), TimeNextDayEvent)

    def ValidateHourDecrement(self, value):
        self.__ValidateIncrementDecrement(-datetime.timedelta(hours=1), TimePrevDayEvent)

    def ValidateMinuteChange(self, value):
        if value < 0 or value > 59:
            wx.Bell()
            return None

        evt = TimeChangeEvent(self, self.__NewValue(minute=value))
        self.ProcessEvent(evt)
        if evt.IsVetoed():
            wx.Bell()
        else:
            self.SetTime(evt.GetValue())
        return None

    def ValidateMinuteIncrement(self, value):
        self.__ValidateIncrementDecrement(datetime.timedelta(minutes=1), TimeNextDayEvent)

    def ValidateMinuteDecrement(self, value):
        self.__ValidateIncrementDecrement(-datetime.timedelta(minutes=1), TimePrevDayEvent)

    def ValidateSecondChange(self, value):
        if value < 0 or value > 59:
            wx.Bell()
            return None

        evt = TimeChangeEvent(self, self.__NewValue(second=value))
        self.ProcessEvent(evt)
        if evt.IsVetoed():
            wx.Bell()
        else:
            self.SetTime(evt.GetValue())
        return None

    def ValidateSecondIncrement(self, value):
        self.__ValidateIncrementDecrement(datetime.timedelta(seconds=1), TimeNextDayEvent)

    def ValidateSecondDecrement(self, value):
        self.__ValidateIncrementDecrement(-datetime.timedelta(seconds=1), TimePrevDayEvent)

    def ValidateAMPMChange(self, value):
        evt = TimeChangeEvent(self, self.__NewValue(ampm=value))
        self.ProcessEvent(evt)
        if evt.IsVetoed():
            wx.Bell()
        else:
            self.SetTime(evt.GetValue())
        return None

#}

#=======================================
#{ Date

def MaxDayOfMonth(year, month):
    return calendar.monthrange(year, month)[1]


wxEVT_DATE_CHANGE = wx.NewEventType()
EVT_DATE_CHANGE = wx.PyEventBinder(wxEVT_DATE_CHANGE)

class DateChangeEvent(FieldValueChangeEvent):
    type_ = wxEVT_DATE_CHANGE


class YearField(NumericField):
    pass


class MonthField(NumericField):
    pass


class DayField(NumericField):
    pass


class DateEntry(Entry):
    class YearFormatCharacter(SingleFormatCharacter):
        character = 'y'
        valueName = 'year'

        def createField(self, *args, **kwargs):
            kwargs['width'] = 4 # No support for 2-digits year
            return YearField(*args, **kwargs)

    class MonthFormatCharacter(SingleFormatCharacter):
        character = 'm'
        valueName = 'month'

        def createField(self, *args, **kwargs):
            kwargs['width'] = 2
            return MonthField(*args, **kwargs)

    class DayFormatCharacter(SingleFormatCharacter):
        character = 'd'
        valueName = 'day'

        def createField(self, *args, **kwargs):
            kwargs['width'] = 2
            return DayField(*args, **kwargs)

    Entry.addFormat(YearFormatCharacter)
    Entry.addFormat(MonthFormatCharacter)
    Entry.addFormat(DayFormatCharacter)

    def __init__(self, *args, **kwargs):
        fmt = kwargs.pop('format', lambda x: x.strftime('%x'))
        fmt = fmt(datetime.date(year=3333, day=22, month=11))
        fmt = re.sub('1+', 'm', fmt)
        fmt = re.sub('2+', 'd', fmt)
        fmt = re.sub('3+', 'y', fmt)
        kwargs['format'] = fmt

        self.__value = datetime.date(year=kwargs['year'], month=kwargs['month'], day=kwargs['day'])

        super(DateEntry, self).__init__(*args, **kwargs)

        self.__calendar = None

        wx.EVT_LEFT_UP(self, self.__OnLeftUp)
        if '__WXMAC__' in wx.PlatformInfo:
            wx.EVT_KILL_FOCUS(self, self.__OnKillFocus)

    def DismissPopup(self):
        super(DateEntry, self).DismissPopup()
        if self.__calendar is not None:
            self.__calendar.Dismiss()

    def __OnKillFocus(self, event):
        self.DismissPopup()
        event.Skip()

    def OnKeyDown(self, event):
        if event.GetKeyCode() == wx.WXK_TAB and self.__calendar is not None:
            self.__calendar.Dismiss()
        super(DateEntry, self).OnKeyDown(event)

    def OnKeyDown(self, event):
        if event.GetUnicodeKey() == ord('/'):
            self.FocusNext()
            event.Skip()
        else:
            return super(DateEntry, self).OnKeyDown(event)

    def GetDate(self):
        return datetime.date(year=self.Field('year').GetValue(),
                             month=self.Field('month').GetValue(),
                             day=self.Field('day').GetValue())

    def SetDate(self, dt, notify=False):
        if notify:
            evt = DateChangeEvent(self, dt)
            self.ProcessEvent(evt)
            if evt.IsVetoed():
                wx.Bell()
                return
        self.Field('year').SetValue(dt.year)
        self.Field('month').SetValue(dt.month)
        self.Field('day').SetValue(dt.day)

        if self.__calendar is not None:
            self.__calendar.SetSelection(self.GetDate())

    def __NewValue(self, **kwargs):
        keywords = dict(year=self.Field('year').GetValue(),
                        month=self.Field('month').GetValue(),
                        day=self.Field('day').GetValue())
        keywords.update(kwargs)
        return datetime.date(**keywords)

    def ValidateChange(self, field, value):
        if field == self.Field('year'):
            return self.ValidateYearChange(value)
        elif field == self.Field('month'):
            return self.ValidateMonthChange(value)
        elif field == self.Field('day'):
            return self.ValidateDayChange(value)
        return None

    def ValidateYearChange(self, value):
        if value < 1 or value > 9999: # This should let us breath.
            wx.Bell()
            return None

        evt = DateChangeEvent(self, self.__NewValue(year=value,
                                                    month=self.Field('month').GetValue(),
                                                    day=min(MaxDayOfMonth(value, self.Field('month').GetValue()),
                                                            self.Field('day').GetValue())))
        self.ProcessEvent(evt)
        if evt.IsVetoed():
            wx.Bell()
        else:
            self.SetDate(evt.GetValue())
        return None

    def ValidateIncrement(self, field, value):
        if field == self.Field('year'):
            return self.ValidateYearChange(value)
        elif field == self.Field('month'):
            return self.ValidateMonthIncrement(value)
        elif field == self.Field('day'):
            return self.ValidateDayIncrement(value)
        return None

    def ValidateDecrement(self, field, value):
        if field == self.Field('year'):
            return self.ValidateYearChange(value)
        elif field == self.Field('month'):
            return self.ValidateMonthDecrement(value)
        elif field == self.Field('day'):
            return self.ValidateDayDecrement(value)

    def ValidateMonthChange(self, value):
        if value < 1 or value > 12:
            wx.Bell()
            return None

        evt = DateChangeEvent(self, self.__NewValue(month=value,
                                                    day=min(MaxDayOfMonth(self.Field('year').GetValue(), value),
                                                            self.Field('day').GetValue())))
        self.ProcessEvent(evt)
        if evt.IsVetoed():
            wx.Bell()
        else:
            self.SetDate(evt.GetValue())
        return None

    def ValidateMonthIncrement(self, value):
        if value == 13:
            if self.Field('year').GetValue() == 9999:
                wx.Bell()
                return None
            evt = DateChangeEvent(self, self.__NewValue(year=self.Field('year').GetValue() + 1,
                                                        month=1,
                                                        day=min(MaxDayOfMonth(self.Field('year').GetValue() + 1, 1),
                                                                self.Field('day').GetValue())))
        else:
            evt = DateChangeEvent(self, self.__NewValue(month=value,
                                                        day=min(MaxDayOfMonth(self.Field('year').GetValue(), value),
                                                                self.Field('day').GetValue())))

        self.ProcessEvent(evt)
        if evt.IsVetoed():
            wx.Bell()
        else:
            self.SetDate(evt.GetValue())
        return None

    def ValidateMonthDecrement(self, value):
        if value == 0:
            if self.Field('year').GetValue() == 1:
                wx.Bell()
                return None
            evt = DateChangeEvent(self, self.__NewValue(year=self.Field('year').GetValue() - 1,
                                                        month=12,
                                                        day=min(MaxDayOfMonth(self.Field('year').GetValue() - 1, 12),
                                                                self.Field('day').GetValue())))
        else:
            evt = DateChangeEvent(self, self.__NewValue(month=value,
                                                        day=min(MaxDayOfMonth(self.Field('year').GetValue(), value),
                                                                self.Field('day').GetValue())))

        self.ProcessEvent(evt)
        if evt.IsVetoed():
            wx.Bell()
        else:
            self.SetDate(evt.GetValue())
        return None

    def ValidateDayChange(self, value):
        if value < 1 or value > MaxDayOfMonth(self.Field('year').GetValue(), self.Field('month').GetValue()):
            wx.Bell()
            return None

        evt = DateChangeEvent(self, self.__NewValue(day=value))
        self.ProcessEvent(evt)
        if evt.IsVetoed():
            wx.Bell()
        else:
            self.SetDate(evt.GetValue())
        return None

    def ValidateDayIncrement(self, value):
        if value > MaxDayOfMonth(self.Field('year').GetValue(), self.Field('month').GetValue()):
            if self.Field('month').GetValue() == 12:
                if self.Field('year').GetValue() == 9999:
                    wx.Bell()
                    return None
                evt = DateChangeEvent(self, self.__NewValue(year=self.Field('year').GetValue() + 1,
                                                            month=1, day=1))
            else:
                evt = DateChangeEvent(self, self.__NewValue(month=self.Field('month').GetValue() + 1,
                                                            day=1))
        else:
            evt = DateChangeEvent(self, self.__NewValue(day=value))

        self.ProcessEvent(evt)
        if evt.IsVetoed():
            wx.Bell()
        else:
            self.SetDate(evt.GetValue())
        return None

    def ValidateDayDecrement(self, value):
        if value == 0:
            if self.Field('month').GetValue() == 1:
                if self.Field('year').GetValue() == 1:
                    wx.Bell()
                    return None
                evt = DateChangeEvent(self, self.__NewValue(year=self.Field('year').GetValue() - 1,
                                                            month=12,
                                                            day=MaxDayOfMonth(self.Field('year').GetValue() - 1, 12)))
            else:
                evt = DateChangeEvent(self, self.__NewValue(month=self.Field('month').GetValue() - 1,
                                                            day=MaxDayOfMonth(self.Field('year').GetValue(),
                                                                              self.Field('month').GetValue() - 1)))
        else:
            evt = DateChangeEvent(self, self.__NewValue(day=value))

        self.ProcessEvent(evt)
        if evt.IsVetoed():
            wx.Bell()
        else:
            self.SetDate(evt.GetValue())
        return None

    def __OnLeftUp(self, event):
        if self.__calendar is None:
            w, h = self.GetClientSizeTuple()
            x, y = self.GetPositionTuple()
            self.__calendar = _CalendarPopup(self, selection=self.GetDate())
            self.__calendar.Popup(self.GetParent().ClientToScreen(wx.Point(x, y + h)))
            EVT_POPUP_DISMISS(self.__calendar, self.OnCalendarDismissed)
            self.ForceFocus()
        else:
            self.__calendar.Dismiss()

        event.Skip()

    def OnCalendarDismissed(self, event):
        self.__calendar = None
        self.ForceFocus(False)
        event.Skip()


#}

#=======================================
#{ Popup window

wxEVT_POPUP_DISMISS = wx.NewEventType()
EVT_POPUP_DISMISS = wx.PyEventBinder(wxEVT_POPUP_DISMISS)

class PopupDismissEvent(wx.PyCommandEvent):
    def __init__(self, owner):
        super(PopupDismissEvent, self).__init__(wxEVT_POPUP_DISMISS)
        self.SetEventObject(owner)


class _PopupWindow(wx.Dialog):
    """wx.PopupWindow does not exist on Mac and doesn't work well on other plaforms."""

    def __init__(self, *args, **kwargs):
        kwargs['style'] = wx.FRAME_NO_TASKBAR|wx.NO_BORDER|wx.FRAME_FLOAT_ON_PARENT
        if '__WXMSW__' in wx.PlatformInfo:
            kwargs['style'] |= wx.WANTS_CHARS
        super(_PopupWindow, self).__init__(*args, **kwargs)

        self.__interior = wx.Panel(self)

        wx.EVT_ACTIVATE(self, self.OnActivate)
        if '__WXGTK__' in wx.PlatformInfo:
            wx.EVT_KEY_DOWN(self.__interior, self.OnKeyDown)
        else:
            wx.EVT_KEY_DOWN(self, self.OnKeyDown)

        self.Fill(self.__interior)

        sizer = wx.BoxSizer()
        sizer.Add(self.__interior, 1, wx.EXPAND)
        self.SetSizer(sizer)

    def Popup(self, position):
        self.Move(position)
        self.Show()
        if '__WXGTK__' in wx.PlatformInfo:
            self.SetFocus()

    def Dismiss(self):
        self.ProcessEvent(PopupDismissEvent(self))
        self.Destroy()

    def OnKeyDown(self, event):
        if not self.HandleKey(event):
            self.GetParent().OnKeyDown(event)

    def HandleKey(self, event):
        return False

    def OnActivate(self, event):
        if event.GetActive():
            event.Skip()
        else:
            self.Dismiss()

#}

class _RelativeChoicePopup(_PopupWindow):
    def __init__(self, start, *args, **kwargs):
        self.__start = start
        self.__editing = False
        self.__comboState = 0
        self.LoadChoices(kwargs.pop('choices', '60,120,180'))
        super(_RelativeChoicePopup, self).__init__(*args, **kwargs)

    def Fill(self, interior):
        sizer = wx.FlexGridSizer(0, 2)
        sizer.AddGrowableCol(0)
        interior.SetSizer(sizer)
        self.__sizer = sizer
        self.__interior = interior
        self.__Populate()
        self.SetEditing(False)

    def SaveChoices(self):
        return ','.join(map(lambda x: str(int(x.total_seconds() / 60)), self.__choices))

    def LoadChoices(self, choices):
        self.__choices = [datetime.timedelta(minutes=m) for m in map(int, choices.split(','))]

    def __OnComboLeftDown(self, event):
        self.__comboState = 1
        event.Skip()

    def __OnComboFocus(self, event):
        if self.__comboState == 1:
            # Focus after click => popup
            self.__comboState = 2
        else:
            # Popup dismissed
            self.__comboState = 0

    def OnActivate(self, event):
        if self.__comboState != 0 and not event.GetActive():
            event.Skip()
        else:
            super(_RelativeChoicePopup, self).OnActivate(event)

    def __Populate(self):
        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        self.__btnEdit = wx.Button(self.__interior, wx.ID_ANY, _('Edit'))
        wx.EVT_BUTTON(self.__btnEdit, wx.ID_ANY, self.OnEdit)
        hsizer.Add(self.__btnEdit, 0, wx.ALL|wx.ALIGN_CENTRE, 2)

        self.__amountCtrl = wx.SpinCtrl(self.__interior, wx.ID_ANY, '1', min=1)
        hsizer.Add(self.__amountCtrl, 0, wx.ALL, 2)

        self.__unitCtrl = wx.Choice(self.__interior, wx.ID_ANY)
        self.__unitCtrl.Append(_('Week(s)'))
        self.__unitCtrl.Append(_('Day(s)'))
        self.__unitCtrl.Append(_('Hour(s)'))
        self.__unitCtrl.Append(_('Minute(s)'))
        self.__unitCtrl.SetSelection(0)
        hsizer.Add(self.__unitCtrl, 1, wx.ALL|wx.ALIGN_CENTRE, 2)

        if '__WXGTK__' in wx.PlatformInfo:
            wx.EVT_SET_FOCUS(self.__unitCtrl, self.__OnComboFocus)
            wx.EVT_LEFT_DOWN(self.__unitCtrl, self.__OnComboLeftDown)

        self.__sizer.Add(hsizer, flag=wx.EXPAND)

        self.__btnAdd = wx.BitmapButton(self.__interior, wx.ID_ANY, wx.ArtProvider.GetBitmap(wx.ART_ADD_BOOKMARK, wx.ART_BUTTON, (16, 16)))
        self.__sizer.Add(self.__btnAdd, 0, wx.ALL|wx.ALIGN_CENTRE, 3)
        wx.EVT_BUTTON(self.__btnAdd, wx.ID_ANY, self.OnAdd)

        self.__lines = list()
        for line, delta in enumerate(self.__choices):
            idSpan = wx.NewId()
            btn = pbtn.PlateButton(self.__interior, idSpan, self.DeltaRepr(delta), style=pbtn.PB_STYLE_SQUARE)
            self.__sizer.Add(btn, 0, wx.EXPAND)
            wx.EVT_BUTTON(btn, idSpan, self.OnChoose)

            idDel = wx.NewId()
            btn = wx.BitmapButton(self.__interior, idDel, wx.ArtProvider.GetBitmap(wx.ART_DEL_BOOKMARK, wx.ART_BUTTON, (16, 16)))
            self.__sizer.Add(btn, 0, wx.ALL|wx.ALIGN_CENTRE, 3)
            btn.Show(False)
            wx.EVT_BUTTON(btn, idDel, self.OnDel)

            self.__lines.append((delta, idSpan, idDel, btn))

    def Popup(self, position):
        self.Fit()
        super(_RelativeChoicePopup, self).Popup(position)

    def DeltaRepr(self, delta):
        values = list()

        days = delta.days
        if days // 7:
            if days // 7 == 1:
                values.append(_('1 week'))
            else:
                values.append(_('%d weeks') % (days // 7))
        if days % 7:
            if days % 7 == 1:
                values.append(_('1 day'))
            else:
                values.append(_('%d days') % (days % 7))

        minutes = delta.seconds // 60
        if minutes // 60:
            if minutes // 60 == 1:
                values.append(_('1 hour'))
            else:
                values.append(_('%d hours') % (minutes // 60))
        if minutes % 60:
            if minutes % 60 == 1:
                values.append(_('1 minute'))
            else:
                values.append(_('%d minutes') % (minutes % 60))
        return u', '.join(values) + decodeSystemString((self.__start + delta).strftime(' (%c)'))

    def __Empty(self):
        while len(self.__sizer.GetChildren()):
            self.__sizer.Remove(0)
        self.__interior.DestroyChildren()

    def OnChoose(self, event):
        for delta, idSpan, idDel, btn in self.__lines:
            if idSpan == event.GetId():
                self.GetParent().SetDateTime(self.__start + delta, notify=True)
                self.Dismiss()
                break

    def OnEdit(self, event):
        if self.__editing:
            self.GetParent().OnChoicesChanged(self)
        self.SetEditing(not self.__editing)

    def OnDel(self, event):
        for idx, (delta, idSpan, idDel, btn) in enumerate(self.__lines):
            if idDel == event.GetId():
                del self.__choices[idx]
                self.__Empty()
                self.__Populate()
                self.SetEditing(self.__editing)
                break

    def OnAdd(self, event):
        amount = self.__amountCtrl.GetValue()
        if self.__unitCtrl.GetSelection() == 0:
            ns = dict(days=amount * 7)
        elif self.__unitCtrl.GetSelection() == 1:
            ns = dict(days=amount)
        elif self.__unitCtrl.GetSelection() == 2:
            ns = dict(hours=amount)
        else:
            ns = dict(minutes=amount)
        self.__choices.append(datetime.timedelta(**ns))
        self.__choices.sort()
        self.__Empty()
        self.__Populate()
        self.SetEditing(self.__editing)

    def SetEditing(self, editing):
        self.__editing = editing
        self.__btnEdit.SetLabel(_('Done') if self.__editing else _('Edit'))
        self.__amountCtrl.Show(self.__editing)
        self.__unitCtrl.Show(self.__editing)
        self.__btnAdd.Show(self.__editing)
        for delta, idSpan, idDel, btn in self.__lines:
            btn.Show(self.__editing)
        wx.CallAfter(self.Fit)
        wx.CallAfter(self.Refresh)

#=======================================
#{ Calendar popup

class _CalendarPopup(_PopupWindow):
    def __init__(self, *args, **kwargs):
        self.__selection = kwargs.pop('selection')
        self.__year = self.__selection.year
        self.__month = self.__selection.month
        self.__minDate = kwargs.pop('minDate', None)
        self.__maxDate = kwargs.pop('maxDate', None)
        self.__maxDim = None

        super(_CalendarPopup, self).__init__(*args, **kwargs)

    def Fill(self, interior):
        wx.EVT_PAINT(interior, self.OnPaint)
        wx.EVT_LEFT_UP(interior, self.OnLeftUp)
        self.SetClientSize(self.GetExtent(wx.ClientDC(interior)))

    def GetExtent(self, dc):
        W, H = 0, 0
        for month in xrange(1, 13):
            header = datetime.date(year=self.__year, month=month, day=11).strftime('%B %Y')
            tw, th = dc.GetTextExtent(header)
            W = max(W, tw)
            H = max(H, th)
        header = datetime.date(year=self.__year, month=self.__month, day=1).strftime('%B %Y')

        lines = calendar.monthcalendar(self.__year, self.__month)
        self.__maxDim = 0
        for line in lines:
            for day in line:
                tw, th = dc.GetTextExtent('%d' % day)
                self.__maxDim = max(self.__maxDim, tw, th)

        for header in calendar.weekheader(2).split():
            tw, th = dc.GetTextExtent(header)
            self.__maxDim = max(self.__maxDim, tw, th)

        if '__WXMSW__' in wx.PlatformInfo:
            # WTF ?
            self.__maxDim += 10
        else:
            self.__maxDim += 4
        return wx.Size(max(W + 48 + 4, self.__maxDim * len(lines[0])), H + 2 + self.__maxDim * (len(lines) + 1))

    def SetSelection(self, selection):
        self.__selection = selection
        self.Refresh()

    def OnPaint(self, event):
        dc = wx.PaintDC(event.GetEventObject())
        dc.SetBackground(wx.WHITE_BRUSH)
        dc.Clear()

        w, h = self.GetClientSizeTuple()

        # Header: current month/year

        dc.SetPen(wx.BLACK_PEN)
        dc.SetBrush(wx.BLACK_BRUSH)

        header = datetime.date(year=self.__year, month=self.__month, day=1).strftime('%B %Y')
        tw, th = dc.GetTextExtent(header)
        dc.DrawText(header, (w - 48 - tw) / 2, 1)

        buttonDim = min(th, 10)

        cx = w - 24
        cy = th / 2 + 1

        gc = wx.GraphicsContext.Create(dc)
        gc.SetPen(wx.BLACK_PEN)
        gc.SetBrush(wx.BLACK_BRUSH)

        # Prev month
        if self.__month != 1 or self.__year != 1:
            gp = gc.CreatePath()
            xinf = w - 48 + 16 - buttonDim
            xsup = w - 48 + 16
            yinf = th / 2 + 1 - buttonDim / 2
            ysup = th / 2 + 1 + buttonDim / 2

            gp.MoveToPoint(xinf, th / 2 + 1)
            gp.AddArc(cx, cy, math.sqrt((xsup - cx) * (xsup - cx) + (yinf - cy) * (yinf - cy)), math.pi * 3 / 4, math.pi * 5 / 4, True)
            gc.DrawPath(gp)

        # Next month
        if self.__month != 12 or self.__year != 9999:
            gp = gc.CreatePath()
            xinf = w - 16
            xsup = w - 16 + buttonDim
            yinf = th / 2 + 1 - buttonDim / 2
            ysup = th / 2 + 1 + buttonDim / 2

            gp.MoveToPoint(xsup, th / 2 + 1)
            gp.AddArc(cx, cy, math.sqrt((xinf - cx) * (xinf - cx) + (yinf - cy) * (yinf - cy)), math.pi / 4, -math.pi / 4, False)
            gc.DrawPath(gp)

        # Today
        gp = gc.CreatePath()
        gp.AddArc(cx, cy, buttonDim * 3 / 4, 0, math.pi * 2, True)
        gc.DrawPath(gp)

        y = th + 2

        # Weekday first letters

        dc.SetPen(wx.LIGHT_GREY_PEN)
        dc.SetBrush(wx.LIGHT_GREY_BRUSH)
        dc.DrawRectangle(0, y, self.__maxDim * 7, self.__maxDim)
        dc.SetTextForeground(wx.BLUE)
        for idx, header in enumerate(calendar.weekheader(2).split()):
            tw, th = dc.GetTextExtent(header)
            dc.DrawText(header, self.__maxDim * idx + int((self.__maxDim - tw) / 2), y + int((self.__maxDim - th) / 2))

        y += self.__maxDim

        # Days

        self.__days = list()
        for line in calendar.monthcalendar(self.__year, self.__month):
            x = 0
            for dayIndex, day in enumerate(line):
                if day != 0:
                    dt = datetime.date(year=self.__year, month=self.__month, day=day)
                    active = (self.__minDate is None or dt >= self.__minDate) and (self.__maxDate is None or dt <= self.__maxDate)

                    dc.SetPen(wx.BLACK_PEN)
                    dc.SetTextForeground(wx.RED if dayIndex + calendar.firstweekday() in [5, 6] else wx.BLACK)

                    if dt == self.__selection:
                        color = wx.SystemSettings.GetColour(wx.SYS_COLOUR_HIGHLIGHT)
                        dc.SetPen(wx.Pen(color))
                        dc.SetBrush(wx.Brush(color))
                        dc.DrawRectangle(x, y, self.__maxDim, self.__maxDim)
                        dc.SetTextForeground(wx.SystemSettings.GetColour(wx.SYS_COLOUR_HIGHLIGHTTEXT))

                    if not active:
                        dc.SetPen(wx.LIGHT_GREY_PEN)
                        dc.SetBrush(wx.LIGHT_GREY_BRUSH)
                        dc.DrawRectangle(x, y, self.__maxDim, self.__maxDim)

                    now = datetime.datetime.now()
                    if (dt.year, dt.month, dt.day) == (now.year, now.month, now.day):
                        dc.SetPen(wx.RED_PEN)
                        dc.SetBrush(wx.TRANSPARENT_BRUSH)
                        dc.DrawRectangle(x, y, self.__maxDim, self.__maxDim)

                    label = '%d' % day
                    tw, th = dc.GetTextExtent(label)
                    dc.DrawText(label, x + (self.__maxDim - tw) / 2, y + (self.__maxDim - th) / 2)

                    if active:
                        self.__days.append((x, y, day))
                x += self.__maxDim
            y += self.__maxDim

    def OnLeftUp(self, event):
        w, h = self.GetClientSizeTuple()

        # Buttons
        if event.GetY() < 16 and event.GetX() > w - 48:
            if event.GetX() < w - 48 + 16 and (self.__month != 1 or self.__year != 1):
                if self.__month == 1:
                    self.__year -= 1
                    self.__month = 12
                else:
                    self.__month -= 1
            elif event.GetX() < w - 48 + 32:
                today = datetime.datetime.now()
                self.__year = today.year
                self.__month = today.month
            elif self.__month != 12 or self.__year != 9999:
                if self.__month == 12:
                    self.__year += 1
                    self.__month = 1
                else:
                    self.__month += 1
            self.Refresh()
            return

        for x, y, day in self.__days:
            if event.GetX() >= x and event.GetX() < x + self.__maxDim and \
                event.GetY() >= y and event.GetY() < y + self.__maxDim:
                self.GetParent().SetDate(datetime.date(year=self.__year, month=self.__month, day=day), notify=True)
                self.Dismiss()
                break

#}

#=======================================
#{ Multiple choices popup

class _MultipleChoicesPopup(_PopupWindow):
    def __init__(self, choices, selection, *args, **kwargs):
        self.__choices = choices
        self.__selection = selection or 0
        super(_MultipleChoicesPopup, self).__init__(*args, **kwargs)

    def Fill(self, interior):
        wx.EVT_PAINT(interior, self.OnPaint)
        wx.EVT_LEFT_UP(interior, self.OnLeftUp)
        self.SetClientSize(self.GetExtent(wx.ClientDC(interior)))

    def GetExtent(self, dc):
        maxW = 0
        totH = 0

        for choice in self.__choices:
            tw, th = dc.GetTextExtent(unicode(choice))
            maxW = max(tw, maxW)
            totH += th

        return wx.Size(maxW + 4, totH + 4 + 2 * (len(self.__choices) + 1))

    def OnPaint(self, event):
        dc = wx.PaintDC(event.GetEventObject())

        dc.SetBackground(wx.WHITE_BRUSH)
        dc.Clear()

        y = 2
        w, h = self.GetClientSize()

        for index, choice in enumerate(self.__choices):
            tw, th = dc.GetTextExtent(unicode(choice))
            if index == self.__selection:
                color = wx.SystemSettings.GetColour(wx.SYS_COLOUR_HIGHLIGHT)
                dc.SetPen(wx.Pen(color))
                dc.SetBrush(wx.Brush(color))
                dc.DrawRoundedRectangle(1, y, w - 2, th, 3)
                dc.SetTextForeground(wx.SystemSettings.GetColour(wx.SYS_COLOUR_HIGHLIGHTTEXT))
            else:
                dc.SetTextForeground(wx.BLACK)
            dc.DrawText(unicode(choice), 2 + (w - 4 - tw) // 2, y)
            y += th + 2

    def HandleKey(self, event):
        if event.GetKeyCode() == wx.WXK_UP:
            self.__selection = (self.__selection + len(self.__choices) - 1) % len(self.__choices)
            self.Refresh()
            return True

        if event.GetKeyCode() == wx.WXK_DOWN:
            self.__selection = (self.__selection + 1) % len(self.__choices)
            self.Refresh()
            return True

        if event.GetKeyCode() == wx.WXK_RETURN:
            evt = EntryChoiceSelectedEvent(self, self.__choices[self.__selection])
            self.ProcessEvent(evt)
            return True

        return False

    def OnLeftUp(self, event):
        y = 2
        dc = wx.ClientDC(event.GetEventObject())
        for choice in self.__choices:
            tw, th = dc.GetTextExtent(unicode(choice))
            if event.GetY() >= y and event.GetY() < y + th:
                evt = EntryChoiceSelectedEvent(self, choice)
                self.ProcessEvent(evt)
                break
            y += th + 2

#}

#=======================================
#{ Date/time control

wxEVT_DATETIME_CHANGE = wx.NewEventType()
EVT_DATETIME_CHANGE = wx.PyEventBinder(wxEVT_DATETIME_CHANGE)

class DateTimeChangeEvent(FieldValueChangeEvent):
    type_ = wxEVT_DATETIME_CHANGE


class SmartDateTimeCtrl(wx.Panel):
    def __init__(self, *args, **kwargs):
        value = kwargs.pop('value', None)
        label = kwargs.pop('label', u'')
        self.__enableNone = kwargs.pop('enableNone', False)
        dateFormat = kwargs.pop('dateFormat', lambda x: x.strftime('%x'))
        timeFormat = kwargs.pop('timeFormat', lambda x: x.strftime('%H:%M:%S'))
        startHour = kwargs.pop('startHour', 0)
        endHour = kwargs.pop('endHour', 24)
        minuteDelta = kwargs.pop('minuteDelta', 10)
        secondDelta = kwargs.pop('secondDelta', 10)
        showRelative = kwargs.pop('showRelative', False)

        super(SmartDateTimeCtrl, self).__init__(*args, **kwargs)

        sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.__label = None
        if self.__enableNone:
            self.__checkbox = wx.CheckBox(self, wx.ID_ANY, label)
            wx.EVT_CHECKBOX(self.__checkbox, wx.ID_ANY, self.OnToggleNone)
            sizer.Add(self.__checkbox, 0, wx.ALL|wx.ALIGN_CENTRE, 3)
            self.__label = self.__checkbox
        elif label:
            self.__label = wx.StaticText(self, wx.ID_ANY, label)
            sizer.Add(self.__label, 0, wx.ALL|wx.ALIGN_CENTRE, 3)

        dateTime = value or datetime.datetime.now()

        self.__dateCtrl = DateEntry(self, year=dateTime.year, month=dateTime.month, day=dateTime.day, format=dateFormat)
        sizer.Add(self.__dateCtrl, 0, wx.ALL|wx.ALIGN_CENTRE, 3)

        self.__timeCtrl = TimeEntry(self, hour=dateTime.hour, minute=dateTime.minute, second=dateTime.second, format=timeFormat,
                                    startHour=startHour, endHour=endHour, minuteDelta=minuteDelta, secondDelta=secondDelta)
        sizer.Add(self.__timeCtrl, 0, wx.ALL|wx.ALIGN_CENTRE, 3)

        if showRelative:
            self.__relButton = wx.BitmapButton(self, wx.ID_ANY, wx.ArtProvider.GetBitmap(wx.ART_LIST_VIEW, wx.ART_BUTTON, (16, 16)))
            wx.EVT_BUTTON(self.__relButton, wx.ID_ANY, self.__OnPopupRelativeChoices)
            sizer.Add(self.__relButton, 0, wx.ALL|wx.ALIGN_CENTRE, 1)
            self.__relButton.Enable(False)
        else:
            self.__relButton = None

        self.SetSizer(sizer)

        if self.__enableNone and value is None:
            self.Enable(False)

        EVT_DATE_CHANGE(self, self.OnDateChange)
        EVT_TIME_CHANGE(self, self.OnTimeChange)
        EVT_TIME_CHOICES_CHANGE(self.__timeCtrl, self.__OnChoicesChange)
        EVT_TIME_NEXT_DAY(self, self.OnNextDay)
        EVT_TIME_PREV_DAY(self, self.OnPrevDay)

    def __OnPopupRelativeChoices(self, event):
        self.__timeCtrl.PopupRelativeChoices()

    def HideRelativeButton(self):
        # For alignment purposes...
        self.__relButton.Hide()

    def HandleKey(self, event):
        if self.GetDateTime() is not None:
            if event.GetUnicodeKey() in [ord('t'), ord('T')]:
                # Today, same time
                self.SetDateTime(datetime.datetime.combine(datetime.datetime.now().date(), self.GetDateTime().time()),
                                 notify=True)
                return True
            elif event.GetUnicodeKey() in [ord('n'), ord('N')]:
                # Now
                self.SetDateTime(datetime.datetime.now())
                return True
        return False

    def Cleanup(self):
        self.__dateCtrl.Cleanup()
        self.__timeCtrl.Cleanup()

    def GetLabelWidth(self):
        if self.__label is not None:
            return self.__label.GetSizeTuple()[0]

    def SetLabelWidth(self, width):
        if self.__label is not None:
            self.__label.SetMinSize(wx.Size(width, -1))

    def EnableChoices(self, enabled=True):
        self.__timeCtrl.EnableChoices(enabled=enabled)

    def SetRelativeChoicesStart(self, start=None):
        self.__timeCtrl.SetRelativeChoicesStart(start)
        if self.__relButton is not None:
            self.__relButton.Enable(self.__timeCtrl.IsEnabled() and start is not None)

    def LoadChoices(self, choices):
        self.__timeCtrl.LoadChoices(choices)

    def GetDateTime(self):
        if self.__dateCtrl.IsEnabled():
            return datetime.datetime.combine(self.__dateCtrl.GetDate(), self.__timeCtrl.GetTime())
        return None

    def SetDateTime(self, value, notify=False):
        event = DateTimeChangeEvent(self, value)
        if notify:
            self.ProcessEvent(event)
        if not event.IsVetoed():
            if value is None:
                if self.__enableNone:
                    self.__checkbox.SetValue(False)
                    self.Enable(False)
                else:
                    raise ValueError('This control does not support the None value')
            else:
                self.Enable(True)
                if self.__enableNone:
                    self.__checkbox.SetValue(True)
                self.__dateCtrl.SetDate(datetime.date(year=value.year, month=value.month, day=value.day))
                self.__timeCtrl.SetTime(datetime.time(hour=value.hour, minute=value.minute, second=value.second))
                self.Enable(True)

    def Enable(self, enabled=True):
        self.__dateCtrl.Enable(enabled)
        self.__timeCtrl.Enable(enabled)
        if self.__relButton is not None:
            self.__relButton.Enable(enabled and self.__timeCtrl.GetRelativeChoicesStart() is not None)

    def OnToggleNone(self, event):
        if event.IsChecked():
            evt = DateTimeChangeEvent(self, datetime.datetime.combine(self.__dateCtrl.GetDate(), self.__timeCtrl.GetTime()))
        else:
            evt = DateTimeChangeEvent(self, None)
        self.ProcessEvent(evt)
        self.Enable(event.IsChecked())
        self.Refresh()
        self.__dateCtrl.SetFocus()

    def OnDateChange(self, event):
        newValue = datetime.datetime.combine(event.GetValue(), self.__timeCtrl.GetTime())
        evt = DateTimeChangeEvent(self, newValue)
        self.ProcessEvent(evt)
        if evt.IsVetoed():
            wx.Bell()
            event.Veto()
        else:
            self.SetDateTime(evt.GetValue())

    def OnTimeChange(self, event):
        newValue = datetime.datetime.combine(self.__dateCtrl.GetDate(), event.GetValue())
        evt = DateTimeChangeEvent(self, newValue)
        self.ProcessEvent(evt)
        if evt.IsVetoed():
            wx.Bell()
            event.Veto()
        else:
            self.SetDateTime(evt.GetValue())

    def OnNextDay(self, event):
        evt = DateTimeChangeEvent(self, datetime.datetime.combine(self.GetDateTime().date(), event.GetValue()) + datetime.timedelta(days=1))
        self.ProcessEvent(evt)
        if evt.IsVetoed():
            wx.Bell()
            event.Veto()
        else:
            self.SetDateTime(evt.GetValue())

    def OnPrevDay(self, event):
        evt = DateTimeChangeEvent(self, datetime.datetime.combine(self.GetDateTime().date(), event.GetValue()) - datetime.timedelta(days=1))
        self.ProcessEvent(evt)
        if evt.IsVetoed():
            wx.Bell()
            event.Veto()
        else:
            self.SetDateTime(evt.GetValue())

    def __OnChoicesChange(self, event):
        self.ProcessEvent(TimeChoicesChangedEvent(self, event.GetValue()))

#}

#=======================================
#{ Date/time span

wxEVT_DATETIMESPAN_CHANGE = wx.NewEventType()
EVT_DATETIMESPAN_CHANGE = wx.PyEventBinder(wxEVT_DATETIMESPAN_CHANGE)

class DateTimeSpanChangeEvent(FieldValueChangeEvent):
    type_ = wxEVT_DATETIMESPAN_CHANGE


class DateTimeSpanCtrl(wx.EvtHandler):
    def __init__(self, ctrlStart, ctrlEnd, minSpan=None):
        super(DateTimeSpanCtrl, self).__init__()

        self.__ctrlStart = ctrlStart
        self.__ctrlEnd = ctrlEnd
        self.__minSpan = minSpan

        self.__ctrlStart.EnableChoices()
        self.__ctrlEnd.EnableChoices()
        self.__ctrlEnd.SetRelativeChoicesStart(self.__ctrlStart.GetDateTime())

        EVT_DATETIME_CHANGE(self.__ctrlStart, self.OnStartChange)
        EVT_DATETIME_CHANGE(self.__ctrlEnd, self.OnEndChange)

        w1 = self.__ctrlStart.GetLabelWidth()
        w2 = self.__ctrlEnd.GetLabelWidth()
        self.__ctrlStart.SetLabelWidth(max(w1, w2))
        self.__ctrlEnd.SetLabelWidth(max(w1, w2))

    def OnStartChange(self, event):
        if event.GetValue() is None:
            if self.__ctrlStart.GetDateTime() is None:
                raise RuntimeError('WTF?')
            # Start control disabled. Nothing to do.
            self.__ctrlEnd.SetRelativeChoicesStart(None)
        else:
            if self.__minSpan is not None:
                if self.__ctrlStart.GetDateTime() is None:
                    # Start enabled; ensure min span
                    if self.__ctrlEnd.GetDateTime() is not None and event.GetValue() + self.__minSpan > self.__ctrlEnd.GetDateTime():
                        self.__ctrlStart.SetDateTime(self.__ctrlEnd.GetDateTime() - self.__minSpan)
                        event.Veto()
                else:
                    # Start changed => keep difference
                    if self.__ctrlEnd.GetDateTime() is not None:
                        self.__ctrlEnd.SetDateTime(self.__ctrlEnd.GetDateTime() + (event.GetValue() - self.__ctrlStart.GetDateTime()))
            self.__ctrlEnd.SetRelativeChoicesStart(event.GetValue())

        self.ProcessEvent(DateTimeSpanChangeEvent(self, (event.GetValue(), self.__ctrlEnd.GetDateTime())))

    def OnEndChange(self, event):
        if event.GetValue() is None:
            if self.__ctrlEnd.GetDateTime() is None:
                raise RuntimeError('WTF?')
            # Nothing to do
            value = None
        else:
            value = event.GetValue()
            if self.__minSpan is not None:
                # End control enabled or changed; ensure min span, without changing start value
                if self.__ctrlStart.GetDateTime() is not None and \
                    self.__ctrlStart.GetDateTime() + self.__minSpan > event.GetValue():
                    value = self.__ctrlStart.GetDateTime() + self.__minSpan
                    self.__ctrlEnd.SetDateTime(value)
                    event.Veto()

        self.ProcessEvent(DateTimeSpanChangeEvent(self, (self.__ctrlStart.GetDateTime(), value)))

#}

if __name__ == '__main__':
    class Dialog(wx.Dialog):
        def __init__(self):
            super(Dialog, self).__init__(None, wx.ID_ANY, 'Test', style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)
            sz = wx.BoxSizer(wx.VERTICAL)

            pnl1 = SmartDateTimeCtrl(self, label='Start', enableNone=True, timeFormat=lambda x: x.strftime('%I:%M %p'), startHour=8, endHour=18)
            pnl1.EnableChoices()
            sz.Add(pnl1, 0, wx.ALL|wx.ALIGN_LEFT, 3)

            pnl2 = SmartDateTimeCtrl(self, label='End', enableNone=True, timeFormat=lambda x: x.strftime('%H:%M:%S'), showRelative=True)
            pnl2.EnableChoices()
            sz.Add(pnl2, 0, wx.ALL|wx.ALIGN_LEFT, 3)

            sz.Add(wx.TextCtrl(self, wx.ID_ANY, ''), 1, wx.ALL|wx.EXPAND, 3)
            sz.Add(wx.TextCtrl(self, wx.ID_ANY, ''), 1, wx.ALL|wx.EXPAND, 3)
            self.SetSizer(sz)

            spanCtrl = DateTimeSpanCtrl(pnl1, pnl2, minSpan=datetime.timedelta(hours=1))
            EVT_DATETIMESPAN_CHANGE(spanCtrl, self.OnChange)

            cfg = wx.Config('SmartDateTimeCtrlSample')
            if cfg.HasEntry('Choices'):
                pnl2.LoadChoices(cfg.Read('Choices'))
            EVT_TIME_CHOICES_CHANGE(pnl2, self.OnChoicesChanged)

            wx.EVT_CLOSE(self, self.OnClose)

            self.Fit()
            self.CentreOnScreen()
            self.Show()

        def OnChoicesChanged(self, event):
            wx.Config('SmartDateTimeCtrlSample').Write('Choices', event.GetValue())

        def OnChange(self, event):
            print event.GetValue()

        def OnClose(self, event):
            self.Destroy()

    class App(wx.App):
        def OnInit(self):
            Dialog()
            return True

    App(0).MainLoop()