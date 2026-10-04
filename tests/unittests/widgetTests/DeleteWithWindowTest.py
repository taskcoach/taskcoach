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

import weakref

import test
import wx
from wx import siplib
from taskcoachlib.tools import wxhelper


class Holder:
    """What a handler's own handlers hold, as an AUI manager holds its
    window's panes."""

    def on_event(self, event):
        pass


class DeleteWithWindowTest(test.wxTestCase):
    def setUp(self):
        super().setUp()
        self.window = wx.Panel(self.frame)
        self.handler = wx.EvtHandler()
        holder = Holder()
        holder.handler = self.handler
        self.handler.Bind(wx.EVT_MENU, holder.on_event)
        self.holder = weakref.ref(holder)

    def test_without_it_its_handlers_keep_it(self):
        # Why it exists: once this fails, wx frees such a handler
        # itself and delete_with_window() can go
        self.handler = None
        self.window.Destroy()
        test.settle()
        self.assertIsNotNone(self.holder())

    def test_deleted_once_its_window_is_destroyed(self):
        wxhelper.delete_with_window(self.handler, self.window)
        self.window.Destroy()
        test.settle()
        self.assertTrue(siplib.isdeleted(self.handler))

    def test_what_its_handlers_hold_is_freed(self):
        wxhelper.delete_with_window(self.handler, self.window)
        self.window.Destroy()
        test.settle()
        self.assertIsNone(self.holder())

    def test_kept_while_its_window_lives(self):
        wxhelper.delete_with_window(self.handler, self.window)
        test.settle()
        self.assertFalse(siplib.isdeleted(self.handler))

    def test_kept_when_a_child_of_its_window_is_destroyed(self):
        # The child's destroy event comes up to the window
        wxhelper.delete_with_window(self.handler, self.window)
        wx.Panel(self.window).Destroy()
        test.settle()
        self.assertFalse(siplib.isdeleted(self.handler))

    def test_deleted_with_a_top_level_window(self):
        # Its destroy event comes once its wrapper is deleted
        frame = wx.Frame(self.frame)
        wxhelper.delete_with_window(self.handler, frame)
        frame.Destroy()
        test.settle()
        self.assertTrue(siplib.isdeleted(self.handler))

    def test_released_first(self):
        released = []
        wxhelper.delete_with_window(
            self.handler,
            self.window,
            lambda handler: released.append(siplib.isdeleted(handler)),
        )
        self.window.Destroy()
        test.settle()
        self.assertEqual([False], released)
