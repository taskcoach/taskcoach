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

# Backend-selected controller for minimizing / restoring the main
# window from the system tray.
#
# Why this exists: Wayland's core xdg-shell has no minimize state an
# application can read or react to, and GTK3 (hence wxGTK) never sets
# the iconified state on Wayland, so the old
# IsIconized()/IsShown()/IsActive() heuristic in taskbaricon.py was
# unreliable and menu-driven invocation broke it entirely. The fix is
# to stop guessing window state and instead use the mechanism
# appropriate to the session, selected once by a probe (same pattern
# as the idle backend in taskcoachlib/powermgt/idle.py).
#
# See docs/SYSTEM_TRAY.md ("Window Show/Hide on Wayland") for the full
# analysis, the coverage matrix, and the one unsupported configuration
# (GNOME Wayland with a taskbar extension).

from taskcoachlib import operating_system


class ToplevelController(object):
    """Minimize / restore the main window.

    Subclasses use whatever mechanism is correct for the session so
    that the tray "Show/Hide" works regardless of how the window was
    minimized (tray menu, titlebar button, shortcut).
    """

    backend = "abstract"

    def __init__(self, window):
        self._window = window

    def is_minimized(self):
        """True if the window is currently minimized or hidden."""
        raise NotImplementedError

    def minimize(self):
        """Minimize the window, keeping its taskbar entry where the
        platform allows."""
        raise NotImplementedError

    def restore(self):
        """Unminimize the window and bring it to the front."""
        raise NotImplementedError


class NativeController(ToplevelController):
    """X11, Windows and macOS: wx tracks window state natively, so
    the toolkit's own minimize/restore is correct and keeps the
    taskbar/dock entry.
    """

    backend = "native"

    def is_minimized(self):
        return self._window.IsIconized() or not self._window.IsShown()

    def minimize(self):
        if operating_system.isMac():
            # macOS tray apps do not minimize to the tray; the
            # established behaviour is to just bring the window
            # forward. Preserve it (no regression on macOS).
            self._window.Raise()
        else:
            self._window.Iconize()

    def restore(self):
        # MainWindow.restore() ignores its event argument.
        self._window.restore(None)


class HideShowController(ToplevelController):
    """Universal Wayland fallback.

    Used when no session window-management protocol is usable (GNOME
    default, no taskbar configured, or pywayland unavailable). Hide()
    unmaps the surface so the window leaves the taskbar entirely; the
    tray icon is the deliberate access point. This is the only
    mechanism that works on every Wayland compositor.
    """

    backend = "hide_show"

    def is_minimized(self):
        return not self._window.IsShown()

    def minimize(self):
        self._window.Hide()

    def restore(self):
        self._window.Show()
        self._window.Raise()


