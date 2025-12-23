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

from buildlib import (
    clean,
    bdist_rpm_fedora,
    bdist_rpm_opensuse,
    bdist_deb,
    bdist_winpenpack,
    bdist_portableapps,
)
from setup import setupOptions
from taskcoachlib import meta
import sys
import os
import glob
import wx


setupOptions["cmdclass"] = dict(
    clean=clean,
    bdist_rpm_fedora=bdist_rpm_fedora,
    bdist_rpm_opensuse=bdist_rpm_opensuse,
    bdist_deb=bdist_deb,
    bdist_winpenpack=bdist_winpenpack,
    bdist_portableapps=bdist_portableapps,
)

distdir = "dist"
builddir = "build"


manifest = (
    """
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<assembly xmlns="urn:schemas-microsoft-com:asm.v1" manifestVersion="1.0">
    <assemblyIdentity version="0.64.1.0" processorArchitecture="x86" 
    name="Controls" type="win32"/>
    <description>%s</description>
    <dependency>
        <dependentAssembly>
            <assemblyIdentity type="win32" 
            name="Microsoft.Windows.Common-Controls" version="6.0.0.0" 
            processorArchitecture="X86" publicKeyToken="6595b64144ccf1df"
            language="*"/>
        </dependentAssembly>
    </dependency>
    <dependency>
        <dependentAssembly>
            <assemblyIdentity type="win32" 
            name="Microsoft.VC90.CRT" version="9.0.21022.8"
            processorArchitecture="x86" publicKeyToken="1fc8b3b9a1e18e3b" />
        </dependentAssembly>
    </dependency>
</assembly>
"""
    % meta.name
)

doubleline = (
    "================================================================\n"
)

header = (
    doubleline + "%(name)s - %(description)s\n" % meta.metaDict + doubleline
)

aboutText = (
    header
    + """
Version %(version)s, %(date)s

By %(author)s <%(author_email)s>

%(url)s

%(copyright)s
%(license)s

"""
    % meta.metaDict
    + doubleline
)

installText = (
    header
    + """

--- Prerequisites ----------------------------------------------

You need Python version %(pythonversion)s or higher, wxPython 
version %(wxpythonversion)s or higher, and Twisted version
%(twistedversionnumber)s or higher.


--- Testing ----------------------------------------------------

Before installing, you may want to run the unittests included.
Issue the following command:

  cd tests; python test.py

If all goes well, you should see a number of dots appearing and
the message 'Ran X tests in Y seconds. OK'. If not, you'll get
one or more failed tests. In that case, please run the tests
again, redirecting the output to a textfile, like this:

  python test.py 2> errors.txt

Please mail me the errors.txt file and your platform information
(operating system version, Python version and wxPython version).


--- Installation -----------------------------------------------

There are two options to install %(name)s: 

First, you can simply move this directory to some suitable 
location and run taskcoach.py (or taskcoach.pyw if you are on 
the Windows platform) from there.

Alternatively, you can use the Python distutils setup script
to let Python install %(name)s for you. In that case run the
following command:

  python setup.py install

If you have a previous version of %(name)s installed, you may
need to force old files to be overwritten, like this:

  python setup.py install --force

"""
    % meta.metaDict
    + doubleline
)

buildText = (
    header
    + """

--- Building ---------------------------------------------------

To be done.

"""
    % meta.metaDict
    + doubleline
)


def writeFile(filename, text, directory="."):  # pylint: disable=W0621
    if not os.path.exists(directory):
        os.mkdir(directory)
    with open(os.path.join(directory, filename), "w") as textFile:
        textFile.write(text)


def createDocumentation():
    writeFile("README.txt", aboutText)
    writeFile("INSTALL.txt", installText)
    writeFile("LICENSE.txt", meta.licenseText)


def createInnoSetupScript():
    script = open("build.in/windows/taskcoach.iss").read()
    writeFile("taskcoach.iss", script % meta.metaDict, builddir)


def createDebianChangelog():
    changelog = open("build.in/debian/changelog").read()
    writeFile(
        "changelog",
        changelog % meta.metaDict,
        os.path.join(builddir, "debian"),
    )


if sys.argv[1] == "py2exe":
    from distutils.core import setup
    import py2exe  # pylint: disable=F0401
    import shutil

    shutil.copyfile("taskcoach.pyw", "taskcoach_console.py")
    py2exeDistdir = "%s-%s-win32exe" % (meta.filename, meta.version)
    # Get .mo files for wxWidgets:
    locale_dir = os.path.join(os.path.dirname(wx.__file__), "locale")
    mo_path = os.path.join("LC_MESSAGES", "wxstd.mo")
    mo_files = []
    for language_dir in os.listdir(locale_dir):
        mo_abs_filename = os.path.join(locale_dir, language_dir, mo_path)
        mo_rel_dir = os.path.join("locale", language_dir, "LC_MESSAGES")
        mo_files.append((mo_rel_dir, [mo_abs_filename]))
    # DLL's we redistribute so people don't have to download them:
    dll_files = [
        ("", ["dist.in/gdiplus.dll"]),
        (
            "Microsoft.VC90.CRT",
            [
                "dist.in/msvcp90.dll",
                "dist.in/msvcr90.dll",
                "dist.in/Microsoft.VC90.CRT.manifest",
            ],
        ),
    ]
    setupOptions.update(
        {
            "windows": [
                {
                    "script": "taskcoach.pyw",
                    "other_resources": [(24, 1, manifest)],
                    "icon_resources": [(1, "icons.in/taskcoach.ico")],
                }
            ],
            "console": [
                {
                    "script": "taskcoach_console.py",
                    "other_resources": [(24, 1, manifest)],
                }
            ],
            "options": {
                "py2exe": {
                    "compressed": 1,
                    "optimize": 2,
                    # We need to explicitly include these packages because they
                    # are imported implicitly:
                    "packages": [
                        "taskcoachlib.i18n",
                        "igraph.vendor.texttable",
                        "cairo",
                    ],
                    "dist_dir": os.path.join(builddir, py2exeDistdir),
                    "dll_excludes": ["MSVCR80.dll", "UxTheme.dll"],
                }
            },
            "data_files": dll_files + mo_files,
        }
    )
    os.environ["PATH"] = "dist.in;" + os.environ["PATH"]

