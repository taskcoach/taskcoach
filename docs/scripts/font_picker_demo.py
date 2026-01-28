#!/usr/bin/env python3
"""Font Picker Demo — Numbered Variations

Displays multiple font picker implementations side-by-side for visual
comparison. Uses scrollable window to fit all variations.

Run from the taskcoach root:
    python3 docs/scripts/font_picker_demo.py

Variations:
    1. Baseline (GenButton — production FontPickerCtrl)
    2. FontPickerCtrl2 (grow — production control)
    3. Checkbox + FontPickerCtrl2 in panel (SetSizerAndFit — current TC pattern)
    4. Checkbox + FontPickerCtrl2 FLAT in panel (SetSizerAndFit, BORDER_NONE)
    5. Checkbox + FontPickerCtrl2 in panel (fix: SetSizer only, no Fit)
       NOTE: clearing min size + InvalidateBestSize also works, but SetSizer-only is simpler.
    6. FontPickerCtrl2 (maxWidth=75 — production control)
    7. ThemedGenButton + DrawLabel bg (old failed attempt, FIXED_WIDTH=75)
    8. wx.Button, no bg override (font + fg only)
    9. ThemedGenButton, grow (icon picker pattern)
   10. ThemedGenButton, maxWidth=75 + ellipsis (icon picker pattern)
   11. ThemedGenButton grow — dark bg
"""

import sys
import os

# Add project root to path so we can import taskcoachlib
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import wx
import wx.lib.buttons as buttons

# wx.App must exist before importing taskcoachlib (triggers i18n/locale init)
_app = wx.App(False)

# Import the production font picker as baseline
from taskcoachlib.widgets.fontpicker import FontPickerCtrl as BaselineFontPickerCtrl


# ---------------------------------------------------------------------------
# FontPickerCtrl2 — wx.Button font picker (demo only, not used in TC app)
# Kept here for comparison. The TC app uses the baseline GenButton control
# because wx.Button has rendering artifacts (see FONT_PICKER.md).
# ---------------------------------------------------------------------------
class FontPickerCtrl2(wx.Button):
    """A plain wx.Button font picker that displays the selected font preview
    and opens wx.FontDialog on click. Optional maxWidth with pre-ellipsis.

    When maxWidth is None, the button grows to fit the font description.
    When maxWidth is set, the label is pre-ellipsized to fit."""

    def __init__(self, *args, **kwargs):
        self._fc2_font = kwargs.pop("font")
        self._fc2_colour = kwargs.pop("colour")
        self._fc2_bgColour = kwargs.pop("bgColour", None)
        self._fc2_readOnly = kwargs.pop("readOnly", False)
        self._fc2_maxWidth = kwargs.pop("maxWidth", None)
        kwargs.pop("name", None)
        super().__init__(*args, **kwargs)
        if self._fc2_maxWidth:
            self.SetMaxSize(wx.Size(self._fc2_maxWidth, -1))
        self._fc2_updateButton()
        if self._fc2_readOnly:
            self.Bind(wx.EVT_LEFT_DOWN, lambda e: None)
            self.Bind(wx.EVT_LEFT_DCLICK, lambda e: None)
        else:
            self.Bind(wx.EVT_BUTTON, self._fc2_onClick)

    def GetSelectedFont(self):
        return self._fc2_font

    def SetSelectedFont(self, font):
        self._fc2_font = font
        self._fc2_updateButton()

    def GetSelectedColour(self):
        return self._fc2_colour

    def SetSelectedColour(self, colour):
        self._fc2_colour = colour
        self._fc2_updateButton()

    def GetSelectedBgColour(self):
        return self._fc2_bgColour

    def SetSelectedBgColour(self, colour):
        self._fc2_bgColour = colour
        self._fc2_updateButton()

    def _fc2_onClick(self, event):
        event.Skip(False)
        if self._fc2_readOnly:
            return
        fontData = wx.FontData()
        fontData.SetInitialFont(self._fc2_font)
        fontData.SetColour(self._fc2_colour)
        dialog = wx.FontDialog(self, fontData)
        if wx.ID_OK == dialog.ShowModal():
            data = dialog.GetFontData()
            self._fc2_font = data.GetChosenFont()
            self._fc2_colour = data.GetColour()
            self._fc2_updateButton()
            evt = wx.FontPickerEvent(self, self.GetId(), self._fc2_font)
            self.GetEventHandler().ProcessEvent(evt)

    def _fc2_updateButton(self):
        desc = self._fc2_font.GetNativeFontInfoUserDesc()
        if self._fc2_maxWidth:
            dc = wx.ClientDC(self)
            dc.SetFont(self._fc2_font)
            available = self._fc2_maxWidth - 20
            desc = wx.Control.Ellipsize(desc, dc, wx.ELLIPSIZE_END, available)
        self.SetLabel(desc)
        self.SetFont(self._fc2_font)
        self.SetForegroundColour(self._fc2_colour)
        if self._fc2_bgColour:
            self.SetBackgroundColour(self._fc2_bgColour)
        self.InvalidateBestSize()
        self.SetInitialSize()
        parent = self.GetParent()
        while parent and not isinstance(parent, wx.TopLevelWindow):
            parent.Layout()
            parent = parent.GetParent()
        self.Refresh()


