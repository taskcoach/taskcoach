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

from taskcoachlib import mailer

# A format only Outlook (classic) drags, with the dragged items' IDs;
# not "Object Descriptor", which any OLE program's drag offers
# (docs/EMAIL_ATTACHMENTS.md, The Drop)
OUTLOOK_FORMAT = "RenPrivateMessages"

# Outlook's MAPI property for the mail's Message-ID
_MESSAGE_ID = "http://schemas.microsoft.com/mapi/proptag/0x1035001F"


if os.name == "nt":
    from pywintypes import com_error  # pylint: disable=F0401
    from win32com.client import GetActiveObject  # pylint: disable=F0401

    def getCurrentSelection():
        """The fields of the mails selected in Outlook, one attachment
        each (mailer.mail_fields()): the dragged ones."""
        try:
            outlook = GetActiveObject("Outlook.Application")
            selection = outlook.ActiveExplorer().Selection
        except com_error:
            return []  # Outlook gone meanwhile
        return [
            _fields(selection.Item(n)) for n in range(1, selection.Count + 1)
        ]

    def _fields(item):
        # Not every selected item is a mail (a meeting request, a
        # contact): what it lacks stays empty
        sent = getattr(item, "SentOn", None)
        return mailer.mail_fields(
            subject=getattr(item, "Subject", ""),
            from_name=getattr(item, "SenderName", ""),
            from_address=_sender_address(item),
            # Outlook's local time, whatever time zone pywin32 marks
            sent=(
                None
                if sent is None
                else datetime.datetime(*sent.timetuple()[:6])
            ),
            message_id=_message_id(item),
        )

    def _sender_address(item):
        if getattr(item, "SenderEmailType", "") == "EX":
            # An Exchange sender's address is an X.500 path
            try:
                user = item.Sender.GetExchangeUser()
            except com_error:
                return ""
            return user.PrimarySmtpAddress if user else ""
        return getattr(item, "SenderEmailAddress", "")

    def _message_id(item):
        try:
            return item.PropertyAccessor.GetProperty(_MESSAGE_ID)
        except com_error:
            # Not sent through the Internet: no Message-ID
            return ""

else:

    def getCurrentSelection():
        return []  # Outlook runs on Windows only
