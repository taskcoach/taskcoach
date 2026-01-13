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
from taskcoachlib import gui, config, persistence
from taskcoachlib.domain import note, base
from unittests import dummy


class EditorUnderTest(gui.dialog.editor.NoteEditor):
    def __init__(self, *args, **kwargs):
        kwargs["call_after"] = lambda f, *args, **kwargs: f(*args, **kwargs)
        super().__init__(*args, **kwargs)
        self.editorClosed = False

    def on_close_editor(self, event):
        self.editorClosed = True
        super().on_close_editor(event)


class EditorTestCase(test.wxTestCase):
    def setUp(self):
        super().setUp()
        self.settings = config.Settings(load=False)
        self.taskFile = persistence.TaskFile()
        self.items = base.filter.SearchFilter(self.taskFile.notes())
        self.item = note.Note(subject="item")
        self.items.append(self.item)
        self.editor = EditorUnderTest(
            self.frame, [self.item], self.settings, self.items, self.taskFile
        )
        self.appearance = self.editor._interior[-1]

    def tearDown(self):
        super().tearDown()
        self.taskFile.close()
        self.taskFile.stop()

    def testCloseEditorWhenItemIsDeleted(self):
        self.items.remove(self.item)
        self.assertTrue(self.editor.editorClosed)

    def testDontCloseEditorWhenItemIsFiltered(self):
        self.items.setSearchFilter("abc")
        self.assertFalse(self.editor.editorClosed)

    def testVeryLongSubject(self):
        longSubject = "Subject" * 1000
        self.item.setSubject(longSubject)
        self.assertEqual(
            longSubject, self.editor._interior[0]._subjectEntry.GetValue()
        )

    def testThatPickingAForegroundColorChangesTheItemForegroundColor(self):
        self.appearance._foregroundColorEntry.SetValue(wx.RED)
        self.appearance._foregroundColorSync.onAttributeEdited(dummy.Event())
        self.assertEqual(wx.RED, self.item.foregroundColor())

    def testThatChangingTheItemForegroundColorAffectsTheForegroundColorButton(
        self,
    ):
        self.item.setForegroundColor(wx.RED)
        self.assertEqual(
            wx.RED, self.appearance._foregroundColorEntry.GetValue()
        )

    def testThatPickingABackgroundColorChangesTheItemBackgroundColor(self):
        self.appearance._backgroundColorEntry.SetValue(wx.RED)
        self.appearance._backgroundColorSync.onAttributeEdited(dummy.Event())
        self.assertEqual(wx.RED, self.item.backgroundColor())

    def testThatChangingTheItemBackgroundColorAffectsTheBackgroundColorButton(
        self,
    ):
        self.item.setBackgroundColor(wx.RED)
        self.assertEqual(
            wx.RED, self.appearance._backgroundColorEntry.GetValue()
        )

    def testThatPickingAFontChangesTheItemFont(self):
        font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
        font.SetPointSize(font.GetPointSize() + 1)
        self.appearance._fontEntry.SetValue(font)
        self.appearance._fontSync.onAttributeEdited(dummy.Event())
        self.assertEqual(font, self.item.font())

    def testThatChangingTheItemFontAffectsTheFontButton(self):
        font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
        font.SetPointSize(font.GetPointSize() + 1)
        self.item.setFont(font)
        self.assertEqual(font, self.appearance._fontEntry.GetValue())

    def testThatPickingAColoredFontChangesTheItemColor(self):
        self.appearance._fontEntry.SetColor(wx.RED)
        self.appearance._fontColorSync.onAttributeEdited(dummy.Event())
        self.assertEqual(wx.RED, self.item.foregroundColor())

    def testThatChangingTheItemColorAffectsTheFontButton(self):
        self.item.setForegroundColor(wx.RED)
        self.assertEqual(wx.RED, self.appearance._fontEntry.GetColor())

    def testThatPickingAColoredFontChangesTheColorButton(self):
        self.appearance._fontEntry.SetColor(wx.RED)
        self.appearance._fontColorSync.onAttributeEdited(dummy.Event())
        self.assertEqual(
            wx.RED, self.appearance._foregroundColorEntry.GetValue()
        )

    def testThatPickingAColorChangesTheFontButtonColor(self):
        self.appearance._foregroundColorEntry.SetValue(wx.RED)
        self.appearance._foregroundColorSync.onAttributeEdited(dummy.Event())
        self.assertEqual(wx.RED, self.appearance._fontEntry.GetColor())

    def testThatPickingAnIconChangesTheItemIcon(self):
        self.appearance._iconEntry.SetValue("bomb_icon")
        self.appearance._iconSync.onAttributeEdited(dummy.Event())
        self.assertEqual("bomb_icon", self.item.icon())

    def testThatChangingTheItemIconAffectsTheIconEntry(self):
        imageNames = sorted(gui.artprovider.chooseableItemImages.keys())
        self.item.setIcon(imageNames[10])
        self.assertEqual(10, self.appearance._iconEntry.GetSelection())
