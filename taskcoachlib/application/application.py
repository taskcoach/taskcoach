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
import datetime
import locale
import os
import sys
import time
import wx
import calendar
import re
import threading
import subprocess


# ============================================================================
# Logging Functions
# ============================================================================
#
# Simple logging using stdout/stderr. The tee module (initialized in
# taskcoach.py) captures all output to the log file.
#
# Architecture:
#   - log_message() prints to stdout (informational messages)
#   - log_error() prints to stderr (errors)
#   - The tee captures both stdout and stderr to log file
#   - Any stderr output triggers error popup on exit
#
# ============================================================================

# TEMPORARILY DISABLED: TEE module import
# from taskcoachlib import tee


def log_message(msg):
    """Log a message to stdout (captured by tee to log file)."""
    print(msg)


def log_error(msg):
    """Log an error to stderr (captured by tee, triggers exit popup)."""
    print(msg, file=sys.stderr)


def _log_environment():
    """Log environment info early, before wxApp is created.

    This logs version info and environment variables that don't require wx.
    """
    from taskcoachlib import meta
    import platform

    # Log session start with date/time centered in separator
    date_str = datetime.datetime.now().strftime("%a %b %d %H:%M:%S %Y")
    log_message(f" {date_str} ".center(60, "="))

    # Log version info at startup for debugging
    log_message(f"Task Coach {meta.version_full}")
    log_message(f"Python {sys.version}")
    log_message(f"wxPython {wx.version()}")
    log_message(f"Platform: {platform.platform()}")

    # Log GTK/glibc/distro info on Linux
    if platform.system() == 'Linux':
        # Log distro version (e.g., "Ubuntu 24.04.3 LTS (Noble Numbat)")
        try:
            os_release = platform.freedesktop_os_release()
            distro_name = os_release.get('NAME', 'Unknown')
            distro_version = os_release.get('VERSION', '')
            if distro_version:
                log_message(f"Distro: {distro_name} {distro_version}")
            else:
                log_message(f"Distro: {distro_name}")
        except OSError:
            pass

        try:
            import ctypes
            libc = ctypes.CDLL('libc.so.6')
            gnu_get_libc_version = libc.gnu_get_libc_version
            gnu_get_libc_version.restype = ctypes.c_char_p
            log_message(f"glibc {gnu_get_libc_version().decode()}")
        except (OSError, AttributeError):
            pass

        # NOTE: GTK version logged in _log_wx_info() after wxApp creates GTK context

    # Log required package versions
    _log_required_packages()

    # Probe numpy usability early (before any module imports wxhelper).
    # On old CPUs, numpy import triggers a fatal SIGILL — the subprocess
    # probe detects this safely. Result is logged and cached for wxhelper.
    from taskcoachlib.tools._numpy_probe import numpy_usable  # noqa: F401

    # Platform-specific environment info (no wx needed)
    log_message("=" * 60)
    if sys.platform == 'linux':
        _log_linux_environment_early()


def _get_package_version(package_name, import_name=None):
    """Get version of a package. Returns version string or 'missing'."""
    if import_name is None:
        import_name = package_name
    try:
        # Try importlib.metadata first (Python 3.8+)
        from importlib.metadata import version
        return version(package_name)
    except Exception:
        pass
    # Try importing the module and checking __version__
    try:
        module = __import__(import_name)
        if hasattr(module, '__version__'):
            return module.__version__
        if hasattr(module, 'VERSION'):
            return str(module.VERSION)
        return 'installed (version unknown)'
    except ImportError:
        return 'missing'


def _log_required_packages():
    """Log versions of all required packages."""
    log_message("-" * 60)
    log_message("Required packages:")

    # Core packages (package_name, import_name if different)
    packages = [
        ('six', None),
        ('pypubsub', 'pubsub'),
        ('watchdog', None),
        ('chardet', None),
        ('python-dateutil', 'dateutil'),
        ('pyparsing', None),
        ('lxml', None),
        ('pyxdg', 'xdg'),
        ('keyring', None),
        ('numpy', None),
        ('fasteners', None),
        ('squaremap', None),
    ]

    # Windows-only
    if sys.platform == 'win32':
        packages.append(('WMI', 'wmi'))

    for pkg_name, import_name in packages:
        version = _get_package_version(pkg_name, import_name)
        log_message(f"  {pkg_name}: {version}")


