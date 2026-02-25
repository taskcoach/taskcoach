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
from taskcoachlib import gui, config
from taskcoachlib.gui.uicommand import Separator, Spacer


class ToolBar(gui.toolbar.ToolBar):
    def uiCommands(self, cache=True):
        return []


class ToolBarTest(test.wxTestCase):
    def testAppendUICommand(self):
        gui.init()
        settings = config.Settings(load=False)
        toolbar = ToolBar(self.frame, settings)
        uiCommand = dummy.DummyUICommand(menu_text="undo", bitmap="undo")
        toolId = toolbar.append_ui_command(uiCommand)
        self.assertNotEqual(wx.NOT_FOUND, toolbar.GetToolPos(toolId))


class ToolBarSizeTest(test.wxTestCase):
    def testSizeDefault(self):
        self.createToolBarAndTestSize(None, (32, 32))

    def testSizeSmall(self):
        self.createToolBarAndTestSize((16, 16))

    def testSizeMedium(self):
        self.createToolBarAndTestSize((22, 22))

    def testSizeBig(self):
        self.createToolBarAndTestSize((32, 32))

    def createToolBarAndTestSize(self, size, expectedSize=None):
        settings = config.Settings(load=False)
        toolbarArgs = [self.frame, settings]
        if size:
            toolbarArgs.append(size)
        toolbar = ToolBar(*toolbarArgs)
        if not expectedSize:
            expectedSize = size
        self.assertEqual(wx.Size(*expectedSize), toolbar.GetToolBitmapSize())


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
        self.settings = config.Settings(load=False)

    def tearDown(self):
        self.tbFrame.Close()

    def test_empty(self):
        bar = gui.toolbar.ToolBar(self.tbFrame, self.settings)
        self.assertEqual(bar.perspective(), "Test1,Separator,Test2,Spacer")

    def test_restrict(self):
        self.tbFrame.toolbarPerspective = "Test1,Spacer"
        bar = gui.toolbar.ToolBar(self.tbFrame, self.settings)
        self.assertEqual(bar.perspective(), "Test1,Spacer")

    def test_does_not_exist(self):
        self.tbFrame.toolbarPerspective = "Test1,Spacer,Test3"
        bar = gui.toolbar.ToolBar(self.tbFrame, self.settings)
        self.assertEqual(bar.perspective(), "Test1,Spacer")
