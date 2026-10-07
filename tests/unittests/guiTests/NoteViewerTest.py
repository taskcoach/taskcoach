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
from taskcoachlib import command, gui, persistence
from taskcoachlib.gui.icons import image_list_cache
from taskcoachlib.domain import note, attachment, category
from taskcoachlib.config import settings


class NoteViewerTest(test.wxTestCase):
    def setUp(self):
        super().setUp()
        self.taskFile = persistence.TaskFile()
        self.note = note.Note()
        self.taskFile.notes().append(self.note)
        self.viewer = gui.viewer.NoteViewer(
            self.frame,
            self.taskFile,
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

    def test_local_note_viewer_for_item_without_notes(self):
        local_viewer = gui.viewer.NoteViewer(
            self.frame,
            self.taskFile,
            notesToShow=note.NoteContainer(),
        )
        self.assertFalse(local_viewer.presentation())

    def test_the_editor_pastes_every_note(self):
        owner = category.Category("owner")
        local_viewer = gui.dialog.editor.LocalNoteViewer(
            self.frame, self.taskFile, owner=owner
        )
        copied = [note.Note(subject="a"), note.Note(subject="b")]
        command.Clipboard().put(copied, self.taskFile.notes())
        self.addCleanup(command.Clipboard().clear)
        local_viewer.pasteItemCommand().do()
        self.assertEqual(
            ["a", "b"], [each.subject() for each in owner.notes()]
        )

    def test_show_description_column(self):
        self.note.setDescription("Description")
        self.viewer.showColumnByName("description")
        self.assertEqual("Description", self.firstItemText(column=1))

    def test_show_categories_column(self):
        new_category = category.Category("Category")
        self.taskFile.categories().append(new_category)
        self.note.addCategory(new_category)
        self.viewer.showColumnByName("categories")
        self.assertEqual("Category", self.firstItemText(column=3))

    def test_show_attachment_column(self):
        self.note.addAttachments(attachment.FileAttachment("whatever"))
        self.assertEqual(
            image_list_cache.get_index("nuvola_status_mail-attachment"),
            self.firstItemIcon(column=2),
        )

    def test_filter_on_all_categories(self):
        cat1 = category.Category("category 1")
        cat2 = category.Category("category 2")
        self.note.addCategory(cat1)
        self.taskFile.categories().extend([cat1, cat2])
        cat1.setFiltered(True)
        cat2.setFiltered(True)
        self.assertEqual(1, self.viewer.size())
        settings.set("view", "categoryfiltermatchall", True)
        self.assertEqual(0, self.viewer.size())

    def test_filter_on_any_category(self):
        cat1 = category.Category("category 1")
        cat2 = category.Category("category 2")
        self.note.addCategory(cat1)
        self.taskFile.categories().extend([cat1, cat2])
        cat1.setFiltered(True)
        cat2.setFiltered(True)
        self.assertEqual(1, self.viewer.size())
        settings.set("view", "categoryfiltermatchall", False)
        self.assertEqual(1, self.viewer.size())
