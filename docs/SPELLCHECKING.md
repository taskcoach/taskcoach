# Spell Checking Implementation

Task Coach uses [pyenchant](https://pyenchant.github.io/pyenchant/) with Hunspell dictionaries for spell checking in Subject and Description fields.

## Installation

### Linux (Debian/Ubuntu)
```bash
sudo apt install python3-enchant hunspell-en-us
```

### Linux (Arch)
```bash
sudo pacman -S python-pyenchant hunspell-en_us
```

### Linux (Fedora)
```bash
sudo dnf install python3-enchant hunspell-en-US
```

### Windows
Dictionaries must be bundled with the application. See [WINDOWS.md](WINDOWS.md#spell-check-dictionaries) for details on dictionary installation and bundling.

### macOS
```bash
brew install enchant
pip install pyenchant
```

## Text Fields Overview

Task Coach has the following text-based input fields:

| Field       | Widget              | Multi-line | Max Length | Spell Check | Used In                      |
|-------------|---------------------|------------|------------|-------------|------------------------------|
| Subject     | SingleLineTextCtrl  | No         | None       | Yes         | Task, Note, Category, Effort |
| Description | MultiLineTextCtrl   | Yes        | None       | Yes         | Task, Note, Category, Effort |
| Location    | SingleLineTextCtrl  | No         | None       | No          | Attachment (file path/URL)   |

**Notes:**
- No maximum length has ever been enforced on any text field (stored as Python strings)
- Subject and Description use `wx.stc.StyledTextCtrl` internally for spell check squiggle support
- Location does not have spell check (file paths/URLs should not be spell checked)
- `SingleLineTextCtrl` is `MultiLineTextCtrl` with `singleLine=True` parameter

## Technical Implementation

### The Squiggle Problem

Red squiggly underline support varies by platform and control:

| Platform  | wx.TextCtrl.SetStyle() | wx.stc.StyledTextCtrl | Native EnableProofCheck() |
|-----------|------------------------|----------------------|---------------------------|
| Windows   | Works (TE_RICH2)       | **Works**            | Not in wxPython           |
| macOS     | Works (multiline only) | **Works**            | Not in wxPython           |
| Linux/GTK | **Does NOT work**      | **Works**            | Not in wxPython           |

**Summary:**
- `wx.TextCtrl.SetStyle()` - Platform-dependent, fails on Linux/GTK
- `wx.stc.StyledTextCtrl` - **Cross-platform**, works everywhere (our solution)
- `EnableProofCheck()` - Native wxWidgets method, not wrapped in wxPython 4.2.x

### Solution: StyledTextCtrl (Scintilla)

We use `wx.stc.StyledTextCtrl` (Scintilla editor component) which provides cross-platform indicator support:

```python
# Red squiggly underline indicator
self.IndicatorSetStyle(SPELLCHECK_INDICATOR, stc.STC_INDIC_SQUIGGLE)
self.IndicatorSetForeground(SPELLCHECK_INDICATOR, wx.RED)

# Mark misspelled word
self.IndicatorFillRange(byte_start, byte_length)
```

This approach is used by other wxPython applications like [WikidPad](https://github.com/WikidPad/WikidPad).

### Keyboard Navigation (Spreadsheet Convention)

Using `StyledTextCtrl` means Scintilla captures Tab and Enter by default. Task Coach uses the spreadsheet convention (like Excel / LibreOffice Calc) so plain Tab and Enter navigate instead of inserting characters. Modified keys insert the character:

| Key              | Single-line (Subject)     | Multiline (Description)    |
|------------------|---------------------------|----------------------------|
| Tab              | Navigate to next control  | Navigate to next control   |
| Shift+Tab        | Navigate to prev control  | Navigate to prev control   |
| Ctrl+Tab         | Switch notebook tab (OS)  | Switch notebook tab (OS)   |
| Enter            | Navigate to next control  | Insert newline (normal)    |
| Ctrl+V           | Paste (newlines stripped) | Paste (normal)             |

**Implementation:** `CmdKeyClear` removes Scintilla's default Tab binding in all modes, and Enter binding in single-line mode. `EVT_KEY_DOWN` in `_onKeyDown` handles Tab navigation and single-line Enter navigation. Tab always navigates — no literal tab insertion (Ctrl+Tab is reserved for notebook tab switching). In multiline mode, Enter inserts newlines normally (Scintilla default). Tab navigation uses `Navigate()` which preserves forward/backward direction.

### Single-Line Text Box Patches

Using `StyledTextCtrl` for a single-line field (like Subject) requires several patches to make it behave like a standard single-line text entry:

| #  | Problem                      | Solution                                         | Status     |
|----|------------------------------|--------------------------------------------------|------------|
| 1  | Enter key creates newlines   | `CmdKeyClear(STC_KEY_RETURN, 0)` + navigate focus| Done       |
| 2  | Tab key inserts tab char     | `CmdKeyClear(STC_KEY_TAB, 0)` + navigate focus   | Done (all modes) |
| 3  | Height too small for scrollbar| 50% extra height: `int(baseHeight * 1.5)`       | Done       |
| 4  | Paste can include newlines   | `EVT_KEY_DOWN` intercepts Ctrl+V, strips newlines| Done       |
| 5  | Word wrap enabled            | `SetWrapMode(STC_WRAP_NONE)`                     | Done       |
| 6  | Scrollbars visible           | `SetUseVerticalScrollBar(False)` + `SetUseHorizontalScrollBar(False)` | Done |
| 7  | Rich text paste (fonts)      | STC is plain text by default                     | N/A        |
| 8  | Tables/images                | STC doesn't render these                         | N/A        |
| 9  | Hyperlinks                   | Acceptable per requirements                      | Keep as-is |

### Fallback Option

If the StyledTextCtrl approach proves too complex, a fallback is possible:

- Use standard `wx.TextCtrl` for Subject field
- Spell checking still works (suggestions via right-click menu)
- **No red squiggly underline** on Linux/GTK (visual feedback only)
- Description field would still have squiggly (it's multiline)

This fallback trades visual consistency for implementation simplicity.

## Configuration

Spell checking is configured in **Edit > Preferences > Regional**:

- **Enable spell checking**: Toggle on/off
- **Language**: Dropdown shows installed dictionaries (auto-detects system language if not set)

## Theme-Aware STC Improvements

The `_StyledTextCtrl` class responds to system theme colours (light/dark) instead of using hardcoded values.

### 1. Theme Colours (`_applyThemeColours` method) — Done

Uses system colours for text, background, caret, and selection:

```python
def _applyThemeColours(self):
    font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
    self.StyleSetFont(stc.STC_STYLE_DEFAULT, font)
    self.StyleSetForeground(stc.STC_STYLE_DEFAULT, wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOWTEXT))
    self.StyleSetBackground(stc.STC_STYLE_DEFAULT, wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOW))
    self.StyleClearAll()
    self.SetCaretForeground(wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOWTEXT))
    self.SetSelBackground(True, wx.SystemSettings.GetColour(wx.SYS_COLOUR_HIGHLIGHT))
    self.SetSelForeground(True, wx.SystemSettings.GetColour(wx.SYS_COLOUR_HIGHLIGHTTEXT))
```

**Note:** `StyleSetBackground` sets Scintilla's internal rendering background, which may affect `GetBackgroundColour()` on GTK. The wrapper panel's background must be set from the parent (not the STC) to avoid white corners at the rounded border.

### 2. System Link Colour for URLs — Planned

URL indicators currently use hardcoded `wx.BLUE`. Replace with system link colour:

```python
linkColour = wx.SystemSettings.GetColour(wx.SYS_COLOUR_HOTLIGHT)
self.IndicatorSetForeground(self.URL_INDICATOR, linkColour)
self.IndicatorSetHoverForeground(self.URL_INDICATOR, linkColour)
self.SetHotspotActiveForeground(True, linkColour)
```

### 3. Live Theme Switching — Done

The `MultiLineTextCtrl` wrapper detects theme changes and re-applies colours. On GTK, `EVT_SYS_COLOUR_CHANGED` doesn't reliably reach children, so the wrapper polls via `EVT_PAINT` and calls `_applyThemeColours` when a change is detected.

**Important:** Panel bg must come from `self.GetParent().GetBackgroundColour()` (not the STC) so rounded corners blend with the dialog background.

---

## References

- [pyenchant documentation](https://pyenchant.github.io/pyenchant/)
- [Scintilla indicators](https://www.scintilla.org/ScintillaDoc.html#Indicators)
- [wxStyledTextCtrl key mapping](https://proton-ce.sourceforge.net/rc/scintilla/pyframe/www.pyframe.com/stc/keymap.html)
- [WINDOWS.md - Spell Check Dictionaries](WINDOWS.md#spell-check-dictionaries)
