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
from unittests import dummy
from taskcoachlib import gui
from taskcoachlib.gui.uicommand import Separator, Spacer


class ToolBar(gui.toolbar.ToolBar):
    def uiCommands(self, cache=True):
        return []


class ToolBarTest(test.wxTestCase):
    def test_append_ui_command(self):
        gui.init()
        toolbar = ToolBar(self.frame)
        ui_command = dummy.DummyUICommand(menu_text="undo", bitmap="undo")
        tool_id = toolbar.append_ui_command(ui_command)
        self.assertNotEqual(wx.NOT_FOUND, toolbar.GetToolPos(tool_id))


class ToolBarSizeTest(test.wxTestCase):
    def test_size_default(self):
        self.createToolBarAndTestSize(None, (22, 22))  # Medium

    def test_size_small(self):
        self.createToolBarAndTestSize((16, 16))

    def test_size_medium(self):
        self.createToolBarAndTestSize((22, 22))

    def test_size_big(self):
        self.createToolBarAndTestSize((32, 32))

    def createToolBarAndTestSize(self, size, expected_size=None):
        toolbar_args = [self.frame]
        if size:
            toolbar_args.append(size)
        toolbar = ToolBar(*toolbar_args)
        if not expected_size:
            expected_size = size
        self.assertEqual(wx.Size(*expected_size), toolbar.GetToolBitmapSize())


class ToolBarPerspectiveTest(test.wxTestCase):
    def setUp(self):
        class NoBitmapUICommand(dummy.DummyUICommand):
            def append_to_toolbar(self, toolbar):
                pass

        class TestFrame(test.TestCaseFrame):
            def createToolBarUICommands(self):
                class Test1(NoBitmapUICommand):
                    pass

                class Test2(NoBitmapUICommand):
                    pass

                return [Test1(), Separator(), Test2(), Spacer()]

        self.tbFrame = TestFrame()

    def tearDown(self):
        self.tbFrame.Close()

    def test_empty(self):
        bar = gui.toolbar.ToolBar(self.tbFrame)
        # An empty perspective is an empty toolbar
        self.assertEqual(bar.perspective(), "")

    def test_restrict(self):
        self.tbFrame.toolbarPerspective = "Test1,Spacer"
        bar = gui.toolbar.ToolBar(self.tbFrame)
        self.assertEqual(bar.perspective(), "Test1,Spacer")

    def test_does_not_exist(self):
        self.tbFrame.toolbarPerspective = "Test1,Spacer,Test3"
        bar = gui.toolbar.ToolBar(self.tbFrame)
        self.assertEqual(bar.perspective(), "Test1,Spacer")
