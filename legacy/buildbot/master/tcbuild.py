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

# pylint: disable=F0401,E1101
from buildbot.steps.shell import Compile, ShellCommand, WithProperties
from buildbot.steps.master import MasterShellCommand
from buildbot.steps.transfer import FileUpload, DirectoryUpload
from buildbot import interfaces
from buildbot.process.buildstep import SUCCESS, FAILURE

from twisted.python import log

from zope.interface import implements
import re, os


class TaskCoachEmailLookup(object):
    implements(interfaces.IEmailLookup)

    def getAddress(self, name):
        try:
            return {
                "fraca7": "fraca7@free.fr",
                "fniessink": "frank@niessink.com",
            }[name]
        except KeyError:
            return None


class Revert(Compile):
    name = "Revert"
    description = ["Reverting", "locally", "modified", "files"]
    descriptionDone = ["Local", "changes", "reverted"]
    command = ["hg", "revert", "."]


class Cleanup(Compile):
    name = "Cleanup"
    description = ["Deleting", "unversioned", "files"]
    descriptionDone = ["Unversioned", "files", "deleted"]
    command = ["make", "nuke"]

    def start(self):
        try:
            self.getProperty("release")
        except KeyError:
            self.setProperty("release", False)

        Compile.start(self)


class Revision(Compile):
    name = "Revision"
    description = ["Generating", "revision", "file"]
    descriptionDone = ["Revision", "file", "generated"]
    command = [
        "make",
        "revision",
        WithProperties("TCREV=%s", "got_revision_number"),
    ]


# ==============================================================================
# Tests and documentation


class UnitTests(Compile):
    name = "unit tests"
    description = ["Running", "unit", "tests"]
    descriptionDone = ["Unit", "tests"]
    haltOnFailure = False
    command = ["make", "unittests"]


class IntegrationTests(Compile):
    name = "integration tests"
    description = ["Running", "integration", "tests"]
    descriptionDone = ["Integration", "tests"]
    command = ["make", "integrationtests"]


class LanguageTests(Compile):
    name = "language tests"
    description = ["Running", "language", "tests"]
    descriptionDone = ["Language", "tests"]
    haltOnFailure = False
    command = ["make", "languagetests"]


class ReleaseTests(Compile):
    name = "release tests"
    description = ["Running", "release", "tests"]
    descriptionDone = ["Release", "tests"]
    haltOnFailure = False
    command = ["make", "releasetests"]


class DistributionTests(Compile):
    name = "distribution tests"
    description = ["Running", "distribution", "tests"]
    descriptionDone = ["Distribution", "tests"]
    haltOnFailure = False
    command = ["make", "disttests"]


class KillEXE(ShellCommand):
    haltOnFailure = False
    flunkOnFailure = False
    name = "Cleanup"
    command = ["taskkill", "/F", "/IM", "taskcoach.exe"]
    description = ["Killing", "exe"]
    descriptionDone = ["Exe", "killed"]

    def evaluateCommand(self, cmd):
        return SUCCESS


class Coverage(Compile):
    name = "coverage"
    description = ["Running", "coverage"]
    descriptionDone = ["Coverage"]
    haltOnFailure = False
    command = ["make", "coverage"]

    def createSummary(self, log):
        Compile.createSummary(self, log)

        self.addURL(
            "coverage",
            "http://jeromelaheurte.net/TaskCoach-coverage/%s/index.html"
            % (self.getProperty("buildername")),
        )


class UploadCoverage(DirectoryUpload):
    def __init__(self, **kwargs):
        kwargs["slavesrc"] = "tests/coverage.out"
        kwargs["masterdest"] = WithProperties(
            "/var/www/TaskCoach-coverage/%s", "buildername"
        )
        DirectoryUpload.__init__(self, **kwargs)


class Epydoc(Compile):
    name = "epydoc"
    description = ["Generating", "documentation"]
    descriptionDone = ["Documentation"]
    warningPattern = ".*Warning:.*"
    command = ["make", "epydoc"]


class UploadDoc(DirectoryUpload):
    def __init__(self, **kwargs):
        kwargs["slavesrc"] = "epydoc.out"
        kwargs["masterdest"] = WithProperties(
            "/var/www/TaskCoach-doc/%s", "buildername"
        )
        DirectoryUpload.__init__(self, **kwargs)

    def start(self):
        DirectoryUpload.start(self)

        self.addURL(
            "Documentation",
            "http://jeromelaheurte.net/TaskCoach-doc/%s/index.html"
            % (self.getProperty("buildername")),
        )


