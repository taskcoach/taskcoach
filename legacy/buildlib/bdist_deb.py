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

from distutils import log, errors
from distutils.core import Command
from distutils.file_util import copy_file, move_file
import os
import tarfile
import shutil
import textwrap
import time
import glob


class bdist_deb(Command, object):
    # pylint: disable=W0201
    description = "create a Debian (.deb) package"

    user_options = [
        ("sdist=", None, "Source distribution .tar.gz archive"),
        (
            "bdist-base=",
            None,
            "base directory for creating built distributions [build]",
        ),
        ("dist-dir=", "d", "directory to put final deb files in [dist]"),
        ("package=", None, "package name of the application"),
        (
            "section=",
            None,
            "section of the menu to put the application in [Applications]",
        ),
        (
            "subsection=",
            None,
            "subsection of the menu to put the application in",
        ),
        ("title=", None, "title of the application"),
        (
            "description=",
            None,
            "brief single line description of the application",
        ),
        ("long-description=", None, "long description of the application"),
        ("version=", None, "version of the application"),
        ("package-version=", None, "version of the package [1]"),
        ("changelog-content=", None, "Content of the changelog file"),
        ("distribution=", None, "distribution of the package [UNRELEASED]"),
        ("command=", None, "command to start the application"),
        ("priority=", None, "priority of the deb package [optional]"),
        ("urgency=", None, "urgency of the deb package [low]"),
        ("maintainer=", None, "maintainer of the deb package [<author>]"),
        (
            "maintainer-email=",
            None,
            "email address of the package maintainer [<author-email>]",
        ),
        ("author=", None, "author of the application"),
        ("author-email=", None, "email address of the application author"),
        ("copyright=", None, "copyright notice of the application"),
        ("license=", None, "license (title and version) of the application"),
        ("license-abbrev=", None, 'abbreviated license title, e.g. "GPLv3"'),
        (
            "license-summary=",
            None,
            "summary of the license of the application",
        ),
        ("license-path=", None, "path of the license on Debian systems"),
        ("wxpythonversion=", None, "minimal wxPython version needed"),
        ("pythonversion=", None, "minimal Python version needed"),
        ("twistedversion=", None, "minimal Twisted version needed"),
        (
            "sdist-exclude=",
            None,
            "dirs and files in the source distribution to exclude from the deb package",
        ),
        ("url=", None, "url of the application homepage"),
        ("architecture=", None, "architecure of the deb package [all]"),
    ]

    def initialize_options(self):
        self.bdist_base = "build"
        self.dist_dir = "dist"
        self.section = "Applications"
        self.priority = "optional"
        self.urgency = "low"
        self.architecture = "all"
        self.changelog_content = ""
        self.sdist = self.package = self.subsection = self.title = (
            self.description
        ) = self.long_description = self.command = self.maintainer = (
            self.maintainer_email
        ) = self.author = self.author_email = self.copyright = self.license = (
            self.license_abbrev
        ) = self.license_summary = self.license_path = self.url = (
            self.version
        ) = self.package_version = self.distribution = self.wxpythonversion = (
            self.pythonversion
        ) = self.twistedversion = self.sdist_exclude = None

    def finalize_options(self):
        mandatoryOptions = [
            ("package", "the package name"),
            ("subsection", "a subsection for the menu"),
            ("title", "a title for the menu"),
            ("description", "a brief description for the menu"),
            ("long_description", "a long description of the application"),
            ("version", "the version of the application"),
            (
                "copyright",
                'a copyright description ("Copyright (C) year-year, author")',
            ),
            ("license", "the title (including version) of the license"),
            ("license_abbrev", "an abbreviated license title"),
            ("license_summary", "a summary of the license of the application"),
            ("license_path", "the path of the license on Debian systems"),
            ("command", "the command to start the application"),
            ("author", "the author of the application"),
            ("author_email", "the email address of the author"),
            ("url", "the url of the application homepage"),
        ]
        for option, description in mandatoryOptions:
            if not getattr(self, option):
                raise errors.DistutilsOptionError(
                    "you must provide %s (--%s)" % (description, option)
                )
        if not self.maintainer:
            self.maintainer = self.author
            self.maintainer_email = self.author_email
        if not self.package_version:
            self.package_version = "1"
        if not self.distribution:
            self.distribution = "UNRELEASED"
        if not self.wxpythonversion:
            self.wxpythonversion = "3.0"
        if not self.twistedversion:
            self.twistedversion = "12.1"
        if not self.pythonversion:
            self.pythonversion = "2.6"
        self.sdist_exclude = (
            self.sdist_exclude.split(",") if self.sdist_exclude else []
        )
        self.subsection_lower = self.subsection.lower()
        self.datetime = time.strftime(
            "%a, %d %b %Y %H:%M:%S +0000", time.gmtime()
        )
        self.year = time.gmtime()[0]
        self.license_summary = self.wrap_paragraphs(
            self.license_summary, indent="    "
        )
        self.long_description = self.wrap_paragraphs(
            self.long_description, indent=" "
        )

    def run(self):
        self.copy_sdist()
        self.untar_sdist()
        self.remove_sdist_excludes()
        self.create_debian_dir()
        self.write_debian_files()
        self.build_debian_package()
        self.move_debian_package_to_distdir()

    def copy_sdist(self):
        """Copy the source distribution (.tar.gz archive) to the build dir."""
        (dest_name, dummy_copied) = copy_file(self.sdist, self.bdist_base)
        orig_name = dest_name[: -len(".tar.gz")] + ".orig.tar.gz"
        orig_name = orig_name.lower()
        if os.path.exists(orig_name):
            os.remove(orig_name)
        self.sdist_archive = move_file(dest_name, orig_name)

    def untar_sdist(self):
        """Unzip and extract the source distribution archive."""
        expected_extracted_dir = (
            self.sdist_archive[: -len(".orig.tar.gz")] + "/"
        )
        if self.verbose:
            log.info(
                "extracting %s to %s"
                % (self.sdist_archive, expected_extracted_dir)
            )
        archive = tarfile.open(self.sdist_archive)
        extracted_dir = os.path.join(self.bdist_base, archive.getnames()[0])
        archive.extractall(self.bdist_base)
        archive.close()
        if expected_extracted_dir != extracted_dir:
            if os.path.exists(expected_extracted_dir):
                shutil.rmtree(expected_extracted_dir)
            os.rename(extracted_dir, expected_extracted_dir)
        self.extracted_dir = expected_extracted_dir

    def remove_sdist_excludes(self):
        """Remove directories and files from the source distribution that are
        not needed for the debian package."""
        for relative_path in self.sdist_exclude:
            absolute_path = os.path.join(self.extracted_dir, relative_path)
            if self.verbose:
                log.info(
                    "removing %s from source distribution" % relative_path
                )
            if os.path.isdir(absolute_path):
                shutil.rmtree(absolute_path)
            else:
                os.remove(absolute_path)

    def create_debian_dir(self):
        """Create the debian dir for package files."""
        self.debian_dir = os.path.join(self.extracted_dir, "debian")
        if self.verbose:
            log.info("creating %s" % self.debian_dir)
        os.mkdir(self.debian_dir)

    def write_debian_files(self):
        """Create the different package files in the debian folder."""
        debian_files = dict(
            rules=rules,
            compat="9\n",
            menu=menu,
            control=control,
            copyright=self.copyright_contents(),
            changelog=changelog,
        )
        for filename, contents in debian_files.items():
            self.write_debian_file(filename, contents % self.__dict__)

    def write_debian_file(self, filename, contents):
        filename = os.path.join(self.debian_dir, filename)
        if self.verbose:
            log.info("writing %s" % filename)
        fd = open(filename, "w")
        fd.write(contents)
        fd.close()
        os.chmod(filename, 0o755)

    def build_debian_package(self):
        os.system(
            "cd %s; debuild -S; dpkg-buildpackage -rfakeroot; cd .."
            % self.extracted_dir
        )

    def move_debian_package_to_distdir(self):
        for deb_package in glob.glob("build/*.deb"):
            move_file(deb_package, self.dist_dir)

    def copyright_contents(self):
        """Create copyright contents. This is a bit complicated because the
        header and footer need to have their variables filled in first
        before their text can be wrapped."""
        return (
            self.wrap_paragraphs(copyright_header % self.__dict__)
            + copyright
            + self.wrap_paragraphs(copyright_footer % self.__dict__)
        )

    def wrap_paragraphs(self, text, indent=""):
        paragraphs = text.split("\n\n")
        paragraphs = [
            "\n".join(
                textwrap.wrap(
                    paragraph,
                    width=76,
                    initial_indent=indent,
                    subsequent_indent=indent,
                )
            )
            for paragraph in paragraphs
        ]
        return "\n\n".join(paragraphs)


