"""
Task Coach - Your friendly task manager
Copyright (C) 2011 Task Coach developers <developers@taskcoach.org>

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

import sys

from taskcoachlib.command import (
    NewEffortCommand,
    EditEffortStopDateTimeCommand,
)
from taskcoachlib.domain import effort, date
from taskcoachlib.i18n import _
from taskcoachlib.meta.debug import log_step
from taskcoachlib.notify import NotificationFrameBase, NotificationCenter
from taskcoachlib.patterns import Observer
from taskcoachlib.powermgt import IdleNotifier
from pubsub import pub
from taskcoachlib import render
from taskcoachlib.gui.icons.icon_library import icon_catalog, LIST_ICON_SIZE
import wx


class WakeFromIdleFrame(NotificationFrameBase):
    def __init__(self, idle_time, effort, displayed_efforts, *args, **kwargs):
        self._idle_time = idle_time
        self._effort = effort
        self._displayed = displayed_efforts
        super().__init__(*args, **kwargs)

    def add_inner_content(self, sizer, panel):
        idle_time_formatted = render.dateTime(self._idle_time)
        sizer.Add(
            wx.StaticText(
                panel,
                wx.ID_ANY,
                _(
                    "No user input since %s. The following task was\nbeing tracked:"
                )
                % idle_time_formatted,
            )
        )
        sizer.Add(
            wx.StaticText(panel, wx.ID_ANY, self._effort.task().subject())
        )

        btn_nothing = wx.Button(panel, wx.ID_ANY, _("Do nothing"))
        btn_stop_at = wx.Button(
            panel, wx.ID_ANY, _("Stop it at %s") % idle_time_formatted
        )
        btn_stop_resume = wx.Button(
            panel,
            wx.ID_ANY,
            _("Stop it at %s and resume now") % idle_time_formatted,
        )

        sizer.Add(btn_nothing, 0, wx.EXPAND | wx.ALL, 1)
        sizer.Add(btn_stop_at, 0, wx.EXPAND | wx.ALL, 1)
        sizer.Add(btn_stop_resume, 0, wx.EXPAND | wx.ALL, 1)

        btn_nothing.Bind(wx.EVT_BUTTON, self.do_nothing)
        btn_stop_at.Bind(wx.EVT_BUTTON, self.do_stop_at)
        btn_stop_resume.Bind(wx.EVT_BUTTON, self.do_stop_resume)

    def close_button(self, panel):
        return None

    def do_nothing(self, event):
        self._displayed.remove(self._effort)
        self.do_close()

    def do_stop_at(self, event):
        self._displayed.remove(self._effort)
        EditEffortStopDateTimeCommand(
            newValue=self._idle_time, items=[self._effort]
        ).do()
        self.do_close()

    def do_stop_resume(self, event):
        self._displayed.remove(self._effort)
        EditEffortStopDateTimeCommand(
            newValue=self._idle_time, items=[self._effort]
        ).do()
        NewEffortCommand(items=[self._effort.task()]).do()
        self.do_close()


class IdleController(Observer, IdleNotifier):
    def __init__(self, main_window, settings, effort_list):
        self._main_window = main_window
        self._settings = settings
        self._effort_list = effort_list
        self._displayed = set()
        self._went_idle_at = None

        super().__init__()

        self._tracker = effort.EffortListTracker(self._effort_list)
        self._tracker.subscribe(self._on_tracked_changed, "effortlisttracker")

        pub.subscribe(self.poweroff, "powermgt.off")
        pub.subscribe(self.poweron, "powermgt.on")

        self._log_backend_if_enabled()

    def _log_backend_if_enabled(self):
        """Probe and report the idle-detection backend at startup.

        Runs only when the feature is enabled (minidletime > 0). Calling
        get_idle_seconds() also forces lazy backend selection on Linux, so
        no separate runtime logging is needed when the dialog later fires.
        """
        min_time_sec = self.get_min_idle_time()
        if min_time_sec <= 0:
            return

        log_step(
            "Idle time notice enabled; threshold=%d min (%ds)"
            % (min_time_sec // 60, min_time_sec),
            prefix="IDLE",
        )
        log_step("Probing idle backend on %s..." % sys.platform, prefix="IDLE")

        try:
            idle_seconds = self.get_idle_seconds()
        except Exception as e:
            log_step("ERROR: probe raised %r" % e, prefix="IDLE")
            return

        for name, ok, detail in self.get_probe_log():
            status = "OK" if ok else "unavailable"
            suffix = " (%s)" % detail if detail else ""
            log_step("  %s: %s%s" % (name, status, suffix), prefix="IDLE")

        backend = self.get_backend_name()
        if backend:
            log_step("Selected backend: %s" % backend, prefix="IDLE")
            log_step(
                "Test query returned idle=%.2fs" % idle_seconds,
                prefix="IDLE",
            )
        else:
            log_step(
                "WARNING: no backend available; "
                "idle-time notice will not function",
                prefix="IDLE",
            )

    def _on_tracked_changed(self, efforts):
        if len(efforts):
            self.resume()
        else:
            self.pause()

    def get_min_idle_time(self):
        return self._settings.getint("feature", "minidletime") * 60

    def sleep(self):
        log_step("Idle threshold reached while tracking effort", prefix="IDLE")

    def wake(self, timestamp):
        # Keep the went-idle timestamp in its own attribute. Storing it
        # in _last_activity overwrote the IdleNotifier state machine's
        # activity clock with a stale time, which made _check() cycle
        # through sleep/wake on every wx idle event and reopen the
        # notification endlessly after "Do nothing".
        self._went_idle_at = timestamp
        log_step(
            "Wake from idle; idle since %s"
            % date.DateTime.fromtimestamp(timestamp),
            prefix="IDLE",
        )
        self._on_wake()

    def _on_wake(self):
        for tracked_effort in self._tracker.trackedEfforts():
            if tracked_effort not in self._displayed:
                self._displayed.add(tracked_effort)
                frm = WakeFromIdleFrame(
                    date.DateTime.fromtimestamp(self._went_idle_at),
                    tracked_effort,
                    self._displayed,
                    _("Notification"),
                    wx_bitmap=icon_catalog.get_bitmap(
                        "nuvola_apps_korganizer", LIST_ICON_SIZE
                    ),
                )
                NotificationCenter().notify_frame(frm)
