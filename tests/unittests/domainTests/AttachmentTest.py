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
    def test_base_and_path_equal(self):
        self.assertEqual("", attachment.getRelativePath("/test", "/test"))

    def test_path_is_sub_dir_of_base(self):
        self.assertEqual(
            "subdir", attachment.getRelativePath("/test/subdir", "/test")
        )

    def test_base_is_sub_dir_of_path(self):
        self.assertEqual(
            "..", attachment.getRelativePath("/test", "/test/subdir")
        )

    def test_base_and_path_are_different(self):
        self.assertEqual(
            os.path.join("..", "bar"),
            attachment.getRelativePath("/bar", "/foo"),
        )


class FileAttachmentTest(test.TestCase):
    def setUp(self):
        self.filename = ""
        self.attachment = attachment.FileAttachment("filename")
        self.events = []

    def open_attachment(self, filename):
        self.filename = filename

    def test_create_file_attachment(self):
        self.assertEqual("filename", self.attachment.location())

    def test_open_file_attachment_with_relative_filename(self):
        self.attachment.open(open_attachment=self.open_attachment)
        self.assertEqual("filename", self.filename)

    def test_open_file_attachment_with_relative_filename_and_working_dir(self):
        self.attachment.open("/home", open_attachment=self.open_attachment)
        self.assertEqual(
            os.path.normpath(os.path.join("/home", "filename")), self.filename
        )

    def test_open_file_attachment_with_absolute_filename_and_working_dir(self):
        att = attachment.FileAttachment("/home/frank/attachment.txt")
        att.open("/home/jerome", open_attachment=self.open_attachment)
        self.assertEqual(
            os.path.normpath(os.path.join("/home/frank/attachment.txt")),
            self.filename,
        )

    def test_copy(self):
        copy = self.attachment.copy()
        self.assertEqual(copy.location(), self.attachment.location())
        self.attachment.setDescription("new")
        self.assertEqual(copy.location(), self.attachment.location())

    def test_location_notification(self):
        self.registerObserver(self.attachment.locationChangedEventType())
        self.attachment.setLocation("new location")
        self.assertIn(self.attachment, self.events[0].sources())

    def test_modification_event_types(self):
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
        with mock.patch.object(openfile, "open_file") as open_file:
            self.mail.open()
        open_file.assert_called_once_with("mid:1@example.com")

    def test_other_attachments_have_no_mail_fields(self):
        link = attachment.URIAttachment("http://example.com")
        self.assertEqual(
            ("", "", date.DateTime()),
            (link.from_name(), link.from_address(), link.sent_datetime()),
        )
