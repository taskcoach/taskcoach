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

import wx
import test
from taskcoachlib import widgets


class CtrlWithColumnsTestCase(test.wxTestCase):
    def setUp(self):
        super().setUp()
        self.column1 = widgets.Column("Column 1", "eventType1")
        self.column2 = widgets.Column("Column 2", "eventType2")
        self.control = self.createControl()

    def createControl(self):
        raise NotImplementedError  # pragma: no cover


class CtrlWithHideableColumnsUnderTest(
    widgets.itemctrl._CtrlWithHideableColumnsMixin,  # pylint: disable=W0212
    wx.ListCtrl,
):
    pass


class CtrlWithHideableColumnsTestsMixin(object):
    def testColumnIsVisibleByDefault(self):
        self.assertTrue(self.control.isColumnVisible(self.column1))

    def testHideColumn(self):
        self.control.showColumn(self.column1, show=False)
        self.assertFalse(self.control.isColumnVisible(self.column1))

    def testShowColumn(self):
        self.control.showColumn(self.column1, show=False)
        self.control.showColumn(self.column1, show=True)
        self.assertTrue(self.control.isColumnVisible(self.column1))


class CtrlWithHideableColumnsTest(
    CtrlWithColumnsTestCase, CtrlWithHideableColumnsTestsMixin
):
    def createControl(self):
        return CtrlWithHideableColumnsUnderTest(
            self.frame,
            style=wx.LC_REPORT,
            columns=[self.column1, self.column2],
        )


class CtrlWithSortableColumnsUnderTest(
    widgets.itemctrl._CtrlWithSortableColumnsMixin,  # pylint: disable=W0212
    wx.ListCtrl,
):
    pass


class CtrlWithSortableColumnsTestsMixin(object):
    def assertCurrentSortColumn(self, expectedSortColumn):
        currentSortColumn = (
            self.control._currentSortColumn()
        )  # pylint: disable=W0212
        self.assertEqual(expectedSortColumn, currentSortColumn)

    def testDefaultSortColumn(self):
        self.assertCurrentSortColumn(self.column1)

    def testShowSortColumn(self):
        self.control.show_sort_column(self.column2)
        self.assertCurrentSortColumn(self.column2)


class CtrlWithSortableColumnsTest(
    CtrlWithColumnsTestCase, CtrlWithSortableColumnsTestsMixin
):
    def createControl(self):
        return CtrlWithSortableColumnsUnderTest(
            self.frame,
            style=wx.LC_REPORT,
            columns=[self.column1, self.column2],
        )


class CtrlWithColumnsUnderTest(
    widgets.itemctrl.CtrlWithColumnsMixin, wx.ListCtrl
):
    pass


class CtrlWithColumnsTest(
    CtrlWithColumnsTestCase,
    CtrlWithHideableColumnsTestsMixin,
    CtrlWithSortableColumnsTestsMixin,
):
    def createControl(self):
        # NOTE: the resizeableColumn is the column that is not hidden
        return CtrlWithColumnsUnderTest(
            self.frame,
            style=wx.LC_REPORT,
            columns=[self.column1, self.column2],
            resizeableColumn=1,
            columnPopupMenu=None,
        )


class DummyEvent(object):
    def __init__(self, eventObject):
        self.eventObject = eventObject

    def Skip(self, *args):
        pass

    def GetColumn(self):
        return 0

    def GetEventObject(self):
        return self.eventObject

    def GetPosition(self):
        return 0, 0


class ListCtrlWithColumnPopupMenuTest(CtrlWithColumnsTestCase):
    def createControl(self):
        return CtrlWithColumnsUnderTest(
            self.frame,
            style=wx.LC_REPORT,
            columns=[self.column1, self.column2],
            resizeableColumn=1,
            columnPopupMenu=wx.Menu(),
        )

    @test.skipOnPlatform("__WXGTK__")  # Popup menu hangs the test
    def testColumnHeaderPopupMenu(self):
        self.control.on_column_popup_menu(DummyEvent(self.control))


class HyperListTreeCtrlWithColumnPopupMenuTest(CtrlWithColumnsTestCase):
    def createControl(self):
        return widgets.TreeListCtrl(
            self.frame,
            [self.column1, self.column2],
            None,
            None,
            None,
            None,
            columnPopupMenu=wx.Menu(),
        )

    @test.skipOnPlatform("__WXGTK__")  # Popup menu hangs the test
    def testColumnHeaderPopupMenu(self):
        self.control.on_column_popup_menu(DummyEvent(self.control))
