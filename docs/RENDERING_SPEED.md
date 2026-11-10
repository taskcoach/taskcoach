# Rendering Speed

Opening an editor: what was measured, the cause of the gray window
and its fix, and where the rest of the time goes. Asked by the
designer, 2026-11-10: "I see the window all gray first. And then I
see a next pass or maybe iteratively the tabs and fields."

1. [How It Was Measured](#how-it-was-measured)
2. [The Gray Window](#the-gray-window)
3. [Before the Window Appears](#before-the-window-appears)
4. [Lists Repaint on Every Scrollbar Fade Frame](#lists-repaint-on-every-scrollbar-fade-frame)

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
`widgets.Notebook`, gets the single queued layout.

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
