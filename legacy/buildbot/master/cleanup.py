#!/usr/bin/python

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

# Cleanup the htdocs subdirectory where the buildbot stores the
# distribution files (only keep 2 latest versions). Run from cron.

import os, re


def cleanup(path, rx):
    files = []
    for name in os.listdir(path):
        mt = rx.search(name)
        if mt:
            files.append((int(mt.group(1)), name))

    if len(files) <= 2:
        return

    files.sort()
    files.reverse()

    for rev, name in files[2:]:
        os.remove(os.path.join(path, name))


def main(path):
    for suffix in [r"-win32\.exe", r"\.dmg", r"\.tar\.gz", r"\.zip"]:
        cleanup(path, re.compile(r"^TaskCoach-r(\d+)" + suffix + "$"))
    cleanup(path, re.compile(r"taskcoach_r(\d+)-1_all\.deb"))


if __name__ == "__main__":
    main("/var/www/htdocs/TaskCoach-packages")