rules = """#!/usr/bin/make -f

DEB_PYTHON2_MODULE_PACKAGES=taskcoach

include /usr/share/cdbs/1/rules/debhelper.mk
include /usr/share/cdbs/1/class/python-distutils.mk

binary-install/taskcoach::
\tdh_icons
"""

menu = """?package(%(package)s):needs="X11"\\
 section="%(section)s/%(subsection)s"\\
 title="%(title)s"\\
 description="%(description)s"\\
 command="%(command)s"
"""

control = """Source: %(package)s
Section: %(section)s
Priority: %(priority)s
Maintainer: %(maintainer)s <%(maintainer_email)s>
Build-Depends: cdbs (>= 0.4.43), debhelper (>= 5), python, devscripts, dh-python
Standards-Version: 4.1.1
Homepage: %(url)s

Package: %(package)s
Architecture: %(architecture)s
Depends: python (>= %(pythonversion)s), python-wxgtk2.8 (>= %(wxpythonversion)s), python-wxversion, python-twisted (>= %(twistedversion)s), libxss1, ttf-dejavu, xdg-utils, python-igraph
Recommends: libgnome2-0, libavahi-compat-libdnssd1, x11-utils
Suggests: python-kde4
Description: %(description)s.
%(long_description)s
"""

copyright_header = """This package was debianized by %(maintainer)s 
<%(maintainer_email)s> on %(datetime)s.
"""

copyright = """

It was downloaded from %(url)s

Upstream Author: 

    %(author)s <%(author_email)s>

Copyright: 

    %(copyright)s

License:

%(license_summary)s

"""

copyright_footer = """On Debian systems, the complete text of the %(license)s
can be found in '%(license_path)s'.

The Debian packaging is (C) %(year)s, %(maintainer)s <%(maintainer_email)s> and
is licensed under the %(license_abbrev)s, see above.

"""

changelog = """%(package)s (%(version)s-%(package_version)s) %(distribution)s; urgency=%(urgency)s

%(changelog_content)s

 -- %(maintainer)s <%(maintainer_email)s>  %(datetime)s
"""