# ---------------------------------------------------------------------------
# Variation 3: Checkbox + FontPickerCtrl2 in panel (current TC pattern)
# Uses SetSizerAndFit — this is what FontEntry does. Button won't grow.
# ---------------------------------------------------------------------------
class FontEntryV3(wx.Panel):
    """Mimics production FontEntry: checkbox + FontPickerCtrl2 in a panel
    using SetSizerAndFit (locks min size)."""

    def __init__(self, parent, font, colour, bgColour=None, readOnly=False, **kwargs):
        super().__init__(parent)
        self._name = "V3-SizerAndFit"
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        self._checkBox = wx.CheckBox(self, label="")
        self._checkBox.SetValue(True)
        self._picker = FontPickerCtrl2(
            self, font=font, colour=colour, bgColour=bgColour, readOnly=readOnly)
        sizer.Add(self._checkBox, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 15)
        sizer.Add(self._picker, 1, wx.ALIGN_CENTER_VERTICAL)
        self.SetSizerAndFit(sizer)  # Locks min size
        self._picker.Bind(wx.EVT_FONTPICKER_CHANGED, self._onFontChanged)

    def _onFontChanged(self, event):
        pass

    # Forward API for test configs
    def GetSelectedFont(self):
        return self._picker.GetSelectedFont()
    def SetSelectedFont(self, f):
        self._picker.SetSelectedFont(f)
    def GetSelectedColour(self):
        return self._picker.GetSelectedColour()
    def SetSelectedColour(self, c):
        self._picker.SetSelectedColour(c)
    def GetSelectedBgColour(self):
        return self._picker.GetSelectedBgColour()
    def SetSelectedBgColour(self, c):
        self._picker.SetSelectedBgColour(c)


# ---------------------------------------------------------------------------
# Variation 4: Checkbox + FontPickerCtrl2 FLAT in panel (SetSizerAndFit)
# Same as V3 but with BORDER_NONE flat buttons.
# ---------------------------------------------------------------------------
class FontEntryV4Flat(wx.Panel):
    """Same as V3 (SetSizerAndFit) but with flat (borderless) FontPickerCtrl2."""

    def __init__(self, parent, font, colour, bgColour=None, readOnly=False, **kwargs):
        super().__init__(parent)
        self._name = "V4-Flat"
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        self._checkBox = wx.CheckBox(self, label="")
        self._checkBox.SetValue(True)
        self._picker = FontPickerCtrl2(
            self, font=font, colour=colour, bgColour=bgColour, readOnly=readOnly,
            style=wx.BORDER_NONE)
        sizer.Add(self._checkBox, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 15)
        sizer.Add(self._picker, 1, wx.ALIGN_CENTER_VERTICAL)
        self.SetSizerAndFit(sizer)
        self._picker.Bind(wx.EVT_FONTPICKER_CHANGED, self._onFontChanged)

    def _onFontChanged(self, event):
        pass

    def GetSelectedFont(self):
        return self._picker.GetSelectedFont()
    def SetSelectedFont(self, f):
        self._picker.SetSelectedFont(f)
    def GetSelectedColour(self):
        return self._picker.GetSelectedColour()
    def SetSelectedColour(self, c):
        self._picker.SetSelectedColour(c)
    def GetSelectedBgColour(self):
        return self._picker.GetSelectedBgColour()
    def SetSelectedBgColour(self, c):
        self._picker.SetSelectedBgColour(c)


