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

import datetime
import os
import tempfile
from unittest import mock

import test
import taskcoachlib.mailer
from taskcoachlib import mailer
from taskcoachlib.domain import date
from taskcoachlib.mailer import thunderbird

MAIL = b"""\
From: =?UTF-8?Q?Ren=C3=A9e_Martin?= <renee@example.com>
To: Bob <bob@example.com>
Subject: =?UTF-8?Q?Devis_r=C3=A9vis=C3=A9?= for the
 garden
Date: Tue, 29 Sep 2026 14:05:00 -0400
Message-ID: <20260929140500.12345@mail.example.com>
MIME-Version: 1.0
Content-Type: text/plain; charset="utf-8"
Content-Transfer-Encoding: quoted-printable

Bonjour Bob, voici le devis r=C3=A9vis=C3=A9.
"""


def local(*args, offset_hours):
    """A mail's date in local time, as its attachment keeps it."""
    zone = datetime.timezone(datetime.timedelta(hours=offset_hours))
    sent = datetime.datetime(*args, tzinfo=zone).astimezone()
    return date.DateTime.fromDateTime(sent)


class TestMailer(test.TestCase):
    def testWriteMail(self):
        def openURL(mailtoString):
            self.mailtoString = mailtoString  # pylint: disable=W0201

        taskcoachlib.mailer.sendMail("to", "subject", "body", openURL=openURL)
        self.assertTrue(self.mailtoString.startswith("mailto:"))


class ParseMailTest(test.TestCase):
    """A dropped mail's attachment keeps its subject, sender, sent date
    and a link to it, not the mail (docs/ATTACHMENTS.md)."""

    def test_fields(self):
        self.assertEqual(
            dict(
                location="mid:20260929140500.12345@mail.example.com",
                subject="Devis révisé for the garden",
                from_name="Renée Martin",
                from_address="renee@example.com",
                sent_datetime=local(2026, 9, 29, 14, 5, 0, offset_hours=-4),
            ),
            mailer.parse_mail(MAIL),
        )

    def test_read_from_a_file(self):
        with tempfile.TemporaryDirectory() as folder:
            filename = os.path.join(folder, "dropped.eml")
            with open(filename, "wb") as mail_file:
                mail_file.write(MAIL)
            self.assertEqual(
                mailer.parse_mail(MAIL), mailer.read_mail(filename)
            )

    def test_an_address_without_a_name(self):
        fields = mailer.parse_mail(b"From: alerts@example.com\n\nBody\n")
        self.assertEqual(
            ("", "alerts@example.com"),
            (fields["from_name"], fields["from_address"]),
        )

    def test_missing_headers_are_empty(self):
        self.assertEqual(
            dict(
                location="",
                subject="",
                from_name="",
                from_address="",
                sent_datetime=date.DateTime(),
            ),
            mailer.parse_mail(b"\nBody\n"),
        )

    def test_an_unreadable_date_is_not_set(self):
        fields = mailer.parse_mail(b"Date: sometime soon\n\nBody\n")
        self.assertEqual(date.DateTime(), fields["sent_datetime"])

    def test_the_link_escapes_what_a_url_cannot_hold(self):
        fields = mailer.parse_mail(
            b"Message-ID: <CA+x=y$z/w%#1@mail.example.com>\n\nBody\n"
        )
        self.assertEqual(
            "mid:CA+x=y$z/w%25%231@mail.example.com", fields["location"]
        )


class ThunderbirdTest(test.TestCase):
    """A mail dragged from Thunderbird is read from its profile's
    mailbox files."""

    def setUp(self):
        super().setUp()
        self.home = tempfile.TemporaryDirectory()
        self.addCleanup(self.home.cleanup)
        profile = os.path.join(self.home.name, ".thunderbird", "p.default")
        self.folder = os.path.join(profile, "Mail", "Local Folders")
        os.makedirs(self.folder)
        with open(
            os.path.join(self.home.name, ".thunderbird", "profiles.ini"), "w"
        ) as ini:
            ini.write(
                "[Profile0]\nName=default\nIsRelative=1\n"
                "Path=p.default\nDefault=1\n"
            )
        with open(os.path.join(profile, "prefs.js"), "w") as prefs:
            prefs.write(
                'user_pref("mail.server.server1.userName", "nobody");\n'
                'user_pref("mail.server.server1.hostname", '
                '"Local Folders");\n'
                'user_pref("mail.server.server1.directory-rel", '
                '"[ProfD]Mail/Local Folders");\n'
            )
        first = b"From - Mon Sep 28 10:00:00 2026\nSubject: First\n\nOne\n"
        self.offset = len(first)
        with open(os.path.join(self.folder, "Inbox"), "wb") as inbox:
            inbox.write(first + b"From - Tue Sep 29 14:05:00 2026\n" + MAIL)
        patcher = mock.patch.dict(os.environ, HOME=self.home.name)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_a_local_folder_mail(self):
        self.assertEqual(
            mailer.parse_mail(MAIL)["location"],
            thunderbird.getMail(
                "mailbox-message://nobody@Local%%20Folders/Inbox#%d"
                % self.offset
            )["location"],
        )

    def test_a_mailbox_mail(self):
        self.assertEqual(
            mailer.parse_mail(MAIL)["subject"],
            thunderbird.getMail(
                "mailbox://%s?number=%d"
                % (os.path.join(self.folder, "Inbox"), self.offset)
            )["subject"],
        )
