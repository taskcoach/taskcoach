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
from .debug import log_step
import json
import threading
import sys
import traceback
import urllib.request
from taskcoachlib import patterns


class VersionChecker(threading.Thread):
    """The running version against GitHub's latest release, in the
    background; a newer one is shown once (docs/PACKAGING.md, Version
    Check)."""

    def __init__(self, verbose=False):
        self.verbose = verbose
        # Don't block application exit
        super().__init__(daemon=True)

    def run(self):
        from taskcoachlib.gui.dialog import version

        try:
            latest_version_string = self.getLatestVersion()
            latest_version = self.tupleVersion(latest_version_string)
            last_version_notified = self.tupleVersion(
                self.get_last_version_notified()
            )
            current_version = self.tupleVersion(data.version_full)
        except Exception as error:
            log_step("check failed: %r" % error, prefix="VERSION")
            if self.verbose:
                self.notifyUser(
                    version.NoVersionDialog,
                    message="".join(
                        traceback.format_exception_only(
                            sys.exc_info()[0], sys.exc_info()[1]
                        )
                    ),
                )
        else:
            log_step(
                "latest release %s, running %s"
                % (latest_version_string, data.version_full),
                prefix="VERSION",
            )
            if latest_version < current_version and self.verbose:
                self.notifyUser(
                    version.PrereleaseVersionDialog, latest_version_string
                )
            elif latest_version == current_version and self.verbose:
                self.notifyUser(
                    version.VersionUpToDateDialog, latest_version_string
                )
            elif latest_version > current_version and (
                self.verbose or latest_version > last_version_notified
            ):
                if threading.current_thread() is threading.main_thread():
                    self.set_last_version_notified(latest_version_string)
                else:  # Settings are for the GUI thread
                    patterns.later.soon(
                        None,
                        self.set_last_version_notified,
                        latest_version_string,
                    )
                self.notifyUser(
                    version.NewVersionDialog, latest_version_string
                )

    def getLatestVersion(self):
        version_text = self.parse_release(self.retrieve_latest_release())
        return version_text.strip()

    def notifyUser(self, dialog, latest_version="", message=""):
        # Shown from the GUI thread; this is not it
        patterns.later.soon(
            None, self.showDialog, dialog, latest_version, message
        )

    def showDialog(self, version_dialog, latest_version, message=""):
        import wx

        dialog = version_dialog(
            wx.GetApp().GetTopWindow(),
            version=latest_version,
            message=message,
        )
        dialog.Show()
        return dialog

    @staticmethod
    def get_last_version_notified():
        # Here: the settings module imports meta, which imports this
        from taskcoachlib.config import settings

        return settings.version.notified

    @staticmethod
    def set_last_version_notified(version):
        from taskcoachlib.config import settings

        settings.version.notified = version

    @staticmethod
    def parse_release(answer):
        """The version of GitHub's latest release: its tag "v2.0.2.26"
        read as "2.0.2.26"."""
        return json.load(answer)["tag_name"].lstrip("v")

    @staticmethod
    def retrieve_latest_release():
        """GitHub's answer for the latest release; it leaves out drafts
        and prereleases."""
        request = urllib.request.Request(
            data.latest_release_api_url,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "%s/%s" % (data.filename, data.version_full),
            },
        )
        return urllib.request.urlopen(request, timeout=15)

    @staticmethod
    def tupleVersion(version_string):
        return tuple(int(i) for i in version_string.split("."))
