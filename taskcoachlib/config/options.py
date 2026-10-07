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

import optparse
from taskcoachlib import meta


class OptionParser(optparse.OptionParser, object):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__addOptionGroups()
        self.__addOptions()

    def __addOptionGroups(self):
        self.__getAndAddOptions("OptionGroup", self.add_option_group)

    def __addOptions(self):
        self.__getAndAddOptions("Option", self.add_option)

    def __getAndAddOptions(self, suffix, add_option):
        for get_option in self.__methodsEndingWith(suffix):
            add_option(get_option(self))

    def __methodsEndingWith(self, suffix):
        return [
            method
            for name, method in list(vars(self.__class__).items())
            if name.endswith(suffix)
        ]


class OptionGroup(optparse.OptionGroup, object):
    pass


class ApplicationOptionParser(OptionParser):
    def __init__(self, *args, **kwargs):
        kwargs["usage"] = "usage: %prog [options] [.tsk file]"
        kwargs["version"] = "%s %s" % (meta.data.name, meta.data.version)
        super().__init__(*args, **kwargs)

    def profileOption(self):
        return optparse.Option(
            "--profile",
            default=False,
            action="store_true",
            help=optparse.SUPPRESS_HELP,
        )

    def iniOption(self):
        return optparse.Option(
            "-i",
            "--ini",
            dest="inifile",
            help="use the specified INIFILE for storing settings",
        )

    def languageOption(self):
        return optparse.Option(
            "-l",
            "--language",
            dest="language",
            type="choice",
            choices=sorted(
                [
                    lang
                    for (lang, enabled) in list(meta.data.languages.values())
                    if lang is not None
                ]
                + ["en"]
            ),
            help='use the specified LANGUAGE for the GUI (e.g. "nl" or "fr"',
        )

    def poOption(self):
        return optparse.Option(
            "-p",
            "--po",
            dest="pofile",
            help="use the specified POFILE for translation of the GUI",
        )
