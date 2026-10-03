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
import ast
import configparser
import functools
import os
import sys
import wx
import shutil
from . import defaults
from taskcoachlib.meta.debug import log_step


def _xdg_dir(variable, default, mode=0o777):
    """The application's folder in an XDG base directory, made when
    missing: the variable's folder, or the default when it is unset or
    empty (XDG Base Directory Specification)."""
    path = os.path.join(
        os.environ.get(variable) or os.path.expanduser(default), meta.name
    )
    if not os.path.isdir(path):
        os.makedirs(path, mode)
    return path


# Reverse mapping: new namespaced icon IDs -> old legacy names.
# Used only when legacystatusicons is True, to write old-format ini.
_LEGACY_REVERSE_MAP = {
    "nuvola_actions_ledblue": "led_blue_icon",
    "nuvola_actions_ledpurple": "led_purple_icon",
    "nuvola_actions_ok": "checkmark_green_icon",
    "nuvola_actions_ledred": "led_red_icon",
    "taskcoach_actions_led_grey_icon": "led_grey_icon",
    "nuvola_actions_ledorange": "led_orange_icon",
}

_LEGACY_STATUS_KEYS = (
    "activetasks",
    "latetasks",
    "completedtasks",
    "overduetasks",
    "inactivetasks",
    "duesoontasks",
)


def _parser():
    """A parser for the INI file: no interpolation, so a "%" in a value
    is kept."""
    return configparser.ConfigParser(interpolation=None)


def _write_legacy_status_icons(parser):
    """The status icons by the names older releases know."""
    for section in ("icon", "icon_dark"):
        for key in _LEGACY_STATUS_KEYS:
            try:
                current = parser.get(section, key)
            except (configparser.NoSectionError, configparser.NoOptionError):
                continue
            old_name = _LEGACY_REVERSE_MAP.get(current)
            if old_name:
                log_step(
                    f"Legacy save: converting '{current}' -> "
                    f"'{old_name}' ({section}.{key})",
                    prefix="ICON",
                )
                parser.set(section, key, old_name)
            else:
                log_step(
                    f"Legacy save: WARNING: '{current}' has no legacy "
                    f"equivalent for {section}.{key}, writing as-is",
                    prefix="ICON",
                )


# Starting with release 1.1.0, the date properties of tasks (startDate,
# dueDate and completionDate) are datetimes
_TASK_DATE_COLUMNS = ("startDate", "dueDate", "completionDate")
# Views with an ordering column, 28 wide unless saved
_ORDERING_VIEWERS = (
    "taskviewer",
    "categoryviewer",
    "noteviewer",
    "noteviewerintaskeditor",
    "noteviewerincategoryeditor",
    "noteviewerinattachmenteditor",
    "categoryviewerintaskeditor",
    "categoryviewerinnoteeditor",
)


def _upgraded(section, option, value, options):
    """The value in today's form, from the forms older releases wrote;
    options are the other values of its section."""
    if option == "sortby":
        if value in _TASK_DATE_COLUMNS:
            value += "Time"
        try:
            ast.literal_eval(value)
        except (ValueError, SyntaxError):
            ascending = options.get("sortascending", "True") != "False"
            value = '["%s%s"]' % (("" if ascending else "-"), value)
    elif option == "columns":
        try:
            columns = ast.literal_eval(value)
        except (ValueError, SyntaxError):
            return value  # Shown as an error when read
        value = str(
            [
                (column + "Time" if column in _TASK_DATE_COLUMNS else column)
                for column in columns
            ]
        )
    elif option == "columnwidths":
        try:
            column_widths = ast.literal_eval(value)
        except (ValueError, SyntaxError):
            column_widths = dict()
        widths = dict()
        for column, width in list(column_widths.items()):
            if column in _TASK_DATE_COLUMNS:
                column += "Time"
            widths[column] = width
        if section in _ORDERING_VIEWERS and "ordering" not in widths:
            widths["ordering"] = 28
        value = str(widths)
    if section in ("icon", "icon_dark"):
        from taskcoachlib.gui.icons.icon_library import icon_catalog

        value = icon_catalog.normalize_icon_id(value)
    return value