class KdePlasmaController(ToplevelController):
    """KDE Plasma Wayland: minimize/restore via the
    org_kde_plasma_window_management protocol (the same channel KWin's
    own taskbar uses), so the window keeps its Plasma taskbar entry
    and the tray "Show" can restore it no matter how it was minimized.

    On-demand: each call opens a short-lived side Wayland connection,
    enumerates toplevels, matches our own by PID (then title), reads
    or sets state, and disconnects. No persistent thread. Any failure
    (no pywayland, protocol absent, own window not found) returns None
    so the caller falls back to plain Hide/Show, never breaking.
    """

    backend = "kde_plasma_window_management"

    def __init__(self, window):
        super().__init__(window)
        self._fallback = HideShowController(window)

    # -- internal: run an action against our own plasma window -------

    def _with_own_window(self, action):
        """Connect, find our OrgKdePlasmaWindow, call
        action(proxy, flags) and return its result; None on any
        failure."""
        import os

        if not os.environ.get("WAYLAND_DISPLAY"):
            return None
        try:
            from pywayland.client import Display
            from taskcoachlib.thirdparty.plasma_window_management import (
                OrgKdePlasmaWindowManagement,
            )
        except ImportError:
            return None

        display = None
        try:
            display = Display()
            display.connect()
            mgr_box = {"mgr": None}

            def on_global(registry, id_, interface, version):
                if interface == "org_kde_plasma_window_management":
                    bind_ver = min(
                        version, OrgKdePlasmaWindowManagement.version
                    )
                    mgr_box["mgr"] = registry.bind(
                        id_, OrgKdePlasmaWindowManagement, bind_ver
                    )

            registry = display.get_registry()
            registry.dispatcher["global"] = on_global
            display.roundtrip()
            mgr = mgr_box["mgr"]
            if mgr is None:
                return None  # not KDE / protocol not advertised

            windows = []

            def attach(win):
                info = {
                    "proxy": win,
                    "pid": None,
                    "title": None,
                    "flags": 0,
                    "mapped": True,
                }
                windows.append(info)
                d = win.dispatcher
                d["pid_changed"] = (
                    lambda w, pid: info.__setitem__("pid", pid)
                )
                d["title_changed"] = (
                    lambda w, t: info.__setitem__("title", t)
                )
                d["state_changed"] = (
                    lambda w, f: info.__setitem__("flags", f)
                )
                d["unmapped"] = (
                    lambda w: info.__setitem__("mapped", False)
                )

            def on_window_uuid(mgr_proxy, id_, uuid):
                attach(mgr_proxy.get_window_by_uuid(uuid))

            def on_window(mgr_proxy, id_):
                attach(mgr_proxy.get_window(id_))

            mgr.dispatcher["window_with_uuid"] = on_window_uuid
            mgr.dispatcher["window"] = on_window
            # First roundtrip: receive window/window_with_uuid events.
            display.roundtrip()
            # Second: receive each window's pid/title/state.
            display.roundtrip()

            mypid = os.getpid()
            mine = [
                w for w in windows if w["mapped"] and w["pid"] == mypid
            ]
            if not mine:
                title = self._window.GetTitle()
                mine = [
                    w
                    for w in windows
                    if w["mapped"] and w["title"] == title
                ]
            if not mine:
                return None

            target = mine[0]
            result = action(target["proxy"], target["flags"])
            display.roundtrip()
            return result
        except Exception:
            return None
        finally:
            if display is not None:
                try:
                    display.disconnect()
                except Exception:
                    pass

    @staticmethod
    def _state_enum():
        from taskcoachlib.thirdparty.plasma_window_management import (
            OrgKdePlasmaWindowManagement,
        )

        return OrgKdePlasmaWindowManagement.state

    # -- ToplevelController interface --------------------------------

    def is_minimized(self):
        s = self._state_enum()

        def read(proxy, flags):
            return bool(flags & int(s.minimized))

        result = self._with_own_window(read)
        if result is None:
            return self._fallback.is_minimized()
        return result

    def minimize(self):
        s = self._state_enum()

        def do(proxy, flags):
            proxy.set_state(int(s.minimized), int(s.minimized))
            return True

        if self._with_own_window(do) is None:
            self._fallback.minimize()

    def restore(self):
        s = self._state_enum()

        def do(proxy, flags):
            # Clear minimized and set active (same call KWin's
            # taskbar uses to un-minimize and raise).
            proxy.set_state(
                int(s.minimized) | int(s.active), int(s.active)
            )
            return True

        if self._with_own_window(do) is None:
            self._fallback.restore()


def _kde_plasma_available():
    """Cheap probe: WAYLAND_DISPLAY set, pywayland importable, and the
    org_kde_plasma_window_management global advertised."""
    import os

    if not os.environ.get("WAYLAND_DISPLAY"):
        return False
    try:
        from pywayland.client import Display
    except ImportError:
        return False

    display = None
    try:
        display = Display()
        display.connect()
        found = {"ok": False}

        def on_global(registry, id_, interface, version):
            if interface == "org_kde_plasma_window_management":
                found["ok"] = True

        registry = display.get_registry()
        registry.dispatcher["global"] = on_global
        display.roundtrip()
        return found["ok"]
    except Exception:
        return False
    finally:
        if display is not None:
            try:
                display.disconnect()
            except Exception:
                pass


def create_toplevel_controller(window):
    """Probe the session and return the controller to use.

    Native on X11/Windows/macOS. On Wayland, prefer the KDE
    org_kde_plasma_window_management backend (keeps the Plasma taskbar
    entry and supports restore); the wlroots
    (wlr-foreign-toplevel-management) backend is follow-up work.
    Everything else (GNOME default, no taskbar, no pywayland) falls
    back to the universally-correct Hide/Show, which never regresses
    behaviour. See docs/SYSTEM_TRAY.md for the coverage matrix.
    """
    if not operating_system.isGTK():
        return NativeController(window)
    if not operating_system.isWayland():
        return NativeController(window)
    if _kde_plasma_available():
        return KdePlasmaController(window)
    return HideShowController(window)
