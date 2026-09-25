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

from taskcoachlib import operating_system, patterns
import subprocess
import wx

if operating_system.isWindows():

    class Speaker(object):
        """No-op class since we don't support speech on Windows yet."""

        def say(self, text):
            """Simply ignore the method call."""
            pass

else:

    class Speaker(object, metaclass=patterns.Singleton):
        """Class for letting the computer speak texts. Currently 'say' is
        supported on Mac OS X and 'espeak' on Linux."""

        def __init__(self):
            if operating_system.isMac():
                self.__binary = "say"
            elif operating_system.isGTK():
                self.__binary = "espeak"
            self.__texts_to_say = []
            self.__current_speech_process = None
            self.__retry_pending = False

        def say(self, text):
            """Schedule the text for speaking."""
            self.__texts_to_say.append(text)
            if not self.__retry_pending:
                self.__say_next_text()

        def __say_next_text(self):
            """Say the oldest waiting text if no speech process is
            running. Otherwise, or if more texts wait, try again in one
            second. Only one retry is pending at a time."""
            self.__retry_pending = False
            if not self.__texts_to_say:
                return
            if not self.__is_speaking():
                text = self.__texts_to_say.pop(0)
                self.__current_speech_process = subprocess.Popen(
                    (self.__binary, text)
                )
            if self.__texts_to_say:
                self.__retry_pending = True
                wx.CallLater(1000, self.__say_next_text)

        def __is_speaking(self):
            """Return whether the computer is currently speaking."""
            process = self.__current_speech_process
            return process and process.poll() is None
