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

Deferred calls tied to their owner's life (docs/DEFERRED_CALLS.md):

    handle = later.call(owner, milliseconds, callback, *args)
    handle = later.every(owner, milliseconds, callback, *args)
    debounced = later.debounced(owner, milliseconds, callback)
    later.soon(owner, callback, *args)

Lazy teardown, by design: nothing is cancelled when an owner closes
or the application quits. Each call runs its course; when due, a call
whose owner was deleted is skipped quietly (TASKCOACH_LATER_LOG=1
logs each skip). One wx timer, owned by this service, serves every
timed call, so no tick can reach a deleted window; close() frees it
once the event loop has ended. A failing call is logged, never
raised. The owner is any object; None means the application.
"""

import heapq
import itertools
import math
import os
import sys
import time

from taskcoachlib.meta.debug import log_step

PREFIX = "LATER"
# Skips are by design and silent; this logs each one
_LOG_SKIPS = os.environ.get("TASKCOACH_LATER_LOG") == "1"


def is_gone(owner):
    """Whether owner is a wx object whose C++ side was deleted."""
    if owner is None:
        return False
    from wx import siplib

    try:
        return siplib.isdeleted(owner)
    except TypeError:
        return False  # Not a wx object: alive while referenced


def _is_deleted_error(exc):
    return isinstance(exc, RuntimeError) and "has been deleted" in str(exc)


def _site(depth):
    """File and line that scheduled the call, for the log."""
    frame = sys._getframe(depth)
    return "%s:%d" % (
        os.path.basename(frame.f_code.co_filename),
        frame.f_lineno,
    )


def _skipped(reason, site):
    if _LOG_SKIPS:
        log_step("skipped: %s, from" % reason, site, prefix=PREFIX)


class Handle:
    """A pending timed call; cancel() drops it, from any thread."""

    __slots__ = (
        "due",
        "seq",
        "owner",
        "callback",
        "args",
        "kwargs",
        "interval",
        "cancelled",
        "site",
        "service",
    )

    def __lt__(self, other):
        return (self.due, self.seq) < (other.due, other.seq)

    def cancel(self):
        if not self.cancelled:
            self.cancelled = True
            self.service.cancelled(self)

    @property
    def pending(self):
        return not self.cancelled

    def release(self):
        """Let go of what the call holds, once it is done or dropped."""
        self.owner = self.callback = None
        self.args = ()
        self.kwargs = {}


class Debounced:
    """A call that runs once, milliseconds after the last time this
    object is called: each call restarts the wait. GUI thread only."""

    def __init__(self, service, owner, milliseconds, callback, site):
        self.__service = service
        self.__owner = owner
        self.__milliseconds = milliseconds
        self.__callback = callback
        self.__site = site
        self.__handle = None

    def __call__(self):
        if self.__handle is not None:
            self.__handle.cancel()
        self.__handle = self.__service.schedule(
            self.__owner,
            self.__milliseconds,
            self.__run,
            (),
            {},
            None,
            self.__site,
        )

    def __run(self):
        self.__handle = None
        self.__callback()

    def cancel(self):
        if self.__handle is not None:
            self.__handle.cancel()
            self.__handle = None

    @property
    def pending(self):
        return self.__handle is not None and self.__handle.pending


class Deferred:
    """The service: a queue of timed calls sorted by due time, and one
    timer set for the earliest."""

    def __init__(self, clock=time.monotonic):
        self.__clock = clock
        self.__queue = []
        self.__seq = itertools.count()
        self.__timer = None
        self.__closed = False  # close() ran: the event loop has ended

    def call(self, owner, milliseconds, callback, *args, **kwargs):
        """Call callback once, milliseconds from now."""
        return self.schedule(
            owner, milliseconds, callback, args, kwargs, None, _site(2)
        )

    def every(self, owner, milliseconds, callback, *args, **kwargs):
        """Call callback every milliseconds until cancelled."""
        return self.schedule(
            owner,
            milliseconds,
            callback,
            args,
            kwargs,
            milliseconds,
            _site(2),
        )

    def debounced(self, owner, milliseconds, callback):
        """A Debounced call of callback."""
        return Debounced(self, owner, milliseconds, callback, _site(2))

    def soon(self, owner, callback, *args, **kwargs):
        """Call callback on the next event dispatch, from any thread, in
        the order of the requests (wx.CallAfter)."""
        if self.__closed:
            _skipped("closed", _site(2))
            return
        import wx

        wx.CallAfter(self.__run_soon, owner, callback, args, kwargs, _site(2))

    def close(self):
        """Free the timer and the pending calls; the application's last
        step, once its event loop has ended. Nothing runs after it."""
        self.__closed = True
        pending = [handle for handle in self.__queue if not handle.cancelled]
        for handle in self.__queue:
            handle.cancelled = True
            handle.release()
        self.__queue = []
        if self.__timer is not None:
            self.__timer.Stop()
            self.__timer = None
        if _LOG_SKIPS:
            log_step("closed, %d pending freed" % len(pending), prefix=PREFIX)

    def schedule(
        self, owner, milliseconds, callback, args, kwargs, interval, site
    ):
        handle = Handle()
        handle.owner = owner
        handle.callback = callback
        handle.args = args
        handle.kwargs = kwargs
        handle.interval = interval
        handle.cancelled = False
        handle.site = site
        handle.service = self
        handle.due = self.__clock() + milliseconds / 1000.0
        handle.seq = next(self.__seq)
        import wx

        if wx.IsMainThread():
            self.__push(handle)
        else:
            wx.CallAfter(self.__push, handle)
        return handle

    def cancelled(self, handle):
        """A handle was cancelled: let go of what it holds, and set the
        timer for the next call if it was the earliest (on the GUI
        thread)."""
        import wx

        if not wx.IsMainThread():
            wx.CallAfter(self.cancelled, handle)
            return
        handle.release()
        if self.__queue and self.__queue[0] is handle:
            self.__rearm()

    def run_due(self):
        """Run every call due by now, in due order; the timer calls it
        (tests too, with a fake clock). Calls scheduled while running
        wait for the next wake, so none can loop; the timer is set for
        them first, so a call running a nested event loop (a dialog)
        does not hold them up."""
        now = self.__clock()
        due = []
        while self.__queue and self.__queue[0].due <= now:
            due.append(heapq.heappop(self.__queue))
        self.__rearm()
        for index, handle in enumerate(due):
            try:
                self.__run(handle)
            except BaseException:
                # SystemExit, KeyboardInterrupt: the others still wait
                for rest in due[index + 1 :]:
                    if not rest.cancelled:
                        heapq.heappush(self.__queue, rest)
                self.__rearm()
                raise
        self.__rearm()

    def __run(self, handle):
        if handle.cancelled:
            return
        if is_gone(handle.owner):
            handle.cancelled = True  # Skipped: no longer pending
            _skipped("owner gone", handle.site)
            handle.release()
            return
        call = (handle.owner, handle.callback, handle.args, handle.kwargs)
        if handle.interval is None:
            handle.cancelled = True  # Done: no longer pending
            handle.release()
        self.__invoke(*call, handle.site)
        if not handle.cancelled:  # A repeat its call did not cancel
            handle.due = self.__clock() + handle.interval / 1000.0
            handle.seq = next(self.__seq)
            heapq.heappush(self.__queue, handle)

    def __push(self, handle):
        if handle.cancelled:
            return
        if self.__closed:
            handle.cancelled = True  # The event loop has ended
            _skipped("closed", handle.site)
            handle.release()
            return
        heapq.heappush(self.__queue, handle)
        if self.__queue[0] is handle:
            self.__rearm()

    def __rearm(self):
        queue = self.__queue
        while queue and queue[0].cancelled:
            heapq.heappop(queue)
        if not queue or self.__closed:
            if self.__timer is not None and self.__timer.IsRunning():
                self.__timer.Stop()
            return
        delay = math.ceil((queue[0].due - self.__clock()) * 1000)
        self.__wake_timer().StartOnce(max(1, delay))

    def __wake_timer(self):
        if self.__timer is None:
            import wx

            service = self

            class WakeTimer(wx.Timer):
                def Notify(self):  # wx override
                    service.run_due()

            self.__timer = WakeTimer()
        return self.__timer

    def __run_soon(self, owner, callback, args, kwargs, site):
        if is_gone(owner):
            _skipped("owner gone", site)
            return
        self.__invoke(owner, callback, args, kwargs, site)

    def __invoke(self, owner, callback, args, kwargs, site):
        """Run the call and log its error, unless the error came from
        its owner being deleted meanwhile: then it is skipped."""
        try:
            callback(*args, **kwargs)
        except Exception as exc:  # pylint: disable=W0703
            if is_gone(owner) and _is_deleted_error(exc):
                _skipped("owner gone", site)
            else:
                log_step("failed, from", site, prefix=PREFIX, exc=True)


later = Deferred()
