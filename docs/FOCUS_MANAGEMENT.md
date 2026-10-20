# Focus Management

How the controls answer the focus moving between them, the same on
every platform. Interaction rules change only with a ruling
([DEVELOPMENT.md](DEVELOPMENT.md)); the lists' rules are in
[LIST_MANAGEMENT.md](LIST_MANAGEMENT.md).

1. [Only the Focused Control Shows a Selection](#only-the-focused-control-shows-a-selection)
2. [Platforms](#platforms)
3. [Not Changed](#not-changed)
4. [Read-Only Displays](#read-only-displays)
5. [The Markdown Preview](#the-markdown-preview)

## Only the Focused Control Shows a Selection

**Ruled by designer 2026-10-08**, one rule on every platform: in a
window, when a control gets the focus, every other text control of
that window drops its selection; its caret stays where it was. Other
windows keep theirs (an editor beside the main window, a dialog), and
so does a text control whose window opens a menu or loses the focus
to another program: no control of the window got it.

It covers every text control: the Subject and Description boxes
(Scintilla) and the native text fields (numbers, amounts, spin boxes,
the search box). The date, time and duration fields draw their
highlighted part only while they have the focus
(`widgets/maskedtimectrl.py`, since #190).

Code: `gui/focus.py`, installed on the application beside `pagekeys`
(`application.py`): one handler of `EVT_CHILD_FOCUS`, which every
focus change in a window sends up to the application. Until
2026-10-08 the spin box dropped its own selection (#190) and the
Subject and Description boxes kept theirs; the rule replaces both.

If users ask for GTK's way back (below), this is the place to change.

## Platforms

Researched 2026-10-08: a native text field's selection when the user
clicks into another field of the same window.

| Platform | The other field's selection | Source |
|---|---|---|
| Windows | hidden; shown again when its window gets the focus back | [ES_NOHIDESEL](https://learn.microsoft.com/en-us/windows/win32/controls/edit-control-styles), [wxTE_NOHIDESEL](https://docs.wxwidgets.org/3.2/classwx_text_ctrl.html) |
| macOS | not shown: it lives in the field editor, which only the focused field has | [wxWidgets 1e70e49](https://github.com/wxWidgets/wxWidgets/commit/1e70e497e23f8f0770d9fa2709bd2760dfed935d) |
| Qt (KDE) | cleared, except for a menu or another window | [`QLineEdit::focusOutEvent`](https://raw.githubusercontent.com/qt/qtbase/dev/src/widgets/widgets/qlineedit.cpp) |
| GTK 3 | kept and drawn | [`gtk_entry_focus_out`](https://gitlab.gnome.org/GNOME/gtk/-/raw/gtk-3-24/gtk/gtkentry.c); seen in the search box |

The Subject and Description boxes are Scintilla, which draws its
selection whatever the focus
([EditView.cxx, wxWidgets 3.2.7](https://github.com/wxWidgets/wxWidgets/blob/v3.2.7/src/stc/scintilla/src/EditView.cxx)),
so they kept it on every platform. The rule clears, as Qt does, in
the window only: a click back into a field puts the caret where it is
clicked anyway.

## Not Changed

- **A click** puts the caret where it is clicked; the old selection
  is gone, as on every platform.
- **Tab into a field**: native text fields select all their text
  (Windows' dialog manager,
  [`DLGC_HASSETSEL`](https://devblogs.microsoft.com/oldnewthing/20031114-00/?p=41823);
  GTK's
  [`gtk-entry-select-on-focus`](https://docs.gtk.org/gtk3/property.Settings.gtk-entry-select-on-focus.html);
  macOS). The Subject and Description boxes keep their caret instead:
  P251 in [REFINEMENT_REFACTOR.md](REFINEMENT_REFACTOR.md), not
  changed.

## Read-Only Displays

A value shown but not editable (the Appearance tab's derived and
effective colours, fonts and icons; the Dates tab's status) is a
display: Tab passes it by, and it keeps no focus
(`widgets.skip_focus`; `AcceptsFocusFromKeyboard` is False). Focus
reaching one another way (code, a container giving back its last
focus) moves on to the next field once handled, and only if it is
still there: moved on meanwhile, it stays.

It moves on from the display itself. On Windows and macOS `Navigate()`
moves from wherever the focus is (`wxWindowBase::DoNavigateIn`), so
from a picker's inner button it would come back to the picker's own
handler without end: the Appearance tab's crash on Windows (#487). GTK
moves the focus itself and sends no navigation event.

## The Markdown Preview

Unlike a display, a Description box's preview takes the focus, by Tab
or a click: it scrolls with the keys, and F2 swaps it with the edit
box ([MARKDOWN.md](MARKDOWN.md)). It shows the focus with the same
style as the edit box, and so as any text box, in the user's system
theme: **ruled by designer 2026-10-19**, "the user should have the
same focus style on the edit box as a preview (as any other edit box),
per their system theme style", and "match the system theme always".

The theme draws a text box's field and frame in one call (wxGTK
`DrawTextCtrl()`: `gtk_render_background`, then `gtk_render_frame`),
so the preview draws the focused text box into a bitmap and masks the
field's colour, read in its middle
(`MultiLineTextCtrl._focused_frame()`): what is left is the theme's
focus highlight, pixel for pixel the edit box's, without the field
that would make an input box of read-only text
([DEVELOPMENT.md](DEVELOPMENT.md#design), Read-only looks read-only).
So the look is the theme's on every desktop: GTK draws the theme's
focused entry, macOS its focus ring (`HIThemeDrawFrame`, focused);
wx's Windows renderer draws no focused state, so on Windows neither
box shows a highlight (P271 in
[REFINEMENT_REFACTOR.md](REFINEMENT_REFACTOR.md#found-2026-10-19)).

F2 swaps the box from the box, in both modes, and from its
Edit/Preview button, as a click on the button does, the focus staying
on the button.
