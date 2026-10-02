#!/usr/bin/env python

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

import sys, unittest, os, time, wx, logging
import platform
import re
import subprocess

projectRoot = os.path.abspath("..")
if projectRoot not in sys.path:
    sys.path.insert(0, projectRoot)

# The runtime patches taskcoach.py applies (hypertreelist, SetSize)
import taskcoachlib.workarounds.monkeypatches  # noqa: F401,E402

from taskcoachlib.notify import AbstractNotifier

# The platform this suite is certified on (docs/TESTING.md); a run
# stops anywhere else. Change a version here, on purpose, once the
# full suite passes on it.
CERTIFIED = {
    "OS": "Linux",
    "Display": "X11",
    "Python": "3.13.5",
    "wxPython": "4.2.3",
    "wxWidgets": "3.2.8",
    "GTK": "3.24.49",
}


def platform_in_use():
    """The certified components as found on this machine."""
    library = wx.GetLibraryVersionInfo()
    in_use = {
        "OS": platform.system(),
        "Display": "none",
        "Python": platform.python_version(),
        "wxPython": wx.__version__,
        "wxWidgets": "%d.%d.%d"
        % (library.GetMajor(), library.GetMinor(), library.GetMicro()),
        "GTK": "none",
    }
    try:
        import gi

        gi.require_version("Gtk", "3.0")
        from gi.repository import Gdk, Gtk
    except (ImportError, ValueError):
        return in_use
    in_use["GTK"] = "%d.%d.%d" % (
        Gtk.get_major_version(),
        Gtk.get_minor_version(),
        Gtk.get_micro_version(),
    )
    display = Gdk.Display.get_default()
    if display is not None:
        in_use["Display"] = type(display).__name__.replace("Display", "")
    return in_use


def check_platform():
    """Stop unless this is the certified platform."""
    in_use = platform_in_use()
    differences = [
        "  %s %s, certified %s" % (name, in_use[name], version)
        for name, version in CERTIFIED.items()
        if in_use[name] != version
    ]
    if differences:
        sys.exit(
            "Not the certified test platform (docs/TESTING.md):\n"
            + "\n".join(differences)
        )
    print(
        "Certified platform: "
        + ", ".join("%s %s" % item for item in CERTIFIED.items()),
        file=sys.stderr,
    )


def skipOnPlatform(*platforms):
    """Decorator for unit tests that are to be skipped on specific
    platforms."""

    def wrapper(func):
        if wx.Platform in platforms:
            return lambda self, *args, **kwargs: self.skipTest(
                "platform is %s" % wx.Platform
            )
        return func

    return wrapper


def settle():
    """Run what wx leaves for idle time: deferred calls and the
    destroys of top-level windows."""
    import gc

    for _ in range(3):
        wx.WakeUpIdle()
        wx.Yield()
    gc.collect()


def stale(reason):
    """Skip a test that no longer matches the application and needs a
    rewrite. List them with: grep -rn "test.stale" tests"""
    return unittest.skip("stale: " + reason)


class ChangeRecorder(list):
    """The changes of an event type, as they are sent: (value, source)
    for each source, or the source alone when the event carries no
    value. Keep it referenced: the Publisher holds it weakly."""

    def __init__(self, event_type):
        super().__init__()
        from taskcoachlib import patterns

        patterns.Publisher().registerObserver(
            self.on_event, eventType=event_type
        )

    def on_event(self, event):
        for source in event.sources():
            values = event.values(source)
            self.append((values[0], source) if values else source)


def styled(item):
    """The item after the master loop's pass over it: its categories,
    then its parents and itself, parents first (a child reads its
    parent's style), with the loop's own steps."""
    from taskcoachlib.domain import date
    from taskcoachlib.domain.base.appearance import computeStyles
    from taskcoachlib.gui.scheduler import MasterScheduler

    def parents_first(each):
        return list(reversed(each.ancestors())) + [each]

    order = []
    for each in parents_first(item):
        for category in getattr(each, "categories", set)():
            order.extend(parents_first(category))
    order.extend(parents_first(item))
    for each in order:
        if hasattr(each, "compute_stored_status"):
            MasterScheduler._process_task(each, date.Now())
        else:
            computeStyles(each)
    return item