# ==============================================================================
# Platform-specific packages


class DistCompile(Compile):
    sep = "/"
    ignoreWarnings = False
    filesuffix = None
    fileprefix = None
    target = None

    def start(self):
        if self.getProperty("release"):
            self.command = ["make", self.target or self.name]
        else:
            self.command = [
                "make",
                self.target or self.name,
                "TCREV=%s" % self.getProperty("got_revision_number"),
            ]

        Compile.start(self)

    def commandComplete(self, cmd):
        log = cmd.logs["stdio"]

        for line in log.readlines():
            mt = self.filename_rx.search(line)
            if mt:
                filename = mt.group(1).strip()
                if self.filesuffix is not None:
                    filename += self.filesuffix
                if self.fileprefix is not None:
                    filename = self.fileprefix + filename
                self.setProperty("filename", filename)
                self.setProperty(
                    "basefilename", filename[filename.rfind(self.sep) + 1 :]
                )
                break

        Compile.commandComplete(self, cmd)

    def createSummary(self, log):
        if not self.ignoreWarnings:
            Compile.createSummary(self, log)


class UploadBase(FileUpload):
    def __init__(self, **kwargs):
        kwargs["slavesrc"] = WithProperties("%s", "filename")
        kwargs["masterdest"] = WithProperties(
            "/var/www/TaskCoach-packages/branches/%s/%s",
            "branch",
            "basefilename",
        )
        kwargs["mode"] = 0o644
        FileUpload.__init__(self, **kwargs)

    def start(self):
        if self.getProperty("release"):
            self.masterdest = (
                "/var/www/TaskCoach-packages/release/%s"
                % self.getProperty("basefilename")
            )

        FileUpload.start(self)

        if not self.getProperty("release"):
            url = (
                "http://jeromelaheurte.net/TaskCoach-packages/branches/%s/%s"
                % (
                    self.getProperty("branch") or "",
                    self.getProperty("basefilename"),
                )
            )

            self.addURL("Download", url)


class UploadChangelog(FileUpload):
    def __init__(self, **kwargs):
        kwargs["slavesrc"] = "changelog_content"
        kwargs["masterdest"] = WithProperties(
            "/var/www/TaskCoach-packages/branches/%s/changelog_content",
            "branch",
        )
        kwargs["mode"] = 0o644
        FileUpload.__init__(self, **kwargs)


# Mac OS X


class BuildDMG(DistCompile):
    filename_rx = re.compile(r"^created: (.*)")

    name = "dmg-signed"
    description = ["Generating", "MacOS", "binary"]
    descriptionDone = ["MacOS", "binary"]


class UploadDMG(UploadBase):
    pass


# Windows


class BuildEXE(DistCompile):
    filename_rx = re.compile(r"(dist\\.*-win32\.exe)")
    sep = "\\"

    ignoreWarnings = True
    name = "windist"
    description = ["Generating", "Windows", "binary"]
    descriptionDone = ["Windows", "binary"]


class UploadEXE(UploadBase):
    pass


class BuildWinPenPack(DistCompile):
    filename_rx = re.compile(r"^Generated (dist\\.*\.zip)")
    sep = "\\"

    name = "winpenpack"
    description = ["Generating", "WinPenPack", "binary"]
    descriptionDone = ["WinPenPack", "binary"]


class UploadWinPenPack(UploadBase):
    pass


class BuildPortableApps(DistCompile):
    filename_rx = re.compile(r"^mv build/(.*\.paf\.exe) dist")
    fileprefix = "dist\\"
    sep = "\\"

    name = "portableapps"
    description = ["Generating", "PortableApps", "binary"]
    descriptionDone = ["PortableApps", "binary"]


class UploadPortableApps(UploadBase):
    pass


# Source


class BuildSourceTar(DistCompile):
    filename_rx = re.compile("^Created (.*)$")

    name = "sdist_linux"
    description = ["Generating", "source", "distribution"]
    descriptionDone = ["Source", "distribution"]


class BuildSourceZip(DistCompile):
    filename_rx = re.compile(r"creating '(.*\.zip)'")
    sep = "\\"

    ignoreWarnings = True
    name = "sdist_windows"
    description = ["Generating", "source", "distribution"]
    descriptionDone = ["Source", "distribution"]


