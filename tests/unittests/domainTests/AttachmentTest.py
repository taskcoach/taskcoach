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

import os
import test
from unittest import mock
from taskcoachlib.domain import attachment, date
from taskcoachlib.tools import openfile


class GetRelativePathTest(test.TestCase):
    def testBaseAndPathEqual(self):
        self.assertEqual("", attachment.getRelativePath("/test", "/test"))

    def testPathIsSubDirOfBase(self):
        self.assertEqual(
            "subdir", attachment.getRelativePath("/test/subdir", "/test")
        )

    def testBaseIsSubDirOfPath(self):
        self.assertEqual(
            "..", attachment.getRelativePath("/test", "/test/subdir")
        )

    def testBaseAndPathAreDifferent(self):
        self.assertEqual(
            os.path.join("..", "bar"),
            attachment.getRelativePath("/bar", "/foo"),
        )


class FileAttachmentTest(test.TestCase):
    def setUp(self):
        self.filename = ""
        self.attachment = attachment.FileAttachment("filename")
        self.events = []

    def openAttachment(self, filename):
        self.filename = filename

    def testCreateFileAttachment(self):
        self.assertEqual("filename", self.attachment.location())

    def testOpenFileAttachmentWithRelativeFilename(self):
        self.attachment.open(openAttachment=self.openAttachment)
        self.assertEqual("filename", self.filename)

    def testOpenFileAttachmentWithRelativeFilenameAndWorkingDir(self):
        self.attachment.open("/home", openAttachment=self.openAttachment)
        self.assertEqual(
            os.path.normpath(os.path.join("/home", "filename")), self.filename
        )

    def testOpenFileAttachmentWithAbsoluteFilenameAndWorkingDir(self):
        att = attachment.FileAttachment("/home/frank/attachment.txt")
        att.open("/home/jerome", openAttachment=self.openAttachment)
        self.assertEqual(
            os.path.normpath(os.path.join("/home/frank/attachment.txt")),
            self.filename,
        )

    def testCopy(self):
        copy = self.attachment.copy()
        self.assertEqual(copy.location(), self.attachment.location())
        self.attachment.setDescription("new")
        self.assertEqual(copy.location(), self.attachment.location())

    def testLocationNotification(self):
        self.registerObserver(self.attachment.locationChangedEventType())
        self.attachment.setLocation("new location")
        self.assertIn(self.attachment, self.events[0].sources())

    def testModificationEventTypes(self):
        Attachment = attachment.Attachment
        # pylint: disable=E1101
        self.assertEqual(
            [
                Attachment.notesChangedEventType(),
                Attachment.subjectChangedEventType(),
                Attachment.descriptionChangedEventType(),
                Attachment.appearanceChangedEventType(),
                Attachment.orderingChangedEventType(),
                Attachment.locationChangedEventType(),
            ],
            Attachment.modificationEventTypes(),
        )


class MailAttachmentTest(test.TestCase):
    """A mail's subject, sender, sent date and mid: link, not the mail
    (docs/EMAIL_ATTACHMENTS.md)."""

    def setUp(self):
        super().setUp()
        self.mail = attachment.MailAttachment(
            "mid:1@example.com",
            subject="Quote",
            from_name="Alice",
            from_address="alice@example.com",
            sent_datetime=date.DateTime(2026, 9, 29, 14, 5, 0),
        )

    def test_its_fields_are_one_line_of_text(self):
        # docs/ATTRIBUTE_PATTERN.md, Text
        mail = attachment.MailAttachment(
            "mid:2@example.com\n",
            from_name="Bob\x00\tSmith",
            from_address="bob@example.com\r\n",
        )
        self.assertEqual(
            ("mid:2@example.com ", "Bob Smith", "bob@example.com "),
            (mail.location(), mail.from_name(), mail.from_address()),
        )

    def fields(self, mail):
        return (
            mail.location(),
            mail.subject(),
            mail.from_name(),
            mail.from_address(),
            mail.sent_datetime(),
        )

    def test_a_new_mail_has_no_sender_nor_date(self):
        mail = attachment.MailAttachment("mid:2@example.com")
        self.assertEqual(
            ("", "", date.DateTime()),
            (mail.from_name(), mail.from_address(), mail.sent_datetime()),
        )

    def test_copy(self):
        self.assertEqual(self.fields(self.mail), self.fields(self.mail.copy()))

    def test_open_hands_the_link_to_the_system(self):
        with mock.patch.object(openfile, "openFile") as open_file:
            self.mail.open()
        open_file.assert_called_once_with("mid:1@example.com")

    def test_other_attachments_have_no_mail_fields(self):
        link = attachment.URIAttachment("http://example.com")
        self.assertEqual(
            ("", "", date.DateTime()),
            (link.from_name(), link.from_address(), link.sent_datetime()),
        )
