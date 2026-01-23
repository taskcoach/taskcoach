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

from taskcoachlib import i18n, operating_system
import wx
import wx.stc as stc
import webbrowser
import re

# Try to import enchant for spell checking
try:
    import enchant
    from enchant.checker import SpellChecker
    ENCHANT_AVAILABLE = True
except ImportError:
    ENCHANT_AVAILABLE = False

# Indicator number for spell check (0-31 available in Scintilla)
SPELLCHECK_INDICATOR = 0


class SpellCheckMixin:
    """Utility class for spell check helper methods.

    Provides language detection and available languages list for the
    preferences UI. Actual spell checking is done by StyledTextCtrl.
    """

    @classmethod
    def _detectLanguage(cls):
        """Detect the system language for spell checking."""
        import locale
        try:
            lang, _ = locale.getdefaultlocale()
            if lang:
                return lang
        except (ValueError, TypeError):
            pass
        return 'en_US'  # Default fallback

    @classmethod
    def getAvailableLanguages(cls):
        """Get list of available spell check languages.

        Returns:
            List of language codes (e.g., ['en_US', 'de_DE', 'fr_FR'])
        """
        if not ENCHANT_AVAILABLE:
            return []
        try:
            return enchant.list_languages()
        except Exception:
            return []


UNICODE_CONTROL_CHARACTERS_TO_WEED = {}
for ordinal in range(0x20):
    if chr(ordinal) not in "\t\r\n":
        UNICODE_CONTROL_CHARACTERS_TO_WEED[ordinal] = None


class BaseTextCtrl(wx.TextCtrl):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, -1, *args, **kwargs)
        self.__data = None
        if operating_system.isGTK() or operating_system.isMac():
            if operating_system.isGTK():
                self.Bind(wx.EVT_KEY_DOWN, self.__on_key_down)
            self.Bind(wx.EVT_KILL_FOCUS, self.__on_kill_focus)
            self.__initial_value = self.GetValue()
            self.__undone_value = None

    def GetValue(self, *args, **kwargs):
        value = super().GetValue(*args, **kwargs)
        # Don't allow unicode control characters:
        return value.translate(UNICODE_CONTROL_CHARACTERS_TO_WEED)

    def SetValue(self, *args, **kwargs):
        super().SetValue(*args, **kwargs)
        if operating_system.isGTK() or operating_system.isMac():
            self.__initial_value = self.GetValue()

    def AppendText(self, *args, **kwargs):
        super().AppendText(*args, **kwargs)
        if operating_system.isGTK() or operating_system.isMac():
            self.__initial_value = self.GetValue()

    def SetData(self, data):
        self.__data = data

    def GetData(self):
        return self.__data

    def CanUndo(self):
        if operating_system.isMac():
            return self.__can_undo()
        return super().CanUndo()

    def Undo(self):
        if operating_system.isMac():
            self.__undo()
        else:
            super().Undo()

    def CanRedo(self):
        if operating_system.isMac():
            return self.__can_redo()
        return super().CanRedo()

    def Redo(self):
        if operating_system.isMac():
            self.__redo()
        else:
            super().Redo()

    def __on_key_down(self, event):
        """Check whether the user pressed Ctrl-Z (or Ctrl-Y) and if so,
        undo (or redo) the editing."""
        if self.__ctrl_z_pressed(event) and self.__can_undo():
            self.__undo()
        elif self.__ctrl_y_pressed(event) and self.__can_redo():
            self.__redo()
        else:
            event.Skip()

    @staticmethod
    def __ctrl_z_pressed(event):
        """Did the user press Ctrl-Z (for undo)?"""
        return event.GetKeyCode() == ord("Z") and event.ControlDown()

    def __can_undo(self):
        """Is there a change to be undone?"""
        return self.GetValue() != self.__initial_value

    def __undo(self):
        """Undo the last change."""
        insertion_point = self.GetInsertionPoint()
        self.__undone_value = self.GetValue()
        super().SetValue(self.__initial_value)
        insertion_point = min(insertion_point, self.GetLastPosition())
        self.SetInsertionPoint(insertion_point)

    @staticmethod
    def __ctrl_y_pressed(event):
        """Did the user press Ctrl-Y (for redo)?"""
        return event.GetKeyCode() == ord("Y") and event.ControlDown()

    def __can_redo(self):
        """Is there an undone change to be redone?"""
        return self.__undone_value not in (self.GetValue(), None)

    def __redo(self):
        """Redo the last undone change."""
        insertion_point = self.GetInsertionPoint()
        super().SetValue(self.__undone_value)
        self.__undone_value = None
        insertion_point = min(insertion_point, self.GetLastPosition())
        self.SetInsertionPoint(insertion_point)

    def __on_kill_focus(self, event):
        """Reset the edit history."""
        self.__initial_value = self.GetValue()
        self.__undone_value = None


