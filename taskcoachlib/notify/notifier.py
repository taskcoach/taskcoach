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


class AbstractNotifier(object):
    """
    Abstract base class for interfacing with notification systems.
    Uses the universal notifier (Task Coach's own notification popups).

    Note: The notifier selection feature was removed as of January 2026.
    Only the built-in Task Coach universal notifier is supported.
    See PYTHON3_MIGRATION_5.md for details.
    """

    _notifier = None
    _enabled = True

    def getName(self):
        raise NotImplementedError

    def isAvailable(self):
        raise NotImplementedError

    def notify(self, title, summary, bitmap, **kwargs):
        raise NotImplementedError

    @classmethod
    def register(klass, notifier):
        """Register the universal notifier."""
        if notifier.isAvailable():
            klass._notifier = notifier

    @classmethod
    def get(klass):
        """Get the universal notifier instance."""
        return klass._notifier

    @classmethod
    def getSimple(klass):
        """
        Returns a notifier suitable for simple notifications.
        Uses the universal notifier on all platforms.
        """

        if klass._enabled:
            return klass._notifier
        else:

            class DummyNotifier(AbstractNotifier):
                def getName(self):
                    return "Dummy"

                def isAvailable(self):
                    return True

                def notify(self, title, summary, bitmap, **kwargs):
                    pass

            return DummyNotifier()

    @classmethod
    def disableNotifications(klass):
        klass._enabled = False
