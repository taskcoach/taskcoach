# Task Statistics View

The view that shows the tasks per status as a pie, with a legend of
the counts: View > New viewer > Task statistics. Not open by default
(`view.taskstatsviewercount` is 0).

## Table of Contents

1. [Code](#code)
2. [Known Load](#known-load)
3. [To Do](#to-do)

---

## Code

- `TaskStatsViewer` in `taskcoachlib/gui/viewer/task.py`: one pie part
  per status, its label the count and percentage, its colour the
  status's (`fgcolor`); redrawn after a status change or a scheduler
  pass. The toolbar's slider sets the tilt (`piechartangle`, saved per
  view); the status filters hide statuses.
- The pie is wxPython's `wx.lib.agw.piectrl.PieCtrl` (AGW, pure
  Python, its header's latest revision 16 Jul 2012): a tilted pie
  drawn as a polygon per step, into a canvas bitmap blitted at each
  paint; the legend is its child window, `PieCtrlLegend`.

## Known Load

The view keeps most of a CPU core busy while open, whatever the file
holds; master and released versions too (D10, P146 in
[MASTER_SCHEDULER_REFACTOR.md](MASTER_SCHEDULER_REFACTOR.md#deferred-and-will-not-do)).

**Cause**: `PieCtrl.Draw()` ends with
`self._legend.RecreateBackground(_canvasDC)`, which calls the legend's
`Refresh()`; on GTK 3 the legend's repaint brings the pie's paint back.
They repaint each other without end, about 100 times a second.

**Measured** (do not repeat: the numbers below are the reference):

- 2026-10-01: about 100 repaints a second (D10).
- 2026-10-04, the view open in the scratch profile, idle on the
  virtual display: 24 to 26 s of CPU per 30 s with a one-task file,
  this branch and master alike; with 5,000 tasks the same. A 30 s
  `py-spy` profile: 78% in `PieCtrl.OnPaint()` and `Draw()` (62% in
  `Draw()` itself), 17% in the AUI manager repainting pane captions,
  nothing in Task Coach's own code.
- How: the app's CPU ticks from `/proc/PID/stat` (fields 14 and 15)
  over 30 s after it settles; `py-spy record -p PID -d 30 --format raw`
  for the profile.

**Tried 2026-10-01, not kept** (deferred): the view turning that
refresh off (its legend is opaque, so it needs no copy of the pie
behind it) and refreshing the legend when the counts change. Idle 0%,
the pie and legend unchanged, the legend following a change.

**Ruling**: deferred, **by designer 2026-10-01** (D10: "I don't use
it. I don't know anyone that uses it. No one's complained"); to be
refactored, **asked by designer 2026-10-04**: "there's no reason for it
to be so heavy ... it relies on a, maybe not well maintained or
obsolete or abandoned package ... there's probably ... more modern
ways".

---

## To Do

1. Draw the view in Task Coach's own code instead of
   `wx.lib.agw.piectrl`: a pie painted only when the counts, colours,
   tilt or size change (`wx.GraphicsContext`, antialiased), and a
   legend of plain labels. Keep what users set: the statuses shown,
   their colours and the tilt slider. Checks: idle CPU near 0 with the
   view open (method above); the counts follow status changes and
   scheduler passes; light and dark themes; the view's tests.