class _StyledTextCtrl(stc.StyledTextCtrl):
    """Inner StyledTextCtrl with theme colours, URL handling, and spell check.

    Uses Scintilla for spell check highlighting (squiggly underlines) and
    manual URL detection with clickable links. Theme colours (foreground,
    background, caret, selection) are applied from system settings.

    Use MultiLineTextCtrl (wrapper panel) in application code — it provides
    the native border, padding, focus indication, and highlight.

    Args:
        singleLine: If True, prevents Enter key from creating newlines.
    """

    # Shared spell checker instance cache (per language)
    _spell_dicts = {}
    _word_pattern = re.compile(r'\b[a-zA-Z\u00C0-\u024F\u1E00-\u1EFF]+\b')
    _url_pattern = re.compile(
        r'(https?://[^\s<>"{}|\\^`\[\]]+|www\.[^\s<>"{}|\\^`\[\]]+)',
        re.IGNORECASE
    )

    # Indicator numbers (0-31 available in Scintilla)
    URL_INDICATOR = 1

    def __init__(self, parent, text="", *args, settings=None, singleLine=False, spellCheck=True, **kwargs):
        # Filter out TextCtrl-specific kwargs that don't apply to StyledTextCtrl
        kwargs.pop("style", None)
        super().__init__(parent, style=wx.BORDER_NONE)

        self._settings = settings
        self._singleLine = singleLine
        self._spellCheckRequested = spellCheck  # User requested spell check
        self._spellCheckEnabled = False
        self._spellCheckLanguage = None
        self._misspelledRanges = []
        self._urlRanges = []
        self.__data = None

        # Configure text control mode
        self._setupTextMode()

        # Configure indicators (spell check and URL)
        self._setupIndicators()

        # Initialize text
        if text:
            self.SetText(text)
            self.SetCurrentPos(0)
            self.SetAnchor(0)

        # Initialize spell checking
        self._initSpellCheck()

        # URL handling
        try:
            self.__webbrowser = webbrowser.get()
        except webbrowser.Error:
            self.__webbrowser = None

        self.Bind(wx.EVT_LEFT_DOWN, self._onLeftClick)
        self.Bind(stc.EVT_STC_UPDATEUI, self._onUpdateUI)

        # Single line mode: additional configuration
        if self._singleLine:
            # Clear the newline command from Enter and Shift+Enter
            # See: https://proton-ce.sourceforge.net/rc/scintilla/pyframe/www.pyframe.com/stc/keymap.html
            self.CmdKeyClear(stc.STC_KEY_RETURN, 0)
            self.CmdKeyClear(stc.STC_KEY_RETURN, stc.STC_SCMOD_SHIFT)
            # Intercept Ctrl+V to strip newlines from pasted text
            self.Bind(wx.EVT_KEY_DOWN, self._onKeyDown)

    def _onKeyDown(self, event):
        """Intercept Ctrl+V to strip newlines from pasted text."""
        # Check for Ctrl+V (paste)
        if event.ControlDown() and event.GetKeyCode() == ord('V'):
            self._pasteWithoutNewlines()
            # Don't Skip() - prevents default paste
            return
        event.Skip()

    def _pasteWithoutNewlines(self):
        """Paste clipboard text with newlines replaced by spaces."""
        if wx.TheClipboard.Open():
            try:
                if wx.TheClipboard.IsSupported(wx.DataFormat(wx.DF_UNICODETEXT)):
                    data = wx.TextDataObject()
                    wx.TheClipboard.GetData(data)
                    text = data.GetText()
                    # Replace newlines with spaces
                    text = text.replace('\r\n', ' ').replace('\r', ' ').replace('\n', ' ')
                    # Insert at current position (replacing selection if any)
                    self.ReplaceSelection(text)
            finally:
                wx.TheClipboard.Close()

    def _setupTextMode(self):
        """Configure StyledTextCtrl for editing."""
        # Hide margins (line numbers, fold markers, etc.)
        self.SetMarginWidth(0, 0)
        self.SetMarginWidth(1, 0)
        self.SetMarginWidth(2, 0)

        # Word wrap: enabled for multiline, disabled for single-line
        if self._singleLine:
            self.SetWrapMode(stc.STC_WRAP_NONE)
            self.SetUseVerticalScrollBar(False)
            self.SetUseHorizontalScrollBar(False)
        else:
            self.SetWrapMode(stc.STC_WRAP_WORD)

        self._applyThemeColours()

    def _applyThemeColours(self):
        """Apply system theme colours to the control."""
        font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
        self.StyleSetFont(stc.STC_STYLE_DEFAULT, font)
        self.StyleSetForeground(stc.STC_STYLE_DEFAULT, wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOWTEXT))
        self.StyleSetBackground(stc.STC_STYLE_DEFAULT, wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOW))
        self.StyleClearAll()
        self.SetCaretForeground(wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOWTEXT))
        self.SetSelBackground(True, wx.SystemSettings.GetColour(wx.SYS_COLOUR_HIGHLIGHT))
        self.SetSelForeground(True, wx.SystemSettings.GetColour(wx.SYS_COLOUR_HIGHLIGHTTEXT))

    def _setupIndicators(self):
        """Set up indicators for spell check and URLs."""
        # Spell check: red squiggly underline
        self.IndicatorSetStyle(SPELLCHECK_INDICATOR, stc.STC_INDIC_SQUIGGLE)
        self.IndicatorSetForeground(SPELLCHECK_INDICATOR, wx.RED)

        # URLs: blue underline with hotspot
        self.IndicatorSetStyle(self.URL_INDICATOR, stc.STC_INDIC_PLAIN)
        self.IndicatorSetForeground(self.URL_INDICATOR, wx.BLUE)
        self.IndicatorSetHoverStyle(self.URL_INDICATOR, stc.STC_INDIC_PLAIN)
        self.IndicatorSetHoverForeground(self.URL_INDICATOR, wx.BLUE)

        # Enable hotspot clicking
        self.SetHotspotActiveUnderline(True)
        self.SetHotspotActiveForeground(True, wx.BLUE)
        self.Bind(stc.EVT_STC_HOTSPOT_CLICK, self._onHotspotClick)

    def _initSpellCheck(self):
        """Initialize spell checking."""
        if not ENCHANT_AVAILABLE or not self._spellCheckRequested:
            return

        # Load settings
        if self._settings:
            try:
                self._spellCheckEnabled = self._settings.getboolean('spellcheck', 'enabled')
                self._spellCheckLanguage = self._settings.get('spellcheck', 'language') or None
            except Exception:
                self._spellCheckEnabled = True
                self._spellCheckLanguage = None
        else:
            # No settings passed - enable spell check by default if requested
            self._spellCheckEnabled = True

        if self._spellCheckEnabled:
            self.Bind(stc.EVT_STC_MODIFIED, self._onTextModified)
            self.Bind(wx.EVT_CONTEXT_MENU, self._onSpellCheckContextMenu)
            # Initial spell check and URL detection
            wx.CallAfter(self._performHighlighting)

    def _onTextModified(self, event):
        """Handle text changes - schedule spell check and URL detection."""
        event.Skip()
        if event.GetModificationType() & (stc.STC_MOD_INSERTTEXT | stc.STC_MOD_DELETETEXT):
            # Debounce highlighting
            if hasattr(self, '_highlightTimer') and self._highlightTimer.IsRunning():
                self._highlightTimer.Stop()
            self._highlightTimer = wx.CallLater(300, self._performHighlighting)

    def _getSpellDict(self):
        """Get spell dictionary for current language."""
        if not ENCHANT_AVAILABLE:
            return None

        language = self._spellCheckLanguage
        if language is None:
            import locale
            try:
                language, _ = locale.getdefaultlocale()
            except (ValueError, TypeError):
                language = 'en_US'

        if language not in self._spell_dicts:
            try:
                self._spell_dicts[language] = enchant.Dict(language)
            except enchant.errors.DictNotFoundError:
                base_lang = language.split('_')[0] if '_' in language else None
                if base_lang:
                    try:
                        self._spell_dicts[language] = enchant.Dict(base_lang)
                    except enchant.errors.DictNotFoundError:
                        self._spell_dicts[language] = None
                else:
                    self._spell_dicts[language] = None

        return self._spell_dicts.get(language)

    def _performHighlighting(self):
        """Perform spell checking and URL detection."""
        text = self.GetText()
        text_bytes = text.encode('utf-8')

        # Clear all indicators
        self.SetIndicatorCurrent(SPELLCHECK_INDICATOR)
        self.IndicatorClearRange(0, len(text_bytes))
        self.SetIndicatorCurrent(self.URL_INDICATOR)
        self.IndicatorClearRange(0, len(text_bytes))

        # Spell check
        self._misspelledRanges = []
        if self._spellCheckEnabled and ENCHANT_AVAILABLE:
            spell_dict = self._getSpellDict()
            if spell_dict:
                self.SetIndicatorCurrent(SPELLCHECK_INDICATOR)
                for match in self._word_pattern.finditer(text):
                    word = match.group()
                    if len(word) > 1 and not spell_dict.check(word):
                        start = len(text[:match.start()].encode('utf-8'))
                        length = len(word.encode('utf-8'))
                        self._misspelledRanges.append((match.start(), match.end(), word))
                        self.IndicatorFillRange(start, length)

        # URL detection
        self._urlRanges = []
        self.SetIndicatorCurrent(self.URL_INDICATOR)
        for match in self._url_pattern.finditer(text):
            url = match.group()
            char_start = match.start()
            char_end = match.end()
            byte_start = len(text[:char_start].encode('utf-8'))
            byte_length = len(url.encode('utf-8'))
            self._urlRanges.append((char_start, char_end, url))
            self.IndicatorFillRange(byte_start, byte_length)
            # Apply link styling
            self.StartStyling(byte_start)

    def _onLeftClick(self, event):
        """Handle left click for URL opening."""
        pos = self.PositionFromPoint(event.GetPosition())
        text = self.GetText()
        byte_text = text.encode('utf-8')
        char_pos = len(byte_text[:pos].decode('utf-8', errors='replace'))

        for start, end, url in self._urlRanges:
            if start <= char_pos < end:
                if self.__webbrowser:
                    # Add protocol if missing
                    if url.lower().startswith('www.'):
                        url = 'http://' + url
                    try:
                        self.__webbrowser.open(url)
                    except Exception as message:
                        wx.MessageBox(str(message), i18n._("Error opening URL"))
                    return
        event.Skip()

    def _onHotspotClick(self, event):
        """Handle hotspot click (URLs)."""
        pos = event.GetPosition()
        text = self.GetText()
        byte_text = text.encode('utf-8')
        char_pos = len(byte_text[:pos].decode('utf-8', errors='replace'))

        for start, end, url in self._urlRanges:
            if start <= char_pos < end:
                if self.__webbrowser:
                    if url.lower().startswith('www.'):
                        url = 'http://' + url
                    try:
                        self.__webbrowser.open(url)
                    except Exception as message:
                        wx.MessageBox(str(message), i18n._("Error opening URL"))
                return

    def _onUpdateUI(self, event):
        """Update cursor when hovering over URLs."""
        event.Skip()
        pos = self.GetCurrentPos()
        text = self.GetText()
        byte_text = text.encode('utf-8')
        if pos <= len(byte_text):
            char_pos = len(byte_text[:pos].decode('utf-8', errors='replace'))
            for start, end, _ in self._urlRanges:
                if start <= char_pos < end:
                    self.SetCursor(wx.Cursor(wx.CURSOR_HAND))
                    return
        self.SetCursor(wx.Cursor(wx.CURSOR_IBEAM))

    def _onSpellCheckContextMenu(self, event):
        """Show context menu with spelling suggestions."""
        if not self._spellCheckEnabled or not ENCHANT_AVAILABLE:
            event.Skip()
            return

        # Get click position in text
        pos = event.GetPosition()
        if pos == wx.DefaultPosition:
            text_pos = self.GetCurrentPos()
        else:
            pos = self.ScreenToClient(pos)
            text_pos = self.PositionFromPoint(pos)

        # Convert byte position to character position
        text = self.GetText()
        byte_text = text.encode('utf-8')
        char_pos = len(byte_text[:text_pos].decode('utf-8', errors='replace'))

        # Check if we clicked on a misspelled word
        misspelled_word = None
        word_start = None
        word_end = None

        for start, end, word in self._misspelledRanges:
            if start <= char_pos <= end:
                misspelled_word = word
                word_start = start
                word_end = end
                break

        if misspelled_word:
            spell_dict = self._getSpellDict()
            if spell_dict:
                suggestions = spell_dict.suggest(misspelled_word)[:5]

                menu = wx.Menu()
                if suggestions:
                    for suggestion in suggestions:
                        item = menu.Append(wx.ID_ANY, suggestion)
                        self.Bind(wx.EVT_MENU,
                                 lambda evt, s=suggestion, ws=word_start, we=word_end:
                                     self._replaceWord(ws, we, s), item)
                    menu.AppendSeparator()

                add_item = menu.Append(wx.ID_ANY, i18n._("Add to dictionary"))
                self.Bind(wx.EVT_MENU,
                         lambda evt, w=misspelled_word: self._addToDictionary(w), add_item)

                ignore_item = menu.Append(wx.ID_ANY, i18n._("Ignore"))
                self.Bind(wx.EVT_MENU,
                         lambda evt: self._performHighlighting(), ignore_item)

                menu.AppendSeparator()
                self._addStandardContextMenuItems(menu)

                self.PopupMenu(menu)
                menu.Destroy()
                return

        event.Skip()

    def _addStandardContextMenuItems(self, menu):
        """Add standard Cut/Copy/Paste items to context menu."""
        cut_item = menu.Append(wx.ID_CUT, i18n._("Cut"))
        copy_item = menu.Append(wx.ID_COPY, i18n._("Copy"))
        paste_item = menu.Append(wx.ID_PASTE, i18n._("Paste"))
        menu.AppendSeparator()
        select_all_item = menu.Append(wx.ID_SELECTALL, i18n._("Select All"))

        self.Bind(wx.EVT_MENU, lambda e: self.Cut(), cut_item)
        self.Bind(wx.EVT_MENU, lambda e: self.Copy(), copy_item)
        self.Bind(wx.EVT_MENU, lambda e: self.Paste(), paste_item)
        self.Bind(wx.EVT_MENU, lambda e: self.SelectAll(), select_all_item)

    def _replaceWord(self, start, end, replacement):
        """Replace a misspelled word."""
        text = self.GetText()
        new_text = text[:start] + replacement + text[end:]
        self.SetText(new_text)
        self.SetSelection(start + len(replacement), start + len(replacement))
        wx.CallAfter(self._performHighlighting)

    def _addToDictionary(self, word):
        """Add word to personal dictionary."""
        spell_dict = self._getSpellDict()
        if spell_dict:
            try:
                spell_dict.add(word)
                wx.CallAfter(self._performHighlighting)
            except Exception:
                pass

    # Compatibility methods to match wx.TextCtrl interface
    def GetValue(self):
        """Get the text value (TextCtrl compatibility)."""
        return self.GetText().translate(UNICODE_CONTROL_CHARACTERS_TO_WEED)

    def SetValue(self, value):
        """Set the text value (TextCtrl compatibility)."""
        self.SetText(value)
        wx.CallAfter(self._performHighlighting)

    def AppendText(self, text):
        """Append text (TextCtrl compatibility)."""
        self.AddText(text)
        wx.CallAfter(self._performHighlighting)

    def GetInsertionPoint(self):
        """Get cursor position (TextCtrl compatibility)."""
        return self.GetCurrentPos()

    def SetInsertionPoint(self, pos):
        """Set cursor position (TextCtrl compatibility)."""
        self.SetCurrentPos(pos)
        self.SetAnchor(pos)

    def GetRange(self, start, end):
        """Get text range (TextCtrl compatibility)."""
        return self.GetTextRange(start, end)

    def SetData(self, data):
        """Store arbitrary data with the control."""
        self.__data = data

    def GetData(self):
        """Get stored data."""
        return self.__data

    def setSpellCheckEnabled(self, enabled):
        """Enable or disable spell checking."""
        self._spellCheckEnabled = enabled
        self._performHighlighting()

    def setSpellCheckLanguage(self, language):
        """Set spell check language."""
        self._spellCheckLanguage = language or None
        if self._spellCheckEnabled:
            self._performHighlighting()


