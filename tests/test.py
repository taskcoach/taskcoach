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

projectRoot = os.path.abspath("..")
if projectRoot not in sys.path:
    sys.path.insert(0, projectRoot)

from taskcoachlib.notify import AbstractNotifier


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


def skipOnTwistedVersions(*versions):
    """
    Decorator for unit tests that were previously skipped on specific
    versions of Twisted.

    DESIGN NOTE (Twisted Removal - 2024):
    This decorator is now a no-op since Twisted has been removed.
    It's kept for backward compatibility with existing test code.
    Tests that used reactor.iterate() have been updated to use
    wx event processing instead.
    """
    def wrapper(func):
        # No longer skip based on Twisted versions since Twisted is removed
        return func

    return wrapper


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

    def tearDown(self):
        # pylint: disable=W0404
        # Prevent processing of pending events after the test has finished:
        wx.GetApp().Disconnect(wx.ID_ANY)
        from taskcoachlib import patterns

        patterns.Publisher().clear()
        patterns.CommandHistory().clear()
        patterns.NumberedInstances.count = dict()
        from taskcoachlib.domain import date

        date.Scheduler().shutdown()
        date.Scheduler.deleteInstance()
        if hasattr(self, "events"):
            del self.events
        from pubsub import pub

        pub.unsubAll()
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
    frame = TestCaseFrame()
    from taskcoachlib import i18n

    i18n.Translator("en_US")
    from taskcoachlib import gui

    gui.init()

    def tearDown(self):
        super().tearDown()
        self.frame.DestroyChildren()  # Clean up GDI objects on Windows


class TestResultWithTimings(unittest._TextTestResult):  # pylint: disable=W0212
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
        if not testFiles:
            if self._options.unittests:
                testFiles.extend(self.getTestFilesFromDir("unittests"))
            if self._options.integrationtests:
                testFiles.extend(self.getTestFilesFromDir("integrationtests"))
            if self._options.languagetests:
                testFiles.extend(self.getTestFilesFromDir("languagetests"))
            if self._options.releasetests:
                testFiles.extend(self.getTestFilesFromDir("releasetests"))
            if self._options.disttests:
                path = os.path.join("disttests", sys.platform)
                if os.path.exists(path):
                    testFiles.extend(self.getTestFilesFromDir(path))
                else:
                    print(
                        "WARNING: no disttest for your platform (%s)"
                        % sys.platform
                    )
        for filename in testFiles:
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
    def getPyFilesFromDir(directory):
        return AllTests.getFilesFromDir(directory, ".py")

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

        description = dict(dist="the platform-specific package", all="all")

        def helpText(selection):
            return "run %s tests" % description.get(
                selection, "the %s" % selection
            ) + (" [default]" if selection == "unit" else "")

        for selection in (
            "unit",
            "integration",
            "language",
            "release",
            "dist",
            "all",
        ):
            testselection.add_option(
                "--%stests" % selection,
                default=False,
                action="store_true",
                help=helpText(selection),
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
            or options.releasetests
            or options.disttests
            or options.alltests
        ):
            options.unittests = True  # the default option
        if options.alltests:
            options.unittests = True
            options.integrationtests = True
            options.languagetests = True
            options.releasetests = True
            options.disttests = True
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
    allTests = AllTests(theOptions, theTestFiles)
    if theOptions.profile:
        TestProfiler(theOptions).run(allTests)
    else:
        theResult = allTests.runTests()
        if not theResult.wasSuccessful():
            sys.exit(1)
