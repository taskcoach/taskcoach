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

import os, fnmatch
from distutils.command.clean import clean as BaseCleanCommand
from distutils import log


class clean(BaseCleanCommand):
    user_options = BaseCleanCommand.user_options + [
        ("really-clean", "r", "remove even more files")
    ]
    boolean_options = BaseCleanCommand.boolean_options + ["really-clean"]

    def initialize_options(self):
        super().initialize_options()
        # pylint: disable=W0201
        self.really_clean = False
        self.cleaning_patterns = ["*.pyc"]
        self.really_clean_patterns = ["*.bak"]

    def finalize_options(self):
        super().finalize_options()
        if self.really_clean:
            self.cleaning_patterns.extend(self.really_clean_patterns)

    def run(self):
        super().run()
        if not self.verbose:
            log.info(
                "recursively removing '"
                + "', '".join(self.cleaning_patterns)
                + "'"
            )
        for root, _, files in os.walk("."):
            for pattern in self.cleaning_patterns:
                for filename in fnmatch.filter(files, pattern):
                    filename = os.path.join(root, filename)
                    try:
                        if not self.dry_run:
                            os.unlink(filename)
                        if self.verbose:
                            log.info("removing '%s'" % filename.strip(".\\"))
                    except IOError:
                        pass
