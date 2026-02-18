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

import test, wx
from taskcoachlib import gui, config, persistence
from taskcoachlib.domain import attachment


class AttachmentViewerTest(test.wxTestCase):
    def setUp(self):
        settings = config.Settings(load=False)
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
            self.viewer.imageIndex[expectedIcon],
            self.viewer.typeImageIndices(anAttachment, **kwargs)[
                wx.TreeItemIcon_Normal
            ],
        )

    def testTypeImageIndex_WhenFileDoesNotExist(self):
        fileAttachment = attachment.FileAttachment("whatever")
        self.assertIcon("fileopen_red", fileAttachment)

    def testTypeImageIndex_WhenFileDoesExist(self):
        fileAttachment = attachment.FileAttachment("whatever")
        self.assertIcon(
            "fileopen", fileAttachment, exists=lambda filename: True
        )

    def testTypeImageIndex_UriAttachment(self):
        uriAttachment = attachment.URIAttachment("http://whatever.we")
        self.assertIcon("nuvola_categories_applications-internet", uriAttachment)

    def testTypeImgeIndex_MailAttachment(self):
        mailAttachment = attachment.MailAttachment(
            "", readMail=lambda location: ("", "")
        )
        self.assertIcon("nuvola_apps_email", mailAttachment)
