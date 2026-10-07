"""
Task Coach - Your friendly task manager
Copyright (C) 2004-2026 Task Coach developers <developers@taskcoach.org>

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

# Written data stays in the system's memory for some seconds before it
# reaches the disk; a power cut then can leave a file empty or old.
# Saves put the new file on disk before it replaces the old one, then
# the folder's entry (docs/PERSISTENCE_XML.md, Saving).

import errno
import os

# File systems that cannot sync (some network and FUSE ones) say so
_UNSUPPORTED = (errno.EINVAL, errno.ENOTSUP)


def sync_file(file):
    """Write out a file object's buffer and put its data on disk."""
    file.flush()
    try:
        os.fsync(file.fileno())
    except OSError as reason:
        if reason.errno not in _UNSUPPORTED:
            raise


def sync_folder(path):
    """Put a folder's entries on disk where the system allows it: POSIX;
    Windows has no such call and needs none."""
    if os.name == "nt":
        return
    try:
        descriptor = os.open(path or os.curdir, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(descriptor)
    except OSError:
        pass  # The file itself is on disk; its entry follows soon
    finally:
        os.close(descriptor)
