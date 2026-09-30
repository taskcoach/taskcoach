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

# Each mail program's drag, per system, as wx hands it to Task
# Coach's drop target: the format chosen and its data
# (docs/EMAIL_ATTACHMENTS.md, The Drop, with the sources).
# tools/fake_mail_drag.py drags the same from a window, for the whole
# application.

import os
import tempfile
from unittest import mock

import test
import wx
from taskcoachlib import mailer
from taskcoachlib.mailer import outlook, thunderbird
from taskcoachlib.widgets import draganddrop


def mail(subject, message_id, crlf=False):
    """A mail as a mail program stores it."""
    text = (
        "From: Alice Martin <alice@example.com>\n"
        "Date: Tue, 29 Sep 2026 14:05:00 -0400\n"
        "Subject: %s\n"
        "Message-ID: <%s>\n\nText.\n" % (subject, message_id)
    )
    return text.replace("\n", "\r\n" if crlf else "\n").encode()


def mbox(*mails):
    """Mails as Evolution drags them: an mbox file, a From line before
    each mail."""
    return b"".join(
        b"From alice@example.com Tue Sep 29 18:05:00 2026\n" + each
        for each in mails
    )


class DropTestCase(test.wxTestCase):
    def setUp(self):
        super().setUp()
        self.mails, self.files, self.urls = [], [], []
        self.target = draganddrop.DropTarget(
            lambda x, y, url: self.urls.append(url),
            lambda x, y, files: self.files.extend(files),
            lambda x, y, mails: self.mails.append(mails),
        )
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = folder.name
        # The system's temporary folder, apart from the rest
        self.system_temp = self.path("systemtemp")
        os.makedirs(self.system_temp)
        patcher = mock.patch.object(
            tempfile, "gettempdir", return_value=self.system_temp
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def path(self, *parts):
        return os.path.join(self.root, *parts)

    def write(self, data, *parts):
        filename = self.path(*parts)
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, "wb") as file:
            file.write(data)
        return filename

    def drop_files(self, *filenames):
        for filename in filenames:
            self.target._file_data.AddFile(filename)
        self.target.dispatch(0, 0, wx.DF_FILENAME, "text/uri-list")

    def drop_text(self, text):
        self.target._text_data.SetText(text)
        self.target.dispatch(0, 0, wx.DF_UNICODETEXT, None)

    def drop_mac_url(self, url):
        self.target._url_data.SetData(url.encode())
        self.target.dispatch(0, 0, wx.DF_PRIVATE, "public.url")

    def subjects(self):
        return [[fields["subject"] for fields in drop] for drop in self.mails]


class EvolutionTest(DropTestCase):
    """Evolution (Linux) drags one mbox file with every mail: a
    text/uri-list after x-uid-list, which wx does not take."""

    def test_3_56(self):
        # /tmp/drag-n-drop-XXXXXX/<date>_<subject>.mbox
        self.drop_files(
            self.write(
                mbox(mail("Quote", "1@example.com")),
                "systemtemp",
                "drag-n-drop-Q3ZK1P",
                "20260929140500_Quote.mbox",
            )
        )
        self.assertEqual([["Quote"]], self.subjects())
        self.assertEqual([], self.files)

    def test_several_mails_3_44_to_3_55(self):
        # No .mbox before 3.56; the folder's name for several mails
        self.drop_files(
            self.write(
                mbox(mail("Quote", "1@x"), mail("Invoice", "2@x")),
                "systemtemp",
                "drag-n-drop-A1B2C3",
                "Messages from Inbox",
            )
        )
        self.assertEqual([["Quote", "Invoice"]], self.subjects())

    def test_before_3_44(self):
        # ~/.cache/evolution/tmp/drag-n-drop-XXXXXX/
        self.drop_files(
            self.write(
                mbox(mail("Quote", "1@x")),
                "home",
                ".cache",
                "evolution",
                "tmp",
                "drag-n-drop-X1Y2Z3",
                "20260929140500_Quote",
            )
        )
        self.assertEqual([["Quote"]], self.subjects())

    def test_flatpak(self):
        # Straight into the sandbox's cache tmp folder
        self.drop_files(
            self.write(
                mbox(mail("Quote", "1@x")),
                "home",
                ".var",
                "app",
                "org.gnome.Evolution",
                "cache",
                "evolution",
                "tmp",
                "20260929140500_Quote.mbox",
            )
        )
        self.assertEqual([["Quote"]], self.subjects())


