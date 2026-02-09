#!/usr/bin/env python

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

from setuptools import setup, find_namespace_packages
import platform
import re
import os
import sys


def _read_metadata():
    """Read metadata from data.py without importing the module.

    This is necessary for PEP 517 builds where the package isn't installed yet.
    """
    data_path = os.path.join(
        os.path.dirname(__file__), "taskcoachlib", "meta", "data.py"
    )
    with open(data_path, "r", encoding="utf-8") as f:
        content = f.read()

    def extract(pattern, default=""):
        match = re.search(pattern, content, re.MULTILINE)
        return match.group(1) if match else default

    # Extract basic values
    version = extract(r'^version\s*=\s*["\']([^"\']+)["\']', "0.0.0")
    patch = extract(r'^patch\s*=\s*["\']([^"\']+)["\']', "0")
    version_full = f"{version}.{patch}"

    name = extract(r'^name\s*=\s*["\']([^"\']+)["\']', "Task Coach")
    description = extract(r'^description\s*=\s*["\']([^"\']+)["\']', "")
    url = extract(r'^url\s*=\s*["\']([^"\']+)["\']', "")

    return {
        "name": name,
        "filename": name.replace(" ", ""),
        "version": version_full,
        "description": description,
        # These rarely change, so hardcode them to avoid complex regex
        "author": "Frank Niessink, Jerome Laheurte, and Aaron Wolf",
        "author_email": "https://github.com/taskcoach/taskcoach/issues",
        "url": url,
        "license": "GPLv3+",
    }


# Read metadata without importing
_meta = _read_metadata()

# Try to import distro for platform detection, but don't fail if unavailable
try:
    import distro
except ImportError:
    distro = None


def majorAndMinorPythonVersion():
    info = sys.version_info
    try:
        return info.major, info.minor
    except AttributeError:
        return info[0], info[1]


# Dependency Installation Strategy
# ================================
# On Linux distros: Use distro packages where available, pip fallback for missing.
# On Windows/macOS: Use pip for all dependencies.
#
# IMPORTANT: Some packages have minimum version requirements:
# - pyparsing>=3.1.3: Required for pp.Tag() in delta_time.py
# - watchdog>=3.0.0: Required for file monitoring API
# - fasteners>=0.19: Required for file locking API
#
# Debian Bookworm note: pyparsing (3.0.9) and watchdog (2.2.1) are too old,
# must pip install newer versions. See docs/DEBIAN_BOOKWORM_SETUP.md
#
# Optional dependencies (in extras_require):
# - squaremap: Hierarchic data visualization (not in Fedora/Arch repos)

install_requires = [
    "six",
    "pypubsub",
    "watchdog>=3.0.0",  # File monitoring - Bookworm too old, needs pip
    "chardet",
    "python-dateutil",
    "pyparsing>=3.1.3",  # For pp.Tag() - Bookworm too old, needs pip
    "lxml",
    "pyxdg",
    "keyring",
    "numpy",  # Pinned to 1.x in pip-based builds only (see build workflows)
    "fasteners>=0.19",  # File locking
    "pyenchant>=3.2.0",  # Spell checking for text fields
]

# Optional/platform-specific dependencies
extras_require = {
    "squaremap": ["squaremap>=1.0.5"],  # Not in Fedora/Arch repos
    "all": ["squaremap>=1.0.5"],
}

system = platform.system()
if system == "Windows":
    install_requires.append("WMI")

tests_requires = []

# Long description for PyPI
long_description = (
    "Task Coach is a free open source todo manager. It grew "
    "out of frustration about other programs not handling composite tasks well. "
    "In addition to flexible composite tasks, Task Coach has grown to include "
    "prerequisites, prioritizing, effort tracking, category tags, budgets, "
    "notes, and many other features. However, users are not forced to use all "
    "these features; Task Coach can be as simple or complex as you need it to be. "
    "Task Coach is available for Windows, Mac OS X, and GNU/Linux; and there is a "
    "companion iOS app."
)

setupOptions = {
    "name": _meta["filename"],
    "author": _meta["author"],
    "author_email": _meta["author_email"],
    "description": _meta["description"],
    "long_description": long_description,
    "version": _meta["version"],
    "url": _meta["url"],
    "license": _meta["license"],
    "install_requires": install_requires,
    "extras_require": extras_require,
    "tests_require": tests_requires,
    "packages": find_namespace_packages(include=["taskcoachlib", "taskcoachlib.*"]),
    "include_package_data": True,
    "scripts": ["taskcoach.py"],
    "classifiers": [
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: GNU General Public License (GPL)",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Programming Language :: Python :: 3.14",
        "Topic :: Office/Business",
        "Natural Language :: English",
        "Natural Language :: Dutch",
        "Natural Language :: French",
        "Natural Language :: German",
        "Natural Language :: Italian",
        "Natural Language :: Polish",
        "Natural Language :: Portuguese",
        "Natural Language :: Russian",
        "Natural Language :: Spanish",
    ],
}

system = platform.system()
if system == "Linux" and distro is not None:
    # Add data files for Debian-based systems:
    current_dist = distro.id().lower()
    if "debian" in current_dist or "ubuntu" in current_dist:
        setupOptions["data_files"] = [
            (
                "share/applications",
                ["build.in/linux_common/taskcoach.desktop"],
            ),
            ("share/appdata", ["build.in/debian/taskcoach.appdata.xml"]),
            ("share/pixmaps", ["icons.in/taskcoach.png"]),
        ]
elif system == "Windows":
    setupOptions["scripts"].append("taskcoach.pyw")
    # ...
    # ModuleFinder can't handle runtime changes to __path__, but win32com uses them
    try:
        # py2exe 0.6.4 introduced a replacement modulefinder.
        # This means we have to add package paths there, not to the built-in
        # one.  If this new modulefinder gets integrated into Python, then
        # we might be able to revert this some day.
        # if this doesn't work, try import modulefinder
        try:
            import py2exe.mf as modulefinder
        except ImportError:
            import modulefinder
        import win32com, sys

        for p in win32com.__path__[1:]:
            modulefinder.AddPackagePath("win32com", p)
        for extra in ["win32com.shell"]:  # ,"win32com.mapi"
            __import__(extra)
            m = sys.modules[extra]
            for p in m.__path__[1:]:
                modulefinder.AddPackagePath(extra, p)
    except ImportError:
        # no build path setup, no worries.
        pass
elif system == "Darwin":
    # When packaging for MacOS, choose the right binary depending on
    # the platform word size. Actually, we're always packaging on 32
    # bits.
    import struct

    wordSize = "32" if struct.calcsize("L") == 4 else "64"
    sys.path.insert(
        0, os.path.join("taskcoachlib", "bin.in", "macos", "IA%s" % wordSize)
    )
    sys.path.insert(
        0, os.path.join("extension", "macos", "bin-ia%s" % wordSize)
    )
    # pylint: disable=F0401,W0611
    import _powermgt
    import _idle


if __name__ == "__main__":
    setup(**setupOptions)  # pylint: disable=W0142
