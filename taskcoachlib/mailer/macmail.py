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

from taskcoachlib.i18n import _
from taskcoachlib import operating_system
import wx, subprocess, threading, time


class MailAppInfoLoader(wx.ProgressDialog):
    def __init__(self, parent):
        super().__init__(
            _("Reading mail info..."),
            _("Reading mail information. Please wait."),
            parent=parent,
            style=wx.PD_SMOOTH | wx.PD_ELAPSED_TIME | wx.PD_CAN_SKIP,
        )

        self.__title = None
        thread = threading.Thread(target=self.__run)
        thread.start()

    def __run(self):
        script = """
tell application "Mail"
    set theMessages to selection
    subject of beginning of theMessages
end tell
"""
        try:
            sp = subprocess.Popen(
                "osascript",
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
            out, err = sp.communicate(script)
            if not sp.returncode:
                self.__title = operating_system.decodeSystemString(out.strip())
                return
        except (OSError, subprocess.SubprocessError):
            pass  # AppleScript execution failed

        self.__title = _("Mail.app message")

    def title(self):
        return self.__title


def getSubjectOfMail(messageId):  # pylint: disable=W0613
    """This should return the subject of the mail having the specified
    message-id. Unfortunately, until I find an Applescript guru, it
    will only return the subject of the currently selected mail in
    Mail.app."""

    dlg = MailAppInfoLoader(None)
    dlg.ShowModal()
    try:
        while dlg.title() is None:
            time.sleep(0.2)
            unused, skip = dlg.Pulse()
            if skip:
                return _("Mail.app message")
        return dlg.title()
    finally:
        dlg.Destroy()
