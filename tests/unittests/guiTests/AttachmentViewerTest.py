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
from taskcoachlib import gui, config, persistence
from taskcoachlib.gui.icons import image_list_cache
from taskcoachlib.domain import attachment, date


class AttachmentViewerTest(test.wxTestCase):
    def setUp(self):
        settings = config.settings.current()
        self.taskFile = persistence.TaskFile()
        attachments = attachment.AttachmentList()
        self.viewer = gui.viewer.AttachmentViewer(
            self.frame,
            self.taskFile,
            settings,
            attachmentsToShow=attachments,
            settingsSection="attachmentviewer",
        )

    def tearDown(self):
        super().tearDown()
        self.taskFile.close()
        self.taskFile.stop()

    def assertIcon(self, expectedIcon, anAttachment, **kwargs):
        self.assertEqual(
            image_list_cache.get_index(expectedIcon),
            self.viewer.typeImageIndices(anAttachment, **kwargs)[
                wx.TreeItemIcon_Normal
            ],
        )

    def testTypeImageIndex_WhenFileDoesNotExist(self):
        fileAttachment = attachment.FileAttachment("whatever")
        self.assertIcon("taskcoach_actions_fileopen_red", fileAttachment)

    def testTypeImageIndex_WhenFileDoesExist(self):
        fileAttachment = attachment.FileAttachment("whatever")
        self.assertIcon(
            "nuvola_mimetypes_application-x-dvi",
            fileAttachment,
            exists=lambda filename: True,
        )

    def testTypeImageIndex_UriAttachment(self):
        uriAttachment = attachment.URIAttachment("http://whatever.we")
        self.assertIcon(
            "nuvola_categories_applications-internet", uriAttachment
        )

    def test_type_image_index_of_a_mail(self):
        mail_attachment = attachment.MailAttachment("mid:1@example.com")
        self.assertIcon("nuvola_apps_email", mail_attachment)


class AttachmentViewerMailColumnsTest(test.wxTestCase):
    """A mail's fields have their own columns, shown by default with
    every other column but the ID (docs/ATTACHMENTS.md)."""

    def setUp(self):
        super().setUp()
        self.settings = config.settings.current()
        self.taskFile = persistence.TaskFile()
        self.early = attachment.MailAttachment(
            "mid:2@example.com",
            subject="Quote",
            from_name="Zoe",
            from_address="zoe@example.com",
            sent_datetime=date.DateTime(2026, 9, 1, 8, 0, 0),
        )
        self.late = attachment.MailAttachment(
            "mid:1@example.com",
            subject="Invoice",
            from_name="Alice",
            from_address="alice@example.com",
            sent_datetime=date.DateTime(2026, 9, 29, 14, 5, 0),
        )
        self.link = attachment.URIAttachment("http://example.com")
        self.attachments = attachment.AttachmentList(
            [self.late, self.link, self.early]
        )
        self.viewer = gui.viewer.AttachmentViewer(
            self.frame,
            self.taskFile,
            self.settings,
            attachmentsToShow=self.attachments,
            settingsSection="attachmentviewer",
        )

    def tearDown(self):
        super().tearDown()
        self.taskFile.close()
        self.taskFile.stop()

    def column(self, name):
        return [c for c in self.viewer.columns() if c.name() == name][0]

    def sorted_by(self, key):
        self.viewer.sortBy(key)
        self.viewer.setSortOrderAscending(True)
        return list(self.viewer.presentation())

    def test_every_column_but_the_id_shows_by_default(self):
        self.assertEqual(
            [
                "type",
                "subject",
                "location",
                "fromName",
                "fromAddress",
                "sentDateTime",
                "description",
                "notes",
                "creationDateTime",
                "modificationDateTime",
            ],
            [column.name() for column in self.viewer.visibleColumns()],
        )

    def test_mail_columns(self):
        self.assertEqual(
            ["mid:1@example.com", "Alice", "alice@example.com"],
            [
                self.column(name).render(self.late)
                for name in ("location", "fromName", "fromAddress")
            ],
        )
        self.assertTrue(self.column("sentDateTime").render(self.late))

    def test_a_link_has_no_mail_fields(self):
        self.assertEqual(
            ["", "", ""],
            [
                self.column(name).render(self.link)
                for name in ("fromName", "fromAddress", "sentDateTime")
            ],
        )

    def test_sort_by_sent_date(self):
        self.assertEqual(
            [self.early, self.late, self.link],
            self.sorted_by("sentDateTime"),
        )

    def test_sort_by_sender(self):
        self.assertEqual(
            [self.link, self.late, self.early], self.sorted_by("fromName")
        )

    def test_sort_by_location(self):
        self.assertEqual(
            [self.link, self.late, self.early], self.sorted_by("location")
        )