class MultiLineTextCtrl(wx.Panel):
    """Text control with native border, focus indication, and spell check.

    Wraps _StyledTextCtrl in a panel that draws the native text control border
    using RendererNative, providing proper focus indication on GTK3.
    StyledTextCtrl (Scintilla) cannot display native focus borders on its own.
    """

    _nativePadding = None  # Cached native padding value

    @classmethod
    def _getNativePadding(cls, parent):
        """Get the native TextCtrl padding by querying the GTK theme."""
        if cls._nativePadding is not None:
            return cls._nativePadding

        # Try to get padding from GTK directly via PyGObject
        if operating_system.isGTK():
            try:
                import gi
                gi.require_version('Gtk', '3.0')
                from gi.repository import Gtk
                entry = Gtk.Entry()
                padding = entry.get_style_context().get_padding(Gtk.StateFlags.NORMAL)
                if padding.left > 0:
                    cls._nativePadding = padding.left
                    return cls._nativePadding
            except Exception:
                pass

        # Fallback: try wxPython GetMargins (works on Windows)
        try:
            temp = wx.TextCtrl(parent, -1, "X", style=wx.TE_MULTILINE | wx.BORDER_DEFAULT)
            margins = temp.GetMargins()
            temp.Destroy()
            if margins.x > 0:
                cls._nativePadding = margins.x
                return cls._nativePadding
        except Exception:
            pass

        # Last fallback
        cls._nativePadding = 6
        return cls._nativePadding

    def __init__(self, parent, text="", *args, settings=None, singleLine=False, spellCheck=True, **kwargs):
        style = kwargs.pop("style", 0)
        super().__init__(parent, style=wx.BORDER_NONE)

        self._singleLine = singleLine
        self._hasFocus = False
        self._padding = self._getNativePadding(parent)

        # Create the inner text control
        self._textCtrl = _StyledTextCtrl(
            self, text, *args, settings=settings, singleLine=singleLine,
            spellCheck=spellCheck, style=style, **kwargs
        )

        # Don't set explicit bg — inherit from parent so corners
        # auto-update on theme change (explicit bg prevents inheritance)

        # Use sizer to add padding
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self._textCtrl, 1, wx.EXPAND | wx.ALL, self._padding)
        self.SetSizer(sizer)

        # For single-line mode, constrain height to one line
        if singleLine:
            font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
            dc = wx.ScreenDC()
            dc.SetFont(font)
            textHeight = dc.GetTextExtent("Ay")[1]
            totalHeight = textHeight + (self._padding * 2) + 4
            self.SetMinSize((-1, totalHeight))
            self.SetMaxSize((-1, totalHeight))

        # Bind focus events to update focus state and repaint
        self._textCtrl.Bind(wx.EVT_SET_FOCUS, self._onFocus)
        self._textCtrl.Bind(wx.EVT_KILL_FOCUS, self._onKillFocus)

        # Bind paint event to draw native border
        self.Bind(wx.EVT_PAINT, self._onPaint)
        self._lastWindowBg = wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOW)

    def _onFocus(self, event):
        """Update focus state and repaint."""
        self._hasFocus = True
        self.Refresh()
        event.Skip()

    def _onKillFocus(self, event):
        """Update focus state and repaint."""
        self._hasFocus = False
        self.Refresh()
        event.Skip()

    def _onPaint(self, event):
        """Draw native TextCtrl border using RendererNative."""
        dc = wx.PaintDC(self)
        renderer = wx.RendererNative.Get()
        rect = self.GetClientRect()
        flags = wx.CONTROL_FOCUSED if self._hasFocus else 0
        renderer.DrawTextCtrl(self, dc, rect, flags)
        # Detect theme change (EVT_SYS_COLOUR_CHANGED doesn't reach children on GTK)
        windowBg = wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOW)
        if self._lastWindowBg != windowBg:
            self._lastWindowBg = windowBg
            wx.CallAfter(self._textCtrl._applyThemeColours)

    # Proxy common TextCtrl methods to the inner control
    def GetValue(self, *args, **kwargs):
        return self._textCtrl.GetValue(*args, **kwargs)

    def SetValue(self, *args, **kwargs):
        return self._textCtrl.SetValue(*args, **kwargs)

    def AppendText(self, *args, **kwargs):
        return self._textCtrl.AppendText(*args, **kwargs)

    def SetFont(self, *args, **kwargs):
        return self._textCtrl.SetFont(*args, **kwargs)

    def GetFont(self, *args, **kwargs):
        return self._textCtrl.GetFont(*args, **kwargs)

    def SetForegroundColour(self, *args, **kwargs):
        return self._textCtrl.SetForegroundColour(*args, **kwargs)

    def SetBackgroundColour(self, colour):
        super().SetBackgroundColour(colour)
        if hasattr(self, '_textCtrl'):
            self._textCtrl.SetBackgroundColour(colour)

    def SetData(self, data):
        return self._textCtrl.SetData(data)

    def GetData(self):
        return self._textCtrl.GetData()

    def CanUndo(self):
        return self._textCtrl.CanUndo()

    def Undo(self):
        return self._textCtrl.Undo()

    def CanRedo(self):
        return self._textCtrl.CanRedo()

    def Redo(self):
        return self._textCtrl.Redo()

    def SetInsertionPoint(self, *args, **kwargs):
        return self._textCtrl.SetInsertionPoint(*args, **kwargs)

    def GetInsertionPoint(self):
        return self._textCtrl.GetInsertionPoint()

    def GetRange(self, *args, **kwargs):
        return self._textCtrl.GetRange(*args, **kwargs)

    def SetFocus(self):
        return self._textCtrl.SetFocus()

    def Bind(self, event, handler, *args, **kwargs):
        # Text and focus events go to inner control; others to panel
        if event in (wx.EVT_TEXT, wx.EVT_TEXT_URL, wx.EVT_TEXT_ENTER,
                     wx.EVT_SET_FOCUS, wx.EVT_KILL_FOCUS):
            if event == wx.EVT_TEXT:
                return self._textCtrl.Bind(stc.EVT_STC_CHANGE, handler, *args, **kwargs)
            return self._textCtrl.Bind(event, handler, *args, **kwargs)
        return super().Bind(event, handler, *args, **kwargs)

    def setSpellCheckEnabled(self, enabled):
        return self._textCtrl.setSpellCheckEnabled(enabled)

    def setSpellCheckLanguage(self, language):
        return self._textCtrl.setSpellCheckLanguage(language)


def SingleLineTextCtrl(parent, value="", settings=None, spellCheck=True, **kwargs):
    """Single-line text control with optional spell checking.

    This is a convenience wrapper that creates a MultiLineTextCtrl with
    singleLine=True, which prevents Enter from creating newlines.

    Args:
        spellCheck: Enable spell checking (default True). Set False for
                    fields like file paths/URLs that shouldn't be spell checked.
    """
    return MultiLineTextCtrl(parent, value, settings=settings, singleLine=True, spellCheck=spellCheck, **kwargs)


class StaticTextWithToolTip(wx.StaticText):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        label = kwargs["label"]
        self.SetToolTip(wx.ToolTip(label))
