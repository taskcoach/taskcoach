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
from taskcoachlib import gui, persistence, operating_system, render
from taskcoachlib.domain import category, attachment


class DummyEvent(object):
    def Skip(self):  # pragma: no cover
        pass


class CategoryEditorTest(test.wxTestCase):
    def setUp(self):
        super().setUp()
        self.taskFile = persistence.TaskFile()
        self.categories = self.taskFile.categories()
        self.categories.extend(self.createCategories())
        self.editor = gui.dialog.editor.CategoryEditor(
            self.frame,
            list(self.categories),
            self.categories,
            self.taskFile,
        )

    def tearDown(self):
        # CategoryEditor uses CallAfter for setting the focus, make sure those
        # calls are dealt with, otherwise they'll turn up in other tests
        if operating_system.isGTK():
            wx.Yield()  # pragma: no cover
        super().tearDown()
        self.taskFile.close()
        self.taskFile.stop()

    # pylint: disable=E1101,E1103,W0212

    def createCategories(self):
        # pylint: disable=W0201
        self.category = category.Category("Category to edit")
        self.attachment = attachment.FileAttachment("some attachment")
        self.category.addAttachments(self.attachment)
        return [self.category]

    def setSubject(self, new_subject):
        page = self.editor._interior[0]
        page._subjectEntry.SetFocus()
        page._subjectEntry.SetValue(new_subject)
        if operating_system.isGTK():  # pragma: no cover
            page._subjectSync.onAttributeEdited(DummyEvent())
        else:  # pragma: no cover
            page._descriptionEntry.SetFocus()

    def setDescription(self, new_description):
        page = self.editor._interior[0]
        page._descriptionEntry.SetFocus()
        page._descriptionEntry.SetValue(new_description)
        if operating_system.isGTK():  # pragma: no cover
            page._descriptionSync.onAttributeEdited(DummyEvent())
        else:  # pragma: no cover
            page._subjectEntry.SetFocus()

    def test_create(self):
        self.assertEqual(
            "Category to edit",
            self.editor._interior[0]._subjectEntry.GetValue(),
        )

    def test_edit_subject(self):
        self.setSubject("Done")
        self.assertEqual("Done", self.category.subject())

    def test_edit_description(self):
        self.setDescription("Description")
        self.assertEqual("Description", self.category.description())

    def test_add_attachment(self):
        self.editor._interior[2].viewer.on_drop_files(
            self.category, ["filename"]
        )
        self.assertTrue(
            "filename"
            in [att.location() for att in self.category.attachments()]
        )
        self.assertTrue(
            "filename"
            in [att.subject() for att in self.category.attachments()]
        )

    def test_remove_attachment(self):
        self.editor._interior[2].viewer.select(self.category.attachments())
        self.editor._interior[2].viewer.deleteItemCommand().do()
        self.assertEqual([], self.category.attachments())

    def test_edit_mutual_exclusive_subcategories(self):
        self.editor._interior[0]._exclusiveSubcategoriesCheckBox.SetValue(True)
        self.editor._interior[0]._exclusiveSubcategoriesSync.onAttributeEdited(
            DummyEvent()
        )
        self.assertTrue(self.category.hasExclusiveSubcategories())

    def test_style_priority_edit_shows_the_new_modification_date(self):
        page = self.editor._interior[0]
        page._stylePriorityEntry.SetValue(3)
        page._stylePrioritySync.onAttributeEdited(DummyEvent())
        self.assertEqual(3, self.category.stylePriority())
        self.assertEqual(
            render.dateTime(
                self.category.modificationDateTime(), human_readable=True
            ),
            page._modificationTextEntry.GetLabel(),
        )

    def test_add_note(self):
        viewer = self.editor._interior[1].viewer
        viewer.newItemCommand(viewer.presentation()).do()
        self.assertEqual(1, len(self.category.notes()))