def _log_locale_info():
    """Log locale and language settings for debugging i18n issues."""
    import locale as locale_module

    log_message("-" * 60)
    log_message("Locale/Language Info:")

    # Environment variables related to locale
    locale_vars = ['LANG', 'LC_ALL', 'LC_CTYPE', 'LC_MESSAGES', 'LC_TIME',
                   'LC_NUMERIC', 'LC_COLLATE', 'LANGUAGE']
    for var in locale_vars:
        value = os.environ.get(var)
        if value:
            log_message(f"  {var}: {value}")

    # Python locale settings
    try:
        default_locale = locale_module.getdefaultlocale()
        log_message(f"  locale.getdefaultlocale(): {default_locale}")
    except Exception as e:
        log_message(f"  locale.getdefaultlocale(): ERROR - {e}")

    try:
        current_locale = locale_module.getlocale()
        log_message(f"  locale.getlocale(): {current_locale}")
    except Exception as e:
        log_message(f"  locale.getlocale(): ERROR - {e}")

    try:
        preferred_encoding = locale_module.getpreferredencoding()
        log_message(f"  locale.getpreferredencoding(): {preferred_encoding}")
    except Exception as e:
        log_message(f"  locale.getpreferredencoding(): ERROR - {e}")

    # sys.getdefaultencoding and filesystem encoding
    log_message(f"  sys.getdefaultencoding(): {sys.getdefaultencoding()}")
    log_message(f"  sys.getfilesystemencoding(): {sys.getfilesystemencoding()}")


def _log_linux_environment_early():
    """Log Linux environment variables (no wx needed)."""
    log_message(f"XDG_SESSION_TYPE: {os.environ.get('XDG_SESSION_TYPE', 'not set')}")
    log_message(f"WAYLAND_DISPLAY: {os.environ.get('WAYLAND_DISPLAY', 'not set')}")
    log_message(f"DISPLAY: {os.environ.get('DISPLAY', 'not set')}")
    log_message(f"GDK_BACKEND: {os.environ.get('GDK_BACKEND', 'auto')}")

    desktop = os.environ.get('XDG_CURRENT_DESKTOP',
              os.environ.get('DESKTOP_SESSION', 'unknown'))
    log_message(f"Desktop Environment: {desktop}")

    # Log locale info (important for debugging i18n segfaults)
    _log_locale_info()


def detect_dark_theme():
    """Detect if system is using dark theme.

    Returns True if dark theme detected, False otherwise.
    Requires wxApp to be initialized.
    """
    try:
        appearance = wx.SystemSettings.GetAppearance()
        return appearance.IsDark()
    except AttributeError:
        # Older wxPython without GetAppearance()
        # Fallback: check if window background is dark
        try:
            bg = wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOW)
            # Consider dark if luminance < 128
            luminance = (0.299 * bg.Red() + 0.587 * bg.Green() + 0.114 * bg.Blue())
            return luminance < 128
        except Exception:
            return False


def _log_wx_info():
    """Log wx-specific info after wxApp is created.

    This logs display info that requires wxApp to be initialized.
    GTK version is logged here because importing gi.repository.Gtk before
    wxApp would cause 'gtk_disable_setlocale() must be called before gtk_init()'.
    """
    # Log GTK version (must be after wxApp creates GTK context)
    if sys.platform == 'linux':
        try:
            import gi
            gi.require_version('Gtk', '3.0')
            from gi.repository import Gtk
            log_message(f"GTK {Gtk.get_major_version()}.{Gtk.get_minor_version()}.{Gtk.get_micro_version()}")
        except Exception:
            pass

    log_message("=" * 60)
    log_message("WX DISPLAY INFO")
    log_message("=" * 60)

    # wx platform details
    log_message(f"wx.PlatformInfo: {wx.PlatformInfo}")

    # Display/monitor info (cross-platform, requires wxApp)
    try:
        num_displays = wx.Display.GetCount()
        log_message(f"Number of displays: {num_displays}")
        for i in range(num_displays):
            display = wx.Display(i)
            geom = display.GetGeometry()
            client = display.GetClientArea()
            try:
                ppi = display.GetPPI()
                log_message(f"  Display {i}: geometry={geom.x},{geom.y} {geom.width}x{geom.height}  "
                             f"client_area={client.x},{client.y} {client.width}x{client.height}  "
                             f"PPI={ppi.x}x{ppi.y}")
            except Exception:
                log_message(f"  Display {i}: geometry={geom.x},{geom.y} {geom.width}x{geom.height}  "
                             f"client_area={client.x},{client.y} {client.width}x{client.height}")
    except Exception as e:
        log_message(f"Display info unavailable: {e}")

    # Log scaling info (useful for HiDPI debugging)
    try:
        scale_factors = [wx.Display(i).GetScaleFactor() for i in range(wx.Display.GetCount())]
        log_message(f"wx scale factors: {scale_factors}")
    except Exception:
        pass
    # Linux-specific scaling environment variables
    if sys.platform == 'linux':
        scale_vars = ['GDK_SCALE', 'GDK_DPI_SCALE', 'QT_SCALE_FACTOR', 'QT_AUTO_SCREEN_SCALE_FACTOR']
        scale_info = [f"{v}={os.environ.get(v, 'not set')}" for v in scale_vars]
        log_message(f"Scaling env: {', '.join(scale_info)}")

    # Log dark theme detection
    is_dark = detect_dark_theme()
    log_message(f"Dark theme detected: {is_dark}")

    log_message("=" * 60)


