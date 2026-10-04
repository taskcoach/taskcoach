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

# Undo and redo for the text fields whose platform gives them none:
# every wx text field on GTK (wxGTK leaves Undo() unimplemented; GTK 3
# has no undo in its entries, GTK 4 added it) and single-line ones on
# macOS (wxOSX implements undo for multi-line fields only and leaves
# the native undo: action unmapped). Windows' own undo is kept, as is
# the editors' Scintilla fields' (docs/MENUS.md, Keyboard Shortcuts).

import wx

_HISTORY = "_text_undo_history"
_MAX_STEPS = 100


def needs_own_undo(field):
    """Whether the field gets its undo here, not from the platform."""
    if isinstance(field, wx.SearchCtrl):
        single_line = True
    elif isinstance(field, wx.TextCtrl):
        if not field.IsEditable() or field.HasFlag(wx.TE_PASSWORD):
            return False
        single_line = not field.IsMultiLine()
    else:
        return False
    if wx.Platform == "__WXGTK__":
        return True
    return wx.Platform == "__WXMAC__" and single_line


def _edit(old, new):
    """The change from old to new: its kind, where it starts, and
    the length of what it removed and inserted."""
    shortest = min(len(old), len(new))
    start = 0
    while start < shortest and old[start] == new[start]:
        start += 1
    end = 0
    while end < shortest - start and old[-1 - end] == new[-1 - end]:
        end += 1
    removed = len(old) - start - end
    inserted = len(new) - start - end
    if not removed:
        kind = "insert"
    elif not inserted:
        kind = "delete"
    else:
        kind = "replace"
    return kind, start, removed, inserted


class TextHistory:
    """A field's undo and redo steps, each the text and insertion point
    before a change. Typing on where the last character went in joins
    its step, as does deleting on from where the last deletion was."""

    def __init__(self, text, point):
        self.applying = False
        self.reset(text, point)

    def reset(self, text, point):
        """Start over from this text: the program set it."""
        self.__text, self.__point = text, point
        self.__undo, self.__redo = [], []
        self.__joins = None

    def record(self, text, point):
        """Note the field as it is now."""
        if text == self.__text:
            self.__point = point
            return
        kind, start, removed, inserted = _edit(self.__text, text)
        if kind == "insert" and inserted == 1:
            joins = self.__joins == ("insert", start)
            self.__joins = ("insert", start + 1)
        elif kind == "delete" and removed == 1:
            # Backspace deletes just before the last deletion, Delete
            # where it was
            joins = self.__joins in (("delete", start + 1), ("delete", start))
            self.__joins = ("delete", start)
        else:
            # Typing over a selection: what is typed on joins it
            joins = False
            self.__joins = ("insert", start + 1) if inserted == 1 else None
        if not joins:
            self.__undo.append((self.__text, self.__point))
            del self.__undo[:-_MAX_STEPS]
        self.__redo.clear()
        self.__text, self.__point = text, point

    def undo(self, text, point):
        """The text and insertion point to go back to, or None."""
        return self.__step(text, point, self.__undo, self.__redo)

    def redo(self, text, point):
        """The text and insertion point to go forward to, or None."""
        return self.__step(text, point, self.__redo, self.__undo)

    def __step(self, text, point, source, target):
        self.record(text, point)
        if not source:
            return None
        target.append((self.__text, self.__point))
        self.__text, self.__point = source.pop()
        self.__joins = None
        return self.__text, self.__point


def _text_class(field):
    """The wx class of the field, whose GetValue() and SetValue() are
    its text: a subclass may make them another value (NumericCtrl, an
    amount)."""
    return wx.SearchCtrl if isinstance(field, wx.SearchCtrl) else wx.TextCtrl


def _text(field):
    return _text_class(field).GetValue(field)


def _history(field):
    history = getattr(field, _HISTORY, None)
    if history is None:
        history = TextHistory(_text(field), field.GetInsertionPoint())
        setattr(field, _HISTORY, history)
    return history


def _go(field, direction):
    history = _history(field)
    state = getattr(history, direction)(
        _text(field), field.GetInsertionPoint()
    )
    if state is None:
        return
    text, point = state
    history.applying = True
    try:
        # SetValue, not ChangeValue: the field's handlers see the text
        _text_class(field).SetValue(field, text)
    finally:
        history.applying = False
    field.SetInsertionPoint(point)


def undo(field):
    """Undo in a text field: its own history if the platform has
    none, its native undo otherwise."""
    if needs_own_undo(field):
        _go(field, "undo")
    else:
        field.Undo()


def redo(field):
    """Redo in a text field, as undo() does."""
    if needs_own_undo(field):
        _go(field, "redo")
    else:
        field.Redo()


def _on_char_hook(event):
    """Before each key acts: record the field's last change, and take
    Ctrl+Z, Ctrl+Y and Ctrl+Shift+Z for its history."""
    event.Skip()
    field = event.GetEventObject()
    if not needs_own_undo(field):
        return
    _history(field).record(_text(field), field.GetInsertionPoint())
    if not event.CmdDown() or event.AltDown():
        return
    key = event.GetKeyCode()
    if key == ord("Z") and not event.ShiftDown():
        direction = "undo"
    elif key == ord("Y") or key == ord("Z"):
        direction = "redo"
    else:
        return
    event.Skip(False)
    _go(field, direction)


def _resetting(method):
    """The method, starting the field's history over when it changes
    the text: the program set it, so undo does not bring back what
    was there before."""

    def set_text(self, *args, **kwargs):
        before = _text(self)
        result = method(self, *args, **kwargs)
        history = getattr(self, _HISTORY, None)
        if history is not None and not history.applying:
            if _text(self) != before:
                history.reset(_text(self), self.GetInsertionPoint())
        return result

    return set_text


_installed = False


def install(app):
    """Give the text fields that need it their own undo; once, at
    start."""
    global _installed  # pylint: disable=W0603
    if _installed or wx.Platform not in ("__WXGTK__", "__WXMAC__"):
        return
    _installed = True
    for field_class in (wx.TextCtrl, wx.SearchCtrl):
        for name in ("SetValue", "ChangeValue", "Clear"):
            setattr(
                field_class,
                name,
                _resetting(getattr(field_class, name)),
            )
    app.Bind(wx.EVT_CHAR_HOOK, _on_char_hook)
