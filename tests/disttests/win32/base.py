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

""" These tests actually assume a fresh configuration (new .ini file, 
nothing changed). """  # pylint: disable=W0105

import sys, os, time, re, shutil, unittest
import win32process, win32event, win32gui, win32con

sys.path.insert(0, os.path.join(os.path.split(__file__)[0], "sendinput"))
from . import sendinput as si


class Window(object):
    def __init__(self, hwnd):
        self.hwnd = hwnd

    def _get_title(self):
        return win32gui.GetWindowText(self.hwnd)

    def _set_title(self, title):
        win32gui.SetWindowText(self.hwnd, title)

    title = property(_get_title, _set_title, doc="The window title/text")

    def _get_klass(self):
        return win32gui.GetClassName(self.hwnd)

    klass = property(_get_klass, doc="The window class name")

    def _get_children(self):
        result = []

        def cb(hwnd, lparam):  # pylint: disable=W0613
            result.append(Window(hwnd))
            return True

        try:
            win32gui.EnumChildWindows(self.hwnd, cb, None)
        except Exception:
            result = []  # Window enumeration failed
        return result

    children = property(_get_children, doc="The window direct children")

    def _get_isForeground(self):
        return win32gui.GetForegroundWindow() == self.hwnd

    isForeground = property(
        _get_isForeground, doc="Whether the window is the foreground"
    )

    def waitFocus(self):
        for _ in range(10):
            time.sleep(1)
            if self.isForeground:
                return True
        return False

    def clickAt(self, dx, dy):
        """Simulates a click at a given position (relative to the window)"""

        # Posting WM_LBUTTON[DOWN/UP] does not work it seems. Use
        # SendInput instead. We must find the absolute coordinates
        # first, and normalize them for SendInput.

        x, y = win32gui.ClientToScreen(self.hwnd, (0, 0))
        x += dx
        y += dy

        desktop = win32gui.GetDesktopWindow()
        left, top, right, bottom = win32gui.GetClientRect(desktop)

        x = int(x * 65535 / (right - left))
        y = int(y * 65535 / (bottom - top))

        si.SendInput(
            (
                si.INPUT_MOUSE,
                (x, y, 0, si.MOUSEEVENTF_ABSOLUTE | si.MOUSEEVENTF_MOVE, 0),
            ),
            (si.INPUT_MOUSE, (0, 0, 0, si.MOUSEEVENTF_LEFTDOWN, 0)),
            (si.INPUT_MOUSE, (0, 0, 0, si.MOUSEEVENTF_LEFTUP, 0)),
        )

    def sendText(self, text):
        inputs = []
        for char in text:
            inputs.append((si.INPUT_KEYBOARD, (char, 0)))
            inputs.append((si.INPUT_KEYBOARD, (char, si.KEYEVENTF_KEYUP)))
        si.SendInput(*tuple(inputs))

    def close(self):
        """Closes the window."""
        win32gui.SendMessage(self.hwnd, win32con.WM_CLOSE, 0, 0)

    def findChildren(self, klass, title):
        """Find all children, recursively, matching a class and a title."""

        result = []
        for child in self.children:
            if child.klass == klass and child.title == title:
                result.append(child)
            result.extend(child.findChildren(klass, title))
        return result

    def dump(self, level=0):
        """Dumps the window and its children, recursively, to stdout."""
        print((" " * level) + str(self))
        for child in self.children:
            child.dump(level + 1)

    def __str__(self):
        return '%s("%s")' % (self.klass, self.title)


class Win32TestCase(unittest.TestCase):
    args = []
    basepath = os.path.split(__file__)[0]

    def setUp(self):
        self.processHandle = None
        shutil.copyfile(
            os.path.join(self.basepath, "test.tsk"),
            os.path.join(self.basepath, "testfile.tsk"),
        )

        path = os.path.join("..", "build")
        for name in os.listdir(path):
            dirname = os.path.join(path, name)
            filename = os.path.join(dirname, "taskcoach.exe")
            if os.path.isdir(dirname) and os.path.exists(filename):
                break
        else:
            self.fail("Could not find Task Coach executable.")

        self.logfilename = filename + ".log"
        cmd = [filename, "-i", "test.ini", "-l", "en"] + self.args

        sinfo = win32process.STARTUPINFO()
        sinfo.dwFlags = 0
        hProcess = win32process.CreateProcess(
            None, " ".join(cmd), None, None, False, 0, None, os.getcwd(), sinfo
        )[0]
        self.processHandle = hProcess
        if (
            win32event.WaitForInputIdle(hProcess, 120000)
            == win32event.WAIT_TIMEOUT
        ):
            self.fail("Could not launch Task Coach.")

        window = self.findWindow(r"^Errors occurred", tries=3)
        if window is not None:
            window.close()
            self.fail(
                "Errors occurred. The log content was:\n"
                + open(self.logfilename, "rb").read()
            )

        window = self.findWindow(r"^Tip of the day$")
        if window is None:
            self.fail("Tip window didn't appear")
        window.close()

        window = self.findWindow(
            r"^New version of Task Coach available$", tries=3
        )
        if window:
            window.close()

    def tearDown(self):
        if self.processHandle is not None:
            win32process.TerminateProcess(self.processHandle, 0)
            win32event.WaitForSingleObject(
                self.processHandle, win32event.INFINITE
            )
        os.remove(os.path.join(self.basepath, "testfile.tsk"))
        lockdir = os.path.join(self.basepath, "testfile.tsk.lock")
        if os.path.exists(lockdir):
            shutil.rmtree(os.path.join(self.basepath, "testfile.tsk.lock"))
        if os.path.exists(self.logfilename):
            os.remove(self.logfilename)

    def findWindow(self, title, tries=5):
        """Waits for a window to appear, and return a Window instance,
        or None if not found.

        @param title: Criterion for the window's title
            (regular expression string)
        @param tries: Max number of scans to perform. Scans are one
            second apart."""

        titleRegex = re.compile(title)

        for _ in range(tries):
            windows = []

            def enumCb(hwnd, lparam):  # pylint: disable=W0613
                try:
                    if titleRegex.search(win32gui.GetWindowText(hwnd)):
                        windows.append(hwnd)
                except Exception:
                    pass  # Window title matching failed
                return True

            win32gui.EnumWindows(enumCb, None)

            if windows:
                return Window(windows[0])
            time.sleep(1)

        return None
