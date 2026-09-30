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

import email
import email.policy
import urllib.parse

from taskcoachlib import operating_system
from taskcoachlib.domain import date
from taskcoachlib.tools import openfile

# Kept in a mid: link's Message-ID (RFC 2392): what a URL allows,
# other characters escaped
_MID_SAFE = "@!$&'()*+,;=:/~"


def read_mail(filename):
    """The fields of a dropped mail's attachment, from the mail file
    the mail program left (docs/ATTACHMENTS.md)."""
    with open(filename, "rb") as mail_file:
        return parse_mail(mail_file.read())


def parse_mail(data):
    """The fields of a mail's attachment, from the mail's bytes."""
    message = email.message_from_bytes(data, policy=email.policy.default)
    sender = message["from"]
    addresses = getattr(sender, "addresses", ())
    sent = message["date"]
    return mail_fields(
        subject=str(message["subject"] or ""),
        from_name=addresses[0].display_name if addresses else "",
        from_address=addresses[0].addr_spec if addresses else "",
        sent=getattr(sent, "datetime", None),
        message_id=str(message["message-id"] or ""),
    )


def mail_fields(subject, from_name, from_address, sent, message_id):
    """A mail attachment's fields: the sent date in local time, the
    Message-ID as a mid: link."""
    if sent is None:
        sent_datetime = date.DateTime()
    else:
        if sent.tzinfo is not None:
            sent = sent.astimezone().replace(tzinfo=None)
        sent_datetime = date.DateTime.fromDateTime(sent)
    message_id = message_id.strip().strip("<>")
    return dict(
        location=(
            "mid:" + urllib.parse.quote(message_id, safe=_MID_SAFE)
            if message_id
            else ""
        ),
        subject=subject.strip(),
        from_name=from_name.strip(),
        from_address=from_address.strip(),
        sent_datetime=sent_datetime,
    )


def sendMail(to, subject, body, cc=None, openURL=openfile.openFile):
    def unicode_quote(s):
        # This is like urllib.quote but leaves out Unicode characters,
        # which urllib.quote does not support.
        chars = [c if ord(c) >= 128 else urllib.parse.quote(c) for c in s]
        return "".join(chars)

    cc = cc or []
    if isinstance(to, str):
        to = [to]

    # FIXME: Very  strange things happen on  MacOS X. If  there is one
    # non-ASCII character in the body, it works. If there is more than
    # one, it fails.  Maybe we should use Mail.app  directly ? What if
    # the user uses something else ?

    if not operating_system.isMac():
        body = unicode_quote(body)  # Otherwise newlines disappear
        cc = list(map(unicode_quote, cc))
        to = list(map(unicode_quote, to))

    components = ["subject=%s" % subject, "body=%s" % body]
    if cc:
        components.append("cc=%s" % ",".join(cc))

    openURL("mailto:%s?%s" % (",".join(to), "&".join(components)))
