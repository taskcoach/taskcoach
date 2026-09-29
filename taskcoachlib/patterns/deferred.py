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

A call runs only while its owner exists: a destroyed window cancels
its pending calls, and a call whose owner is gone when due is dropped.
One wx timer, owned by this service, serves every timed call, so no
tick can reach a deleted window. A failing call is logged, never
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


def _is_gone(owner):
    """Whether owner is a wx object whose C++ side was deleted."""
    if owner is None:
        return False
    from wx import siplib

    try:
        return siplib.isdeleted(owner)
    except TypeError:
        return False  # Not a wx object: alive while referenced


def _address(window):
    """A window's C++ address: its destroy event may carry another
    Python proxy of it."""
    from wx import siplib

    try:
        return siplib.unwrapinstance(window)
    except (TypeError, RuntimeError):
        return None


def _key(owner):
    """Key of a live window's pending calls: its address, and the
    Python object, as a new window may reuse a gone one's address."""
    import wx

    if not isinstance(owner, wx.Window):
        return None
    address = _address(owner)
    return None if address is None else (address, id(owner))


def _site(depth):
    """File and line that scheduled the call, for the log."""
    frame = sys._getframe(depth)
    return "%s:%d" % (
        os.path.basename(frame.f_code.co_filename),
        frame.f_lineno,
    )


def _quitting():
    import wx

    app = wx.GetApp()
    return app is None or getattr(app, "quitting", False)


class Handle:
    """A pending timed call; cancel() drops it."""

    __slots__ = (
        "due",
        "seq",
        "owner",
        "key",
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


class Debounced:
    """A call that runs once, milliseconds after the last time this
    object is called: each call restarts the wait."""

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
        self.__by_owner = {}  # _key(window) -> its pending handles

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
        """Call callback at the next idle moment, from any thread, in
        the order of the requests (wx.CallAfter); also while the
        application quits, as quitting relies on it."""
        import wx

        wx.CallAfter(self.__run_soon, owner, callback, args, kwargs, _site(2))

    def cancel_all(self, owner):
        """Drop the owner's pending timed calls (windows only)."""
        key = _key(owner)
        if key is not None:
            self.__forget_owner(key)
            self.__rearm()

    def shutdown(self):
        """Drop every pending call and delete the timer; the
        application calls it when it quits."""
        for handle in self.__queue:
            handle.cancelled = True
        self.__queue = []
        self.__by_owner.clear()
        if self.__timer is not None:
            self.__timer.Stop()
            self.__timer = None

    def schedule(
        self, owner, milliseconds, callback, args, kwargs, interval, site
    ):
        handle = Handle()
        handle.owner = owner
        handle.key = None
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

        if _quitting():
            handle.cancelled = True
        elif wx.IsMainThread():
            self.__push(handle)
        else:
            wx.CallAfter(self.__push, handle)
        return handle

    def cancelled(self, handle):
        """A handle was cancelled: forget it, and set the timer for the
        next call if it was the earliest (on the GUI thread)."""
        import wx

        if not wx.IsMainThread():
            wx.CallAfter(self.cancelled, handle)
            return
        self.__unindex(handle)
        if self.__queue and self.__queue[0] is handle:
            self.__rearm()

    def run_due(self):
        """Run every call due by now, in due order; the timer calls it
        (tests too, with a fake clock). Calls scheduled while running
        wait for the next wake, so none can loop. None runs while the
        application quits."""
        if _quitting():
            return
        now = self.__clock()
        due = []
        while self.__queue and self.__queue[0].due <= now:
            due.append(heapq.heappop(self.__queue))
        for handle in due:
            if handle.cancelled:
                continue
            if _is_gone(handle.owner):
                log_step(
                    "dropped: owner gone, from", handle.site, prefix=PREFIX
                )
                self.__drop_owner(handle)
                continue
            if handle.interval is None:
                handle.cancelled = True  # Done: no longer pending
                self.__unindex(handle)
            if not self.__invoke(
                handle.owner,
                handle.callback,
                handle.args,
                handle.kwargs,
                handle.site,
            ):
                self.__drop_owner(handle)
            elif handle.interval is not None and not handle.cancelled:
                handle.due = self.__clock() + handle.interval / 1000.0
                handle.seq = next(self.__seq)
                heapq.heappush(self.__queue, handle)
        self.__rearm()

    def __push(self, handle):
        if handle.cancelled or _quitting():
            return
        heapq.heappush(self.__queue, handle)
        self.__index(handle)
        if self.__queue[0] is handle:
            self.__rearm()

    def __index(self, handle):
        key = _key(handle.owner)
        if key is None:
            return
        handle.key = key
        if key not in self.__by_owner:
            self.__by_owner[key] = set()
            self.__watch(handle.owner, key)
        self.__by_owner[key].add(handle)

    def __unindex(self, handle):
        handles = self.__by_owner.get(handle.key)
        if handles is not None:
            handles.discard(handle)

    def __watch(self, window, key):
        import wx

        def on_destroy(event):
            event.Skip()
            # Children's destroy events reach this handler too
            if _address(event.GetEventObject()) == key[0]:
                self.__forget_owner(key)
                self.__rearm()

        wx.EvtHandler.Bind(window, wx.EVT_WINDOW_DESTROY, on_destroy)

    def __forget_owner(self, key):
        for handle in self.__by_owner.pop(key, ()):
            handle.cancelled = True

    def __drop_owner(self, handle):
        handle.cancelled = True
        if handle.key is not None:
            self.__forget_owner(handle.key)

    def __rearm(self):
        queue = self.__queue
        while queue and queue[0].cancelled:
            heapq.heappop(queue)
        if not queue:
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
        if _is_gone(owner):
            log_step("dropped: owner gone, from", site, prefix=PREFIX)
            return
        self.__invoke(owner, callback, args, kwargs, site)

    def __invoke(self, owner, callback, args, kwargs, site):
        """Run the call, errors logged; False when the owner turned out
        gone."""
        try:
            callback(*args, **kwargs)
        except Exception:  # pylint: disable=W0703
            if _is_gone(owner):
                log_step("dropped: owner gone, from", site, prefix=PREFIX)
                return False
            log_step("failed, from", site, prefix=PREFIX, exc=True)
        return True


later = Deferred()
