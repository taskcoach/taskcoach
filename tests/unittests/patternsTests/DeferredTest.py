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
"""

import ast
import contextlib
import gc
import io
import os
import threading
import time
import weakref
from unittest import mock

import test
import wx
from taskcoachlib.patterns import deferred


class FakeClock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now

    def advance(self, milliseconds):
        self.now += milliseconds / 1000.0


class DeferredTestCase(test.wxTestCase):
    def setUp(self):
        super().setUp()
        self.clock = FakeClock()
        self.later = deferred.Deferred(clock=self.clock)
        self.addCleanup(self.later.close)
        self.calls = []

    def record(self, name):
        return lambda *args: self.calls.append((name,) + args)

    def run_after(self, milliseconds):
        self.clock.advance(milliseconds)
        self.later.run_due()


class CallTest(DeferredTestCase):
    def test_runs_once_when_due(self):
        self.later.call(None, 500, self.record("a"), 1)
        self.run_after(499)
        self.assertEqual([], self.calls)
        self.run_after(1)
        self.run_after(1000)
        self.assertEqual([("a", 1)], self.calls)

    def test_due_calls_run_in_due_order_in_one_wake(self):
        self.later.call(None, 30, self.record("late"))
        self.later.call(None, 10, self.record("early"))
        self.later.call(None, 10, self.record("early too"))
        self.run_after(100)
        self.assertEqual([("early",), ("early too",), ("late",)], self.calls)

    def test_call_scheduled_by_a_call_waits_for_the_next_wake(self):
        def reschedule():
            self.calls.append(("first",))
            self.later.call(None, 0, self.record("second"))

        self.later.call(None, 0, reschedule)
        self.run_after(0)
        self.assertEqual([("first",)], self.calls)
        self.run_after(0)
        self.assertEqual([("first",), ("second",)], self.calls)

    def test_cancel_drops_the_call(self):
        handle = self.later.call(None, 10, self.record("a"))
        handle.cancel()
        self.run_after(100)
        self.assertEqual(([], False), (self.calls, handle.pending))

    def test_done_call_is_no_longer_pending(self):
        handle = self.later.call(None, 10, self.record("a"))
        self.run_after(10)
        self.assertFalse(handle.pending)

    def test_failing_call_is_logged_and_the_next_still_runs(self):
        def fail():
            raise ValueError("boom")

        self.later.call(None, 10, fail)
        self.later.call(None, 20, self.record("next"))
        self.run_after(100)
        self.assertEqual([("next",)], self.calls)

    def quitting(self):
        wx.GetApp().quitting = True
        self.addCleanup(setattr, wx.GetApp(), "quitting", False)

    def test_calls_run_on_while_quitting_and_after_a_cancel(self):
        # Lazy teardown: a quit stops nothing
        self.later.call(None, 30, self.record("a"))
        self.quitting()
        self.run_after(150)
        wx.GetApp().quitting = False  # Cancelled at "Save changes?"
        self.later.call(None, 30, self.record("b"))
        self.run_after(30)
        self.assertEqual([("a",), ("b",)], self.calls)

    def test_close_frees_every_pending_call(self):
        handle = self.later.every(None, 10, self.record("a"))
        self.later.close()
        self.run_after(100)
        self.assertEqual(
            ([], False, None), (self.calls, handle.pending, handle.callback)
        )

    def test_nothing_is_scheduled_after_close(self):
        self.later.close()
        handle = self.later.call(None, 10, self.record("a"))
        self.run_after(10)
        self.assertEqual(([], False), (self.calls, handle.pending))

    def test_cancelled_call_lets_go_of_its_arguments(self):
        class Argument:
            pass

        argument = Argument()
        alive = weakref.ref(argument)
        handle = self.later.call(None, 3600 * 1000, self.record("a"), argument)
        handle.cancel()
        del argument
        gc.collect()
        self.assertIsNone(alive())


class EveryTest(DeferredTestCase):
    def test_repeats_until_cancelled(self):
        handle = self.later.every(None, 100, self.record("tick"))
        self.run_after(100)
        self.run_after(100)
        handle.cancel()
        self.run_after(100)
        self.assertEqual([("tick",), ("tick",)], self.calls)

    def test_a_call_can_cancel_itself(self):
        def tick():
            self.calls.append(("tick",))
            handle.cancel()

        handle = self.later.every(None, 100, tick)
        self.run_after(100)
        self.run_after(100)
        self.assertEqual([("tick",)], self.calls)


class DebouncedTest(DeferredTestCase):
    def test_runs_once_after_the_last_trigger(self):
        debounced = self.later.debounced(None, 300, self.record("check"))
        debounced()
        self.run_after(200)
        debounced()
        self.run_after(200)
        self.assertEqual(([], True), (self.calls, debounced.pending))
        self.run_after(100)
        self.assertEqual(
            ([("check",)], False), (self.calls, debounced.pending)
        )

    def test_cancel(self):
        debounced = self.later.debounced(None, 300, self.record("check"))
        debounced()
        debounced.cancel()
        self.run_after(1000)
        self.assertEqual(([], False), (self.calls, debounced.pending))

    def test_two_debounced_calls_of_one_owner_are_independent(self):
        owner = wx.Panel(self.frame)
        search = self.later.debounced(owner, 500, self.record("find"))
        tip = self.later.debounced(owner, 200, self.record("tip"))
        search()
        tip()
        self.run_after(100)
        tip()  # Restarts the tip only
        self.run_after(400)
        self.assertEqual([("tip",), ("find",)], self.calls)


class OwnerTest(DeferredTestCase):
    def setUp(self):
        super().setUp()
        self.window = wx.Panel(self.frame)

    def test_a_call_whose_owner_is_gone_is_skipped_when_due(self):
        handle = self.later.call(self.window, 10, self.record("a"))
        other = self.later.call(self.frame, 10, self.record("other"))
        self.window.Destroy()
        # Lazy teardown: the destroy cancels nothing
        self.assertEqual((True, True), (handle.pending, other.pending))
        self.run_after(100)
        self.assertEqual(
            ([("other",)], False, None),
            (self.calls, handle.pending, handle.callback),
        )

    def test_skipped_when_its_destroy_event_never_came(self):
        # As in an AuiNotebook, whose AuiManager consumes the event
        self.later.call(self.window, 10, self.record("a"))
        self.window.Bind(wx.EVT_WINDOW_DESTROY, lambda event: None)
        self.window.Destroy()
        self.run_after(100)
        self.assertEqual([], self.calls)

    def test_a_call_scheduled_during_its_owners_destroy_is_skipped(self):
        def on_destroy(event):
            event.Skip()
            if event.GetEventObject() is self.window:
                self.later.call(self.window, 10, self.record("a"))

        self.window.Bind(wx.EVT_WINDOW_DESTROY, on_destroy)
        self.window.Destroy()
        self.run_after(10)
        self.assertEqual([], self.calls)

    def test_a_repeat_ends_at_its_first_tick_after_its_owner_is_gone(self):
        handle = self.later.every(self.window, 10, self.record("tick"))
        self.run_after(10)
        self.window.Destroy()
        self.run_after(10)
        self.run_after(10)
        self.assertEqual(([("tick",)], False), (self.calls, handle.pending))

    def skip_log(self, logged):
        self.later.call(self.window, 10, self.record("a"))
        self.window.Destroy()
        output = io.StringIO()
        with mock.patch.object(deferred, "_LOG_SKIPS", logged):
            with contextlib.redirect_stdout(output):
                self.run_after(10)
        return output.getvalue()

    def test_a_skip_is_silent_by_design(self):
        self.assertEqual("", self.skip_log(False))

    def test_a_skip_is_logged_with_its_flag(self):
        self.assertIn("skipped: owner gone", self.skip_log(True))

    def test_a_failure_after_the_owner_closed_itself_is_logged(self):
        def close_and_fail():
            self.window.Destroy()
            raise ValueError("a bug")

        self.later.call(self.window, 10, close_and_fail)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.run_after(10)
        self.assertIn("failed", output.getvalue())

    def test_a_child_destroy_does_not_skip_the_parent(self):
        child = wx.Panel(self.window)
        handle = self.later.call(self.window, 10, self.record("a"))
        child.Destroy()
        self.run_after(100)
        self.assertEqual(([("a",)], False), (self.calls, handle.pending))


def reconnect_call_after():
    """TestCase.tearDown disconnects wx.CallAfter's handler from the
    app; the next wx.CallAfter connects it again."""
    app = wx.GetApp()
    if hasattr(app, "_CallAfterId"):
        del app._CallAfterId


class SoonTest(test.wxTestCase):
    def setUp(self):
        super().setUp()
        reconnect_call_after()
        self.later = deferred.Deferred()
        self.calls = []

    def flush(self):
        wx.GetApp().ProcessPendingEvents()

    def test_runs_at_the_next_idle_moment_in_order(self):
        self.later.soon(None, self.calls.append, 1)
        self.later.soon(None, self.calls.append, 2)
        self.assertEqual([], self.calls)
        self.flush()
        self.assertEqual([1, 2], self.calls)

    def test_runs_while_the_app_quits(self):
        self.later.soon(None, self.calls.append, 1)
        wx.GetApp().quitting = True
        try:
            self.flush()
        finally:
            wx.GetApp().quitting = False
        self.assertEqual([1], self.calls)

    def test_a_call_whose_owner_is_gone_is_skipped(self):
        window = wx.Panel(self.frame)
        self.later.soon(window, self.calls.append, 1)
        window.Destroy()
        self.flush()
        self.assertEqual([], self.calls)

    def test_nothing_runs_after_close(self):
        self.later.close()
        self.later.soon(None, self.calls.append, 1)
        self.flush()
        self.assertEqual([], self.calls)

    def test_from_another_thread(self):
        thread = threading.Thread(
            target=self.later.soon, args=(None, self.calls.append, 1)
        )
        thread.start()
        thread.join()
        self.flush()
        self.assertEqual([1], self.calls)


class TimerTest(test.wxTestCase):
    def setUp(self):
        super().setUp()
        reconnect_call_after()

    def test_the_timer_runs_due_calls(self):
        later = deferred.Deferred()
        self.addCleanup(later.close)
        calls = []
        later.call(None, 20, calls.append, 1)
        deadline = time.monotonic() + 2
        while not calls and time.monotonic() < deadline:
            wx.Yield()
            time.sleep(0.005)
        self.assertEqual([1], calls)

    def wait_for(self, done, seconds=2):
        deadline = time.monotonic() + seconds
        while not done() and time.monotonic() < deadline:
            wx.Yield()
            time.sleep(0.005)

    def test_the_timer_runs_through_a_cancelled_quit(self):
        later = deferred.Deferred()
        self.addCleanup(later.close)
        self.addCleanup(setattr, wx.GetApp(), "quitting", False)
        calls = []
        later.call(None, 30, calls.append, 1)
        wx.GetApp().quitting = True  # "Save changes?" is open
        self.wait_for(lambda: calls, seconds=0.15)
        wx.GetApp().quitting = False  # Cancel
        later.call(None, 30, calls.append, 2)
        self.wait_for(lambda: 2 in calls)
        self.assertEqual([1, 2], calls)

    def test_close_stops_the_timer(self):
        later = deferred.Deferred()
        calls = []
        later.call(None, 20, calls.append, 1)
        later.close()
        self.wait_for(lambda: calls, seconds=0.15)
        self.assertEqual([], calls)

    def test_the_timer_follows_a_cancelled_first_call(self):
        later = deferred.Deferred()
        self.addCleanup(later.close)
        calls = []
        later.call(None, 20, calls.append, 1).cancel()
        later.call(None, 60, calls.append, 2)
        self.wait_for(lambda: calls)
        self.assertEqual([2], calls)

    def test_a_call_in_a_nested_event_loop_does_not_hold_up_the_others(self):
        later = deferred.Deferred()
        self.addCleanup(later.close)
        calls = []

        def slow():
            calls.append("slow")
            deadline = time.monotonic() + 0.4
            while time.monotonic() < deadline:  # A dialog, say
                wx.Yield()
                time.sleep(0.005)
            calls.append("slow done")

        later.call(None, 10, slow)
        later.call(None, 100, calls.append, "other")
        self.wait_for(lambda: "slow done" in calls)
        self.assertEqual(["slow", "other", "slow done"], calls)

    def test_a_timed_call_from_another_thread(self):
        later = deferred.Deferred()
        self.addCleanup(later.close)
        calls = []
        thread = threading.Thread(
            target=later.call, args=(None, 10, calls.append, 1)
        )
        thread.start()
        thread.join()
        deadline = time.monotonic() + 2
        while not calls and time.monotonic() < deadline:
            wx.Yield()
            time.sleep(0.005)
        self.assertEqual([1], calls)


class ThreadTest(DeferredTestCase):
    def setUp(self):
        super().setUp()
        reconnect_call_after()

    def test_cancel_from_another_thread(self):
        owner = wx.Panel(self.frame)
        handle = self.later.call(owner, 10, self.record("a"))
        thread = threading.Thread(target=handle.cancel)
        thread.start()
        thread.join()
        wx.GetApp().ProcessPendingEvents()  # The GUI thread's part
        self.run_after(100)
        self.assertEqual(
            ([], False, None),
            (self.calls, handle.pending, handle.callback),
        )


class NoRawDeferredCallsTest(test.TestCase):
    """The app schedules through the service only
    (docs/DEFERRED_CALLS.md)."""

    RAW = {"CallLater", "CallAfter", "Timer", "PyTimer", "FutureCall"}
    # The service, the master scheduler's own clock (whole seconds),
    # the crash guards, and bundled library code
    ALLOWED = (
        os.path.join("patterns", "deferred.py"),
        os.path.join("gui", "scheduler.py"),
        os.path.join("workarounds", "monkeypatches.py"),
        "patches" + os.sep,
        "thirdparty" + os.sep,
    )

    def test_no_raw_wx_deferred_calls(self):
        root = os.path.join(
            os.path.dirname(test.__file__), "..", "taskcoachlib"
        )
        found = []
        for folder, _, files in os.walk(root):
            for name in files:
                if not name.endswith(".py"):
                    continue
                path = os.path.join(folder, name)
                relative = os.path.relpath(path, root)
                if relative.startswith(self.ALLOWED):
                    continue
                with open(path, encoding="utf-8") as source:
                    tree = ast.parse(source.read(), path)
                for node in ast.walk(tree):
                    if (
                        isinstance(node, ast.Attribute)
                        and node.attr in self.RAW
                        and isinstance(node.value, ast.Name)
                        and node.value.id == "wx"
                    ):
                        found.append(
                            "%s:%d wx.%s" % (relative, node.lineno, node.attr)
                        )
        self.assertEqual([], found)