def _log_windows_environment():
    """Log Windows-specific GUI environment info."""
    import platform

    # Windows version
    log_message(f"Windows Version: {platform.win32_ver()[0]} {platform.win32_ver()[1]}")
    log_message(f"Windows Edition: {platform.win32_edition()}")

    # DPI awareness
    try:
        import ctypes
        awareness = ctypes.windll.shcore.GetProcessDpiAwareness(0)
        awareness_names = {0: 'Unaware', 1: 'System', 2: 'PerMonitor'}
        log_message(f"DPI Awareness: {awareness_names.get(awareness, awareness)}")
    except Exception as e:
        log_message(f"DPI Awareness: unavailable ({e})")

    # DWM (Desktop Window Manager) composition
    try:
        import ctypes
        dwm_enabled = ctypes.c_bool()
        ctypes.windll.dwmapi.DwmIsCompositionEnabled(ctypes.byref(dwm_enabled))
        log_message(f"DWM Composition: {'Enabled' if dwm_enabled.value else 'Disabled'}")
    except Exception as e:
        log_message(f"DWM Composition: unavailable ({e})")

    # System DPI
    try:
        import ctypes
        hdc = ctypes.windll.user32.GetDC(0)
        dpi_x = ctypes.windll.gdi32.GetDeviceCaps(hdc, 88)  # LOGPIXELSX
        dpi_y = ctypes.windll.gdi32.GetDeviceCaps(hdc, 90)  # LOGPIXELSY
        ctypes.windll.user32.ReleaseDC(0, hdc)
        log_message(f"System DPI: {dpi_x}x{dpi_y} (scale: {dpi_x/96*100:.0f}%)")
    except Exception as e:
        log_message(f"System DPI: unavailable ({e})")

    # Log locale info on Windows too
    _log_locale_info()


