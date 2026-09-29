# Deferred Calls

Every call the app makes later (a debounce, a delay, a repeat, "as
soon as possible") goes through one service, `patterns.later`
(`taskcoachlib/patterns/deferred.py`), so none can reach a window that
is gone. **Decided by designer, 2026-09-29**; lazy teardown the same
day.

## Index

- [Design Philosophy](#design-philosophy)
- [Why: the Problem](#why-the-problem)
- [How We Got Here](#how-we-got-here)
- [Use](#use)
- [How It Works](#how-it-works)
- [End of Life](#end-of-life)
- [What Moved](#what-moved)
- [Limits](#limits)
- [Related Documents](#related-documents)

## Design Philosophy

1. **A call belongs to its owner.** Every deferred call names the
   object it serves (usually the window it acts on) and never runs
   once that owner is deleted. wx does not tie a call to a window, so
   the app does.
2. **Safe by construction, not by discipline.** No call site stops a
   timer on destroy or wraps its callback in a liveness check; the
   service does it for all. A test fails if app code schedules through
   wx directly, so the rule cannot erode.
3. **One implementation per operation** (the Modular canon,
   [DEVELOPMENT.md](DEVELOPMENT.md#design)): one queue, one timer, one
   owner check, one error handler, instead of a dozen hand-made timer
   patterns.
4. **Lazy teardown, by design.** Nothing is cancelled or stopped when
   a window closes or the app quits: stopping things early risks side
   effects nobody planned for. Each call runs its course; when due, a
   call whose owner was deleted is skipped quietly. One check covers
   every case, including a destroy event that never comes (an
   `AuiNotebook`, [AUI.md](AUI.md#destroy-event)). The timers are
   freed last, once the event loop has ended
   ([End of Life](#end-of-life)). **Decided by designer, 2026-09-29.**
5. **Contained and logged.** A failing call is logged with where it
   was scheduled (`[LATER] failed`), never raised into wx, so a
   problem is diagnosed from the log
   ([DEVELOPMENT.md](DEVELOPMENT.md#diagnosing)). A skip is by design
   and silent; `TASKCOACH_LATER_LOG=1` logs each one.
6. **Milliseconds, apart from the master scheduler.** UI timing (a
   debounce, an animation) runs in milliseconds on a monotonic clock;
   the master scheduler's loop and its 1 s tick work in whole seconds
   of the wall clock and stay separate
   ([SCHEDULERS.md](SCHEDULERS.md),
   [MASTER_SCHEDULER_REFACTOR.md](MASTER_SCHEDULER_REFACTOR.md#time-resolution)).
7. **Same behaviour.** Moving a call keeps what users see: timings,
   order, and the calls that must run while the app quits.

## Why: the Problem

wx does not tie a timer or a deferred call to the window it serves.
When the window is destroyed first:

- a `wx.CallLater` or `wx.CallAfter` still calls into it: a Python
  `RuntimeError` ("wrapped C/C++ object ... has been deleted");
- a `wx.Timer` owned by it ticks into freed memory: a native crash,
  with only `MainLoop` in the traceback
  ([CRASH_GUARD.md](CRASH_GUARD.md)).

Guarding each site by hand (stopping timers on destroy, `if self:`
checks, `__safe*()` wrappers) is easy to forget, and destroy-based
cleanup never runs for an `AuiNotebook`, whose AUI manager consumes
its destroy event.

## How We Got Here

1. A lost traceback (to-do 44 in
   [MASTER_SCHEDULER_REFACTOR.md](MASTER_SCHEDULER_REFACTOR.md#to-do)):
   one app run on 2026-09-28 logged one, and relaunching overwrote the
   log.
2. The candidate: the spell check's 0.3 s `wx.CallLater`
   ([SPELLCHECKING.md](SPELLCHECKING.md#when-the-check-runs)) was not
   stopped when its editor closed. Reproduced 3 times out of 3 (type a
   letter, close the editor at once).
3. A survey of the app found 23 timers and delayed calls and about 90
   `wx.CallAfter`s: one unprotected, six relying on the crash guard,
   four safe only because of the quit path, and `wx.CallAfter`
   closures the guard cannot see.
4. Options weighed: fix each site; a global guard on `wx.CallLater`;
   one central service; the designer's idea of delivering through the
   Publisher, whose subscriptions already end with their window
   ([PUBLISHER_OBSERVER.md](PUBLISHER_OBSERVER.md)). The central
   service keeps the Publisher's lifetime idea (end with the owner,
   drop a dead one at dispatch) without an event type per debounce.
   With nothing of the app left to guard, no global guard was added.
5. Design points settled with the designer:
   - A debounced action is an object, created once and called on each
     event; no key. The owner is only its lifetime, so one control can
     have several independent ones (a search and a tooltip), each
     serving one action.
   - The owner is fully qualified: the window acted on, or `None` for
     the application.
   - The mechanics: a cancel on destroy, a check when due, one wake
     for everything due, calls scheduled during a wake wait for the
     next.
6. Found while moving the calls:
   - Pending calls hold ordinary references, as `wx.CallAfter` did:
     weak ones would silently drop a call on an object nothing else
     holds.
   - `soon` still runs while the app quits, as quitting relies on it
     (the editors' deferred destroy); timed calls stop only once the
     quit is decided (`shutdown()`), not at the "Save changes?"
     prompt, which the user may cancel.
   - The status bar keeps two debounces (the viewer's status 0.5 s, a
     temporary message 3 s): one would change when a message
     disappears.
   - The two copies of drag hover-expand became one `HoverExpander`.
7. Checked: the spell check case 0 times out of 5 after the change; in
   the app the search, tooltips, drag hover-expand, the reminder
   dialog, the notification popups and quitting; the unit tests
   (`tests/unittests/patternsTests/DeferredTest.py`) and the full
   suite, unchanged from the baseline.
8. An integrated review then found, and the service fixed, each with a
   test that fails on the earlier version: timed calls stalled for
   good after a cancelled quit (they paused while quitting instead of
   after `shutdown()`); a window reusing an unwatched window's address
   went unwatched; `shutdown()` from inside a call did not stop that
   wake; a call running a nested event loop held up the others;
   cancelled calls kept their arguments until due; a call scheduled
   during its owner's destroy waited to be dropped; a real error after
   the owner closed itself was logged as a drop. A second review
   compared every moved call with the old code: all keep their
   behaviour; it found a pre-existing fault (P18). Re-checked in the
   app: the spell check case (0 of 3), and a quit cancelled after 4 s
   at "Save changes?" (the search still filters); the full suite,
   unchanged from the baseline.
9. The stall showed the cost of stopping things early: the stop
   needed state (closed while quitting) that a cancelled quit had to
   undo, and four of the eight findings were in the destroy watch and
   the shutdown. The designer ruled lazy teardown (principle 4): the
   destroy watch, `shutdown()` and the app's close-time stops went
   (the notification animations, the notification centre at quit,
   the search box); the per-second clock follows the same rule. The
   macOS editor poll went too: its cause, wxPython 2.8's Carbon port,
   is gone (to-do 56 in
   [MASTER_SCHEDULER_REFACTOR.md](MASTER_SCHEDULER_REFACTOR.md#to-do)).
   Checked in the
   app with `TASKCOACH_LATER_LOG=1`: editors closed right after typing
   (the spell check skipped, no traceback); a quit cancelled after 4 s
   (the search still filters); a quit with a search pending (`closed,
   3 pending freed`, after the file and ini locks were released); the
   full suite, unchanged.

## Use

```python
handle = patterns.later.call(owner, milliseconds, callback, *args)
handle = patterns.later.every(owner, milliseconds, callback, *args)
check = patterns.later.debounced(owner, milliseconds, callback)
patterns.later.soon(owner, callback, *args)
```

- `call`: once, after the delay. `every`: repeatedly until cancelled.
  Both return a handle with `cancel()` and `pending`.
- `debounced`: create once per action; call it on every event, and
  the callback runs once, the delay after the last call. `cancel()`
  drops a pending run.
- `soon`: on the next event dispatch, in order, from any thread
  (`wx.CallAfter`); also while the app quits.
- `owner`: the object the call belongs to, usually the window it acts
  on; `None` for the application.

**Rule** ([DEVELOPMENT.md](DEVELOPMENT.md#design)): app code never
calls `wx.CallLater`, `wx.CallAfter`, `wx.Timer`, `wx.PyTimer` or
`wx.FutureCall`; `NoRawDeferredCallsTest` fails if it does. The
exceptions: the service itself, the master scheduler's own 1 s clock
(`gui/scheduler.py`), the crash guards, and bundled library code
(`patches/`, `thirdparty/`).

## How It Works

- **One queue, one timer:** timed calls wait in a queue sorted by due
  time on a monotonic clock, so clock changes cannot misfire them. The
  service's own timer is set for the earliest only, and stopped when
  the queue is empty. It lives until the event loop ends, so no tick
  can reach freed memory.
- **A wake runs everything due** by then, in due order. It sets the
  timer for the next first, so a call that runs a nested event loop (a
  dialog) does not hold up the others. Calls scheduled while running
  wait for a later wake, so none can loop.
- **Owner gone:** a window's destroy changes nothing. When a call is
  due, its owner is checked (`siplib.isdeleted`); a deleted owner's
  call is skipped, silently unless `TASKCOACH_LATER_LOG=1`
  (`[LATER] skipped`, with where it was scheduled). A repeat ends at
  its first tick after. A top-level window exists until wx deletes it
  at the next idle after `Destroy()`, so its calls run until then, as
  in wx.
- **Errors are contained:** a failing call is logged (`[LATER]
  failed`, with its traceback and scheduling site) and the next still
  runs. An error from the owner being deleted during the call counts
  as a skip.
- **Quitting:** nothing stops. Calls run as usual, and are skipped
  once their windows are gone; a cancelled quit has nothing to undo.
- **Memory:** a done, cancelled or skipped call lets go of its owner,
  callback and arguments at once. A call whose owner is gone holds it
  until due, at most its delay (the longest, the status bar's 3 s).
- **Threads:** `soon`, `call`, `every` and a handle's `cancel()` may be
  called from any thread; the queue is only touched on the GUI thread.
  A debounced object is for the GUI thread.

## End of Life

`Application.start()`, once `MainLoop()` has returned and just before
the app object is destroyed, frees the app's timers: the service's
(`patterns.later.close()`, with its pending calls) and the per-second
clock (`MainWindow.close_global_timer()`,
[SCHEDULERS.md](SCHEDULERS.md)). No event loop runs then, so nothing
can fire; freed before the app, no timer outlives it (Phoenix issue
429). Nothing is scheduled or run after it.

The one exception to lazy teardown: bundled library code's timers are
owned by its windows and would tick into freed memory, so
`Application._stop_all_timers()` still stops them at quit, before
those windows go, as on master.

## What Moved

| API | Calls | Replaced |
|---|---|---|
| `soon` | 91 | every `wx.CallAfter` |
| `debounced` | 8 | 6 timers, 3 `CallLater` |
| `call` | 5 | 4 `CallLater`, 1 timer |
| `every` | 4 | 4 timers |

- Debounces: the spell check (0.3 s), the search box (0.5 s), the icon
  picker filter, the settings refresh (1 s,
  [SETTINGS.md](SETTINGS.md)), the tooltip delay, the status bar's
  two, drag hover-expand.
- Delays: the reminder dialog's click freeze, a date popup's destroy,
  the mouse filter release after a layout rebuild, the speech retry,
  the window position debug log.
- Repeats: the notification fade-in, slide and timeouts, the geometry
  trace.
- Every `wx.CallAfter`, each with its owner, including those from
  worker threads (the version check, the file watcher, the dependency
  graph's plotting) and the tray menu's Quit
  ([SYSTEM_TRAY.md](SYSTEM_TRAY.md)).

## Limits

- Library code keeps its own timers and `wx.CallAfter`s: the AUI tabs
  and panes, the bundled tree list, the vendored calendar. The crash
  guards stay for them ([CRASH_GUARD.md](CRASH_GUARD.md)).
- The master scheduler's 1 s clock keeps its own timer, in whole
  seconds, under the same rule: its tick is skipped once the main
  window is gone, and it is freed at the [End of Life](#end-of-life)
  ([SCHEDULERS.md](SCHEDULERS.md)).
- A wx event handler reaching a deleted window is not a deferred
  call, but the same rule holds: the handler exits when its window is
  gone (a date popup's text event after its editor closed, P12 in
  [MASTER_SCHEDULER_REFACTOR.md](MASTER_SCHEDULER_REFACTOR.md#pre-existing-issues)).

## Related Documents

- [CRASH_GUARD.md](CRASH_GUARD.md): the guards for library code, and
  debugging a segfault.
- [AUI.md](AUI.md#destroy-event): the destroy event an `AuiNotebook`
  never gets.
- [PUBLISHER_OBSERVER.md](PUBLISHER_OBSERVER.md): subscriptions end
  with their window, the same lifetime rule for events.
- [SCHEDULERS.md](SCHEDULERS.md): the master scheduler and its tick,
  for per-second work.
- [DEVELOPMENT.md](DEVELOPMENT.md): the canon rule, and diagnosing from
  logs.
- [LOGGING_GUIDE.md](LOGGING_GUIDE.md): the `[LATER]` prefix.
- [MASTER_SCHEDULER_REFACTOR.md](MASTER_SCHEDULER_REFACTOR.md): to-dos
  44, 53 and 54, and the pre-existing issues.
- [SPELLCHECKING.md](SPELLCHECKING.md), [SETTINGS.md](SETTINGS.md),
  [SYSTEM_TRAY.md](SYSTEM_TRAY.md): uses of the service.