# ---------------------------------------------------------------------------
# Variation 5: Checkbox + FontPickerCtrl2 in panel (fix: SetSizer only)
# Uses SetSizer instead of SetSizerAndFit — never locks min size.
# NOTE: Clearing min size + InvalidateBestSize on change also works,
#       but SetSizer-only is simpler and was kept as the chosen approach.
# ---------------------------------------------------------------------------
class FontEntryV5(wx.Panel):
    """Checkbox + FontPickerCtrl2 — uses SetSizer (no Fit) to avoid locking
    min size. Layout propagation from FontPickerCtrl2 should work naturally.
    NOTE: clearing min size + InvalidateBestSize also works, but this is simpler."""

    def __init__(self, parent, font, colour, bgColour=None, readOnly=False, **kwargs):
        super().__init__(parent)
        self._name = "V5-SetSizerOnly"
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        self._checkBox = wx.CheckBox(self, label="")
        self._checkBox.SetValue(True)
        self._picker = FontPickerCtrl2(
            self, font=font, colour=colour, bgColour=bgColour, readOnly=readOnly)
        sizer.Add(self._checkBox, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 15)
        sizer.Add(self._picker, 1, wx.ALIGN_CENTER_VERTICAL)
        self.SetSizer(sizer)  # No Fit — min size not locked
        self._picker.Bind(wx.EVT_FONTPICKER_CHANGED, self._onFontChanged)

    def _onFontChanged(self, event):
        pass

    def GetSelectedFont(self):
        return self._picker.GetSelectedFont()
    def SetSelectedFont(self, f):
        self._picker.SetSelectedFont(f)
    def GetSelectedColour(self):
        return self._picker.GetSelectedColour()
    def SetSelectedColour(self, c):
        self._picker.SetSelectedColour(c)
    def GetSelectedBgColour(self):
        return self._picker.GetSelectedBgColour()
    def SetSelectedBgColour(self, c):
        self._picker.SetSelectedBgColour(c)