class Settings:
    """The settings: each option's text by section, read and written as
    the option's type (docs/SETTINGS.md); configparser only reads and
    writes the file."""

    def __init__(self, load=True, ini_file=None):
        self.__sections = {}
        self.__initialize_with_defaults()
        self.__loadAndSave = load
        self.__iniFileSpecifiedOnCommandLine = ini_file
        self.__ini_lock = None  # Only one Task Coach uses the file

        self.migrateConfigurationFiles()

        first_run = load and not self._iniFileExists()
        if load:
            # The file in the program folder first, else the settings
            # folder's
            try:
                parser = _parser()
                if not parser.read(
                    self.filename(forceProgramDir=True), encoding="utf-8"
                ):
                    parser.read(self.filename(), encoding="utf-8")
            except configparser.ParsingError as reason:
                # The defaults, and the failure recorded to be shown
                self.setLoadStatus(str(reason))
            else:
                self.__load(parser)
            if first_run:
                self._setupFirstRunWelcomeFile()
        else:
            # Not loaded, not saved: tests, which want quiet
            self.__be_quiet()

    def acquire_ini_lock(self):
        """Lock the ini file so only one Task Coach uses it. Shows an
        error and exits if another instance holds it.

        Note: This must be called after wxApp is created, as it may display
        a wx.MessageBox on failure."""
        from taskcoachlib.filesystem import resourcelock

        try:
            self.__ini_lock = resourcelock.acquire(self.filename(), "settings")
        except resourcelock.LockInUse as in_use:
            message = (
                _(
                    "Another instance of %s is already running with the same "
                    "configuration file.\n\n"
                    "You can run multiple instances with different "
                    "configuration files using the --ini option:\n"
                    "  taskcoach --ini=/path/to/other.ini\n\n"
                    "The program will now exit."
                )
                % meta.name
            )
            summary = resourcelock.owner_summary(in_use.owner)
            if summary:
                message += "\n\n" + _("In use by: %s") % summary
            # No window exists yet: without STAY_ON_TOP the box can open
            # behind the focused window, with no taskbar entry
            wx.MessageBox(
                message,
                _("%s: configuration locked") % meta.name,
                style=wx.OK | wx.ICON_ERROR | wx.STAY_ON_TOP,
            )
            sys.exit(1)

    def release_ini_lock(self):
        """Release the ini file lock. Call this on application shutdown."""
        if self.__ini_lock is not None:
            self.__ini_lock.release()
            self.__ini_lock = None

    def on_settings_file_location_changed(self):
        if not self.get_typed("file", "saveinifileinprogramdir"):
            try:
                os.remove(self.generatedIniFilename(forceProgramDir=True))
            except OSError:
                return  # File might not exist

    def __initialize_with_defaults(self):
        self.__sections = {
            section: dict(options)
            for section, options in defaults.defaults.items()
        }
        self.__upgrade_old_values()

    def setLoadStatus(self, message):
        self.__set("file", "inifileloaded", "False" if message else "True")
        self.__set("file", "inifileloaderror", message)

    # Not shown when the settings are not loaded, in tests
    _QUIET = (("window", "tips", "False"),)

    def __be_quiet(self):
        for section, setting, value in self._QUIET:
            self.init(section, setting, value)

    def reset(self):
        """The defaults again, telling no listener: a test's settings
        for the next test."""
        self.__initialize_with_defaults()
        if not self.__loadAndSave:
            self.__be_quiet()

    def read_file(self, file):  # pylint: disable=W0622
        """Load the settings in an INI file object over the current
        ones, converting old values."""
        parser = _parser()
        parser.read_file(file)
        self.__load(parser)

    def __load(self, parser):
        for section in parser.sections():
            options = self.__sections.setdefault(section, {})
            for option, value in parser.items(section, raw=True):
                options[option] = value
        self._migrateOldSettingNames()
        self._remove_obsolete_settings()
        self.__upgrade_old_values()

    def write(self, file):  # pylint: disable=W0622
        """Write the settings to an INI file object: the status icons
        by their old names when the legacy status icons are on."""
        parser = _parser()
        for section, options in self.__sections.items():
            parser.add_section(section)
            for option, value in options.items():
                parser.set(section, option, value)
        if self.get_typed("icon", "legacystatusicons"):
            _write_legacy_status_icons(parser)
        parser.write(file)

    def sections(self):
        return list(self.__sections)

    def has_section(self, section):
        return section in self.__sections

    def has_option(self, section, option):
        return option in self.__sections.get(section, {})

    def add_section(self, section, copy_from=None):
        if section in self.__sections:
            raise ValueError("Section %r exists" % section)
        self.__sections[section] = dict(
            self.__sections[copy_from] if copy_from else {}
        )

    def init(self, section, option, value):
        """Store the option's text, telling no listener."""
        self.__sections[section][option] = value

    def __text(self, section, option):
        """The option's text: stored, else its template's default."""
        try:
            return self.__sections[section][option]
        except KeyError:
            return template(section)[option]

    def _migrateOldSettingNames(self):
        """Migrate old setting names to new names for backward compatibility."""
        # Mapping of (section, old_name) -> new_name
        migrations = [
            ("feature", "sdtcspans", "task_duration_presets"),
            ("feature", "sdtcspans_effort", "effort_duration_presets"),
        ]
        for section, old_name, new_name in migrations:
            options = self.__sections.get(section, {})
            if old_name in options:
                old_value = options.pop(old_name)
                options.setdefault(new_name, old_value)

    # Options no release reads any more (2.0.3.0)
    _OBSOLETE_SETTINGS = (
        ("balloontips", "autosavehint"),
        ("view", "effortviewerintaskeditor"),
        ("window", "monitor_index"),
        ("window", "iconized"),
        ("window", "starticonized"),
        ("window", "hidewheniconized"),
        ("window", "hidewhenclosed"),
        ("export", "html_selectiononly"),
        ("export", "csv_selectiononly"),
        ("export", "ical_selectiononly"),
        ("export", "todotxt_selectiononly"),
        ("view", "taskinterdepsviewercount"),
        ("file", "fspoll"),
    )
    # Retired views: their template section and numbered instances
    _OBSOLETE_VIEWERS = ("taskinterdepsviewer",)

    def _remove_obsolete_settings(self):
        """Drop from an old INI file the options nothing reads."""
        for section, option in self._OBSOLETE_SETTINGS:
            self.__sections.get(section, {}).pop(option, None)
        for section in list(self.__sections):
            if section == "effortdialog" or "dialog_with_" in section:
                self.__sections[section].pop("parent_offset", None)
            if section.rstrip("0123456789") in self._OBSOLETE_VIEWERS:
                del self.__sections[section]

    def __upgrade_old_values(self):
        """Values in the forms older releases wrote, in today's."""
        for section, options in self.__sections.items():
            for option, value in options.items():
                options[option] = _upgraded(section, option, value, options)

    def get_typed(self, section, option):
        """The option's value as its type (docs/SETTINGS.md, One
        Settings Object); a value that does not read as its type is
        shown as an error and replaced by the default."""
        kind = option_type(section, option)
        text = self.__text(section, option)
        try:
            value = _READ[kind](text)
        except Exception as reason:  # pylint: disable=W0703
            wx.MessageBox(
                "\n".join(
                    [
                        _("Error while reading the %s-%s setting from %s.ini.")
                        % (section, option, meta.filename),
                        _("The value is: %s") % text,
                        _("The error is: %s") % reason,
                        _(
                            "%s will use the default value for the setting "
                            "and should proceed normally."
                        )
                        % meta.name,
                    ]
                ),
                caption=_("Settings error"),
                style=wx.ICON_ERROR,
            )
            text = template(section)[option]
            self.__sections[section][option] = text
            value = _READ[kind](text)
        minimum = defaults.minimum.get(section, {}).get(option)
        if minimum is not None:
            value = max(value, _READ[kind](minimum))
        return value

    def set_typed(self, section, option, value):
        """Store the value, of the option's type, and tell the
        listeners when it changed."""
        kind = option_type(section, option)
        if not _ACCEPTS[kind](value):
            raise TypeError(
                "%s.%s takes %s, not %r" % (section, option, kind, value)
            )
        self.__set(section, option, value if kind == "text" else str(value))

    def __set(self, section, option, text):
        if text == self.__text(section, option):
            return
        self.__sections[section][option] = text
        self.send_changed(section, option)
        # Called, not subscribed: the Publisher would keep every
        # Settings object, also the ones tests make and drop
        if (section, option) == ("file", "saveinifileinprogramdir"):
            self.on_settings_file_location_changed()

    @staticmethod
    def section_changed_event_type(section):
        """Any option of the section changed: the settings are the
        source and the option's name the value. An option's own event
        type is "<section>.<option>", its value the new text."""
        return "settings.%s" % section

    def send_changed(self, section, option):
        """Tell the listeners of the option and of its section that it
        changed; they read typed values from the settings."""
        event = patterns.Event(
            "%s.%s" % (section, option), self, self.__text(section, option)
        )
        event.addSource(
            self, option, type=self.section_changed_event_type(section)
        )
        event.send()

    def save(
        self, showerror=wx.MessageBox, file=open
    ):  # pylint: disable=W0622
        self.__set("version", "python", sys.version)
        self.__set(
            "version",
            "wxpython",
            "%s-%s @ %s"
            % (wx.VERSION_STRING, wx.PlatformInfo[2], wx.PlatformInfo[1]),
        )
        self.__set("version", "pythonfrozen", str(hasattr(sys, "frozen")))
        self.__set("version", "current", meta.data.version)
        if not self.__loadAndSave:
            return
        try:
            path = self.path()
            if not os.path.exists(path):
                os.makedirs(path, exist_ok=True)
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
        elif forceProgramDir or self.get_typed(
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
            return os.path.expanduser("~/Documents")
        elif operating_system.isGTK():
            # Check XDG_DOCUMENTS_DIR (standard on Linux)
            xdg_docs = os.environ.get("XDG_DOCUMENTS_DIR")
            if xdg_docs and os.path.isdir(xdg_docs):
                return xdg_docs
            # Fall back to ~/Documents if it exists
            docs_dir = os.path.join(os.path.expanduser("~"), "Documents")
            if os.path.isdir(docs_dir):
                return docs_dir
        # Assuming Unix-like, fall back to home
        return os.path.expanduser("~")

    def _iniFileExists(self):
        """Check if INI file exists in either program dir or config dir."""
        return os.path.exists(
            self.filename(forceProgramDir=True)
        ) or os.path.exists(self.filename())

    @staticmethod
    def pathToSystemWelcomeFile():
        """Find the system-installed Welcome.tsk file."""
        # Check platform-specific locations
        if operating_system.isWindows():
            # Windows: look in install directory
            candidates = [
                os.path.join(os.path.dirname(sys.executable), "Welcome.tsk"),
                os.path.join(os.path.dirname(sys.argv[0]), "Welcome.tsk"),
            ]
        elif operating_system.isMac():
            # macOS: look in app bundle Resources
            candidates = [
                os.path.join(
                    os.path.dirname(sys.executable),
                    "..",
                    "Resources",
                    "Welcome.tsk",
                ),
                os.path.join(os.path.dirname(sys.argv[0]), "Welcome.tsk"),
            ]
        else:
            # Linux: check standard system locations
            candidates = [
                "/usr/share/taskcoach/Welcome.tsk",
                "/usr/local/share/taskcoach/Welcome.tsk",
                "/usr/share/doc/taskcoach/Welcome.tsk",
                os.path.join(os.path.dirname(sys.argv[0]), "Welcome.tsk"),
            ]
        for path in candidates:
            if os.path.exists(path):
                return path
        return None

    def _setupFirstRunWelcomeFile(self):
        """On first run, copy Welcome.tsk to user's Documents folder."""
        systemWelcome = self.pathToSystemWelcomeFile()
        if not systemWelcome:
            return  # No system Welcome.tsk found

        # Create TaskCoach folder in user's Documents
        docsDir = self.pathToDocumentsDir()
        taskcoachDocsDir = os.path.join(docsDir, meta.filename)
        userWelcome = os.path.join(taskcoachDocsDir, "Welcome.tsk")

        # Don't overwrite if user already has a Welcome.tsk
        if os.path.exists(userWelcome):
            # But still set it as the file to open on first run
            self.set("file", "lastfile", userWelcome)
            return

        try:
            if not os.path.exists(taskcoachDocsDir):
                os.makedirs(taskcoachDocsDir)
            shutil.copy(systemWelcome, userWelcome)
            # Set this as the last opened file so it opens on startup
            self.set("file", "lastfile", userWelcome)
        except OSError:
            pass  # Silently fail if we can't copy

    def pathToProgramDir(self):
        path = os.path.abspath(sys.argv[0])
        if not os.path.isdir(path):
            path = os.path.dirname(path)
        return path

    def pathToConfigDir(self, environ):
        try:
            if operating_system.isGTK():
                path = _xdg_dir("XDG_CONFIG_HOME", "~/.config", 0o700)
            elif operating_system.isMac():
                path = os.path.expanduser("~/Library/Preferences")
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
            path = _xdg_dir("XDG_DATA_HOME", "~/.local/share")
        elif operating_system.isMac():
            path = os.path.join(
                os.path.expanduser("~/Library/Application Support"), meta.name
            )
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
        return path

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
        return path

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


# Each option's type comes from its default: "True" or "False", a
# whole number, a Python literal (list, tuple, dict), or text. These
# defaults look like a number but are text.
_TEXT_OPTIONS = {("view", "timeformat")}


def _read_bool(text):
    if text not in ("True", "False"):
        raise ValueError("invalid literal for Boolean value: '%s'" % text)
    return text == "True"


# An option's text read as its type; ValueError or SyntaxError for text
# that is not of the type
_READ = dict(bool=_read_bool, int=int, literal=ast.literal_eval, text=str)


def _is_literal(value):
    try:
        ast.literal_eval(str(value))
    except (ValueError, SyntaxError):
        return False
    return True


_ACCEPTS = dict(
    bool=lambda value: isinstance(value, bool),
    int=lambda value: isinstance(value, int) and not isinstance(value, bool),
    literal=lambda value: not isinstance(value, str) and _is_literal(value),
    text=lambda value: isinstance(value, str),
)


def template(section):
    """The defaults of the section: its own, a viewer instance's
    template's (taskviewer1: taskviewer), or an editor window's."""
    if section in defaults.defaults:
        return defaults.defaults[section]
    base = section.rstrip("0123456789")
    if base in defaults.defaults:
        return defaults.defaults[base]
    if "dialog_with_" in section:
        return defaults.editor_window
    raise KeyError(section)


@functools.lru_cache(maxsize=None)
def option_type(section, option):
    """The option's type: "bool", "int", "literal" or "text";
    KeyError for an option no defaults name."""
    default = template(section)[option]
    if (section.rstrip("0123456789"), option) in _TEXT_OPTIONS:
        return "text"
    if default in ("True", "False"):
        return "bool"
    if default.lstrip("-").isdigit():
        return "int"
    if default[:1] in ("[", "(", "{") and _is_literal(default):
        return "literal"
    return "text"


def _default(section_name, option):
    """The option's default as its type: what a module reads while it
    loads, before the application has its settings."""
    kind = option_type(section_name, option)
    return _READ[kind](template(section_name)[option])


def _theme_is_dark():
    """Whether the colours are the dark ones: the theme chosen, or the
    system's when automatic."""
    theme = get("window", "theme")
    if theme in ("dark", "light"):
        return theme == "dark"
    from taskcoachlib.application.application import detect_dark_theme

    return detect_dark_theme()


# Read like options, computed at each read from the settings and the
# system (1.3 microseconds for the theme on GTK)
_COMPUTED = {("window", "theme_is_dark"): _theme_is_dark}


class _Section:
    """One section's options as attributes: read as their type, and
    written, which tells the listeners."""

    __slots__ = ("_name",)

    def __init__(self, name):
        object.__setattr__(self, "_name", name)

    def __getattr__(self, option):
        computed = _COMPUTED.get((self._name, option))
        if computed:
            return computed()
        try:
            if _current is None:
                return _default(self._name, option)
            return _current.get_typed(self._name, option)
        except KeyError:
            raise AttributeError("%s.%s" % (self._name, option)) from None

    def __setattr__(self, option, value):
        try:
            option_type(self._name, option)
        except KeyError:
            raise AttributeError("%s.%s" % (self._name, option)) from None
        _current.set_typed(self._name, option, value)

    def __repr__(self):
        return "<settings section %s>" % self._name


# The one Settings object: the application's, in tests the harness's
_current = None
_sections = {}


def use(settings):
    """Make settings the object every module reads and writes."""
    global _current  # pylint: disable=W0603
    _current = settings


def current():
    """The Settings object every module reads and writes."""
    return _current


def section(name):
    """The section's options as attributes, for a section named while
    running (settings.section("taskviewer1").sortby)."""
    try:
        return _sections[name]
    except KeyError:
        return _sections.setdefault(name, _Section(name))


def get(section_name, option):
    """The option's value as its type, for names the caller computes."""
    return getattr(section(section_name), option)


def set(section_name, option, value):  # pylint: disable=W0622
    """Store the value, of the option's type, for names the caller
    computes."""
    setattr(section(section_name), option, value)


def templates_dir():
    """The task templates' folder, made if missing."""
    return _current.pathToTemplatesDir()


def backups_dir():
    """The automatic backups' folder, made if missing."""
    return _current.pathToBackupsDir()


def send_changed(section_name, option):
    """Tell the option's listeners it changed though its value did not
    (window.theme "automatic" when the system theme changes)."""
    _current.send_changed(section_name, option)


def from_text(section_name, option, text):
    """The option's value as its type from its text form, as a choice
    list holds it ("15" for a whole number)."""
    return _READ[option_type(section_name, option)](text)


def has_section(name):
    """Whether the section exists: a viewer instance's or an editor
    window's, made while running or loaded from the file."""
    return _current.has_section(name)


def add_section(name, copy_from=None):
    """Make a section while running, telling no listener: with
    copy_from's values (a new viewer takes the previous one's), else
    its template's defaults."""
    _current.add_section(name, copy_from=copy_from)
    if not copy_from:
        for option, value in template(name).items():
            _current.init(name, option, value)


def __getattr__(name):
    """settings.view and the other declared sections (PEP 562)."""
    if name in defaults.defaults:
        return section(name)
    raise AttributeError(name)
