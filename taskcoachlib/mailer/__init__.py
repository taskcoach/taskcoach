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
import os
import re
import tempfile
import urllib.parse

from taskcoachlib import operating_system
from taskcoachlib.domain import date
from taskcoachlib.tools import openfile

# Kept in a mid: link's Message-ID (RFC 2392): what a URL allows,
# other characters escaped
_MID_SAFE = "@!$&'()*+,;=:/~"

# The line starting each mail in an mbox file
_MBOX_FROM = re.compile(rb"^From .*\r?\n", re.MULTILINE)

# A header line's name (RFC 5322)
_HEADER_NAME = re.compile(rb"^([!-9;-~]+):")

# Enough of a file to tell a mail by its headers
_HEAD_SIZE = 65536


def dropped_mails(filename):
    """The fields of each mail in a file a mail program dropped: a mail
    or mbox file in a temporary folder, where the programs put what
    they drag. [] for any other file, a saved mail included, which is
    attached as a file (docs/EMAIL_ATTACHMENTS.md, The Drop)."""
    if not is_temporary(filename):
        return []
    try:
        with open(filename, "rb") as mail_file:
            head = mail_file.read(_HEAD_SIZE)
    except OSError:
        return []
    return read_mails(filename) if looks_like_mail(head) else []


def is_temporary(filename):
    """Whether the file is in a temporary folder: under the system's,
    or in (or one folder below) a folder named tmp or temp, as the
    mail programs keeping their own use (Evolution's Flatpak cache,
    Claws Mail's)."""
    folder = os.path.dirname(os.path.abspath(filename))
    system = os.path.abspath(tempfile.gettempdir())
    if os.path.commonpath([folder, system]) == system:
        return True
    names = (
        os.path.basename(folder),
        os.path.basename(os.path.dirname(folder)),
    )
    return any(name.lower() in ("tmp", "temp") for name in names)


def looks_like_mail(data):
    """Whether the bytes start as a mail: an mbox file's From line, or
    a header block with a sender and a date, Message-ID, subject or
    Received header."""
    if data.startswith(b"From "):
        return True
    names = set()
    for line in re.split(rb"\r?\n\r?\n", data, maxsplit=1)[0].splitlines():
        match = _HEADER_NAME.match(line)
        if match:
            names.add(match.group(1).lower())
        elif not line[:1].isspace():  # Not a header nor its next line
            return False
    return b"from" in names and bool(
        names & {b"date", b"message-id", b"subject", b"received"}
    )


def read_mails(filename):
    """The fields of each dropped mail's attachment, from the file the
    mail program left: one mail, or several in mbox format (Evolution)
    (docs/EMAIL_ATTACHMENTS.md)."""
    with open(filename, "rb") as mail_file:
        data = mail_file.read()
    if not data.startswith(b"From "):
        return [parse_mail(data)]
    return [parse_mail(mail) for mail in _MBOX_FROM.split(data)[1:]]


def parse_mail(data):
    """The fields of a mail's attachment, from the mail's bytes."""
    message = email.message_from_bytes(
        _utf8_headers(data), policy=email.policy.default
    )
    sender = message["from"]
    addresses = getattr(sender, "addresses", ())
    sent = message["date"]
    return mail_fields(
        subject=_text(message["subject"]),
        from_name=_text(addresses[0].display_name if addresses else ""),
        from_address=_text(addresses[0].addr_spec if addresses else ""),
        sent=getattr(sent, "datetime", None),
        message_id=_text(message["message-id"]),
    )


def _utf8_headers(data):
    """The mail with its headers in UTF-8. RFC 6532 allows UTF-8 in
    headers; older mails may hold Latin-1, which the parser would turn
    into replacement characters."""
    end = re.search(rb"\r?\n\r?\n", data)
    headers = data[: end.start()] if end else data
    try:
        headers.decode("utf-8")
    except UnicodeDecodeError:
        return headers.decode("latin-1").encode("utf-8") + data[len(headers) :]
    return data


def _text(value):
    """A header's text. The parser keeps raw 8-bit bytes in some headers
    (addresses) as surrogates, which the task file cannot hold."""
    return (
        str(value or "")
        .encode("utf-8", "surrogateescape")
        .decode("utf-8", "replace")
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


# What would cut a mailto: link sent unescaped, as on macOS
_LINK_CUTTERS = str.maketrans({"&": "_", "#": "_"})


def send_mail(to, subject, body, cc=None, open_url=openfile.open_file):
    def unicode_quote(s):
        # Escapes what a mailto: link cannot hold (RFC 6068) but not
        # letters beyond ASCII: Outlook reads their UTF-8 escapes in
        # its own code page
        chars = [c if ord(c) >= 128 else urllib.parse.quote(c) for c in s]
        return "".join(chars)

    cc = cc or []
    if isinstance(to, str):
        to = [to]

    # FIXME: Very  strange things happen on  MacOS X. If  there is one
    # non-ASCII character in the body, it works. If there is more than
    # one, it fails.  Maybe we should use Mail.app  directly ? What if
    # the user uses something else ?

    if operating_system.isMac():
        # Escapes showed in the mail there (bug 3489341, 2012)
        subject = subject.translate(_LINK_CUTTERS)
        body = body.translate(_LINK_CUTTERS)
    else:
        subject = unicode_quote(subject)  # Else & and # cut it short
        body = unicode_quote(body)  # Otherwise newlines disappear
        cc = list(map(unicode_quote, cc))
        to = list(map(unicode_quote, to))

    components = ["subject=%s" % subject, "body=%s" % body]
    if cc:
        components.append("cc=%s" % ",".join(cc))

    open_url("mailto:%s?%s" % (",".join(to), "&".join(components)))
