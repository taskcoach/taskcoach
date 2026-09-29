# Deferred Calls

Every call the app makes later (a debounce, a delay, a repeat, "when
idle") goes through one service, `patterns.later`
(`taskcoachlib/patterns/deferred.py`), so none can reach a window that
is gone. **Decided by designer, 2026-09-29.**

## Why

wx does not tie a timer or a deferred call to the window it serves.
When the window is destroyed first, a `wx.CallLater` or `wx.CallAfter`
still calls into it (a Python error, e.g. the spell check's 0.3 s
timer after its editor closed), and a `wx.Timer` owned by it ticks
into freed memory (a native crash). Guarding each site by hand
(stopping timers on destroy) is easy to forget, and an `AuiNotebook`
never receives its own destroy event ([AUI.md](AUI.md#destroy-event)).

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
  drops a pending run. Each debounced action is its own object, so a
  control can have several (the search box: its search and its
  tooltip).
- `soon`: at the next idle moment, in order, from any thread
  (`wx.CallAfter`); also while the app quits, as quitting relies on
  it.
- `owner`: the object the call belongs to, usually the window it acts
  on; `None` for the application. It is the call's lifetime only.

**Rule:** app code never calls `wx.CallLater`, `wx.CallAfter`,
`wx.Timer`, `wx.PyTimer` or `wx.FutureCall`; a test fails if it does
(`NoRawDeferredCallsTest` in `tests/unittests/patternsTests/`). The
exceptions: the service itself, the master scheduler's own 1 s clock
(`gui/scheduler.py`, whole seconds by design), the crash guards, and
bundled library code (`patches/`, `thirdparty/`).

## How It Works

- **One queue, one timer:** timed calls wait in a queue sorted by due
  time (a monotonic clock, so clock changes cannot misfire them). The
  service's own timer is set for the earliest only, and stopped when
  the queue is empty. It lives until the app quits, so no tick can
  reach freed memory.
- **A wake runs everything due** by then, in due order, and then sets
  the timer for the next. Calls scheduled while running wait for the
  next wake, so none can loop.
- **Owner gone, normal case:** the first call of a window watches its
  destroy event; when it comes, all the window's pending calls are
  cancelled at once.
- **Owner gone, backup:** when the event never comes (an
  `AuiNotebook`) or the owner is not a window, the call is checked
  just before it runs and dropped if its owner was deleted, with a
  `[LATER] dropped` log line naming where it was scheduled.
- **Errors are contained:** a failing call is logged
  (`[LATER] failed`, with its traceback and scheduling site) and never
  raised into wx; the next call still runs.
- **Quitting:** no timed call starts or runs while the app quits, and
  `shutdown()` drops them all (`_stop_all_timers()`).
- **Threads:** `soon`, `call`, `every` and `cancel()` may be called
  from any thread; the queue is only touched on the GUI thread.

## What Moved

- Debounces: the spell check (0.3 s), the search box (0.5 s), the icon
  picker filter, the settings refresh, the tooltip delay; the status
  bar keeps two, one for the viewer's status (0.5 s) and one for a
  temporary message (3 s), as merging them would change when a
  message disappears.
- Drag hover-expand: the drags within a tree and the drops from
  outside had two copies of it; one `HoverExpander` per control now
  (`widgets/draganddrop.py`).
- Delays and repeats: the reminder dialog's click freeze, a date
  popup's destroy, the mouse filter release after a layout rebuild,
  the speech retry, the window position debug log, the notification
  fade-in, slide and timeouts, the macOS editor poll, the geometry
  trace.
- All `wx.CallAfter` calls (about 90), each with its owner.

The crash guards stay, for library code only
([CRASH_GUARD.md](CRASH_GUARD.md)).
