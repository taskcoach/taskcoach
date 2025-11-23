# Welcome to Task Coach - Your friendly task manager

---

## ⚠️ CRITICAL: Debian Bookworm Users

**If you're on Debian 12 (Bookworm), you MUST read [CRITICAL_WXPYTHON_PATCH.md](CRITICAL_WXPYTHON_PATCH.md) first!**

Debian Bookworm ships wxPython 4.2.0 which has critical bugs affecting category row background coloring. A patch is automatically applied during setup, but understanding why it's needed is important for future maintenance.

**TL;DR**: Run `./setup_bookworm.sh` and the patch is applied automatically at step [6/7].

---

Below you find information about running, testing, installing, and
developing Task Coach.

## License

Task Coach - Your friendly task manager

Copyright (C) 2004-2016 Task Coach developers \<developers@taskcoach.org\>

Copyright (C) 2009 George Weeks \<gcw52@telus.net\>

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

## Getting the Code

### For Debian Users

See [DEBIAN_BOOKWORM_SETUP.md](DEBIAN_BOOKWORM_SETUP.md) for detailed Debian-specific installation instructions including shallow clone and ZIP download options.

### General Instructions

If you clone the sources from GitHub, the full repository is ~400MB due to the complete history. Choose the method that best fits your needs:

**Shallow clone (recommended, ~70MB):**
```bash
git clone --depth 1 https://github.com/taskcoach/taskcoach.git
```

**Full clone (~400MB):**
```bash
git clone https://github.com/taskcoach/taskcoach.git
```

**Download as ZIP (~50MB, no git):**
```bash
wget https://github.com/taskcoach/taskcoach/archive/refs/heads/master.zip
unzip master.zip
```

The large size is due to historical binary assets (icon archives, translations, DLLs) stored in the git history.

## Prerequisites

You need Python version 3.8 or higher, wxPython version
4.2.1-unicode or higher and Twisted. 
    
For building distributions and running tests, GNU make is used. Make 
is installed on most systems by default. On Windows you can install 
Cygwin (http://www.cygwin.com) to get make and a lot of other nice 
utilities. Make will automatically use the file Makefile as its 
script, unless directed otherwise. Makefile in turn uses "pymake.py" 
to build distributions. So, if you don't have make installed you can
still build the distributions by running the commands from the 
Makefile by hand.

Since 2012/10/14 you will also need tar, gzip and patch to unpack the
third party modules. Those are part of Cygwin.

In order to build the executable on Windows with py2exe you'll need to
hack zope.interface (a Twisted dependency) as described here:

http://stackoverflow.com/questions/7816799/getting-py2exe-to-work-with-zope-interface

Starting with 1.4.4 you'll also need python-igraph. Binaries are
available for Windows, but installing this on OSX is a bit
difficult. The best way is probably to install the C core using Brew,
and then the Python extension using pip:

    brew install gcc
    brew tap homebrew/science
    brew install --use-gcc --universal igraph
    sudo pip install python-igraph

Note that --universal is needed because wxWidgets 2.x is 32-bits only;
--use-gcc is needed because of a bug in recent versions of the XCode
command-line tools, which make the link fail.

## Running

Start Task Coach from the command line like this:

    python taskcoach.py

## Testing

To run the tests, enter:

    make unittests

Check out the Makefile for more testing options. The test script
has a bunch of options as well, enter: 

    cd tests; python test.py --help

for more information.

If you want to run single one unit test, enter(use unittests.ConfigTest.SettingsIOTest as sample):

    cd tests; python -m unittest unittests.ConfigTest.SettingsIOTest

## Test coverage

To create test coverage reports, you need to install coverage.py
(http://pypi.python.org/pypi/coverage/). Install with:

    sudo easy_install coverage

To create a coverage report, enter:

    make coverage

The coverage report is written to tests/coverage.out.

## Building distributions

Use the Makefile to create distributions (they are placed in dist/):

    make windist # Creates installer for Windows
    make dmg     # Creates disk image for Mac OS X
    make rpm     # Creates generic RPM
    make fedora  # Creates RPM for Fedora 8 or later
    make deb     # Creates Debian package for Debian and Ubuntu

Check out the Makefile for more details. E.g. to create the Task
Coach app on Mac OS X you can also run:

    python pymake.py py2app

The TaskCoach.app ends up in build/

## Installation

There are two options to install Task Coach: 

First, you can simply move this directory to some suitable 
location and run taskcoach.py (or taskcoach.pyw if you are on 
the Windows platform) from there.

Alternatively, you can use the Python distutils setup script
to let Python install Task Coach for you. In that case run the
following command:

    python setup.py install

You may need to run this command as root if you get 
"Permission denied" errors:

    sudo python setup.py install

If you have a previous version of Task Coach installed, you may
need to force old files to be overwritten, like this:

    python setup.py install --force

## Architecture overview
  
Task Coach is a desktop application, developed in Python and using 
wxPython for its GUI. Task Coach is more or less developed using the 
Model-View-Controller architectural style. Its main components are:

* the domain layer that consists of domain classes for tasks, 
  categories, effort, notes and other domain objects,
* the gui layer that consists of viewers, controllers, dialogs, 
  menu's and other GUI objects,
* the persistence layer that knows how to load and save domain 
  objects from and to XML files (the .tsk files) and how to export 
  domain objects to different formats, including HTML.

The layering is not strict: The domain layer has no knowledge of the 
gui and persistence layer. The persistence layer has no knowledge of 
the gui layer. But the gui layer has knowledge of both persistence 
and domain layer.

## Source code overview

The Task Coach source code is organized in python packages. The most 
important and biggest packages are the domain packages that contains 
classes for the domain objects and the gui package that contains 
viewers, dialogs and other gui components.

The command package contains classes that implement user actions, 
e.g. adding a new task or deleting a category. These actions are all 
undoable and redoable. The package is called 'command' since it uses 
the so-called Command patterns to implement unlimited undo-redo.

The config package contains classes related to user configurable 
options that are saved in the TaskCoach.ini file, including all 
default values for the options.

The help package contains help files and the license.

The i18n ('internationalization') package contains the (generated) 
translation modules. These python modules are generated from the .po 
files (see taskcoach/i18n.in).

The mailer package contains modules to interact with email clients
for email attachments and drag and drop from email clients.

The meta package contains meta information about Task Coach, such as 
author, version number, etc.

The patterns package contains base classes for design patterns such 
as Singleton and Observable that are used in other packages.

The persistence package contains modules for saving the Task Coach 
data in its .tsk file format, which actually is XML and for exporting 
data in different formats.

The thirdparty package contains third party modules that are used as 
is, but are included here to ease installation.

The widgets package contains widgets that are used in the gui 
package. These are mostly widgets from wxPython that need a slight 
adaption in their interface.
