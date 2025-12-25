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

from setuptools import setup
from taskcoachlib import meta
import platform
import distro
import os
import sys


def findPackages(base):
    if not os.path.exists(base):
        return list()

    result = [base.replace("/", ".")]

    for name in os.listdir(base):
        fname = os.path.join(base, name)
        if os.path.isdir(fname) and os.path.exists(
            os.path.join(fname, "__init__.py")
        ):
            result.extend(findPackages(fname))
    return result


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
# - zeroconf>=0.50.0: Required for iPhone sync
#
# Debian Bookworm note: pyparsing (3.0.9) and watchdog (2.2.1) are too old,
# must pip install newer versions. See docs/DEBIAN_BOOKWORM_SETUP.md
#
# Optional dependencies (in extras_require):
# - squaremap: Hierarchic data visualization (not in Fedora/Arch repos)
# - gntp: Growl notifications (Windows/Mac only)
# - desktop3: Removed - bundled in taskcoachlib/thirdparty/desktop

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
    "numpy",
    "fasteners>=0.19",  # File locking
    "zeroconf>=0.50.0",  # iPhone sync
]

# Optional/platform-specific dependencies
extras_require = {
    "squaremap": ["squaremap>=1.0.5"],  # Not in Fedora/Arch repos
    "growl": ["gntp>=1.0.3"],            # Growl notifications (Mac/Windows)
    "all": ["squaremap>=1.0.5", "gntp>=1.0.3"],
}

system = platform.system()
if system == "Windows":
    install_requires.append("WMI")
    install_requires.append("gntp")  # Growl notifications
elif system == "Darwin":
    install_requires.append("gntp")  # Growl notifications

setup_requires = ["distro"]

tests_requires = []

setupOptions = {
    "name": meta.filename,
    "author": meta.author,
    "author_email": meta.author_email,
    "description": meta.description,
    "long_description": meta.long_description,
    "version": meta.version,
    "url": meta.url,
    "license": meta.license,
    "install_requires": install_requires,
    "extras_require": extras_require,
    "tests_require": tests_requires,
    "setup_requires": setup_requires,
    "packages": findPackages("taskcoachlib") + findPackages("buildlib"),
    "package_data": {
        "taskcoachlib.gui": ["icons/*.png"],
    },
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
        "Topic :: Office/Business",
    ],
}

# Add available translations:
languages = sorted(
    [
        name
        for name, (code, enabled) in list(meta.data.languages.items())
        if enabled
    ]
)
for language in languages:
    setupOptions["classifiers"].append(
        "Natural Language :: %s" % "English"
        if languages == "English (US)"
        else "Natural Language :: %s" % language
    )

system = platform.system()
if system == "Linux":
    # Add data files for Debian-based systems:
    current_dist = [dist.lower() for dist in distro.id()]
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
    major, minor = majorAndMinorPythonVersion()
    sys.path.insert(
        0,
        os.path.join(
            "taskcoachlib", "bin.in", "windows", "py%d%d" % (major, minor)
        ),
    )
    import _pysyncml

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