class BuildSourceRaw(DistCompile):
    filename_rx = re.compile(r"tar czf (TaskCoach-.*-raw.tgz)")
    fileprefix = "dist/"

    name = "sdist_raw"
    description = ["Generating", "raw", "source", "distribution"]
    descriptionDone = ["Raw", "source", "distribution"]


class UploadSourceTar(UploadBase):
    pass


class UploadSourceZip(UploadBase):
    pass


class UploadSourceRaw(UploadBase):
    pass


# Debian


class BuildDEB(DistCompile):
    filename_rx = re.compile(r"^mv (dist/taskcoach.*)_all\.deb")
    filesuffix = ".deb"

    name = "deb"
    description = ["Generating", "Debian", "package"]
    descriptionDone = ["Debian", "package"]

    def __init__(self, **kwargs):
        # Avoid having the virtualenv bin directory in path, it messes up things
        kwargs["env"] = {"PATH": "/bin:/usr/bin:/usr/local/bin"}
        super().__init__(**kwargs)


class BuildUbuntu(BuildDEB):
    filename_rx = re.compile(r"^moving build/(taskcoach_.*_all)\.deb")
    fileprefix = "dist/"
    name = "ubuntu"


class UploadDEB(UploadBase):
    pass


class PPA(Compile):
    name = "ppa"
    description = ["Uploading", "PPA"]
    description_done = ["PPA", "uploaded"]

    def __init__(self, **kwargs):
        name = kwargs.pop("name")
        kwargs["command"] = ["./uploadppa.sh", name]
        Compile.__init__(self, **kwargs)
        self.addFactoryArguments(name=name)


# Generic RPM


class BuildRPM(DistCompile):
    filename_rx = re.compile(r"([^/]*.noarch.rpm) -> dist")
    fileprefix = "dist/"

    name = "rpm"
    target = "rpm"
    description = ["Generating", "RPM", "package"]
    descriptiondone = ["RPM", "package"]


class BuildSRPM(DistCompile):
    filename_rx = re.compile(r"([^/]*.src.rpm) -> dist")
    fileprefix = "dist/"

    name = "rpm"
    target = "rpm"
    description = ["Generating", "SRPM", "package"]
    descriptiondone = ["SRPM", "package"]


class UploadRPM(UploadBase):
    pass


class UploadSRPM(UploadBase):
    pass


# Fedora


class BuildFedora14(DistCompile):
    filename_rx = re.compile(r"([^/]*.noarch.rpm) -> dist")
    fileprefix = "dist/"

    name = "fedora"
    description = ["Generating", "Fedora", "package"]
    descriptionDone = ["Fedora", "package"]


class UploadFedora14(UploadBase):
    pass


# OpenSuse


class BuildOpenSuse(DistCompile):
    filename_rx = re.compile(r"([^/]*).noarch.rpm -> dist")
    fileprefix = "dist/"
    filesuffix = ".opensuse.i386.rpm"

    name = "opensuse"
    description = ["Generating", "OpenSuse", "package"]
    descriptionDone = ["OpenSuse", "package"]


class UploadOpenSuse(UploadBase):
    pass


# Release


class CleanupReleaseStep(MasterShellCommand):
    name = "Cleanup"
    description = ["Cleanup"]

    def __init__(self, **kwargs):
        kwargs["command"] = "rm -rf /var/www/TaskCoach-packages/release/*"
        MasterShellCommand.__init__(self, **kwargs)


class ZipReleaseStep(MasterShellCommand):
    name = "Zipping"
    description = ["Zip"]

    def __init__(self, **kwargs):
        kwargs["command"] = (
            "cd /var/www/TaskCoach-packages/release\nzip release.zip *"
        )
        MasterShellCommand.__init__(self, **kwargs)

    def start(self):
        MasterShellCommand.start(self)
        self.addURL(
            "Download release",
            "http://jeromelaheurte.net/TaskCoach-packages/release/release.zip",
        )


# Pylint


class PylintStep(Compile):
    name = "pylint"
    description = ["Running", "pylint"]
    descriptionDone = ["pylint"]
    command = ["make", "pylint"]


class PylintUploadStep(FileUpload):
    def __init__(self, **kwargs):
        kwargs["slavesrc"] = "pylint.html"
        kwargs["masterdest"] = WithProperties(
            "/var/www/pylint-%s.html", "buildername"
        )
        kwargs["mode"] = 0o644
        FileUpload.__init__(self, **kwargs)

    def start(self):
        FileUpload.start(self)

        self.addURL(
            "See",
            "http://jeromelaheurte.net/pylint-%s.html"
            % self.getProperty("buildername"),
        )
