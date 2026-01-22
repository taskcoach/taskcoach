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

### Single-Line Text Box Patches

Using `StyledTextCtrl` for a single-line field (like Subject) requires several patches to make it behave like a standard single-line text entry:

| #  | Problem                      | Solution                                         | Status     |
|----|------------------------------|--------------------------------------------------|------------|
| 1  | Enter key creates newlines   | `CmdKeyClear(STC_KEY_RETURN, 0)`                 | Done       |
| 2  | Height too small for scrollbar| 50% extra height: `int(baseHeight * 1.5)`       | Done       |
| 3  | Paste can include newlines   | `EVT_KEY_DOWN` intercepts Ctrl+V, strips newlines| Done       |
| 4  | Word wrap enabled            | `SetWrapMode(STC_WRAP_NONE)`                     | Done       |
| 5  | Vertical scrollbar           | `SetUseVerticalScrollBar(False)`                 | Done       |
| 6  | H-scrollbar with no text     | `SetScrollWidth(1)` + `SetScrollWidthTracking(True)` | Done   |
| 7  | Scrollbar stays after delete | Reset `SetScrollWidth(1)` on text change        | Done       |
| 8  | Rich text paste (fonts)      | STC is plain text by default                     | N/A        |
| 9  | Tables/images                | STC doesn't render these                         | N/A        |
| 10 | Hyperlinks                   | Acceptable per requirements                      | Keep as-is |

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

## References

- [pyenchant documentation](https://pyenchant.github.io/pyenchant/)
- [Scintilla indicators](https://www.scintilla.org/ScintillaDoc.html#Indicators)
- [wxStyledTextCtrl key mapping](https://proton-ce.sourceforge.net/rc/scintilla/pyframe/www.pyframe.com/stc/keymap.html)
- [WINDOWS.md - Spell Check Dictionaries](WINDOWS.md#spell-check-dictionaries)