class ThunderbirdTest(DropTestCase):
    """Thunderbird drags each message's URI as text, a text/uri-list of
    .eml files it writes to the temporary folder, and more that wx does
    not take; it no longer offers text/x-moz-message to other programs
    (since 52)."""

    def setUp(self):
        super().setUp()
        patcher = mock.patch.object(
            thunderbird,
            "get_mail",
            side_effect=lambda uri: mailer.mail_fields(
                uri.rsplit("#", 1)[-1], "", "", None, ""
            ),
        )
        self.get_mail = patcher.start()
        self.addCleanup(patcher.stop)

    def test_linux_x11_one_message(self):
        # text/plain comes first: the message's URI
        self.drop_text("mailbox-message://nobody@Local%20Folders/Inbox#1234")
        self.get_mail.assert_called_once_with(
            "mailbox-message://nobody@Local%20Folders/Inbox#1234"
        )
        self.assertEqual([["1234"]], self.subjects())

    def test_linux_wayland_or_several_messages(self):
        # The order reversed on Wayland, and several messages give only
        # an internal list and text/uri-list: .eml files in dnd_file*
        self.drop_files(
            self.write(
                mail("Quote", "1@x", crlf=True),
                "systemtemp",
                "dnd_file",
                "Quote.eml",
            ),
            self.write(
                mail("Invoice", "2@x", crlf=True),
                "systemtemp",
                "dnd_file-1",
                "Invoice.eml",
            ),
        )
        self.assertEqual([["Quote", "Invoice"]], self.subjects())

    def test_windows_one_message(self):
        # Windows takes our first format the source offers: text
        self.drop_text(
            "imap-message://alice%40example.com@imap.example.com/INBOX#77"
        )
        self.assertEqual([["77"]], self.subjects())

    def test_windows_several_messages(self):
        # The URIs concatenated, with no separator
        self.drop_text(
            "mailbox-message://nobody@Local%20Folders/Inbox#1"
            "mailbox-message://nobody@Local%20Folders/Inbox#2"
        )
        self.assertEqual([["1", "2"]], self.subjects())

    def test_macos(self):
        # public.url: the message's URL
        self.drop_mac_url(
            "mailbox:///Users/alice/Library/Thunderbird/Profiles/p/Mail/"
            "Local%20Folders/Inbox?number=5#5"
        )
        self.assertEqual(1, len(self.mails))


class ClawsMailTest(DropTestCase):
    """Claws Mail (Linux) drags a text/uri-list: one file per mail in
    its tmp folder, the mail with no From line."""

    def test_linux(self):
        self.drop_files(
            self.write(
                mail("Quote", "1@x"),
                "home",
                ".claws-mail",
                "tmp",
                "Quote.42.txt",
            ),
            self.write(
                mail("Invoice", "2@x"),
                "home",
                ".claws-mail",
                "tmp",
                "Invoice.43.txt",
            ),
        )
        self.assertEqual([["Quote", "Invoice"]], self.subjects())

    def test_another_settings_folder(self):
        # --alternate-config-dir: its tmp folder
        self.drop_files(
            self.write(
                mail("Quote", "1@x"),
                "home",
                "claws-work",
                "tmp",
                "Quote.42.txt",
            )
        )
        self.assertEqual([["Quote"]], self.subjects())

    def test_mail_without_subject(self):
        # The mail's own file in the mail folder: attached as a file
        filename = self.write(mail("", "1@x"), "home", "Mail", "inbox", "123")
        self.drop_files(filename)
        self.assertEqual(([], [filename]), (self.mails, self.files))


class OutlookTest(DropTestCase):
    """Outlook (classic, Windows) drags FileGroupDescriptorW,
    FileContents (IStorage, which wx cannot read) and its RenPrivate
    formats; Task Coach asks the running Outlook for the dragged
    mails."""

    def test_windows(self):
        with mock.patch.object(
            outlook,
            "get_current_selection",
            return_value=[mailer.mail_fields("Quote", "", "", None, "1@x")],
        ):
            self.target.dispatch(0, 0, wx.DF_PRIVATE, outlook.OUTLOOK_FORMAT)
        self.assertEqual([["Quote"]], self.subjects())


class AppleMailTest(DropTestCase):
    """Apple Mail (macOS) drags a message: link; it stays a link
    attachment."""

    def test_macos(self):
        self.drop_mac_url("message:%3C1@example.com%3E")
        self.assertEqual(
            ([], ["message:%3C1@example.com%3E"]), (self.mails, self.urls)
        )


class KMailTest(DropTestCase):
    """KMail (Linux) drags akonadi: links only, which wx refuses in a
    text/uri-list: nothing is dropped."""

    def test_linux(self):
        self.drop_files()
        self.assertEqual(([], [], []), (self.mails, self.files, self.urls))


class NotMailTest(DropTestCase):
    """What is not a mail program's drag stays a file or a link."""

    def test_a_saved_mail_is_a_file(self):
        filename = self.write(
            mail("Quote", "1@x"), "home", "Documents", "Quote.eml"
        )
        self.drop_files(filename)
        self.assertEqual(([], [filename]), (self.mails, self.files))

    def test_a_temporary_file_that_is_not_a_mail(self):
        filename = self.write(b"Shopping list\n", "systemtemp", "list.txt")
        self.drop_files(filename)
        self.assertEqual(([], [filename]), (self.mails, self.files))

    def test_text_with_a_message_link_inside(self):
        self.drop_text("see mailbox-message://nobody@Local%20Folders/Inbox#1")
        self.assertEqual([], self.mails)

    def test_a_web_address(self):
        self.drop_text("example.com")
        self.assertEqual(["http://example.com"], self.urls)
