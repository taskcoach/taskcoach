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

import re

# pylint: disable=C0103

# =============================================================================
# VERSION CONFIGURATION - Edit these for every release
# =============================================================================
# IMPORTANT: When releasing a new version:
#   1. Increment patch below (and version if needed)
#   2. Update release_day, release_month, release_year below
#   3. Update version numbers in README.md
#   4. Update changelogs (debian/changelog, build.in/fedora/taskcoach.spec)
#
# The version is defined HERE in data.py as the single source of truth.
# This ensures the version is always available since it's embedded in the
# Python source code and cannot be lost during packaging or installation.
#
# Version format: Major.Minor.Milestone.Patch
#   - Major: Breaking changes or major new features
#   - Minor: New features, backwards compatible
#   - Milestone: Target milestone for a set of patches
#   - Patch: Incremented for each bug fix release
# =============================================================================

version = "2.0.3"  # Major.Minor.Milestone
patch = "4"  # Patch number - INCREMENT THIS for each release
version_full = f"{version}.{patch}"  # Full version: 2.0.3.4

release_day = "8"  # Day of the release (1-31)
release_month = "October"  # Month of the release
release_year = "2026"  # Year of the release

# =============================================================================
# END VERSION CONFIGURATION
# =============================================================================


# Task file format versions (docs/PERSISTENCE_XML.md, Versions and
# Compatibility). The format this release writes and the newest it
# reads (38 since 2.0.3.0: categories stored on the items; 39: the
# "No icon" override):
tskformat = 39
# The format a reader needs for this release's files, which releases
# before 2.0.3.0 check: 37 while the files also hold the forms 2.0.2.0
# and later read (persistence/xml/legacy.py).
tskversion = 37
release_status = "stable"  # One of 'alpha', 'beta', 'stable'

# No editing needed below this line for doing a release.

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

assert release_month in months  # Try to prevent typo's
date = release_month + " " + release_day + ", " + release_year

name = "Task Coach"
description = "Your friendly task manager"
author_first, author_last = "Frank", "Niessink"
author = "%s %s, Jerome Laheurte, Aaron Wolf, and Real Carbonneau" % (
    author_first,
    author_last,
)
author_email = "https://github.com/taskcoach/taskcoach/issues"

filename = name.replace(" ", "")

url = "https://github.com/taskcoach/taskcoach"  # Project homepage (GitHub)
github_url = url  # Alias for backwards compatibility
faq_url = "https://answers.launchpad.net/taskcoach/+faqs"
known_bugs_url = github_url + "/issues"  # GitHub issues for known bugs
support_request_url = github_url + "/issues"  # GitHub issues for support
# GitHub issues for feature requests
feature_request_url = github_url + "/issues"
# GitHub pull requests for translations
translations_url = github_url + "/pulls"
# The latest release, drafts and prereleases left out (version check)
latest_release_url = github_url + "/releases/latest"
latest_release_api_url = (
    "https://api.github.com/repos/taskcoach/taskcoach/releases/latest"
)

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

languages = {
    "English (US)": (None, True),
    "English (AU)": ("en_AU", True),
    "English (CA)": ("en_CA", True),
    "English (GB)": ("en_GB", True),
    "Arabic": ("ar", False),
    "Basque": ("eu", False),
    "Belarusian": ("be", True),
    "Bosnian": ("bs", False),
    "Breton": ("br", False),
    "Bulgarian": ("bg", False),
    "Catalan": ("ca", False),
    "Chinese (Simplified)": ("zh_CN", False),
    "Chinese (Traditional)": ("zh_TW", False),
    "Czech": ("cs", True),
    "Danish": ("da", True),
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
    "Hungarian": ("hu", True),
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
    "Swedish": ("sv", True),
    "Telugu": ("te", False),
    "Thai": ("th", False),
    "Turkish": ("tr", True),
    "Ukranian": ("uk", False),
    "Vietnamese": ("vi", False),
}


def __create_dict(locals_dict):
    """Provide the local variables as a dictionary for use in string
    formatting."""
    meta_dict = {}
    for key in locals_dict:
        if not key.startswith("__"):
            meta_dict[key] = locals_dict[key]
    return meta_dict


# metaDict is used as a %-format mapping across the codebase and in
# the website and legacy build scripts; renaming it is a separate
# change.
metaDict = __create_dict(locals())  # noqa: N816
