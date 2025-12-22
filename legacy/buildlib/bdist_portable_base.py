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

import os
from distutils.core import Command
from distutils.file_util import copy_file
from distutils import log


class bdist_portable_base(Command, object):
    """Base class for bdist commands that create portable distributions."""

    def copy_files(self, src_dir, dest_dir, copy_recursively=False):
        if src_dir.endswith(".hg"):
            return
        if not os.path.exists(dest_dir):
            os.mkdir(dest_dir)
        for entry in os.listdir(src_dir):
            abs_entry = os.path.join(src_dir, entry)
            if os.path.isfile(abs_entry):
                if os.path.splitext(abs_entry)[1] in (".txt", ".ini"):
                    self.copy_and_expand(abs_entry, dest_dir)
                else:
                    copy_file(abs_entry, dest_dir)
            elif os.path.isdir(abs_entry) and copy_recursively:
                self.copy_files(
                    abs_entry, os.path.join(dest_dir, entry), copy_recursively
                )

    def copy_and_expand(self, src_filename, dest_dir):
        log.info("copying and expanding %s to %s" % (src_filename, dest_dir))
        src_file = open(src_filename, "rb")
        contents = src_file.read()
        src_file.close()
        contents = contents % self.__dict__
        dest_filename = os.path.join(dest_dir, os.path.basename(src_filename))
        dest_file = open(dest_filename, "wb")
        dest_file.write(contents)
        dest_file.close()