elif sys.argv[1] == "py2app":
    from setuptools import setup  # pylint: disable=W0404

    setupOptions.update(
        dict(
            app=["taskcoach.py"],
            setup_requires=["py2app"],
            options=dict(
                py2app=dict(
                    argv_emulation=True,
                    compressed=True,
                    dist_dir=os.path.join(builddir, "Task Coach"),
                    optimize=2,
                    iconfile="icons.in/taskcoach.icns",
                    resources=["Welcome.tsk"],
                    # We need to explicitly include i18n modules because they
                    # are imported implicitly via __import__:
                    includes=[
                        filename[:-3].replace("/", ".")
                        for filename in glob.glob("taskcoachlib/i18n/*.py")
                    ],
                    plist=dict(
                        CFBundleIdentifier="org.taskcoach.TaskCoach",
                        CFBundleIconFile="taskcoach.icns",
                        CFBundleDocumentTypes=[
                            dict(
                                CFBundleTypeExtensions=["tsk"],
                                CFBundleTypeIconFile="taskcoach.icns",
                                CFBundleTypeName="%s task file" % meta.name,
                                CFBundleTypeRole="Editor",
                            )
                        ],
                    ),
                )
            ),
        )
    )

elif sys.argv[1] == "bdist_rpm_fedora":
    from distutils.core import setup

    spec_file = open("build.in/fedora/taskcoach.spec").read() % meta.metaDict
    spec_file = spec_file.split("\n")
    setupOptions.update(
        dict(
            options=dict(
                bdist_rpm_fedora=dict(
                    spec_file=spec_file,
                    icon="icons.in/taskcoach.png",
                    desktop_file="build.in/linux_common/taskcoach.desktop",
                )
            )
        )
    )
    # On Fedora, to keep the rpm build process going when it finds
    # unpackaged files you need to create a ~/.rpmmacros file
    # containing the line '%_unpackaged_files_terminate_build 0'.

elif sys.argv[1] == "bdist_rpm_opensuse":
    from distutils.core import setup

    spec_file = open("build.in/opensuse/taskcoach.spec").read() % meta.metaDict
    spec_file = spec_file.split("\n")
    setupOptions.update(
        dict(
            options=dict(
                bdist_rpm_opensuse=dict(
                    spec_file=spec_file,
                    icon="icons.in/taskcoach.png",
                    desktop_file="build.in/linux_common/taskcoach.desktop",
                )
            )
        )
    )

elif sys.argv[1] in ["bdist_deb", "bdist_ubuntu"]:
    from distutils.core import setup

    bdist_deb = dict(
        package=meta.data.filename_lower,
        title=meta.data.name,
        description=meta.data.description,
        long_description=meta.data.long_description,
        version=meta.data.version,
        author=meta.data.author,
        author_email=meta.data.author_email,
        copyright=meta.data.copyright,
        license=meta.data.license_title_and_version,
        license_abbrev=meta.data.license_title_and_version_abbrev,
        license_path="/usr/share/common-licenses/GPL-3",
        license_summary=meta.data.license_notice,
        wxpythonversion=meta.data.wxpythonversionnumber,
        twistedversion=meta.data.twistedversionnumber,
        subsection="Office",
        url=meta.data.url,
        command="/usr/bin/taskcoach.py",
        changelog_content=open("changelog_content", "rb").read().rstrip(),
        sdist_exclude="buildlib",
    )

    if sys.argv[1] == "bdist_ubuntu":
        bdist_deb["distribution"] = sys.argv[2]
        bdist_deb["version"] = "%s-0ubuntu%s~%s" % (
            meta.version,
            sys.argv[3],
            sys.argv[2],
        )
        bdist_deb["section"] = "editors"
        sys.argv[1] = "bdist_deb"
        del sys.argv[2]
        del sys.argv[2]

    setupOptions.update(dict(options=dict(bdist_deb=bdist_deb)))

elif sys.argv[1] == "bdist_winpenpack":
    from distutils.core import setup

    setupOptions.update(
        dict(
            options=dict(
                bdist_winpenpack=dict(
                    version=meta.data.version,
                    license=meta.data.license_title,
                    url=meta.data.url,
                    filename=meta.data.filename,
                    date=meta.data.date,
                )
            )
        )
    )

elif sys.argv[1] == "bdist_portableapps":
    from distutils.core import setup

    setupOptions.update(
        dict(
            options=dict(
                bdist_portableapps=dict(
                    name=meta.data.name,
                    version=meta.data.version,
                    license=meta.data.license_title,
                    url=meta.data.url,
                    filename=meta.data.filename,
                    date=meta.data.date,
                )
            )
        )
    )

else:
    from distutils.core import setup


if __name__ == "__main__":
    for directory in builddir, distdir:
        if not os.path.exists(directory):
            os.mkdir(directory)
    createDocumentation()
    setup(**setupOptions)  # pylint: disable=W0142
    if sys.argv[1] == "py2exe":
        createInnoSetupScript()