# ---------------------------------------------------------------------------
# Variation 7: ThemedGenButton with bg painted in DrawLabel (old attempt)
# ---------------------------------------------------------------------------
class FontPickerV4(buttons.ThemedGenButton):
    """ThemedGenButton — native bezel via RendererNative, bg color painted
    inside DrawLabel between bezel and text. FIXED_WIDTH=75 (old approach)."""

    FIXED_WIDTH = 75

    def __init__(self, *args, **kwargs):
        self._font = kwargs.pop("font")
        self._colour = kwargs.pop("colour")
        self._bgColour = kwargs.pop("bgColour", None)
        self._readOnly = kwargs.pop("readOnly", False)
        super().__init__(*args, **kwargs)
        self.SetUseFocusIndicator(True)
        self._updateButton()
        self.Bind(wx.EVT_BUTTON, self._onClick)

    def DoGetBestSize(self):
        dc = wx.ClientDC(self)
        dc.SetFont(self.GetFont())
        _, textHeight = dc.GetTextExtent("Ay")
        height = textHeight + 10
        return wx.Size(self.FIXED_WIDTH, height)

    def DrawLabel(self, dc, width, height, dx=0, dy=0):
        if self._bgColour:
            dc.SetBrush(wx.Brush(self._bgColour))
            dc.SetPen(wx.TRANSPARENT_PEN)
            inset = 3
            dc.DrawRectangle(inset, inset, width - inset * 2, height - inset * 2)

        dc.SetFont(self.GetFont())
        dc.SetTextForeground(self.GetForegroundColour())
        label = self.GetLabel()
        padding = 8
        availableWidth = width - (padding * 2)
        ellipsizedLabel = wx.Control.Ellipsize(label, dc, wx.ELLIPSIZE_END, availableWidth)
        dc.DrawText(ellipsizedLabel, padding, (height - dc.GetTextExtent(ellipsizedLabel)[1]) // 2)

    def DrawFocusIndicator(self, dc, w, h):
        rect = wx.Rect(3, 3, w - 6, h - 6)
        wx.RendererNative.Get().DrawFocusRect(self, dc, rect)

    def GetSelectedFont(self):
        return self._font

    def SetSelectedFont(self, font):
        self._font = font
        self._updateButton()

    def GetSelectedColour(self):
        return self._colour

    def SetSelectedColour(self, colour):
        self._colour = colour
        self._updateButton()

    def GetSelectedBgColour(self):
        return self._bgColour

    def SetSelectedBgColour(self, colour):
        self._bgColour = colour
        self._updateButton()

    def _onClick(self, event):
        event.Skip(False)
        if self._readOnly:
            return
        fontData = wx.FontData()
        fontData.SetInitialFont(self._font)
        fontData.SetColour(self._colour)
        dialog = wx.FontDialog(self, fontData)
        if wx.ID_OK == dialog.ShowModal():
            data = dialog.GetFontData()
            self._font = data.GetChosenFont()
            self._colour = data.GetColour()
            self._updateButton()

    def _updateButton(self):
        self.SetLabel(self._font.GetNativeFontInfoUserDesc())
        self.SetFont(self._font)
        self.SetForegroundColour(self._colour)
        self.Refresh(eraseBackground=True)
        self.Update()


# ---------------------------------------------------------------------------
# Variation 8: Plain wx.Button, no bg override (font + fg only)
# ---------------------------------------------------------------------------
class FontPickerV5(wx.Button):
    """Plain wx.Button with font and fg only — no SetBackgroundColour."""

    def __init__(self, *args, **kwargs):
        self._font = kwargs.pop("font")
        self._colour = kwargs.pop("colour")
        self._bgColour = kwargs.pop("bgColour", None)
        self._readOnly = kwargs.pop("readOnly", False)
        super().__init__(*args, **kwargs)
        self._updateButton()
        self.Bind(wx.EVT_BUTTON, self._onClick)

    def GetSelectedFont(self):
        return self._font

    def SetSelectedFont(self, font):
        self._font = font
        self._updateButton()

    def GetSelectedColour(self):
        return self._colour

    def SetSelectedColour(self, colour):
        self._colour = colour
        self._updateButton()

    def GetSelectedBgColour(self):
        return self._bgColour

    def SetSelectedBgColour(self, colour):
        self._bgColour = colour

    def _onClick(self, event):
        event.Skip(False)
        if self._readOnly:
            return
        fontData = wx.FontData()
        fontData.SetInitialFont(self._font)
        fontData.SetColour(self._colour)
        dialog = wx.FontDialog(self, fontData)
        if wx.ID_OK == dialog.ShowModal():
            data = dialog.GetFontData()
            self._font = data.GetChosenFont()
            self._colour = data.GetColour()
            self._updateButton()

    def _updateButton(self):
        self.SetLabel(self._font.GetNativeFontInfoUserDesc())
        self.SetFont(self._font)
        self.SetForegroundColour(self._colour)
        self.Refresh()


# ---------------------------------------------------------------------------
# Variation 9: ThemedGenButton, grow (icon picker pattern)
# ---------------------------------------------------------------------------
class FontPickerV6(buttons.ThemedGenButton):
    """ThemedGenButton following the icon picker pattern.
    Grows to fit content. Custom DrawLabel with bg preview and fg color.
    No width constraint."""

    PADDING = 8

    def __init__(self, *args, **kwargs):
        self._font = kwargs.pop("font")
        self._colour = kwargs.pop("colour")
        self._bgColour = kwargs.pop("bgColour", None)
        self._readOnly = kwargs.pop("readOnly", False)
        super().__init__(*args, **kwargs)
        self.SetUseFocusIndicator(True)
        self._updateButton()
        self.Bind(wx.EVT_BUTTON, self._onClick)

    def DoGetBestSize(self):
        dc = wx.ClientDC(self)
        dc.SetFont(self.GetFont())
        tw, th = dc.GetTextExtent(self.GetLabel())
        width = self.PADDING * 2 + tw
        height = th + self.PADDING * 2
        return wx.Size(width, height)

    def DrawLabel(self, dc, width, height, dx=0, dy=0):
        if not self.up:
            dx = dy = self.labelDelta

        # Paint bg color preview as inset rectangle
        if self._bgColour:
            dc.SetBrush(wx.Brush(self._bgColour))
            dc.SetPen(wx.TRANSPARENT_PEN)
            inset = 3
            dc.DrawRectangle(inset + dx, inset + dy,
                             width - inset * 2, height - inset * 2)

        dc.SetFont(self.GetFont())
        if self.IsEnabled():
            dc.SetTextForeground(self._colour)
        else:
            dc.SetTextForeground(wx.SystemSettings.GetColour(wx.SYS_COLOUR_GRAYTEXT))

        label = self.GetLabel()
        tw, th = dc.GetTextExtent(label)
        dc.DrawText(label, self.PADDING + dx, (height - th) // 2 + dy)

    def DrawFocusIndicator(self, dc, w, h):
        rect = wx.Rect(3, 3, w - 6, h - 6)
        wx.RendererNative.Get().DrawFocusRect(self, dc, rect)

    def GetSelectedFont(self):
        return self._font

    def SetSelectedFont(self, font):
        self._font = font
        self._updateButton()

    def GetSelectedColour(self):
        return self._colour

    def SetSelectedColour(self, colour):
        self._colour = colour
        self._updateButton()

    def GetSelectedBgColour(self):
        return self._bgColour

    def SetSelectedBgColour(self, colour):
        self._bgColour = colour
        self._updateButton()

    def _onClick(self, event):
        event.Skip(False)
        if self._readOnly:
            return
        fontData = wx.FontData()
        fontData.SetInitialFont(self._font)
        fontData.SetColour(self._colour)
        dialog = wx.FontDialog(self, fontData)
        if wx.ID_OK == dialog.ShowModal():
            data = dialog.GetFontData()
            self._font = data.GetChosenFont()
            self._colour = data.GetColour()
            self._updateButton()

    def _updateButton(self):
        self.SetLabel(self._font.GetNativeFontInfoUserDesc())
        self.SetFont(self._font)
        self.SetInitialSize()
        self.GetParent().Layout()
        self.Refresh(eraseBackground=True)
        self.Update()


# ---------------------------------------------------------------------------
# Variation 10: ThemedGenButton, maxWidth + ellipsis (icon picker pattern)
# ---------------------------------------------------------------------------
class FontPickerV7(buttons.ThemedGenButton):
    """ThemedGenButton following the icon picker pattern with maxWidth.
    Uses wx.Control.Ellipsize() in DrawLabel — same as IconPickerButton."""

    PADDING = 8

    def __init__(self, *args, **kwargs):
        self._font = kwargs.pop("font")
        self._colour = kwargs.pop("colour")
        self._bgColour = kwargs.pop("bgColour", None)
        self._readOnly = kwargs.pop("readOnly", False)
        self._maxWidth = kwargs.pop("maxWidth", 75)
        super().__init__(*args, **kwargs)
        self.SetUseFocusIndicator(True)
        self.SetMinSize(wx.Size(self._maxWidth, -1))
        self.SetMaxSize(wx.Size(self._maxWidth, -1))
        self._updateButton()
        self.Bind(wx.EVT_BUTTON, self._onClick)

    def DoGetBestSize(self):
        dc = wx.ClientDC(self)
        dc.SetFont(self.GetFont())
        _, th = dc.GetTextExtent("Ay")
        height = th + self.PADDING * 2
        return wx.Size(self._maxWidth, height)

    def DrawLabel(self, dc, width, height, dx=0, dy=0):
        if not self.up:
            dx = dy = self.labelDelta

        # Paint bg color preview as inset rectangle
        if self._bgColour:
            dc.SetBrush(wx.Brush(self._bgColour))
            dc.SetPen(wx.TRANSPARENT_PEN)
            inset = 3
            dc.DrawRectangle(inset + dx, inset + dy,
                             width - inset * 2, height - inset * 2)

        dc.SetFont(self.GetFont())
        if self.IsEnabled():
            dc.SetTextForeground(self._colour)
        else:
            dc.SetTextForeground(wx.SystemSettings.GetColour(wx.SYS_COLOUR_GRAYTEXT))

        label = self.GetLabel()
        available_width = width - self.PADDING * 2
        if available_width > 0:
            label = wx.Control.Ellipsize(label, dc, wx.ELLIPSIZE_END, available_width)

        tw, th = dc.GetTextExtent(label)
        dc.DrawText(label, self.PADDING + dx, (height - th) // 2 + dy)

    def DrawFocusIndicator(self, dc, w, h):
        rect = wx.Rect(3, 3, w - 6, h - 6)
        wx.RendererNative.Get().DrawFocusRect(self, dc, rect)

    def GetSelectedFont(self):
        return self._font

    def SetSelectedFont(self, font):
        self._font = font
        self._updateButton()

    def GetSelectedColour(self):
        return self._colour

    def SetSelectedColour(self, colour):
        self._colour = colour
        self._updateButton()

    def GetSelectedBgColour(self):
        return self._bgColour

    def SetSelectedBgColour(self, colour):
        self._bgColour = colour
        self._updateButton()

    def _onClick(self, event):
        event.Skip(False)
        if self._readOnly:
            return
        fontData = wx.FontData()
        fontData.SetInitialFont(self._font)
        fontData.SetColour(self._colour)
        dialog = wx.FontDialog(self, fontData)
        if wx.ID_OK == dialog.ShowModal():
            data = dialog.GetFontData()
            self._font = data.GetChosenFont()
            self._colour = data.GetColour()
            self._updateButton()

    def _updateButton(self):
        self.SetLabel(self._font.GetNativeFontInfoUserDesc())
        self.SetFont(self._font)
        self.Refresh(eraseBackground=True)
        self.Update()


# ---------------------------------------------------------------------------
# Demo Frame
# ---------------------------------------------------------------------------
class FontPickerDemoFrame(wx.Frame):
    def __init__(self):
        super().__init__(None, title="Font Picker Demo — 11 Variations", size=(950, 900))

        scrolled = wx.ScrolledWindow(self)
        scrolled.SetScrollRate(0, 10)

        mainSizer = wx.BoxSizer(wx.VERTICAL)

        # Reference buttons for size comparison
        refSizer = wx.BoxSizer(wx.HORIZONTAL)
        refSizer.Add(wx.StaticText(scrolled, label="Reference buttons:"),
                     0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        refSizer.Add(wx.Button(scrolled, label="OK"), 0, wx.RIGHT, 5)
        refSizer.Add(wx.Button(scrolled, label="Cancel"), 0, wx.RIGHT, 5)
        refSizer.Add(wx.Button(scrolled, label="A Standard Button"), 0, wx.RIGHT, 5)
        mainSizer.Add(refSizer, 0, wx.ALL, 10)
        mainSizer.Add(wx.StaticLine(scrolled), 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        # Test fonts and colors
        defaultFont = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
        boldFont = wx.Font(defaultFont)
        boldFont.SetWeight(wx.FONTWEIGHT_BOLD)
        italicFont = wx.Font(12, wx.FONTFAMILY_ROMAN, wx.FONTSTYLE_ITALIC, wx.FONTWEIGHT_NORMAL)

        black = wx.Colour(0, 0, 0)
        red = wx.Colour(200, 0, 0)
        blue = wx.Colour(0, 0, 180)
        lightYellow = wx.Colour(255, 255, 220)
        lightBlue = wx.Colour(220, 230, 255)

        sysFg = wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOWTEXT)

        white = wx.Colour(255, 255, 255)

        # Variations 3-5 are panel-wrapped (checkbox + picker), use different class
        variations = [
            ("1. Baseline (GenButton — production)", BaselineFontPickerCtrl, {}, False),
            ("2. FontPickerCtrl2 (grow)", FontPickerCtrl2, {}, False),
            ("3. Checkbox + FPC2 panel (SetSizerAndFit — BROKEN, won't grow)", FontEntryV3, {}, True),
            ("4. Checkbox + FPC2 FLAT panel (SetSizerAndFit, BORDER_NONE)", FontEntryV4Flat, {}, True),
            ("5. Checkbox + FPC2 panel (fix: SetSizer only, no Fit)", FontEntryV5, {}, True),
            ("6. FontPickerCtrl2 (maxWidth=75)", FontPickerCtrl2, {"maxWidth": 75}, False),
            ("7. ThemedGenButton + DrawLabel bg (old, FIXED_WIDTH=75)", FontPickerV4, {}, False),
            ("8. wx.Button, no bg override", FontPickerV5, {}, False),
            ("9. ThemedGenButton, grow (icon picker pattern) \u2605", FontPickerV6, {}, False),
            ("10. ThemedGenButton, maxWidth=75 + ellipsis (icon picker pattern) \u2605", FontPickerV7, {"maxWidth": 75}, False),
        ]

        test_configs = [
            ("Default font, system colors", defaultFont, sysFg, None, False),
            ("Bold, red text", boldFont, red, None, False),
            ("Italic serif, blue on yellow", italicFont, blue, lightYellow, False),
            ("Default, system fg on light blue", defaultFont, sysFg, lightBlue, False),
            ("White on black", defaultFont, white, black, False),
            ("Read-only, italic serif, blue on yellow", italicFont, blue, lightYellow, True),
        ]


        for var_label, PickerClass, extra_kwargs, is_panel in variations:
            section = wx.StaticBoxSizer(wx.VERTICAL, scrolled, var_label)
            grid = wx.FlexGridSizer(cols=2, vgap=5, hgap=10)
            grid.AddGrowableCol(1, 1)

            for cfg_label, font, colour, bgColour, readOnly in test_configs:
                label = wx.StaticText(scrolled, label=cfg_label)
                if is_panel:
                    kwargs = dict(font=font, colour=colour, readOnly=readOnly)
                    kwargs.update(extra_kwargs)
                    if bgColour:
                        kwargs["bgColour"] = bgColour
                    picker = PickerClass(scrolled, **kwargs)
                else:
                    kwargs = dict(font=font, colour=colour, readOnly=readOnly)
                    kwargs.update(extra_kwargs)
                    if bgColour:
                        kwargs["bgColour"] = bgColour
                    picker = PickerClass(scrolled, **kwargs)

                grid.Add(label, 0, wx.ALIGN_CENTER_VERTICAL)
                grid.Add(picker, 0, wx.ALIGN_CENTER_VERTICAL)

            section.Add(grid, 1, wx.EXPAND | wx.ALL, 5)
            mainSizer.Add(section, 0, wx.EXPAND | wx.ALL, 5)

        # --- Variation 11: ThemedGenButton grow — dark bg ---
        section = wx.StaticBoxSizer(wx.VERTICAL, scrolled,
                                    "11. ThemedGenButton grow — dark bg")
        grid = wx.FlexGridSizer(cols=2, vgap=5, hgap=10)
        grid.AddGrowableCol(1, 1)

        for cfg_label, font, colour, bgColour, readOnly in test_configs:
            label = wx.StaticText(scrolled, label=cfg_label)
            kwargs = dict(font=font, colour=colour, readOnly=readOnly)
            if bgColour:
                kwargs["bgColour"] = bgColour
            picker = FontPickerV6(scrolled, **kwargs)
            grid.Add(label, 0, wx.ALIGN_CENTER_VERTICAL)
            grid.Add(picker, 0, wx.ALIGN_CENTER_VERTICAL)

        section.Add(grid, 1, wx.EXPAND | wx.ALL, 5)
        mainSizer.Add(section, 0, wx.EXPAND | wx.ALL, 5)

        scrolled.SetSizer(mainSizer)

        # Set virtual size for scrolling
        mainSizer.Layout()
        scrolled.FitInside()


def main():
    frame = FontPickerDemoFrame()
    frame.Show()
    _app.MainLoop()


if __name__ == "__main__":
    main()
