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

from . import data
import threading
import urllib.request, urllib.error, urllib.parse


class DeveloperMessageChecker(threading.Thread):
    """Check for messages from the developers on the website."""

    def __init__(
        self, settings, urlopen=urllib.request.urlopen, call_after=None
    ):
        self.__settings = settings
        self.__urlopen = urlopen
        self.__call_after = call_after or self.__wx_call_after
        super().__init__()

    def _set_daemon(self):
        return True  # Don't block application exit

    def run(self, show=True):  # pylint: disable=W0221
        try:
            message, url = self.__get_message()
        except Exception:
            return  # Whatever goes wrong, ignore it.
        if self.__message_is_new(message):
            return self.__notify_user(message, url, show)

    def __message_is_new(self, message):
        """Return whether this message has been displayed before. Note that
        we only remember the last message displayed, not the complete
        history of messages."""
        last_message = self.__settings.gettext("view", "lastdevelopermessage")
        return message != last_message

    def __get_message(self):
        """Retrieve and parse the message file."""
        return self.__parse_message_file(self.__retrieve_message_file())

    def __notify_user(self, message, url, show=True):
        """Notify the user about the message."""
        # Must use CallAfter because this is a non-GUI thread.
        return self.__call_after(self.__show_dialog, message, url, show)

    @staticmethod
    def __wx_call_after(function, *args, **kwargs):
        """Use this method for calling GUI methods from a non-GUI thread."""
        # Import wx here so it isn't a build dependency.
        import wx

        wx.CallAfter(function, *args, **kwargs)

    def __show_dialog(self, message, url, show=True):
        """Show the message dialog."""
        dialog = self.__create_dialog(message, url)
        dialog.Show(show)
        return dialog

    def __create_dialog(self, message, url):
        """Create the message dialog."""
        import wx
        from taskcoachlib.gui.dialog import developer_message

        return developer_message.MessageDialog(
            wx.GetApp().GetTopWindow(),
            message=message,
            url=url,
            settings=self.__settings,
        )

    @staticmethod
    def __parse_message_file(message_file):
        """Return a (message, url) tuple parsed from the message file.
        Catching parsing exceptions is a caller responsibility."""
        lines = message_file.readlines()
        lines_without_comments = [
            line for line in lines if not line.startswith("#")
        ]
        return lines_without_comments[0].strip().split("|")

    def __retrieve_message_file(self):
        """Retrieve the message file from the website. Catching exceptions
        is a caller responsibility."""
        return self.__urlopen(data.message_url)
