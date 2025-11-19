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

# This module works around bugs in third party modules, mostly by
# monkey-patching so import it first
from taskcoachlib import workarounds  # pylint: disable=W0611
from taskcoachlib import patterns, operating_system
from taskcoachlib.i18n import _
from pubsub import pub
from taskcoachlib.config import Settings
import locale
import os
import sys
import time
import wx
import calendar
import re
import threading


class RedirectedOutput(object):
    _rx_ignore = [
        re.compile("RuntimeWarning: PyOS_InputHook"),
    ]

    def __init__(self):
        self.__handle = None
        self.__path = os.path.join(
            Settings.pathToDocumentsDir(), "taskcoachlog.txt"
        )

    def write(self, bf):
        for rx in self._rx_ignore:
            if rx.search(bf):
                return

        if self.__handle is None:
            self.__handle = open(self.__path, "a+")
            self.__handle.write("============= %s\n" % time.ctime())
        self.__handle.write(bf)

    def flush(self):
        pass

    def close(self):
        if self.__handle is not None:
            self.__handle.close()
            self.__handle = None

    def summary(self):
        if self.__handle is not None:
            self.close()
            if operating_system.isWindows():
                wx.MessageBox(
                    _(
                        'Errors have occured. Please see "taskcoachlog.txt" in your "My Documents" folder.'
                    ),
                    _("Error"),
                    wx.OK,
                )
            else:
                wx.MessageBox(
                    _('Errors have occured. Please see "%s"') % self.__path,
                    _("Error"),
                    wx.OK,
                )


# pylint: disable=W0404


class wxApp(wx.App):
    def __init__(self, sessionCallback, reopenCallback, *args, **kwargs):
        self.sessionCallback = sessionCallback
        self.reopenCallback = reopenCallback
        self.__shutdownInProgress = False
        super().__init__(*args, **kwargs)

    def MacReopenApp(self):
        self.reopenCallback()

    def OnInit(self):
        if operating_system.isWindows():
            self.Bind(wx.EVT_QUERY_END_SESSION, self.onQueryEndSession)

        try:
            isatty = sys.stdout.isatty()
        except AttributeError:
            isatty = False

        if (
            operating_system.isWindows()
            and hasattr(sys, "frozen")
            and not isatty
        ) or not isatty:
            sys.stdout = sys.stderr = RedirectedOutput()

        return True

    def onQueryEndSession(self, event=None):
        if not self.__shutdownInProgress:
            self.__shutdownInProgress = True
            self.sessionCallback()

        if event is not None:
            event.Skip()


