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

from distutils.command.bdist_rpm import bdist_rpm


class bdist_rpm_fedora(bdist_rpm):
    user_options = bdist_rpm.user_options + [
        ("spec-file=", None, "spec file to use"),
        ("desktop-file", None, "desktop file to use"),
    ]

    def initialize_options(self):
        bdist_rpm.initialize_options(self)
        self.spec_file = []
        self.desktop_file = ""

    def _make_spec_file(self):
        """We don't want the spec file to be generated, instead the rpm build
        process should just use the provided spec file."""
        return self.spec_file

    def copy_file(self, source, dest):
        """HACK WARNING! bdist_rpm is difficult to override because its
        methods are much too long. We need to copy the desktop file in
        addition to the icon, so we override copy_file, check whether the
        icon is being copied, and if so, also copy the desktop file."""
        bdist_rpm.copy_file(self, source, dest)
        if source == self.icon:
            bdist_rpm.copy_file(self, self.desktop_file, dest)
