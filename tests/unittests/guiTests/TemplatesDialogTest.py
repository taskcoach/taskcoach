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

import test, os, shutil
from unittest import mock
from taskcoachlib import gui, config


class TemplatesDialogTestCase(test.wxTestCase):
    def setUp(self):
        super().setUp()
        self.settings = config.settings.current()

        # Monkey-patching
        self.path = os.path.join(os.path.split(__file__)[0], "tmpl")
        self.safelyRemove(self.path)
        os.mkdir(self.path)

        patcher = mock.patch.object(
            self.settings, "pathToTemplatesDir", lambda: self.path
        )
        patcher.start()
        self.addCleanup(patcher.stop)

        self.editor = gui.dialog.templates.TemplatesDialog(
            self.frame, title="title"
        )

    def tearDown(self):
        super().tearDown()
        self.safelyRemove(self.path)

    def safelyRemove(self, path):
        try:
            shutil.rmtree(path)
        except OSError:  # pragma: no cover
            pass

    def testTwoDefaultTemplates(self):
        self.assertEqual(
            0, len(self.editor._templates.tasks())
        )  # pylint: disable=W0212
