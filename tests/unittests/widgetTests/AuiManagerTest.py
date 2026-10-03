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
from unittest import mock

import test
import wx
from wx import siplib
from taskcoachlib import widgets


class Pane(wx.Panel):
    pass


class AuiManagerTestCase(test.wxTestCase):
    """Every AUI manager goes with its window, and with it what it
    holds: a closed view, an editor's pages (docs/AUI.md)."""

    def setUp(self):
        super().setUp()
        self.window = widgets.AuiManagedFrameWithDynamicCenterPane(None)
        self.manager = self.window.manager
        self.addCleanup(self.window.Destroy)
        self.addCleanup(self.manager.UnInit)
        self.count = 0
        self.add_pane()  # The center pane

    def add_pane(self, floating=False):
        self.count += 1
        pane = Pane(self.window)
        self.window.add_pane(pane, "pane", "pane%d" % self.count, floating)
        return pane


class ActivePaneTest(AuiManagerTestCase):
    """Activating a pane marks the captions for the next paint instead
    of repainting the window once per caption (docs/AUI.md)."""

    def setUp(self):
        super().setUp()
        self.pane = self.add_pane()
        self.add_pane()
        test.settle()  # AUI updates the layout later
        self.refreshed = []
        for name, record in (
            ("Refresh", lambda *args: self.refreshed.append(args)),
            ("Update", mock.Mock()),
        ):
            patcher = mock.patch.object(self.window, name, record)
            patcher.start()
            self.addCleanup(patcher.stop)

    def captions(self):
        return [
            part.rect
            for part in self.manager._uiparts
            if part.type == part.typeCaption
        ]

    def test_no_repaint_at_once(self):
        self.manager.ActivatePane(self.pane)
        self.window.Update.assert_not_called()

    def test_each_caption_marked_for_the_next_paint(self):
        self.manager.ActivatePane(self.pane)
        self.assertTrue(self.captions())
        self.assertEqual(
            [(True, rect) for rect in self.captions()], self.refreshed
        )

    def test_the_pane_is_active(self):
        self.manager.ActivatePane(self.pane)
        self.assertTrue(
            self.manager.GetPane(self.pane).HasFlag(
                self.manager.GetPane(self.pane).optionActive
            )
        )


class FloatingPaneTest(AuiManagerTestCase):
    def setUp(self):
        super().setUp()
        self.pane = self.add_pane(floating=True)
        test.settle()  # AUI updates the layout later
        self.frame_manager = self.manager.GetPane(self.pane).frame._mgr

    def test_closed_it_frees_its_frame_manager(self):
        self.manager.ClosePane(self.manager.GetPane(self.pane))
        test.settle()
        self.assertTrue(siplib.isdeleted(self.frame_manager))

    def test_closed_it_is_freed(self):
        pane = weakref.ref(self.pane)
        self.manager.ClosePane(self.manager.GetPane(self.pane))
        self.pane = self.frame_manager = None
        test.settle()
        self.assertIsNone(pane())

    def test_docked_again_it_frees_its_frame_manager(self):
        self.manager.GetPane(self.pane).Dock()
        self.manager.Update()
        test.settle()
        self.assertTrue(siplib.isdeleted(self.frame_manager))

    def test_docked_again_it_stays(self):
        self.manager.GetPane(self.pane).Dock()
        self.manager.Update()
        test.settle()
        self.assertFalse(siplib.isdeleted(self.pane))


class ClosedPaneTest(AuiManagerTestCase):
    def test_the_last_click_forgets_it(self):
        # A click on a caption leaves the pane in the drag state until
        # the next click
        pane = self.add_pane()
        self.manager._action_window = pane
        self.manager._action_pane = self.manager.GetPane(pane)
        self.manager.ClosePane(self.manager.GetPane(pane))
        self.assertEqual(
            (None, None),
            (self.manager._action_window, self.manager._action_pane),
        )

    def test_the_last_click_on_another_stays(self):
        other = self.add_pane()
        pane = self.add_pane()
        self.manager._action_window = other
        self.manager.ClosePane(self.manager.GetPane(pane))
        self.assertIs(other, self.manager._action_window)


class NotebookTest(AuiManagerTestCase):
    def test_tabbed_panes_free_their_manager(self):
        # AUI makes a notebook when a pane is dropped onto another
        notebook = self.manager.CreateNotebook()
        self.manager._notebooks.remove(notebook)
        notebook_manager = notebook.GetAuiManager()
        notebook.Destroy()
        test.settle()
        self.assertTrue(siplib.isdeleted(notebook_manager))

    def test_an_editor_notebook_frees_its_manager(self):
        # Destroyed with its dialog, not by itself
        parent = wx.Panel(self.frame)
        notebook_manager = widgets.Notebook(parent).GetAuiManager()
        parent.Destroy()
        test.settle()
        self.assertTrue(siplib.isdeleted(notebook_manager))

    def test_an_editor_notebook_frees_its_pages(self):
        parent = wx.Panel(self.frame)
        notebook = widgets.Notebook(parent)
        page = Pane(notebook)
        notebook.AddPage(page, "page")
        page = weakref.ref(page)
        notebook = None
        parent.Destroy()
        test.settle()
        self.assertIsNone(page())
