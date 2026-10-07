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

import test, wx
from taskcoachlib.widgets import draganddrop, treectrl


class DummyEvent(object):
    def __init__(self, item=None):
        self.item = item
        self.vetoed = self.allowed = False

    def GetItem(self):
        return self.item

    def Veto(self):
        self.vetoed = True

    def Allow(self):
        self.allowed = True


class TreeCtrlDragAndDropMixinTest(test.wxTestCase):
    # pylint: disable=E1101

    def setUp(self):
        # As the app's trees: the root hidden, so never selected
        self.treeCtrl = treectrl.HyperTreeList(
            self.frame,
            agwStyle=wx.TR_DEFAULT_STYLE | wx.TR_HIDE_ROOT | wx.TR_MULTIPLE,
        )
        self.treeCtrl.AddColumn("First")

        self.rootItem = self.treeCtrl.AddRoot("root")
        self.item = self.treeCtrl.AppendItem(self.rootItem, "item")

    def assertEventIsVetoed(self, event):
        self.assertTrue(event.vetoed)
        self.assertFalse(event.allowed)

    def assertEventIsAllowed(self, event):
        self.assertTrue(event.allowed)
        self.assertFalse(event.vetoed)

    def test_event_is_vetoed_when_drag_begins_without_item(self):
        event = DummyEvent()
        self.treeCtrl._drag_start_pos = wx.Point(0, 0)
        self.treeCtrl.on_begin_drag(event)
        self.assertEventIsVetoed(event)

    def test_event_is_allowed_when_drag_begins_with_item(self):
        event = DummyEvent(self.item)
        self.treeCtrl._drag_start_pos = wx.Point(0, 0)
        self.treeCtrl.on_begin_drag(event)
        self.assertEventIsAllowed(event)

    def test_event_is_allowed_when_drag_begin_with_selected_item(self):
        self.treeCtrl.SelectItem(self.item)
        event = DummyEvent(self.item)
        self.treeCtrl._drag_start_pos = wx.Point(0, 0)
        self.treeCtrl.on_begin_drag(event)
        self.assertEventIsAllowed(event)


class NotAllowedCursorTest(test.wxTestCase):
    def test_the_not_allowed_cursor_comes_from_task_coachs_icons(self):
        # Not wx's no-entry cursor: X draws that as a skull where the
        # cursor theme has no picture for it
        from taskcoachlib.gui.icons.icon_library import icon_catalog

        cursor = draganddrop.not_allowed_cursor()
        self.assertTrue(cursor.IsOk())
        self.assertIs(
            icon_catalog.get_cursor("synthetic_cursor_not_allowed"), cursor
        )