class TestCase(unittest.TestCase, object):
    def assertEqualLists(self, expectedList, actualList):
        self.assertEqual(len(expectedList), len(actualList))
        for item in expectedList:
            self.assertTrue(item in actualList)

    def registerObserver(self, eventType, eventSource=None):
        if not hasattr(self, "events"):
            self.events = []  # pylint: disable=W0201
        from taskcoachlib import patterns  # pylint: disable=W0404

        patterns.Publisher().registerObserver(
            self.onEvent, eventType=eventType, eventSource=eventSource
        )

    def onEvent(self, event):
        self.events.append(event)

    def setUp(self):
        AbstractNotifier.disableNotifications()

    def set_main_window_task_file(self, window=None):
        """Give the test main window (default: the top window) a task
        file, as the app's main window has, for code that reads its
        taskFile."""
        from taskcoachlib import persistence  # pylint: disable=W0404

        window = window or wx.GetApp().GetTopWindow()
        task_file = persistence.TaskFile()
        window.taskFile = task_file
        self.addCleanup(task_file.stop)
        self.addCleanup(task_file.close)
        # Later tests share the top window
        self.addCleanup(delattr, window, "taskFile")

    def tearDown(self):
        # pylint: disable=W0404
        # Prevent processing of pending events after the test has finished:
        app = wx.GetApp()
        app.Disconnect(wx.ID_ANY)
        # That disconnected wx.CallAfter's handler, which it binds once:
        # without this, no deferred call would run in later tests
        if hasattr(app, "_CallAfterId"):
            del app._CallAfterId
        from taskcoachlib import patterns

        patterns.Publisher().clear()
        patterns.CommandHistory().clear()
        patterns.NumberedInstances.count = dict()
        if hasattr(self, "events"):
            del self.events
        super().tearDown()


class TestCaseFrame(wx.Frame):
    def __init__(self):
        super().__init__(None, wx.ID_ANY, "Frame")
        self.toolbarPerspective = ""

    def getToolBarPerspective(self):
        return self.toolbarPerspective

    def AddBalloonTip(self, *args, **kwargs):
        pass


class wxTestCase(TestCase):
    # pylint: disable=W0404
    app = wx.App(0)
    # What the application's wx.App provides (application.py)
    app.quitting = False
    from taskcoachlib import config

    app.settings = config.Settings(load=False)
    # Light, so colours do not follow the desktop theme
    app.settings.settext("window", "theme", "light")
    from taskcoachlib.config import settings2

    if not settings2._initialized:  # test.py also runs as module "test"
        settings2.init(app.settings)
        settings2.wx_ready()
    frame = TestCaseFrame()
    from taskcoachlib import i18n

    i18n.Translator("en_US")
    from taskcoachlib import gui

    gui.init()
    # The gui package does not import its modules; tests use them as
    # gui.<module>, and they need the icons initialized first
    from taskcoachlib.gui import (  # noqa: F401
        dialog,
        iocontroller,
        mainwindow,
        menu,
        printer,
        remindercontroller,
        taskbaricon,
        toolbar,
        uicommand,
        viewer,
        windowdimensionstracker,
    )
    from taskcoachlib.gui.dialog import editor  # noqa: F401

    def tearDown(self):
        super().tearDown()
        self.frame.DestroyChildren()  # Clean up GDI objects on Windows


