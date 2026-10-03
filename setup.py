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
import re
import os


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

# Dependency Installation Strategy
# ================================
# On Linux distros: Use distro packages where available, pip fallback for missing.
# On Windows/macOS: Use pip for all dependencies.
#
# IMPORTANT: Some packages have minimum version requirements:
# - pyparsing>=3.0.0: the pyparsing 3 API of delta_time.py
#
# Optional dependencies (in extras_require):
# - squaremap: Hierarchic data visualization (not in Fedora/Arch repos)

install_requires = [
    "chardet",
    "python-dateutil",
    "pyparsing>=3.0.0",  # pyparsing 3 API, every supported distro has it
    "lxml",
    "keyring",
    "pyenchant>=3.2.0",  # Spell checking for text fields
    # Windows calls: Outlook, folders, windows, monitors, processes
    "pywin32; sys_platform == 'win32'",
]

# Optional/platform-specific dependencies
extras_require = {
    "squaremap": ["squaremap>=1.0.5"],  # Not in Fedora/Arch repos
    "all": ["squaremap>=1.0.5"],
}

# Long description for PyPI
long_description = (
    "Task Coach is a free open source todo manager. It grew "
    "out of frustration about other programs not handling composite tasks well. "
    "In addition to flexible composite tasks, Task Coach has grown to include "
    "prerequisites, prioritizing, effort tracking, category tags, budgets, "
    "notes, and many other features. However, users are not forced to use all "
    "these features; Task Coach can be as simple or complex as you need it to be. "
    "Task Coach is available for Windows, Mac OS X, and GNU/Linux."
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
    # Ubuntu 22.04's, the oldest of the supported distributions
    "python_requires": ">=3.10",
    "packages": find_namespace_packages(
        include=["taskcoachlib", "taskcoachlib.*"]
    ),
    "include_package_data": True,
    "scripts": ["taskcoach.py"],
    "classifiers": [
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: GNU General Public License (GPL)",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
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

if __name__ == "__main__":
    setup(**setupOptions)  # pylint: disable=W0142
