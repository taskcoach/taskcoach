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
from taskcoachlib.widgets import treectrl


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
        self.treeCtrl = treectrl.HyperTreeList(self.frame)
        self.treeCtrl.AddColumn("First")

        self.rootItem = self.treeCtrl.AddRoot("root")
        self.item = self.treeCtrl.AppendItem(self.rootItem, "item")

    def assertEventIsVetoed(self, event):
        self.assertTrue(event.vetoed)
        self.assertFalse(event.allowed)

    def assertEventIsAllowed(self, event):
        self.assertTrue(event.allowed)
        self.assertFalse(event.vetoed)

    def testEventIsVetoedWhenDragBeginsWithoutItem(self):
        event = DummyEvent()
        self.treeCtrl._dragStartPos = wx.Point(0, 0)
        self.treeCtrl.OnBeginDrag(event)
        self.assertEventIsVetoed(event)

    def testEventIsAllowedWhenDragBeginsWithItem(self):
        event = DummyEvent(self.item)
        self.treeCtrl._dragStartPos = wx.Point(0, 0)
        self.treeCtrl.OnBeginDrag(event)
        self.assertEventIsAllowed(event)

    def testEventIsAllowedWhenDragBeginWithSelectedItem(self):
        self.treeCtrl.SelectItem(self.item)
        event = DummyEvent(self.item)
        self.treeCtrl._dragStartPos = wx.Point(0, 0)
        self.treeCtrl.OnBeginDrag(event)
        self.assertEventIsAllowed(event)
