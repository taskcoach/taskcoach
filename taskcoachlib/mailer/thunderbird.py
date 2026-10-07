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

# Thunderbird hands its mails over as .eml files only on Wayland, or
# when several are dragged (mailer.dropped_mails()); otherwise it gives
# each message's address: a key into its own index for a local folder,
# a number on the server for IMAP. Task Coach reads neither
# (docs/EMAIL_ATTACHMENTS.md, Decisions 8).

import re

from taskcoachlib.i18n import _

# As text: each message's URI, concatenated on Windows
_MESSAGE_SCHEMES = ("mailbox-message://", "imap-message://")
_RX_MESSAGE_START = re.compile(r"(?=mailbox-message://|imap-message://)")
# A macOS link to a message
_MAC_SCHEMES = ("mailbox:", "imap:")


def message_uris(text):
    """The message URIs a Thunderbird drag gave as text; [] when the
    text is anything else."""
    parts = [
        part for part in _RX_MESSAGE_START.split("".join(text.split())) if part
    ]
    if parts and all(part.startswith(_MESSAGE_SCHEMES) for part in parts):
        return parts
    return []


def is_mac_message_url(url):
    return url.startswith(_MAC_SCHEMES)


def unreadable():
    """Why a mail given by its address is not attached, and what to
    do instead."""
    return _(
        "Thunderbird gave only this mail's address, not the mail, so "
        "Task Coach cannot read it.\nSave the mail as a file in "
        "Thunderbird, then drag the file onto the task."
    )