class Application(object, metaclass=patterns.Singleton):
    def __init__(self, options=None, args=None, **kwargs):
        self._options = options
        self._args = args
        self.initTwisted()
        self.__wx_app = wxApp(
            self.on_end_session, self.on_reopen_app, redirect=False
        )
        self.registerApp()
        self.init(**kwargs)

        if operating_system.isGTK():
            if self.settings.getboolean("feature", "usesm2"):
                from taskcoachlib.powermgt import xsm

                class LinuxSessionMonitor(xsm.SessionMonitor):
                    def __init__(self, callback):
                        super().__init__()
                        self._callback = callback
                        self.setProperty(xsm.SmCloneCommand, sys.argv)
                        self.setProperty(xsm.SmRestartCommand, sys.argv)
                        self.setProperty(xsm.SmCurrentDirectory, os.getcwd())
                        self.setProperty(xsm.SmProgram, sys.argv[0])
                        self.setProperty(
                            xsm.SmRestartStyleHint, xsm.SmRestartNever
                        )

                    def saveYourself(
                        self, saveType, shutdown, interactStyle, fast
                    ):  # pylint: disable=W0613
                        if shutdown:
                            wx.CallAfter(self._callback)
                        self.saveYourselfDone(True)

                    def die(self):
                        pass

                    def saveComplete(self):
                        pass

                    def shutdownCancelled(self):
                        pass

                self.sessionMonitor = LinuxSessionMonitor(
                    self.on_end_session
                )  # pylint: disable=W0201
            else:
                self.sessionMonitor = None

        calendar.setfirstweekday(
            dict(monday=0, sunday=6)[self.settings.get("view", "weekstart")]
        )

    def initTwisted(self):
        from twisted.internet import wxreactor

        wxreactor.install()

        # Monkey-patching older versions because of https://twistedmatrix.com/trac/ticket/3948
        import twisted

        if tuple(map(int, twisted.__version__.split("."))) < (11,):
            from twisted.internet import reactor

            if wxreactor.WxReactor.callFromThread is not None:
                oldStop = wxreactor.WxReactor.stop

                def stopFromThread(self):
                    self.callFromThread(oldStop, self)

                wxreactor.WxReactor.stop = stopFromThread

    def stopTwisted(self):
        from twisted.internet import reactor, error

        try:
            reactor.stop()
        except error.ReactorNotRunning:
            # Happens on Fedora 14 when running unit tests. Old Twisted ?
            pass

    def registerApp(self):
        from twisted.internet import reactor

        reactor.registerWxApp(self.__wx_app)

    def start(self):
        """Call this to start the Application."""
        # pylint: disable=W0201
        from taskcoachlib import meta
        import sys
        import platform
        import wx

        # Log version info at startup for debugging
        print(f"Task Coach {meta.version_with_patch} (commit {meta.git_commit_hash})" if meta.git_commit_hash
              else f"Task Coach {meta.version}")
        print(f"Python {sys.version}")
        print(f"wxPython {wx.version()}")
        print(f"Platform: {platform.platform()}")

        # Log GTK/glibc info on Linux
        if platform.system() == 'Linux':
            try:
                import ctypes
                libc = ctypes.CDLL('libc.so.6')
                gnu_get_libc_version = libc.gnu_get_libc_version
                gnu_get_libc_version.restype = ctypes.c_char_p
                print(f"glibc {gnu_get_libc_version().decode()}")
            except:
                pass

        # Log zeroconf version (used for iPhone sync)
        try:
            import zeroconf
            print(f"zeroconf {zeroconf.__version__}")
        except ImportError:
            print("zeroconf Not Installed")

        if self.settings.getboolean("version", "notify"):
            self.__version_checker = meta.VersionChecker(self.settings)
            self.__version_checker.start()
        if self.settings.getboolean("view", "developermessages"):
            self.__message_checker = meta.DeveloperMessageChecker(
                self.settings
            )
            self.__message_checker.start()
        self.__copy_default_templates()
        self.mainwindow.Show()
        from twisted.internet import reactor

        reactor.run()

    def __copy_default_templates(self):
        """Copy default templates that don't exist yet in the user's
        template directory."""
        from taskcoachlib.persistence import getDefaultTemplates

        template_dir = self.settings.pathToTemplatesDir()
        if (
            len(
                [
                    name
                    for name in os.listdir(template_dir)
                    if name.endswith(".tsktmpl")
                ]
            )
            == 0
        ):
            for name, template in getDefaultTemplates():
                filename = os.path.join(template_dir, name + ".tsktmpl")
                if not os.path.exists(filename):
                    # Decode bytes to string for text mode writing
                    template_str = template.decode('utf-8') if isinstance(template, bytes) else template
                    open(filename, "w", encoding="utf-8").write(template_str)

    def init(self, loadSettings=True, loadTaskFile=True):
        """Initialize the application. Needs to be called before
        Application.start()."""
        self.__init_config(loadSettings)
        self.__init_language()
        self.__init_domain_objects()
        self.__init_application()
        from taskcoachlib import gui, persistence

        gui.init()
        show_splash_screen = self.settings.getboolean("window", "splash")
        splash = gui.SplashScreen() if show_splash_screen else None
        # pylint: disable=W0201
        self.taskFile = persistence.LockedTaskFile(
            poll=not self.settings.getboolean("file", "nopoll")
        )
        self.__auto_saver = persistence.AutoSaver(self.settings)
        self.__auto_exporter = persistence.AutoImporterExporter(self.settings)
        self.__auto_backup = persistence.AutoBackup(self.settings)
        self.iocontroller = gui.IOController(
            self.taskFile, self.displayMessage, self.settings, splash
        )
        self.mainwindow = gui.MainWindow(
            self.iocontroller, self.taskFile, self.settings, splash=splash
        )
        self.__wx_app.SetTopWindow(self.mainwindow)
        self.__init_spell_checking()
        if not self.settings.getboolean("file", "inifileloaded"):
            self.__close_splash(splash)
            self.__warn_user_that_ini_file_was_not_loaded()
        if loadTaskFile:
            self.iocontroller.openAfterStart(self._args)
        self.__register_signal_handlers()
        self.__create_mutex()
        self.__create_task_bar_icon()
        wx.CallAfter(self.__close_splash, splash)
        wx.CallAfter(self.__show_tips)

    def __init_config(self, load_settings):
        from taskcoachlib import config

        ini_file = self._options.inifile if self._options else None
        # pylint: disable=W0201
        self.settings = config.Settings(load_settings, ini_file)

    def __init_language(self):
        """Initialize the current translation."""
        from taskcoachlib import i18n

        i18n.Translator(self.determine_language(self._options, self.settings))

    @staticmethod
    def determine_language(
        options, settings, locale=locale
    ):  # pylint: disable=W0621
        language = None
        if options:
            # User specified language or .po file on command line
            language = options.pofile or options.language
        if not language:
            # Get language as set by the user via the preferences dialog
            language = settings.get("view", "language_set_by_user")
        if not language:
            # Get language as set by the user or externally (e.g. PortableApps)
            language = settings.get("view", "language")
        if not language:
            # Use the user's locale
            language = locale.getdefaultlocale()[0]
            if language == "C":
                language = None
        if not language:
            # Fall back on what the majority of our users use
            language = "en_US"
        return language

    def __init_domain_objects(self):
        """Provide relevant domain objects with access to the settings."""
        from taskcoachlib.domain import task, attachment

        task.Task.settings = self.settings
        attachment.Attachment.settings = self.settings

    def __init_application(self):
        from taskcoachlib import meta

        self.__wx_app.SetAppName(meta.name)
        self.__wx_app.SetVendorName(meta.author)

    def __init_spell_checking(self):
        self.on_spell_checking(
            self.settings.getboolean("editor", "maccheckspelling")
        )
        pub.subscribe(
            self.on_spell_checking, "settings.editor.maccheckspelling"
        )

    def on_spell_checking(self, value):
        if (
            operating_system.isMac()
            and not operating_system.isMacOsXMountainLion_OrNewer()
        ):
            wx.SystemOptions.SetOptionInt(
                "mac.textcontrol-use-spell-checker", value
            )

    def __register_signal_handlers(self):
        if operating_system.isWindows():
            import win32api  # pylint: disable=F0401

            def quit_adapter(*args):
                # The handler is called from something that is not the main thread, so we can't do
                # much wx-related
                event = threading.Event()

                def quit():
                    try:
                        self.quitApplication()
                    finally:
                        event.set()

                wx.CallAfter(quit)
                event.wait()
                return True

            win32api.SetConsoleCtrlHandler(quit_adapter, True)
        else:
            import signal

            def quit_adapter(*args):
                return self.quitApplication()

            signal.signal(signal.SIGTERM, quit_adapter)
            if hasattr(signal, "SIGHUP"):
                forced_quit = lambda *args: self.quitApplication(force=True)
                signal.signal(
                    signal.SIGHUP, forced_quit
                )  # pylint: disable=E1101

    @staticmethod
    def __create_mutex():
        """On Windows, create a mutex so that InnoSetup can check whether the
        application is running."""
        if operating_system.isWindows():
            import ctypes
            from taskcoachlib import meta

            ctypes.windll.kernel32.CreateMutexA(None, False, meta.filename)

    def __create_task_bar_icon(self):
        if self.__can_create_task_bar_icon():
            from taskcoachlib.gui import taskbaricon, menu

            self.taskBarIcon = taskbaricon.TaskBarIcon(
                self.mainwindow,  # pylint: disable=W0201
                self.taskFile.tasks(),
                self.settings,
            )
            self.taskBarIcon.setPopupMenu(
                menu.TaskBarMenu(
                    self.taskBarIcon,
                    self.settings,
                    self.taskFile,
                    self.mainwindow.__dict__.get("viewer"),
                )
            )

    def __can_create_task_bar_icon(self):
        try:
            from taskcoachlib.gui import taskbaricon  # pylint: disable=W0612

            return True
        except:
            return False  # pylint: disable=W0702

    @staticmethod
    def __close_splash(splash):
        if splash:
            splash.Destroy()

    def __show_tips(self):
        if self.settings.getboolean("window", "tips"):
            from taskcoachlib import help  # pylint: disable=W0622

            help.showTips(self.mainwindow, self.settings)

    def __warn_user_that_ini_file_was_not_loaded(self):
        from taskcoachlib import meta

        reason = self.settings.get("file", "inifileloaderror")
        wx.MessageBox(
            _("Couldn't load settings from TaskCoach.ini:\n%s") % reason,
            _("%s file error") % meta.name,
            style=wx.OK | wx.ICON_ERROR,
        )
        self.settings.setboolean("file", "inifileloaded", True)  # Reset

    def displayMessage(self, message):
        self.mainwindow.displayMessage(message)

    def on_end_session(self):
        self.mainwindow.setShutdownInProgress()
        self.quitApplication(force=True)

    def on_reopen_app(self):
        self.taskBarIcon.onTaskbarClick(None)

    def quitApplication(self, force=False):
        if not self.iocontroller.close(force=force):
            return False
        # Remember what the user was working on:
        self.settings.set("file", "lastfile", self.taskFile.lastFilename())
        self.mainwindow.save_settings()
        self.settings.save()
        if hasattr(self, "taskBarIcon"):
            self.taskBarIcon.RemoveIcon()
        if self.mainwindow.bonjourRegister is not None:
            self.mainwindow.bonjourRegister.stop()
        from taskcoachlib.domain import date

        date.Scheduler().shutdown()
        wx.EventLoop.GetActive().ProcessIdle()

        # For PowerStateMixin
        self.mainwindow.OnQuit()

        if operating_system.isGTK() and self.sessionMonitor is not None:
            self.sessionMonitor.stop()

        if isinstance(sys.stdout, RedirectedOutput):
            sys.stdout.summary()

        self.stopTwisted()
        return True