class TestResultWithTimings(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._timings = {}

    def startTest(self, test):
        super().startTest(test)
        self._timings[test] = time.time()

    def stopTest(self, test):
        super().stopTest(test)
        self._timings[test] = time.time() - self._timings[test]


class TextTestRunnerWithTimings(unittest.TextTestRunner):
    def __init__(self, nrTestsToReport, timeTests=False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._timeTests = timeTests
        self._nrTestsToReport = nrTestsToReport

    def _makeResult(self):
        return TestResultWithTimings(
            self.stream, self.descriptions, self.verbosity
        )

    def run(self, *args, **kwargs):  # pylint: disable=W0221
        result = super().run(*args, **kwargs)
        if self._timeTests:
            sortableTimings = [
                (timing, test)
                for test, timing in list(result._timings.items())
            ]  # pylint: disable=W0212
            sortableTimings.sort(reverse=True)
            print("\n%d slowest tests:" % self._nrTestsToReport)
            for timing, test in sortableTimings[: self._nrTestsToReport]:
                print("%s (%.2f)" % (test, timing))
        return result


class AllTests(unittest.TestSuite):
    def __init__(self, options, testFiles=None):
        super().__init__()
        self._options = options
        self.loadAllTests(testFiles or [])

    def filenameToModuleName(self, filename):
        if filename == os.path.abspath(filename):
            # Strip current working directory to get the relative path:
            filename = filename[len(os.getcwd() + os.sep) :]
        module = filename.replace(os.sep, ".")
        module = module.replace("/", ".")
        return module[:-3]  # strip '.py'

    def loadAllTests(self, testFiles):
        testloader = unittest.TestLoader()
        for filename in testFiles or catalog(self._options):
            moduleName = self.filenameToModuleName(filename)
            # Importing the module is not strictly necessary because
            # loadTestsFromName will do that too as a side effect. But if the
            # test module contains errors our import will raise an exception
            # while loadTestsFromName ignores exceptions when importing from
            # modules.
            __import__(moduleName)
            suite = testloader.loadTestsFromName(moduleName)
            self.addTests(suite._tests)  # pylint: disable=W0212

    def runTests(self):
        testrunner = TextTestRunnerWithTimings(
            verbosity=self._options.verbosity,
            timeTests=self._options.time,
            nrTestsToReport=self._options.time_reports,
        )
        return testrunner.run(self)

    @staticmethod
    def getTestFilesFromDir(directory):
        return AllTests.getFilesFromDir(directory, "Test.py")

    @staticmethod
    def getFilesFromDir(directory, extension):
        result = []
        for root, dirs, filenames in os.walk(
            directory
        ):  # pylint: disable=W0612
            result.extend(
                [
                    os.path.join(root, filename)
                    for filename in filenames
                    if filename.endswith(extension)
                ]
            )
        return result


def catalog(options):
    """The test files of the selected parts of the catalog: the shared
    tests, which run on every platform (docs/TESTING.md)."""
    parts = [
        ("unittests", options.unittests),
        ("integrationtests", options.integrationtests),
        ("languagetests", options.languagetests),
    ]
    return sorted(
        filename
        for directory, selected in parts
        if selected
        for filename in AllTests.getTestFilesFromDir(directory)
    )


def run_catalog(options, test_files):
    """Run each test file in its own process, as a file is run alone;
    report each file and the failures. Return the exit status."""
    files = test_files or catalog(options)
    options_given = [arg for arg in sys.argv[1:] if arg not in test_files]
    failed, tests_run = [], 0
    for filename in files:
        # A crash leaves a traceback, and the output before it
        environment = dict(
            os.environ, PYTHONFAULTHANDLER="1", PYTHONUNBUFFERED="1"
        )
        result = subprocess.run(
            [sys.executable, sys.argv[0], *options_given, filename],
            capture_output=True,
            text=True,
            env=environment,
        )
        output = result.stdout + result.stderr
        ran = re.search(r"^Ran (\d+) tests?", output, re.MULTILINE)
        count = int(ran.group(1)) if ran else 0
        tests_run += count
        print(
            "%-6s %5d  %s"
            % ("FAILED" if result.returncode else "ok", count, filename),
            flush=True,
        )
        if result.returncode:
            failed.append(filename)
            print("exit status %d" % result.returncode)
            report = output.find("=" * 70)
            lines = output[report:] if report >= 0 else output
            print("\n".join(lines.splitlines()[-60:]) + "\n", flush=True)
    print(
        "%d files, %d tests: %s"
        % (
            len(files),
            tests_run,
            "%d failed" % len(failed) if failed else "all passed",
        )
    )
    for filename in failed:
        print("FAILED " + filename)
    return 1 if failed else 0


from taskcoachlib import config


class TestOptionParser(config.OptionParser):
    def __init__(self):
        super().__init__(usage="usage: %prog [options] [testfiles]")

    def testoutputOptionGroup(self):
        testoutput = config.OptionGroup(
            self,
            "Test output",
            "Options to determine the amount of output while running the "
            "tests.",
        )
        testoutput.add_option(
            "-q",
            "--quiet",
            action="store_const",
            default=1,
            const=0,
            dest="verbosity",
            help="show only the final test result",
        )
        testoutput.add_option(
            "--progress",
            action="store_const",
            const=1,
            dest="verbosity",
            help="show progress [default]",
        )
        testoutput.add_option(
            "-v",
            "--verbose",
            action="store_const",
            const=2,
            dest="verbosity",
            help="show all tests",
        )
        testoutput.add_option(
            "-t",
            "--time",
            default=False,
            action="store_true",
            help="time the tests and report the slowest tests",
        )
        testoutput.add_option(
            "--time-reports",
            default=10,
            type="int",
            help="the number of slow tests to report [%default]",
        )
        return testoutput

    def profileOptionGroup(self):
        profile = config.OptionGroup(
            self,
            "Profiling",
            "Options to profile the tests to see what test code or production "
            "code is taking the most time.",
        )
        profile.add_option(
            "-p",
            "--profile",
            default=False,
            action="store_true",
            help="profile the running of all the tests",
        )
        profile.add_option(
            "-r",
            "--report-only",
            dest="profile_report_only",
            action="store_true",
            default=False,
            help="don't make a new profile, report only on the last profile",
        )
        profile.add_option(
            "-s",
            "--sort",
            dest="profile_sort",
            action="append",
            default=[],
            help="sort key to be used for reporting the profile data. "
            "Possible sort keys are: 'calls', 'cumulative' [default], "
            "'file', 'line', 'module', 'name', 'nfl', 'pcalls', 'stdname', "
            "and 'time'. This option may be repeated",
        )
        profile.add_option(
            "--callers",
            dest="profile_callers",
            default=False,
            action="store_true",
            help="print callers",
        )
        profile.add_option(
            "--callees",
            dest="profile_callees",
            default=False,
            action="store_true",
            help="print callees",
        )
        profile.add_option(
            "-l",
            "--limit",
            dest="profile_limit",
            default=50,
            type="int",
            help="limit the number of calls to show in the "
            "profile reports [%default]",
        )
        profile.add_option(
            "--regex",
            dest="profile_regex",
            help="Regular expression to limit the functions shown in the "
            "profile reports",
        )
        return profile

    def testselectionOptionGroup(self):
        testselection = config.OptionGroup(
            self, "Test selection", "Options to determine which tests to run."
        )

        description = dict(all="all")

        def help_text(selection):
            return "run %s tests" % description.get(
                selection, "the %s" % selection
            ) + (" [default]" if selection == "unit" else "")

        for selection in (
            "unit",
            "integration",
            "language",
            "all",
        ):
            testselection.add_option(
                "--%stests" % selection,
                default=False,
                action="store_true",
                help=help_text(selection),
            )

        return testselection

    def parse_args(self):  # pylint: disable=W0221
        options, args = super().parse_args()
        if options.profile_report_only:
            options.profile = True
        if not options.profile_sort:
            options.profile_sort.append("cumulative")
        if not (
            options.unittests
            or options.integrationtests
            or options.languagetests
            or options.alltests
        ):
            options.unittests = True  # the default option
        if options.alltests:
            options.unittests = True
            options.integrationtests = True
            options.languagetests = True
        return options, args


class TestProfiler:
    def __init__(self, options, logfile=".profile"):
        self._logfile = logfile
        self._options = options

    def reportLastRun(self):
        import pstats  # pylint: disable=W0404

        stats = pstats.Stats(self._logfile)
        stats.strip_dirs()
        for sortKey in self._options.profile_sort:
            stats.sort_stats(sortKey)
            stats.print_stats(
                self._options.profile_regex, self._options.profile_limit
            )
        if self._options.profile_callers:
            stats.print_callers()
        if self._options.profile_callees:
            stats.print_callees()

    def run(self, tests, command="runTests"):
        if self._options.profile_report_only or self.profile(tests, command):
            self.reportLastRun()

    def profile(self, tests, command):  # pylint: disable=W0613
        import cProfile  # pylint: disable=W0404

        _locals = dict(locals())
        cProfile.runctx(
            "result = tests.%s()" % command,
            globals(),
            _locals,
            filename=self._logfile,
        )
        result = _locals["result"]
        if not result.wasSuccessful():
            self.cleanup()
        return result.wasSuccessful()

    def cleanup(self):
        os.remove(self._logfile)


if __name__ == "__main__":
    logging.basicConfig()
    theOptions, theTestFiles = TestOptionParser().parse_args()
    check_platform()
    if theOptions.profile:
        TestProfiler(theOptions).run(AllTests(theOptions, theTestFiles))
    elif len(theTestFiles) == 1:
        if not AllTests(theOptions, theTestFiles).runTests().wasSuccessful():
            sys.exit(1)
    else:
        sys.exit(run_catalog(theOptions, theTestFiles))
