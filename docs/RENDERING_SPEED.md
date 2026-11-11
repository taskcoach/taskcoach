# Rendering Speed

Opening an editor or Preferences and changing their tabs: what was
measured, the causes of the gray window and of the flicker at each tab
change and their fixes, and where the rest of the time goes. Asked by
the designer, 2026-11-10: "I see the window all gray first. And then I
see a next pass or maybe iteratively the tabs and fields." Then: "when
I change tabs, I see a flicker that I don't typically see in most
apps", and in Preferences "I don't see it rendering yet, and after
that it opens up and renders".

1. [How It Was Measured](#how-it-was-measured)
2. [The Gray Window](#the-gray-window)
3. [Before the Window Appears](#before-the-window-appears)
4. [Changing Tabs](#changing-tabs)
5. [Opening Preferences](#opening-preferences)
6. [Lists Repaint on Every Scrollbar Fade Frame](#lists-repaint-on-every-scrollbar-fade-frame)

## How It Was Measured

Measured 2026-11-10, do not repeat: the numbers below are the
reference.

- The full app on a virtual display (Adwaita, GTK 3.24.49, wxPython
  4.2.3), the task editor of the `Welcome.tsk`
  task "Markdown preview", opened from the task list with Return.
- The screen recorded at 60 frames a second with its clock
  (`ffmpeg -f x11grab -framerate 60 -copyts`), each frame compared
  with the editor fully drawn: the gray time is from the frame where
  its title bar shows to the frame with its tab strip and first
  field.
- The app's log with milliseconds: each queued call run, each AUI
  layout (`AuiManager.DoUpdate()`) with its caller, each GTK draw of
  the editor (`meta/geometry_trace.py`).
- Times depend on the computer's load, wall and CPU alike (load 7 to
  20 on 12 cores): runs with and without a change were alternated in
  the same session, and counts (layouts, frames, repaints) compared.

## The Gray Window

Fixed 2026-11-10.

The sequence: the editor is built (0.3 to 0.5 s, nothing shows
yet); the window appears all gray but for its Close button; 100 to
180 ms later the tabs and fields appear at once.

Cause: the tabs are an AGW `AuiNotebook`, whose `Update()` lays out
nothing: it queues a whole layout (`wx.CallAfter(self.DoUpdate)`,
`wx/lib/agw/aui/framemanager.py` line 6200). The build asks for one
in `InitNotebook`, `GetActiveTabCtrl`, `RemoveEmptyTabFrames` and
more, and each runs only after the window is shown: GTK draws it
first with the page at its default 200x200 and the tab strip not yet
placed, so gray, then 5 layouts (10 to 32 ms each) follow before the
tabs and fields show.

Fix: `widgets.Notebook` queues one layout for all the requests made
before it runs (`__queue_layout()`), and the editor lays its notebook
out once at the end of its build, at its final size (`layout_now()`):
the first frame drawn has the tabs and fields. Preferences, the other
`widgets.Notebook`, does the same since 2.0.3.11
([Opening Preferences](#opening-preferences)).

| Six opens in a row, alternated | Gray after the window appears | Layouts after the show |
|---|---|---|
| Before | 100 to 116 ms (6 to 7 frames) | 5 |
| After | 17 to 33 ms (1 to 2 frames: GTK's first draw) | 2 |

The 2 left: the one AGW queues itself while the notebook is made,
before Task Coach can take it over, and one asked after the build;
both find the layout done. Tests: `EditorTest` (nothing moves when the
queued work runs after the build), `AuiManagerTest` (three requests,
one layout).

## Before the Window Appears

Not changed. The build itself, 0.3 to 0.5 s of CPU and 253 windows,
makes every tab of the task editor, though one shows. Where it goes
(py-spy, six opens):

| Part | Share |
|---|---|
| The five list tabs (prerequisites, categories, effort, notes, attachments) | 37% (Notes alone 20%) |
| The Dates tab | 24% |
| Check box and radio images, drawn again for each tree list (`customtreectrl.GetControlBmp()`, 10 per tree) | 10% |
| The notebook's static texts (`__createStaticTextControlIfNeeded`) | 7% |
| The stack the `wx.CallAfter` guard formats at each call (`workarounds/monkeypatches.py`) | 4% |

The 76 calls the build queues run after the show in a few
milliseconds together (51 of them a column width pass, one per column
added in the list tabs).

## Changing Tabs

Fixed 2026-11-10 (2.0.3.11).

Each tab change of an editor or of Preferences showed one frame, 16 to
33 ms, with the notebook empty: no tabs, no page, only the dialog's
background and buttons. Eight tab changes of the task editor recorded:
seven had it.

Cause: `Notebook.SetSelection()` froze the notebook, so that AGW's
forced paint of the tab rows would not draw the new page unplaced
([AUI.md](AUI.md#page-painted-over-the-tabs)). A frozen window in
wxGTK draws nothing, and the forced paint draws the whole window: the
notebook empty, until the thaw repainted it.

Fix: no forced paint during a tab change. The new tab shows selected,
the next frame the new page, the old page staying until then; nothing
shows empty, and no page draws over the tabs (each tab's first visit
checked, the editor resized to the screen). Tests: `AuiManagerTest`.

The work per tab change, timed in the app (py-spy's native sampling
slowed the app many times over here, its numbers are not times):

| | Editor | Preferences |
|---|---|---|
| The tab change in all (`SetSelection()`) | 4 to 10 ms | 5 to 27 ms |
| AGW drawing the tab row to check the tab shows (`MakeTabVisible()`), once | 3 to 7 ms | 3 to 14 ms |
| Each focus change dropping the other fields' selections (`gui/focus.py`), 2 to 4 per tab change | under 1.5 ms | |

A first visit costs more: the editor's Prerequisites and Categories
tabs build their lists then (100 and 56 ms), and the first visit to
Preferences' Regional, Durations and Statuses tabs sends the notebook
a size event, its size unchanged, whose AGW handler lays it out and
repaints it at once. The Statuses tab takes 85 to 100 ms to show at
every visit: about 90 controls, a row per status, drawn by GTK (69%
of the time, no Python) and Python for its font pickers
(`widgets/fontpicker.py`, a `wx.lib.buttons.GenButton`).

## Opening Preferences

Changed 2026-11-10 (2.0.3.11).

From Alt+P to the first frame, about 0.5 s on this computer (0.45 to
0.7 s with its load). The window appears 0.3 to 0.6 s after the key:
Preferences builds its ten pages first.

| Page | Build |
|---|---|
| Statuses | 60 to 100 ms |
| Language, Task dates, Durations, Features | 30 to 65 ms each |
| Files, Theme | 25 to 55 ms each |
| Reminders, Icons, Windows | 6 to 30 ms each |

The notebook's layout ran after the window showed: three layouts, the
first a whole one (14 to 19 ms). Now Preferences lays its notebook out
at the end of its build, before the show (`layout_now()`, as the
editor), and the two left find it done (1 ms each). Test:
`PreferencesTest`.

What stays: the window manager draws the window's frame when the
window appears, and GTK its inside at its first frame, 45 to 75 ms
later; without a compositor, what was on the screen shows through the
frame until then (the editor the same). Building only the page shown,
the others at their first visit as the editor's list tabs do, would
make the window appear about 0.3 s sooner: not done (**ruled by
designer 2026-11-10**, the time to open does not matter, flicker
does: "It's okay that the window takes a little bit longer to open
the first time. It can even be slower. It just, we want to avoid some
ridiculous flickering, which should absolutely not occur in modern
apps like this.").

## Lists Repaint on Every Scrollbar Fade Frame

Not the editor's: recorded as P274 in
[REFINEMENT_REFACTOR.md](REFINEMENT_REFACTOR.md#found-2026-11-10).

One click on a row, or the pointer moved over the task list, with
the main window filling a 1600x1000 screen (35 rows) and a 1,000-task
file (`tools/generate_task_file.py`, reminders taken out):

| Desktop setting | Full repaints of the list | Time painting |
|---|---|---|
| GTK default (overlay scrollbars, animations on) | 72 to 76 | 1.8 to 1.9 s |
| Animations off (`gtk-enable-animations=false`) | 3 to 4 | 70 to 85 ms |
| Overlay scrolling off (`GTK_OVERLAY_SCROLLING=0`) | 1 to 2 | |

Master the same. No `Refresh` comes from Task Coach: GTK asks. Its
source (`gtk/gtkscrolledwindow.c`, 3.24.38): an overlay scrollbar
shows on pointer motion or scrolling and fades in and out over 1 s
(`INDICATOR_FADE_OUT_DURATION`, line 191), 2 s after the last
movement (`INDICATOR_FADE_OUT_DELAY`, line 190); a frame callback
(`indicator_fade_cb`, line 4393) changes the scrollbar's opacity and
queues a draw on every frame (lines 4345 to 4348), when animations
are on (`gtk_widget_should_animate`, line 4388). The list
(`patches/hypertreelist.py`) draws every visible cell from Python each
time.

Options: keep a copy of what the list drew and repaint from it when
only GTK asks (no visible change, a larger change to the bundled
widget); GTK animations off inside Task Coach (the scrollbars show and
hide without fading); classic scrollbars in the lists.
