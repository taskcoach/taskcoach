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
from taskcoachlib import gui, config, persistence
from taskcoachlib.domain import note, attachment, category


class NoteViewerTest(test.wxTestCase):
    def setUp(self):
        super().setUp()
        self.settings = config.Settings(load=False)
        self.taskFile = persistence.TaskFile()
        self.note = note.Note()
        self.taskFile.notes().append(self.note)
        self.viewer = gui.viewer.NoteViewer(
            self.frame,
            self.taskFile,
            self.settings,
            notesToShow=self.taskFile.notes(),
        )

    def tearDown(self):
        super().tearDown()
        self.taskFile.close()
        self.taskFile.stop()

    def firstItem(self):
        widget = self.viewer.widget
        return widget.GetFirstChild(widget.GetRootItem())[0]

    def firstItemText(self, column=0):
        return self.viewer.widget.GetItemText(self.firstItem(), column)

    def firstItemIcon(self, column=0):
        return self.viewer.widget.GetItemImage(self.firstItem(), column=column)

    def testLocalNoteViewerForItemWithoutNotes(self):
        localViewer = gui.viewer.NoteViewer(
            self.frame,
            self.taskFile,
            self.settings,
            notesToShow=note.NoteContainer(),
        )
        self.assertFalse(localViewer.presentation())

    def testShowDescriptionColumn(self):
        self.note.setDescription("Description")
        self.viewer.showColumnByName("description")
        self.assertEqual("Description", self.firstItemText(column=1))

    def testShowCategoriesColumn(self):
        newCategory = category.Category("Category")
        self.taskFile.categories().append(newCategory)
        self.note.addCategory(newCategory)
        newCategory.addCategorizable(self.note)
        self.viewer.showColumnByName("categories")
        self.assertEqual("Category", self.firstItemText(column=3))

    def testShowAttachmentColumn(self):
        self.note.addAttachments(attachment.FileAttachment("whatever"))
        self.assertEqual(
            self.viewer.imageIndex["nuvola_status_mail-attachment"],
            self.firstItemIcon(column=2),
        )

    def testFilterOnAllCategories(self):
        cat1 = category.Category("category 1")
        cat2 = category.Category("category 2")
        self.note.addCategory(cat1)
        cat1.addCategorizable(self.note)
        self.taskFile.categories().extend([cat1, cat2])
        cat1.setFiltered(True)
        cat2.setFiltered(True)
        self.assertEqual(1, self.viewer.size())
        self.settings.setboolean("view", "categoryfiltermatchall", True)
        self.assertEqual(0, self.viewer.size())

    def testFilterOnAnyCategory(self):
        cat1 = category.Category("category 1")
        cat2 = category.Category("category 2")
        self.note.addCategory(cat1)
        cat1.addCategorizable(self.note)
        self.taskFile.categories().extend([cat1, cat2])
        cat1.setFiltered(True)
        cat2.setFiltered(True)
        self.assertEqual(1, self.viewer.size())
        self.settings.setboolean("view", "categoryfiltermatchall", False)
        self.assertEqual(1, self.viewer.size())
