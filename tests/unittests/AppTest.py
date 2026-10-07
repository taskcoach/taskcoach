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

import os
import signal
from unittest import mock

import test
import wx
from taskcoachlib import meta, application, i18n, patterns
from taskcoachlib.config import settings
from taskcoachlib.domain import date


class DummyOptions(object):
    pofile = None
    language = None


class DummyLocale(object):
    """The locale calls the app makes, for one language."""

    LC_MESSAGES = 5

    def __init__(self, language="C"):
        self.language = language

    def getlocale(self, category):  # pylint: disable=W0613
        return self.language, None


class AppTests(test.TestCase):
    def setUp(self):
        super().setUp()
        self.options = DummyOptions()

    def test_app_properties(self):
        # The harness made a translator for the unit tests; the app
        # makes its own, as at a real start (its guard stops a second)
        i18n.Translator.deleteInstance()
        # Creating the app is expensive: all the queries in one test
        app = application.Application(
            load_settings=False, load_task_file=False
        )
        wx_app = wx.GetApp()
        self.assertEqual(meta.name, wx_app.GetAppName())
        self.assertEqual(meta.author, wx_app.GetVendorName())
        app.mainwindow._idleController.stop()
        app.quit_application()
        app.mainwindow.Destroy()
        application.Application.deleteInstance()

    def test_the_file_opens_once_the_window_has_drawn(self):
        # The window shows at once, however long the file takes to read
        i18n.Translator.deleteInstance()
        with mock.patch(
            "taskcoachlib.gui.iocontroller.IOController.open_after_start"
        ) as open_after_start:
            app = application.Application(
                load_settings=False, load_task_file=True
            )
            opened_at_start = open_after_start.called
            # Nothing paints here: the first tick opens it
            patterns.Event("timer.second", self, date.DateTime.now()).send()
            opened_at_tick = open_after_start.called
        app.mainwindow._idleController.stop()
        app.quit_application()
        app.mainwindow.Destroy()
        application.Application.deleteInstance()
        self.assertEqual((False, True), (opened_at_start, opened_at_tick))

    def test_the_tray_comes_after_the_file(self):
        # Its menu is made once, with the file's list
        i18n.Translator.deleteInstance()
        order = []

        def open_after_start(*args):
            patterns.later.soon(None, order.append, "file")

        with mock.patch(
            "taskcoachlib.gui.iocontroller.IOController.open_after_start",
            side_effect=open_after_start,
        ), mock.patch.object(
            application.Application,
            "_Application__create_task_bar_icon",
            lambda app: order.append("tray"),
        ):
            app = application.Application(
                load_settings=False, load_task_file=True
            )
            patterns.Event("timer.second", self, date.DateTime.now()).send()
            wx.GetApp().ProcessPendingEvents()
        app.mainwindow._idleController.stop()
        app.quit_application()
        app.mainwindow.Destroy()
        application.Application.deleteInstance()
        self.assertEqual(["file", "tray"], order)

    def assert_language(self, expected_language, locale=None, **environ):
        args = [self.options]
        if locale:
            args.append(locale)
        # Not this machine's language: only the one given here
        with mock.patch.dict(os.environ):
            for name in ("LC_ALL", "LC_MESSAGES", "LANG"):
                os.environ.pop(name, None)
            os.environ.update(environ)
            self.assertEqual(
                expected_language,
                application.Application.determine_language(*args),
            )  # pylint: disable=W0142

    def test_language_via_command_line_option(self):
        self.options.language = "fi_FI"
        self.assert_language("fi_FI")

    def test_language_via_command_line_po_file(self):
        self.options.pofile = "nl_NL"
        self.assert_language("nl_NL")

    def test_language_via_externally_set_language(self):
        settings.view.language = "de_DE"
        self.assert_language("de_DE")

    def test_language_set_by_user(self):
        settings.view.language_set_by_user = "de_DE"
        self.assert_language("de_DE")

    def test_language_set_by_user_overrides_externally_set_language(self):
        settings.view.language = "nl_NL"
        settings.view.language_set_by_user = "de_DE"
        self.assert_language("de_DE")

    def test_language_via_lang(self):
        self.assert_language("en_GB", DummyLocale(), LANG="en_GB.UTF-8")

    def test_lc_all_comes_before_lang(self):
        self.assert_language(
            "de_DE", DummyLocale(), LANG="en_GB.UTF-8", LC_ALL="de_DE.UTF-8"
        )

    def test_lc_messages_comes_before_lang(self):
        self.assert_language(
            "fr_FR",
            DummyLocale(),
            LANG="en_GB.UTF-8",
            LC_MESSAGES="fr_FR.UTF-8",
        )

    def test_lc_all_comes_before_lc_messages(self):
        self.assert_language(
            "de_DE",
            DummyLocale(),
            LC_MESSAGES="fr_FR.UTF-8",
            LC_ALL="de_DE.UTF-8",
        )

    def test_language_via_the_locale(self):
        self.assert_language("en_GB", DummyLocale("en_GB"))

    def test_language_via_the_c_locale(self):
        self.assert_language("en_US", DummyLocale())


class SessionEndTest(test.TestCase):
    """The end of a session nobody can be asked about
    (docs/SESSION_END.md)."""

    def setUp(self):
        super().setUp()
        patcher = mock.patch.object(
            application.application.patterns.later,
            "soon",
            side_effect=lambda owner, callback, *args: callback(*args),
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_sigterm_and_sighup_close_without_asking(self):
        for signum in (signal.SIGTERM, signal.SIGHUP):
            with self.subTest(signum=signum):
                app = mock.Mock()
                application.Application.on_signal(app, signum, None)
                app.on_end_session.assert_called_once_with()
                app.quit_application.assert_not_called()

    def test_a_signal_ignored_at_start_stays_ignored(self):
        # Started with nohup: closing the terminal must not end it
        ignored = {signal.SIGHUP}
        with mock.patch.object(
            signal,
            "getsignal",
            side_effect=lambda signum: (
                signal.SIG_IGN if signum in ignored else signal.SIG_DFL
            ),
        ), mock.patch.object(signal, "signal") as register:
            application.Application._Application__register_signal_handlers(
                mock.Mock()
            )
        registered = {call.args[0] for call in register.call_args_list}
        self.assertEqual({signal.SIGINT, signal.SIGTERM}, registered)

    def test_ended_before_the_startup_open_keeps_the_last_file(self):
        settings.file.lastfile = "tasks.tsk"
        app = mock.Mock()
        app._Application__startup_open_pending = True
        app.taskFile.lastFilename.return_value = ""
        application.Application._Application__remember_last_file(app)
        self.assertEqual("tasks.tsk", settings.file.lastfile)

    def test_ctrl_c_asks_as_quit_does(self):
        app = mock.Mock()
        application.Application.on_signal(app, signal.SIGINT, None)
        app.quit_application.assert_called_once_with()

    def test_a_failing_step_at_quit_skips_no_other(self):
        app = mock.Mock()
        app.settings.save.side_effect = OSError("Disk full")
        application.Application.save_all_settings(app)
        app.settings.release_ini_lock.assert_called_once_with()
