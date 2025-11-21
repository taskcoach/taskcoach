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

from taskcoachlib import meta, patterns, operating_system
from taskcoachlib.i18n import _
from pubsub import pub
from taskcoachlib.workarounds import ExceptionAsUnicode
import ast
import configparser
import os
import sys
import wx
import shutil
from . import defaults


class UnicodeAwareConfigParser(configparser.ConfigParser):
    def __init__(self, *args, **kwargs):
        if "interpolation" not in kwargs:
            kwargs["interpolation"] = None
        super().__init__(*args, **kwargs)


class CachingConfigParser(UnicodeAwareConfigParser):
    """ConfigParser is rather slow, so cache its values."""

    def __init__(self, *args, **kwargs):
        self.__cachedValues = dict()
        super().__init__(*args, **kwargs)

    def read(self, *args, **kwargs):
        self.__cachedValues = dict()
        return super().read(*args, **kwargs)

    def set(self, section, option, value=None):
        self.__cachedValues[(section, option)] = value
        super().set(section, option, value)

    def get(self, section, option, **kwargs):
        cache, key = self.__cachedValues, (section, option)
        if key not in cache:
            cache[key] = super().get(*key, **kwargs)  # pylint: disable=W0142
        return cache[key]


class Settings(CachingConfigParser):
    def __init__(self, load=True, iniFile=None, *args, **kwargs):
        # Sigh, ConfigParser.SafeConfigParser is an old-style class, so we
        # have to call the superclass __init__ explicitly:
        CachingConfigParser.__init__(self, *args, **kwargs)

        self.initializeWithDefaults()
        self.__loadAndSave = load
        self.__iniFileSpecifiedOnCommandLine = iniFile
        self.migrateConfigurationFiles()
        if load:
            # First, try to load the settings file from the program directory,
            # if that fails, load the settings file from the settings directory
            try:
                if not self.read(
                    self.filename(forceProgramDir=True), encoding="utf-8"
                ):
                    self.read(self.filename(), encoding="utf-8")
                errorMessage = ""
            except configparser.ParsingError as errorMessage:
                # Ignore exceptions and simply use default values.
                # Also record the failure in the settings:
                self.initializeWithDefaults()
                self.setLoadStatus(ExceptionAsUnicode(errorMessage))
        else:
            # Assume that if the settings are not to be loaded, we also
            # should be quiet (i.e. we are probably in test mode):
            self.__beQuiet()
        pub.subscribe(
            self.onSettingsFileLocationChanged,
            "settings.file.saveinifileinprogramdir",
        )

    def onSettingsFileLocationChanged(self, value):
        saveIniFileInProgramDir = value
        if not saveIniFileInProgramDir:
            try:
                os.remove(self.generatedIniFilename(forceProgramDir=True))
            except OSError:
                return  # File might not exist

    def initializeWithDefaults(self):
        for section in self.sections():
            self.remove_section(section)
        for section, settings in list(defaults.defaults.items()):
            self.add_section(section)
            for key, value in list(settings.items()):
                # Don't notify observers while we are initializing
                super().set(section, key, value)

    def setLoadStatus(self, message):
        self.set("file", "inifileloaded", "False" if message else "True")
        self.set("file", "inifileloaderror", message)

    def __beQuiet(self):
        noisySettings = [
            ("window", "splash", "False"),
            ("window", "tips", "False"),
            ("window", "starticonized", "Always"),
        ]
        for section, setting, value in noisySettings:
            self.set(section, setting, value)

    def add_section(
        self, section, copyFromSection=None
    ):  # pylint: disable=W0221
        result = super().add_section(section)
        if copyFromSection:
            for name, value in self.items(copyFromSection):
                super().set(section, name, value)
        return result

    def getRawValue(self, section, option):
        return super().get(section, option)

    def init(self, section, option, value):
        return super().set(section, option, value)

    def get(self, section, option, **kwargs):
        try:
            result = super().get(section, option, **kwargs)
        except (configparser.NoOptionError, configparser.NoSectionError):
            return self.getDefault(section, option)
        result = self._fixValuesFromOldIniFiles(section, option, result)
        result = self._ensureMinimum(section, option, result)
        return result

    def getDefault(self, section, option):
        defaultSectionKey = section.strip("0123456789")
        try:
            defaultSection = defaults.defaults[defaultSectionKey]
        except KeyError:
            raise configparser.NoSectionError(defaultSectionKey)
        try:
            return defaultSection[option]
        except KeyError:
            raise configparser.NoOptionError(option, defaultSection)

    def _ensureMinimum(self, section, option, result):
        # Some settings may have a minimum value, make sure we return at
        # least that minimum value:
        if section in defaults.minimum and option in defaults.minimum[section]:
            result = max(result, defaults.minimum[section][option])
        return result

    def _fixValuesFromOldIniFiles(self, section, option, result):
        """Try to fix settings from old TaskCoach.ini files that are no longer
        valid."""
        original = result
        # Starting with release 1.1.0, the date properties of tasks (startDate,
        # dueDate and completionDate) are datetimes:
        taskDateColumns = ("startDate", "dueDate", "completionDate")
        orderingViewers = [
            "taskviewer",
            "categoryviewer",
            "noteviewer",
            "noteviewerintaskeditor",
            "noteviewerincategoryeditor",
            "noteviewerinattachmenteditor",
            "categoryviewerintaskeditor",
            "categoryviewerinnoteeditor",
        ]
        if option == "sortby":
            if result in taskDateColumns:
                result += "Time"
            try:
                ast.literal_eval(result)
            except (ValueError, SyntaxError):
                sortKeys = [result]
                try:
                    ascending = self.getboolean(section, "sortascending")
                except (ValueError, configparser.NoOptionError, configparser.NoSectionError):
                    ascending = True
                result = '["%s%s"]' % (("" if ascending else "-"), result)
        elif option == "columns":
            columns = [
                (col + "Time" if col in taskDateColumns else col)
                for col in ast.literal_eval(result)
            ]
            result = str(columns)
        elif option == "columnwidths":
            widths = dict()
            try:
                columnWidthMap = ast.literal_eval(result)
            except (SyntaxError, ValueError):
                columnWidthMap = dict()
            for column, width in list(columnWidthMap.items()):
                if column in taskDateColumns:
                    column += "Time"
                widths[column] = width
            if section in orderingViewers and "ordering" not in widths:
                widths["ordering"] = 28
            result = str(widths)
        elif (
            section == "feature"
            and option == "notifier"
            and result == "Native"
        ):
            result = "Task Coach"
        elif section == "editor" and option == "preferencespages":
            result = result.replace("colors", "appearance")
        elif section in orderingViewers and option == "columnsalwaysvisible":
            # XXX: remove 'ordering' from always visible columns. This wasn't in any official release
            # but I need it so that people can test without resetting their .ini file...
            # Remove this after the 1.3.38 release.
            try:
                columns = ast.literal_eval(result)
            except (SyntaxError, ValueError):
                columns = ["ordering"]
            else:
                if "ordering" in columns:
                    columns.remove("ordering")
            result = str(columns)
        if result != original:
            super().set(section, option, result)
        return result

    def set(self, section, option, value, new=False):  # pylint: disable=W0221
        if new:
            currentValue = (
                "a new option, so use something as current value"
                " that is unlikely to be equal to the new value"
            )
        else:
            currentValue = self.get(section, option)
        if value != currentValue:
            super().set(section, option, value)
            patterns.Event("%s.%s" % (section, option), self, value).send()
            return True
        else:
            return False

    def setboolean(self, section, option, value):
        if self.set(section, option, str(value)):
            pub.sendMessage("settings.%s.%s" % (section, option), value=value)

    setvalue = settuple = setlist = setdict = setint = setboolean

    def settext(self, section, option, value):
        if self.set(section, option, value):
            pub.sendMessage("settings.%s.%s" % (section, option), value=value)

    def getlist(self, section, option):
        return self.getEvaluatedValue(section, option, ast.literal_eval)

    getvalue = gettuple = getdict = getlist

    def getint(self, section, option):
        return self.getEvaluatedValue(section, option, int)

    def getboolean(self, section, option):
        return self.getEvaluatedValue(section, option, self.evalBoolean)

    def gettext(self, section, option):
        return self.get(section, option)

    @staticmethod
    def evalBoolean(stringValue):
        if stringValue in ("True", "False"):
            return "True" == stringValue
        else:
            raise ValueError(
                "invalid literal for Boolean value: '%s'" % stringValue
            )

    def getEvaluatedValue(
        self, section, option, evaluate=ast.literal_eval, showerror=wx.MessageBox
    ):
        stringValue = self.get(section, option)
        try:
            return evaluate(stringValue)
        except Exception as exceptionMessage:  # pylint: disable=W0703
            message = "\n".join(
                [
                    _("Error while reading the %s-%s setting from %s.ini.")
                    % (section, option, meta.filename),
                    _("The value is: %s") % stringValue,
                    _("The error is: %s") % exceptionMessage,
                    _(
                        "%s will use the default value for the setting and should proceed normally."
                    )
                    % meta.name,
                ]
            )
            showerror(
                message, caption=_("Settings error"), style=wx.ICON_ERROR
            )
            defaultValue = self.getDefault(section, option)
            self.set(
                section, option, defaultValue, new=True
            )  # Ignore current value
            return evaluate(defaultValue)

    def save(
        self, showerror=wx.MessageBox, file=open
    ):  # pylint: disable=W0622
        self.set("version", "python", sys.version)
        self.set(
            "version",
            "wxpython",
            "%s-%s @ %s"
            % (wx.VERSION_STRING, wx.PlatformInfo[2], wx.PlatformInfo[1]),
        )
        self.set("version", "pythonfrozen", str(hasattr(sys, "frozen")))
        self.set("version", "current", meta.data.version)
        if not self.__loadAndSave:
            return
        try:
            path = self.path()
            if not os.path.exists(path):
                os.mkdir(path)
            tmpFile = file(self.filename() + ".tmp", "w", encoding="utf-8")
            self.write(tmpFile)
            tmpFile.close()
            if os.path.exists(self.filename()):
                os.remove(self.filename())
            os.rename(self.filename() + ".tmp", self.filename())
        except Exception as message:  # pylint: disable=W0703
            showerror(
                _("Error while saving %s.ini:\n%s\n")
                % (meta.filename, message),
                caption=_("Save error"),
                style=wx.ICON_ERROR,
            )

    def filename(self, forceProgramDir=False):
        if self.__iniFileSpecifiedOnCommandLine:
            return self.__iniFileSpecifiedOnCommandLine
        else:
            return self.generatedIniFilename(forceProgramDir)

    def path(
        self, forceProgramDir=False, environ=os.environ
    ):  # pylint: disable=W0102
        if self.__iniFileSpecifiedOnCommandLine:
            return self.pathToIniFileSpecifiedOnCommandLine()
        elif forceProgramDir or self.getboolean(
            "file", "saveinifileinprogramdir"
        ):
            return self.pathToProgramDir()
        else:
            return self.pathToConfigDir(environ)

    @staticmethod
    def pathToDocumentsDir():
        if operating_system.isWindows():
            from win32com.shell import shell, shellcon

            try:
                return shell.SHGetSpecialFolderPath(
                    None, shellcon.CSIDL_PERSONAL
                )
            except Exception:
                # Yes, one of the documented ways to get this sometimes fail with "Unspecified error". Not sure
                # this will work either.
                # Update: There are cases when it doesn't work either; see support request #410...
                try:
                    return shell.SHGetFolderPath(
                        None, shellcon.CSIDL_PERSONAL, None, 0
                    )  # SHGFP_TYPE_CURRENT not in shellcon
                except Exception:
                    return os.getcwd()  # Last resort fallback
        elif operating_system.isMac():
            import Carbon.Folder, Carbon.Folders, Carbon.File

            pathRef = Carbon.Folder.FSFindFolder(
                Carbon.Folders.kUserDomain,
                Carbon.Folders.kDocumentsFolderType,
                True,
            )
            return Carbon.File.pathname(pathRef)
        elif operating_system.isGTK():
            try:
                from PyKDE4.kdeui import KGlobalSettings
            except ImportError:
                pass
            else:
                return str(KGlobalSettings.documentPath())
        # Assuming Unix-like
        return os.path.expanduser("~")

    def pathToProgramDir(self):
        path = sys.argv[0]
        if not os.path.isdir(path):
            path = os.path.dirname(path)
        return path

    def pathToConfigDir(self, environ):
        try:
            if operating_system.isGTK():
                from xdg import BaseDirectory

                path = BaseDirectory.save_config_path(meta.name)
            elif operating_system.isMac():
                import Carbon.Folder, Carbon.Folders, Carbon.File

                pathRef = Carbon.Folder.FSFindFolder(
                    Carbon.Folders.kUserDomain,
                    Carbon.Folders.kPreferencesFolderType,
                    True,
                )
                path = Carbon.File.pathname(pathRef)
                # XXXFIXME: should we release pathRef ? Doesn't seem so since I get a SIGSEGV if I try.
            elif operating_system.isWindows():
                from win32com.shell import shell, shellcon

                path = os.path.join(
                    shell.SHGetSpecialFolderPath(
                        None, shellcon.CSIDL_APPDATA, True
                    ),
                    meta.name,
                )
            else:
                path = self.pathToConfigDir_deprecated(environ=environ)
        except Exception:  # Fallback to old dir
            path = self.pathToConfigDir_deprecated(environ=environ)
        return path

    def _pathToDataDir(self, *args, **kwargs):
        forceGlobal = kwargs.pop("forceGlobal", False)
        if operating_system.isGTK():
            from xdg import BaseDirectory

            path = BaseDirectory.save_data_path(meta.name)
        elif operating_system.isMac():
            import Carbon.Folder, Carbon.Folders, Carbon.File

            pathRef = Carbon.Folder.FSFindFolder(
                Carbon.Folders.kUserDomain,
                Carbon.Folders.kApplicationSupportFolderType,
                True,
            )
            path = Carbon.File.pathname(pathRef)
            # XXXFIXME: should we release pathRef ? Doesn't seem so since I get a SIGSEGV if I try.
            path = os.path.join(path, meta.name)
        elif operating_system.isWindows():
            if self.__iniFileSpecifiedOnCommandLine and not forceGlobal:
                path = self.pathToIniFileSpecifiedOnCommandLine()
            else:
                from win32com.shell import shell, shellcon

                path = os.path.join(
                    shell.SHGetSpecialFolderPath(
                        None, shellcon.CSIDL_APPDATA, True
                    ),
                    meta.name,
                )

        else:  # Errr...
            path = self.path()

        if operating_system.isWindows():
            # Follow shortcuts.
            from win32com.client import Dispatch

            shell = Dispatch("WScript.Shell")
            for component in args:
                path = os.path.join(path, component)
                if os.path.exists(path + ".lnk"):
                    shortcut = shell.CreateShortcut(path + ".lnk")
                    path = shortcut.TargetPath
        else:
            path = os.path.join(path, *args)

        exists = os.path.exists(path)
        if not exists:
            os.makedirs(path)
        return path, exists

    def pathToDataDir(self, *args, **kwargs):
        return self._pathToDataDir(*args, **kwargs)[0]

    def _pathToTemplatesDir(self):
        try:
            return self._pathToDataDir("templates")
        except OSError:
            pass  # Fallback on old path
        return self.pathToTemplatesDir_deprecated(), True

    def pathToTemplatesDir(self):
        return self._pathToTemplatesDir()[0]

    def pathToBackupsDir(self):
        return self._pathToDataDir("backups")[0]

    def pathToConfigDir_deprecated(self, environ):
        try:
            path = os.path.join(environ["APPDATA"], meta.filename)
        except Exception:
            path = os.path.expanduser("~")  # pylint: disable=W0702
            if path == "~":
                # path not expanded: apparently, there is no home dir
                path = os.getcwd()
            path = os.path.join(path, ".%s" % meta.filename)
        return operating_system.decodeSystemString(path)

    def pathToTemplatesDir_deprecated(self, doCreate=True):
        path = os.path.join(self.path(), "taskcoach-templates")

        if operating_system.isWindows():
            # Under Windows, check for a shortcut and follow it if it
            # exists.

            if os.path.exists(path + ".lnk"):
                from win32com.client import Dispatch  # pylint: disable=F0401

                shell = Dispatch("WScript.Shell")
                shortcut = shell.CreateShortcut(path + ".lnk")
                return shortcut.TargetPath

        if doCreate:
            try:
                os.makedirs(path)
            except OSError:
                pass
        return operating_system.decodeSystemString(path)

    def pathToIniFileSpecifiedOnCommandLine(self):
        return os.path.dirname(self.__iniFileSpecifiedOnCommandLine) or "."

    def generatedIniFilename(self, forceProgramDir):
        return os.path.join(
            self.path(forceProgramDir), "%s.ini" % meta.filename
        )

    def migrateConfigurationFiles(self):
        # Templates. Extra care for Windows shortcut.
        oldPath = self.pathToTemplatesDir_deprecated(doCreate=False)
        newPath, exists = self._pathToTemplatesDir()
        if self.__iniFileSpecifiedOnCommandLine:
            globalPath = os.path.join(
                self.pathToDataDir(forceGlobal=True), "templates"
            )
            if os.path.exists(globalPath) and not os.path.exists(oldPath):
                # Upgrade from fresh installation of 1.3.24 Portable
                oldPath = globalPath
                if exists and not os.path.exists(newPath + "-old"):
                    # WTF?
                    os.rename(newPath, newPath + "-old")
                exists = False
        if exists:
            return
        if oldPath != newPath:
            if operating_system.isWindows() and os.path.exists(
                oldPath + ".lnk"
            ):
                shutil.move(oldPath + ".lnk", newPath + ".lnk")
            elif os.path.exists(oldPath):
                # pathToTemplatesDir() has created the directory
                try:
                    os.rmdir(newPath)
                except OSError:
                    pass
                shutil.move(oldPath, newPath)
        # Ini file
        oldPath = os.path.join(
            self.pathToConfigDir_deprecated(environ=os.environ),
            "%s.ini" % meta.filename,
        )
        newPath = os.path.join(
            self.pathToConfigDir(environ=os.environ), "%s.ini" % meta.filename
        )
        if newPath != oldPath and os.path.exists(oldPath):
            shutil.move(oldPath, newPath)
        # Cleanup
        try:
            os.rmdir(self.pathToConfigDir_deprecated(environ=os.environ))
        except OSError:
            pass

    def __hash__(self) -> int:
        return id(self)
