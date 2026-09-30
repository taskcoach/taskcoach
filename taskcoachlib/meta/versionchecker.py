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
import sys
import traceback
from taskcoachlib import patterns


class VersionChecker(threading.Thread):
    def __init__(self, settings, verbose=False):
        self.settings = settings
        self.verbose = verbose
        # Don't block application exit
        super().__init__(daemon=True)

    def run(self):
        from taskcoachlib.gui.dialog import version

        try:
            latestVersionString = self.getLatestVersion()
            latestVersion = self.tupleVersion(latestVersionString)
            lastVersionNotified = self.tupleVersion(
                self.getLastVersionNotified()
            )
            currentVersion = self.tupleVersion(data.version)
        except Exception:
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
            if latestVersion < currentVersion and self.verbose:
                self.notifyUser(
                    version.PrereleaseVersionDialog, latestVersionString
                )
            elif latestVersion == currentVersion and self.verbose:
                self.notifyUser(
                    version.VersionUpToDateDialog, latestVersionString
                )
            elif latestVersion > currentVersion and (
                self.verbose or latestVersion > lastVersionNotified
            ):
                if threading.current_thread() is threading.main_thread():
                    self.setLastVersionNotified(latestVersionString)
                else:  # Settings are for the GUI thread
                    patterns.later.soon(
                        None, self.setLastVersionNotified, latestVersionString
                    )
                self.notifyUser(version.NewVersionDialog, latestVersionString)

    def getLatestVersion(self):
        versionText = self.parseVersionFile(self.retrieveVersionFile())
        return versionText.strip()

    def notifyUser(self, dialog, latestVersion="", message=""):
        # Shown from the GUI thread; this is not it
        patterns.later.soon(
            None, self.showDialog, dialog, latestVersion, message
        )

    def showDialog(self, VersionDialog, latestVersion, message=""):
        import wx

        dialog = VersionDialog(
            wx.GetApp().GetTopWindow(),
            version=latestVersion,
            message=message,
            settings=self.settings,
        )
        dialog.Show()
        return dialog

    def getLastVersionNotified(self):
        return self.settings.get("version", "notified")

    def setLastVersionNotified(self, lastVersionNotifiedString):
        self.settings.set("version", "notified", lastVersionNotifiedString)

    @staticmethod
    def parseVersionFile(versionFile):
        return versionFile.readline()

    @staticmethod
    def retrieveVersionFile():
        # Legacy: version checking disabled - use GitHub for updates
        raise Exception("Version checking disabled - visit GitHub for updates")

    @staticmethod
    def tupleVersion(versionString):
        return tuple(int(i) for i in versionString.split("."))
