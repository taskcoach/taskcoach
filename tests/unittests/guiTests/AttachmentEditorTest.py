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
import wx
from taskcoachlib import gui, config, persistence, operating_system
from taskcoachlib.domain import attachment, date


class DummyEvent(object):
    def Skip(self):  # pragma: no cover
        pass


class AttachmentEditorTest(test.wxTestCase):
    def setUp(self):
        super().setUp()
        self.settings = config.settings.current()
        self.taskFile = persistence.TaskFile()
        self.attachment = attachment.FileAttachment("Attachment")
        self.attachments = attachment.AttachmentList()
        self.attachments.append(self.attachment)
        self.editor = gui.dialog.editor.AttachmentEditor(
            self.frame,
            self.attachments,
            self.settings,
            self.attachments,
            self.taskFile,
        )

    def tearDown(self):
        super().tearDown()
        self.taskFile.close()
        self.taskFile.stop()

    def setSubject(self, newSubject):
        page = self.editor._interior[0]
        page._subjectEntry.SetFocus()
        page._subjectEntry.SetValue(newSubject)
        if operating_system.isGTK():  # pragma: no cover
            page._subjectSync.onAttributeEdited(DummyEvent())
        else:  # pragma: no cover
            page._descriptionEntry.SetFocus()

    def setDescription(self, newDescription):
        page = self.editor._interior[0]
        page._descriptionEntry.SetFocus()
        page._descriptionEntry.SetValue(newDescription)
        if operating_system.isGTK():  # pragma: no cover
            page._descriptionSync.onAttributeEdited(DummyEvent())
        else:  # pragma: no cover
            page._subjectEntry.SetFocus()

    def testCreate(self):
        # pylint: disable=W0212
        self.assertEqual(
            "Attachment", self.editor._interior[0]._subjectEntry.GetValue()
        )

    def testEditSubject(self):
        self.setSubject("Done")
        self.assertEqual("Done", self.attachment.subject())

    def testEditDescription(self):
        self.setDescription("Description")
        self.assertEqual("Description", self.attachment.description())

    def testAddNote(self):
        viewer = self.editor._interior[1].viewer
        viewer.newItemCommand(viewer.presentation()).do()
        self.assertEqual(
            1, len(self.attachment.notes())
        )  # pylint: disable=E1101


class MailAttachmentEditorTest(test.wxTestCase):
    """A mail's fields show the mail as it is: only the description
    can change (docs/EMAIL_ATTACHMENTS.md)."""

    def setUp(self):
        super().setUp()
        self.settings = config.settings.current()
        self.taskFile = persistence.TaskFile()
        self.mail = attachment.MailAttachment(
            "mid:1@example.com",
            subject="Quote",
            from_name="Alice",
            from_address="alice@example.com",
            sent_datetime=date.DateTime(2026, 9, 29, 14, 5, 0),
        )
        self.attachments = attachment.AttachmentList([self.mail])
        self.editor = gui.dialog.editor.AttachmentEditor(
            self.frame,
            self.attachments,
            self.settings,
            self.attachments,
            self.taskFile,
        )
        # pylint: disable=W0212
        self.page = self.editor._interior[0]

    def tearDown(self):
        super().tearDown()
        self.taskFile.close()
        self.taskFile.stop()

    def test_the_mail_fields_are_read_only(self):
        entries = (
            self.page._subjectEntry,
            self.page._locationEntry,
            self.page._from_name_entry,
            self.page._from_address_entry,
        )
        # Drawn as text, not in input boxes
        self.assertEqual(
            ["Quote", "mid:1@example.com", "Alice", "alice@example.com"],
            [entry.GetLabel() for entry in entries],
        )
        for entry in entries:
            self.assertIsInstance(entry, wx.StaticText)

    def test_the_description_can_change(self):
        entries = self.page.entries()
        for name in ("firstEntry", "subject"):
            self.assertIs(self.page._descriptionEntry, entries[name])
        self.page._descriptionEntry.SetValue("Call Alice back")
        self.page._descriptionSync.onAttributeEdited(DummyEvent())
        self.assertEqual("Call Alice back", self.mail.description())
