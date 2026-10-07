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
import urllib.parse
from unittest import mock

import test
import taskcoachlib.mailer
from taskcoachlib import mailer
from taskcoachlib.domain import date

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
    def test_write_mail(self):
        opened = []
        taskcoachlib.mailer.send_mail(
            "to", "subject", "body", open_url=opened.append
        )
        self.assertTrue(opened[0].startswith("mailto:"))


class SendMailLinkTest(test.TestCase):
    """The subject reaches the mail program whole: & and # in it are
    escaped as in the body; on macOS, where the link goes unescaped,
    they become _ (P189)."""

    @staticmethod
    def link(subject, body="body", mac=False):
        opened = []
        with mock.patch(
            "taskcoachlib.operating_system.isMac", return_value=mac
        ):
            mailer.send_mail(
                "to@example.com", subject, body, open_url=opened.append
            )
        return opened[0]

    @staticmethod
    def fields(link):
        """The fields as a mail program reads them (RFC 6068): the
        query split at &, then unescaped."""
        query = urllib.parse.urlsplit(link).query
        return dict(
            (name, urllib.parse.unquote(value))
            for name, value in (
                part.split("=", 1) for part in query.split("&")
            )
        )

    def test_an_ampersand_stays_in_the_subject(self):
        fields = self.fields(self.link("R&D review"))
        self.assertEqual("R&D review", fields["subject"])
        self.assertEqual("body", fields["body"])

    def test_the_subject_adds_no_recipient(self):
        fields = self.fields(self.link("Budget&bcc=someone@example.org"))
        self.assertEqual({"subject", "body"}, set(fields))

    def test_a_hash_stays_in_the_subject(self):
        link = self.link("Issue #12")
        self.assertEqual("", urllib.parse.urlsplit(link).fragment)
        self.assertEqual("Issue #12", self.fields(link)["subject"])

    def test_letters_beyond_ascii_stay_as_they_are(self):
        self.assertIn("Devis%20révisé", self.link("Devis révisé"))

    def test_on_macos_ampersands_and_hashes_become_underscores(self):
        link = self.link("R&D review #12", body="Q&A #3", mac=True)
        self.assertEqual(
            "mailto:to@example.com?subject=R_D review _12&body=Q_A _3", link
        )


class ParseMailTest(test.TestCase):
    """A dropped mail's attachment keeps its subject, sender, sent date
    and a link to it, not the mail (docs/EMAIL_ATTACHMENTS.md)."""

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

    def read_mails(self, data):
        with tempfile.TemporaryDirectory() as folder:
            filename = os.path.join(folder, "dropped")
            with open(filename, "wb") as mail_file:
                mail_file.write(data)
            return mailer.read_mails(filename)

    def test_read_a_mail_file(self):
        self.assertEqual([mailer.parse_mail(MAIL)], self.read_mails(MAIL))

    def test_read_an_mbox_file(self):
        # As Evolution drops mails: a "From " line before each
        other = b"Subject: Second\nMessage-ID: <2@example.com>\n\n>From me\n"
        self.assertEqual(
            ["Devis révisé for the garden", "Second"],
            [
                fields["subject"]
                for fields in self.read_mails(
                    b"From renee@example.com Tue Sep 29 18:05:00 2026\n"
                    + MAIL
                    + b"From - Wed Sep 30 09:15:00 2026\n"
                    + other
                )
            ],
        )

    def test_raw_8_bit_headers(self):
        # RFC 6532: UTF-8 in headers, no encoded words; or Latin-1
        for raw in ("Renée".encode("utf-8"), "Renée".encode("latin-1")):
            fields = mailer.parse_mail(
                b"From: "
                + raw
                + b" <renee@example.com>\nSubject: "
                + raw
                + b"\n\nText\n"
            )
            self.assertEqual(
                ("Renée", "Renée"), (fields["from_name"], fields["subject"])
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
