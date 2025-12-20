# -*- coding: utf-8 -*-

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

# pylint: disable=C0103

# Edit these for every release:
# IMPORTANT: Always increment version_patch AND update release_day/release_month below!

version = "1.6.1"  # Current version number of the application
version_patch = "59"  # Patch level - INCREMENT THIS AND UPDATE DATE BELOW!
version_full = f"{version}.{version_patch}"  # Full version string: 1.6.1.11


def _get_git_commit_hash():
    """Dynamically get the current git commit hash at runtime.

    Returns the short (7-char) commit hash, or empty string if not in a git repo
    or git is not available.
    """
    import subprocess
    import os

    try:
        # Get the directory where this file is located
        this_dir = os.path.dirname(os.path.abspath(__file__))
        # Run git rev-parse to get the short commit hash
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=this_dir,
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        pass  # git not available or not in a git repo
    return ""


# Get git commit hash dynamically (empty string if not available)
git_commit_hash = _get_git_commit_hash()
# For display purposes, show "(n/a)" if no commit hash available
version_commit = git_commit_hash if git_commit_hash else "(n/a)"

tskversion = 37  # Current version number of the task file format, changed to 37 for release 1.3.23.
release_day = "20"  # Day number of the release, 1-31, as string
release_month = "December"  # Month of the release in plain English
release_year = "2025"  # Year of the release as string
release_status = "stable"  # One of 'alpha', 'beta', 'stable'

# Legacy: keep version_with_patch for backwards compatibility
version_with_patch = version_full
git_commit_count = version_patch

# No editing needed below this line for doing a release.

import re, datetime

try:
    from taskcoachlib.meta.revision import (
        revision,
    )  # pylint: disable=F0401,W0611
except ImportError:
    revision = None

months = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
]

