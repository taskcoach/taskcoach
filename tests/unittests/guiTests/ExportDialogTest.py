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

import test
from taskcoachlib.gui import dialog
from taskcoachlib import config
from wx.lib import sized_controls


class DummyColumn(object):
    def __init__(self, name):
        self.__name = name

    def name(self):
        return self.__name

    def header(self):
        return 'dummy column "%s"' % self.__name


class DummyViewer(object):
    def __init__(self):
        self.col1 = DummyColumn("one")
        self.col2 = DummyColumn("two")

    def title(self):
        return "viewer"

    def hasHideableColumns(self):
        return True

    def visibleColumns(self):
        return []

    def columns(self):
        return [self.col1, self.col2]

    def selectable_columns(self):
        return [self.col2]


class DummyViewerContainer(object):
    def activeViewer(self):
        return 1

    def __getitem__(self, index):
        if index == 0:
            return DummyViewer()
        else:
            raise IndexError


class ExportDialogTest(test.wxTestCase):
    def testCreate(self):
        self.frame.viewer = DummyViewerContainer()
        settings = config.Settings(load=False)
        dialog.export.ExportAsHTMLDialog(self.frame, settings=settings)


class ColumnPickerTest(test.wxTestCase):
    def testCreate(self):
        panel = sized_controls.SizedPanel(self.frame)
        dialog.export.ColumnPicker(panel, DummyViewer())

    def testOnlySelectableColumns(self):
        panel = sized_controls.SizedPanel(self.frame)
        dlg = dialog.export.ColumnPicker(panel, DummyViewer())
        self.assertEqual(dlg.columnPicker.GetCount(), 1)
        self.assertEqual(dlg.columnPicker.GetClientData(0).name(), "two")