def _log_macos_environment():
    """Log macOS-specific GUI environment info."""
    import platform

    # macOS version
    mac_ver = platform.mac_ver()
    log_message(f"macOS Version: {mac_ver[0]}")
    log_message(f"Architecture: {mac_ver[2]}")

    # Check if running under Rosetta (Apple Silicon)
    try:
        result = subprocess.run(['sysctl', '-n', 'sysctl.proc_translated'],
                               capture_output=True, text=True, timeout=2)
        if result.returncode == 0 and result.stdout.strip() == '1':
            log_message("Rosetta 2: Yes (x86_64 on ARM)")
        else:
            log_message("Rosetta 2: No (native)")
    except Exception:
        pass

    # Retina/scaling info via system_profiler (slow but comprehensive)
    try:
        result = subprocess.run(
            ['system_profiler', 'SPDisplaysDataType', '-json'],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            import json
            data = json.loads(result.stdout)
            displays = data.get('SPDisplaysDataType', [{}])[0].get('spdisplays_ndrvs', [])
            for i, disp in enumerate(displays):
                res = disp.get('_spdisplays_resolution', 'unknown')
                retina = disp.get('spdisplays_retina', 'unknown')
                log_message(f"  macOS Display {i}: {res} Retina={retina}")
    except Exception:
        pass

    # Window server info
    try:
        result = subprocess.run(['defaults', 'read', 'com.apple.WindowServer'],
                               capture_output=True, text=True, timeout=2)
        # Just check if it runs - detailed parsing would be verbose
        if result.returncode == 0:
            log_message("WindowServer: accessible")
    except Exception:
        pass

    # Log locale info on macOS too
    _log_locale_info()


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
        return True

    def onQueryEndSession(self, event=None):
        if not self.__shutdownInProgress:
            self.__shutdownInProgress = True
            self.sessionCallback()

        if event is not None:
            event.Skip()

    def OnExceptionInMainLoop(self):
        """Called by wx when an unhandled exception occurs during event dispatch.

        Logs the full traceback to stderr so crashes during event handling
        are visible instead of being silently swallowed. Returns True to
        continue running (the event that caused the error is skipped).
        See docs/CRASH_GUARD.md for details.
        """
        import traceback
        from taskcoachlib.meta.debug import log_step
        log_step("Unhandled exception in MainLoop:",
                 traceback.format_exc(), prefix="CRASH_GUARD")
        return True


class Application(object, metaclass=patterns.Singleton):
    """
    Main application class for Task Coach.

    DESIGN NOTE (Twisted Removal - 2024):
    Previously used Twisted's wxreactor to integrate Twisted's event loop with
    wxPython. This has been replaced with native wxPython functionality:
    - wxreactor.install() → removed (wx.App.MainLoop() used directly)
    - reactor.registerWxApp() → removed (not needed)
    - reactor.run() → wx.App.MainLoop()
    - reactor.stop() → wx.App.ExitMainLoop() via EVT_CLOSE handlers
    - reactor.callLater() → wx.CallLater() (in scheduler.py)

    This simplifies the event loop architecture and eliminates potential
    race conditions between two event loops.
    """
    def __init__(self, options=None, args=None, **kwargs):
        self._options = options
        self._args = args

        # 1. Log environment info first (no dependencies)
        _log_environment()

        # 2. Load settings
        self.__init_config(kwargs.get('loadSettings', True))

        # 3. Create wxApp
        self.__wx_app = wxApp(
            self.on_end_session, self.on_reopen_app, redirect=False
        )
        # Expose settings on wxApp so wx.GetApp().settings works everywhere
        self.__wx_app.settings = self.settings

        # 4. Log wx-specific info (needs wxApp)
        _log_wx_info()

        # 5. Acquire INI lock (needs wxApp for error dialog)
        self.settings.acquire_ini_lock()

        # 6. Continue with rest of initialization
        self.init(**kwargs)

        calendar.setfirstweekday(
            dict(monday=0, sunday=6)[self.settings.get("view", "weekstart")]
        )

    # NOTE: initTwisted(), stopTwisted(), and registerApp() methods removed.
    # Previously used Twisted's wxreactor for event loop integration.
    # Now using native wx.App.MainLoop() which is simpler and more reliable.
    # See class docstring for migration details.

    def start(self):
        """Call this to start the Application."""
        from taskcoachlib import meta

        if self.settings.getboolean("version", "notify"):
            self.__version_checker = meta.VersionChecker(self.settings)
            self.__version_checker.start()
        if self.settings.getboolean("view", "developermessages"):
            self.__message_checker = meta.DeveloperMessageChecker(
                self.settings
            )
            self.__message_checker.start()
        self.__copy_default_templates()

        # Redirect wx log messages to stderr instead of popup dialogs
        if operating_system.isGTK():
            wx.Log.SetActiveTarget(wx.LogStderr())
            wx.Log.SetLogLevel(wx.LOG_Info)
            wx.Log.SetVerbose(True)

        self.mainwindow.Show()
        # Position correction is handled automatically by WindowDimensionsTracker
        # via EVT_MOVE detection until EVT_ACTIVATE fires (window ready for input)
        # Use native wxPython main loop instead of Twisted reactor
        # NOTE: Previously used reactor.run() with wxreactor integration.
        # Now using wx.App.MainLoop() directly for simpler event handling.
        try:
            self.__wx_app.MainLoop()
        finally:
            # Explicitly cleanup wx.App to prevent crashes during Python shutdown
            # See: https://github.com/wxWidgets/Phoenix/issues/429
            if hasattr(self, '_signal_check_timer') and self._signal_check_timer:
                self._signal_check_timer.Stop()

            # On Windows with console (python.exe), detach from console before cleanup
            # The crash only happens with python.exe (console subsystem), not pythonw.exe (GUI subsystem)
            # This suggests the crash is related to console cleanup during Python shutdown
            if operating_system.isWindows():
                sys.stderr.flush()
                sys.stdout.flush()
                try:
                    import ctypes
                    # FreeConsole detaches the process from its console
                    # This prevents console-related cleanup issues during Python shutdown
                    ctypes.windll.kernel32.FreeConsole()
                except Exception:
                    pass
                # Redirect stdout/stderr to devnull to prevent write errors after console detach
                sys.stderr = open(os.devnull, 'w')
                sys.stdout = open(os.devnull, 'w')

            # Prevent destructor issues by explicitly destroying the app
            self.__wx_app.Destroy()

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
        # Note: tee is initialized in taskcoach.py before any imports
        # Note: Settings and logging already done in __init__ before wxApp creation

        self.__init_language()
        self.__init_domain_objects()
        self.__init_application()

        # Check file lock BEFORE creating main window to avoid dialog/focus issues
        # This is done early because showing dialogs after main window creation
        # causes GTK focus fighting and dialog disappearing issues
        # Note: INI file lock is already checked in __init_config() above
        self.__early_lock_result = None  # None=no file, 'ok'=proceed, 'break'=break lock, 'skip'=don't open file
        if loadTaskFile:
            self.__check_file_lock_early()
            # If user said "No" to break lock, we continue but don't open the file
            # (program starts with no file open, like a fresh start)

        from taskcoachlib import gui, persistence

        gui.init()
        # pylint: disable=W0201
        self.taskFile = persistence.LockedTaskFile(
            poll=self.settings.getboolean("file", "fspoll")
        )
        self.__auto_saver = persistence.AutoSaver(self.settings)
        self.__auto_exporter = persistence.AutoImporterExporter(self.settings)
        self.__auto_backup = persistence.AutoBackup(self.settings)
        self.iocontroller = gui.IOController(
            self.taskFile, self.displayMessage, self.settings
        )
        self.mainwindow = gui.MainWindow(
            self.iocontroller, self.taskFile, self.settings
        )
        self.__wx_app.SetTopWindow(self.mainwindow)
        if not self.settings.getboolean("file", "inifileloaded"):
            self.__warn_user_that_ini_file_was_not_loaded()
        if loadTaskFile:
            self.iocontroller.openAfterStart(self._args, self.__early_lock_result)
        self.__register_signal_handlers()
        self.__create_mutex()
        self.__create_task_bar_icon()
        wx.CallAfter(self.__show_tips)

    def __check_file_lock_early(self):
        """Check file lock before main window creation.

        This avoids GTK dialog/focus issues by showing any lock dialogs
        before any windows exist.
        """
        from taskcoachlib import persistence, meta

        # Get filename from args or last file
        if self._args:
            filename = self._args[0]
        else:
            filename = self.settings.get("file", "lastfile")

        if not filename or not os.path.exists(filename):
            self.__early_lock_result = None
            return

        # Try to check if file is locked
        lock_file_path = filename + ".lock"
        try:
            import fasteners
            lock = fasteners.InterProcessLock(lock_file_path)
            acquired = lock.acquire(blocking=False)
            if acquired:
                # Not locked - release and proceed normally
                lock.release()
                self.__early_lock_result = 'ok'
                return
            else:
                # File is locked - show dialog BEFORE main window
                result = wx.MessageBox(
                    _(
                        """Cannot open %s because it is locked.

This means either that another instance of TaskCoach
is running and has this file opened, or that a previous
instance of Task Coach crashed. If no other instance is
running, you can safely break the lock.

Break the lock?"""
                    ) % filename,
                    _("%s: file locked") % meta.name,
                    style=wx.YES_NO | wx.ICON_QUESTION | wx.NO_DEFAULT,
                )
                if result == wx.YES:
                    self.__early_lock_result = 'break'
                else:
                    # User said No - don't open file, start with empty/new
                    self.__early_lock_result = 'skip'
        except Exception:
            # Lock check failed (e.g., network drive) - proceed normally
            self.__early_lock_result = 'ok'

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
            # Use the user's locale from environment variables
            # Note: locale.getdefaultlocale() is deprecated since Python 3.11
            # and doesn't reliably read LANG on Linux. We check env vars directly.
            language = os.environ.get('LANG', os.environ.get('LC_ALL', ''))
            if language:
                # Strip encoding suffix (e.g., "de_DE.UTF-8" -> "de_DE")
                language = language.split('.')[0]
                if not language or language == "C" or language == "POSIX":
                    language = None
        if not language:
            # Fallback to locale.getlocale() which may work after setlocale
            try:
                language = locale.getlocale(locale.LC_MESSAGES)[0]
                if language == "C" or language == "POSIX":
                    language = None
            except Exception:
                language = None
        if not language:
            # Fall back on what the majority of our users use
            language = "en_US"
        return language

    def __init_domain_objects(self):
        """Provide relevant domain objects with access to the settings."""
        from taskcoachlib.domain import task, attachment, base

        task.Task.settings = self.settings
        attachment.Attachment.settings = self.settings



    def __init_application(self):
        from taskcoachlib import meta

        self.__wx_app.SetAppName(meta.name)
        self.__wx_app.SetVendorName(meta.author)
        # Set WM_CLASS for Linux app grouping (must match StartupWMClass in .desktop)
        self.__wx_app.SetClassName("taskcoach")
        # Set AppUserModelID for Windows 7+ taskbar grouping
        if operating_system.isWindows():
            try:
                import ctypes
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                    "org.taskcoach.TaskCoach"
                )
            except (ImportError, AttributeError, OSError):
                pass  # Not on Windows or API not available

    def __register_signal_handlers(self):
        """Register signal handlers for clean shutdown.

        DESIGN NOTE (Twisted Removal - 2024):
        Previously used Twisted's reactor which properly handled SIGINT.
        Now using Python's signal module with direct cleanup.

        Key challenges with native wxPython:
        1. Python signal handlers only run when main thread has control
        2. GUI event loops block in C code, preventing signal delivery
        3. Must save settings before exit

        Solution:
        - Custom signal handler uses wx.CallAfter for clean shutdown
        - Periodic timer wakes event loop so Python can check signals
        """
        import signal

        def handle_signal(signum, frame):
            """Handle SIGINT/SIGTERM by scheduling clean shutdown."""
            # Use CallAfter to run shutdown in the main event loop
            # This ensures proper cleanup of wx resources
            wx.CallAfter(self.quitApplication)

        # Register SIGINT/SIGTERM handlers for Unix
        if not operating_system.isWindows():
            signal.signal(signal.SIGINT, handle_signal)
            signal.signal(signal.SIGTERM, handle_signal)

            # Start a timer to periodically wake the event loop
            # This allows Python to check for pending signals
            self._signal_check_timer = wx.Timer()
            self._signal_check_timer.Start(500)  # Check every 500ms

        # NOTE: We intentionally do NOT use SetConsoleCtrlHandler on Windows.
        # According to Microsoft docs, if an app loads gdi32.dll or user32.dll
        # (which wxPython does), the handler doesn't receive CTRL_LOGOFF_EVENT
        # or CTRL_SHUTDOWN_EVENT. It can also cause shutdown issues.
        # Instead, we rely on wxPython's EVT_CLOSE and EVT_END_SESSION events.
        # See: https://learn.microsoft.com/en-us/windows/console/setconsolectrlhandler

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

            # Use factory function to get the appropriate icon type
            # (AppIndicator on Wayland, wx.adv.TaskBarIcon otherwise)
            self.taskBarIcon = taskbaricon.create_taskbar_icon(
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
        except ImportError:
            return False  # TaskBarIcon not available on this platform

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
        # Guard against deleted mainwindow during shutdown
        if getattr(self, '_quitting', False):
            return
        try:
            self.mainwindow.displayMessage(message)
        except RuntimeError:
            pass  # MainWindow C++ object already deleted

    def on_end_session(self):
        self.mainwindow.setShutdownInProgress()
        self.quitApplication(force=True)

    def on_reopen_app(self):
        self.taskBarIcon.onTaskbarClick(None)

    def save_all_settings(self):
        """Save all settings to disk. Called on normal exit and signal handlers.

        This is the single place for saving settings, ensuring consistency
        between normal close, Ctrl-C, and other exit paths.
        """
        try:
            # Remember what the user was working on
            if hasattr(self, 'taskFile'):
                self.settings.set("file", "lastfile", self.taskFile.lastFilename())
            # Save window position, size, perspective
            if hasattr(self, 'mainwindow'):
                self.mainwindow.save_settings()
            # Write settings to disk
            self.settings.save()
            # Release ini file lock after saving
            self.settings.release_ini_lock()
        except Exception:
            pass  # Best effort - don't prevent exit

    def _stopAllTimers(self):
        """Stop all known timers to prevent crashes during shutdown.

        Timer events can be delivered after frames are destroyed but before
        the program ends, causing access violations on Windows.
        See: https://github.com/wxWidgets/Phoenix/issues/429
        """
        import sys
        # Stop signal check timer
        if hasattr(self, '_signal_check_timer') and self._signal_check_timer:
            try:
                self._signal_check_timer.Stop()
            except Exception:
                pass

        # Stop all wx.Timer instances we can find
        # Walk through all top-level windows and their children
        def stop_timers_in_window(window):
            if window is None:
                return
            # Check for timer attributes
            for attr_name in ['__timer', '_timer', 'timer', '_sizeTimer', '_refreshTimer',
                              '_dragTimer', '_findTimer', '_editTimer', '__tmr',
                              'scheduledStatusDisplay', '_globalTimer']:
                # Try both public and name-mangled private attributes
                for prefix in ['', '_' + window.__class__.__name__]:
                    full_name = prefix + attr_name
                    timer = getattr(window, full_name, None)
                    if timer is not None and hasattr(timer, 'Stop'):
                        try:
                            if hasattr(timer, 'IsRunning') and timer.IsRunning():
                                timer.Stop()
                        except Exception:
                            pass
            # Recurse into children
            if hasattr(window, 'GetChildren'):
                try:
                    for child in window.GetChildren():
                        stop_timers_in_window(child)
                except Exception:
                    pass

        # Stop timers in all top-level windows
        for window in wx.GetTopLevelWindows():
            stop_timers_in_window(window)

    def quitApplication(self, force=False):
        # Prevent re-entry - quitApplication may be called multiple times
        # (e.g., from window close, signal handler, console ctrl handler)
        if getattr(self, '_quitting', False):
            return True
        self._quitting = True

        if not self.iocontroller.close(force=force):
            return False
        self.save_all_settings()
        if hasattr(self, "taskBarIcon"):
            self.taskBarIcon.RemoveIcon()
            self.taskBarIcon.Destroy()
        # Stop notification timers to prevent crashes during shutdown
        from taskcoachlib.notify.notifier_universal import NotificationCenter
        NotificationCenter().cleanup()
        wx.EventLoop.GetActive().ProcessIdle()

        # For PowerStateMixin
        self.mainwindow.OnQuit()

        # Stop all timers before closing windows to prevent crashes
        # See: https://github.com/wxWidgets/Phoenix/issues/429
        self._stopAllTimers()

        # End any modal dialogs before closing - modal dialogs have their own
        # nested event loops that prevent ExitMainLoop() from working
        has_modal_dialogs = False
        for window in wx.GetTopLevelWindows():
            if isinstance(window, wx.Dialog) and window.IsModal():
                has_modal_dialogs = True
                window.EndModal(wx.ID_CANCEL)

        # Explicitly close the main window to trigger exit.
        # Set shutdown flag so onClose() won't veto or recurse into quitApplication.
        self.mainwindow.setShutdownInProgress()
        self.mainwindow.Close()

        if has_modal_dialogs:
            # Modal dialogs have nested event loops. Use ScheduleExit on the
            # main loop - it will exit when the nested modal loop terminates.
            # See: https://docs.wxpython.org/wx.EventLoopBase.html
            main_loop = wx.GetApp().GetMainLoop()
            if main_loop:
                main_loop.ScheduleExit(0)
            else:
                wx.GetApp().ExitMainLoop()
        else:
            # Force MainLoop to exit in case something is keeping it alive
            # See: https://discuss.wxpython.org/t/wxpython-app-hanging-not-ending-mainloop/29797
            wx.GetApp().ExitMainLoop()
        return True