if revision:  # Buildbot sets revision
    # Decrement version because this version isn't released yet. This
    # assumes that version components are < 100; 99 will actually mean
    # pre-major release
    # pylint: disable=W0141
    major, inter, minor = list(map(int, version.split(".")))
    numversion = major * 10000 + inter * 100 + minor
    numversion -= 1
    major = numversion // 10000
    inter = (numversion // 100) % 100
    minor = numversion % 100
    version = ".".join(map(str, [major, inter, minor]))

    now = datetime.datetime.today()
    release_day = str(now.day)
    release_month = months[now.month - 1]
    release_year = str(now.year)
    release_status = "beta"
    version += "." + revision

assert release_month in months  # Try to prevent typo's
release_month_nr = "%02d" % (months.index(release_month) + 1)
release_day_nr = "%02d" % int(release_day)
date = release_month + " " + release_day + ", " + release_year

name = "Task Coach"
description = "Your friendly task manager"
long_description = (
    "%(name)s is a free open source todo manager. It grew "
    "out of frustration about other programs not handling composite tasks well. "
    "In addition to flexible composite tasks, %(name)s has grown to include "
    "prerequisites, prioritizing, effort tracking, category tags, budgets, "
    "notes, and many other features. However, users are not forced to use all "
    "these features; %(name)s can be as simple or complex as you need it to be. "
    "%(name)s is available for Windows, Mac OS X, and GNU/Linux; and there is a "
    "companion iOS app." % dict(name=name)
)
keywords = "task manager, todo list, pim, time registration, track effort"
author_first, author_last = "Frank", "Niessink"  # Needed for PAD file
author = "%s %s, Jerome Laheurte, and Aaron Wolf" % (author_first, author_last)
author_unicode = "%s %s, Jérôme Laheurte, and Aaron Wolf" % (
    author_first,
    author_last,
)
author_email = "developers@taskcoach.org"

filename = name.replace(" ", "")
filename_lower = filename.lower()

url = "https://github.com/realcarbonneau/taskcoach"  # Project homepage (GitHub)
github_url = url  # Alias for backwards compatibility
faq_url = "https://answers.launchpad.net/taskcoach/+faqs"
bug_report_url = github_url + "/issues"  # GitHub issues for bug reports
known_bugs_url = github_url + "/issues"  # GitHub issues for known bugs
support_request_url = github_url + "/issues"  # GitHub issues for support
feature_request_url = github_url + "/issues"  # GitHub issues for feature requests
translations_url = github_url + "/pulls"  # GitHub pull requests for translations

announcement_addresses = (
    "taskcoach@yahoogroups.com, python-announce-list@python.org"
)
bcc_announcement_addresses = "johnhaller@portableapps.com"

copyright = "Copyright (C) 2004-%s %s" % (
    release_year,
    author,
)  # pylint: disable=W0622
license_title = "GNU General Public License"
license_version = "3"
license_title_and_version = "%s version %s" % (license_title, license_version)
license = (
    "%s or any later version" % license_title_and_version
)  # pylint: disable=W0622
license_title_and_version_abbrev = "GPLv%s" % license_version
license_abbrev = "%s+" % license_title_and_version_abbrev
license_notice = """%(name)s is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

%(name)s is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.""" % dict(
    name=name
)

license_notice_html = "<p>%s</p>" % license_notice.replace("\n\n", "</p><p>")
license_notice_html = re.sub(
    r"<http([^>]*)>",
    r'<a href="http\1" target="_blank">http\1</a>',
    license_notice_html,
)

platform = "Any"
pythonversion = "2.6"
wxpythonversionnumber = "3.0.0.0"
wxpythonversion = "%s-unicode" % wxpythonversionnumber
# NOTE (Twisted Removal - 2024): Twisted is no longer required.
# Replaced with native wxPython event handling, watchdog, and socketserver.
watchdogversionnumber = "3.0.0"
igraphversionnumber = "0.7"

languages = {
    "English (US)": (None, True),
    "English (AU)": ("en_AU", True),
    "English (CA)": ("en_CA", True),
    "English (GB)": ("en_GB", True),
    "Arabic": ("ar", False),
    "Basque": ("eu", False),
    "Belarusian": ("be", False),
    "Bosnian": ("bs", False),
    "Breton": ("br", False),
    "Bulgarian": ("bg", False),
    "Catalan": ("ca", False),
    "Chinese (Simplified)": ("zh_CN", False),
    "Chinese (Traditional)": ("zh_TW", False),
    "Czech": ("cs", True),
    "Danish": ("da", False),
    "Dutch": ("nl", True),
    "Esperanto": ("eo", False),
    "Estonian": ("et", False),
    "Finnish": ("fi", True),
    "French": ("fr", True),
    "Galician": ("gl", False),
    "German": ("de", True),
    "German (Low)": ("nds", False),
    "Greek": ("el", False),
    "Hebrew": ("he", False),
    "Hindi": ("hi", False),
    "Hungarian": ("hu", False),
    "Indonesian": ("id", False),
    "Italian": ("it", True),
    "Japanese": ("ja", False),
    "Korean": ("ko", False),
    "Latvian": ("lv", False),
    "Lithuanian": ("lt", False),
    "Marathi": ("mr", False),
    "Mongolian": ("mn", False),
    "Norwegian (Bokmal)": ("nb", False),
    "Norwegian (Nynorsk)": ("nn", False),
    "Occitan": ("oc", False),
    "Papiamento": ("pap", False),
    "Persian": ("fa", False),
    "Polish": ("pl", True),
    "Portuguese": ("pt", True),
    "Portuguese (Brazilian)": ("pt_BR", True),
    "Romanian": ("ro", True),
    "Russian": ("ru", True),
    "Slovak": ("sk", True),
    "Slovene": ("sl", False),
    "Spanish": ("es", True),
    "Swedish": ("sv", False),
    "Telugu": ("te", False),
    "Thai": ("th", False),
    "Turkish": ("tr", True),
    "Ukranian": ("uk", False),
    "Vietnamese": ("vi", False),
}
languages_list = ",".join(list(languages.keys()))


def __createDict(localsDict):
    """Provide the local variables as a dictionary for use in string
    formatting."""
    metaDict = {}  # pylint: disable=W0621
    for key in localsDict:
        if not key.startswith("__"):
            metaDict[key] = localsDict[key]
    return metaDict


metaDict = __createDict(locals())
