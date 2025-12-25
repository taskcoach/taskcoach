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

import wx, os, re, tempfile, urllib.request, urllib.parse, urllib.error, email, email.header
import chardet
from taskcoachlib.tools import openfile
from taskcoachlib.mailer.macmail import getSubjectOfMail
from taskcoachlib.i18n import _
from taskcoachlib import operating_system


def readMail(filename, readContent=True):
    with open(filename, "r") as fd:
        message = email.message_from_file(fd)
    subject = getSubject(message)
    content = getContent(message) if readContent else ""
    return subject, content


charset_re = re.compile('charset="?([-0-9a-zA-Z]+)"?')


def getSubject(message):
    subject = message["subject"]
    try:
        return " ".join(
            (part[0].decode(part[1]) if part[1] else part[0])
            for part in email.header.decode_header(subject)
        )
    except UnicodeDecodeError:
        encoding = message.get_content_charset()
        if encoding is None:
            encoding = message.get("Content-Transfer-Encoding")
        if encoding is None:
            encoding = "utf-8"
        try:
            return subject.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            return repr(subject)


def getContent(message):
    if message.is_multipart():
        content = []
        for submessage in message.get_payload():
            content.append(getContent(submessage))
        return "\n".join(content)
    elif message.get_content_type() in ("text/plain", "message/rfc822"):
        content = message.get_payload()
        transfer_encoding = message["content-transfer-encoding"]
        if transfer_encoding:
            try:
                content = content.decode(transfer_encoding)
            except LookupError:
                pass  # 8bit transfer encoding gives LookupError, ignore
        content_type = message["content-type"]
        if content_type:
            match = charset_re.search(message["content-type"])
            encoding = match.group(1) if match else ""
            if encoding:
                content = content.decode(encoding)
        return content
    else:
        return ""


def openMailWithOutlook(filename):
    id_ = None
    for line in open(filename, "r"):
        if line.startswith("X-Outlook-ID:"):
            id_ = line[13:].strip()
            break
        elif line.strip() == "":
            break

    if id_ is None:
        return False

    from win32com.client import GetActiveObject  # pylint: disable=F0401

    app = GetActiveObject("Outlook.Application")
    app.ActiveExplorer().Session.GetItemFromID(id_).Display()

    return True


def openMail(filename):
    if os.name == "nt":
        # Find out if Outlook is the so-called 'default' mailer.
        import winreg  # pylint: disable=F0401

        key = winreg.OpenKey(
            winreg.HKEY_CLASSES_ROOT, r"mailto\shell\open\command"
        )
        try:
            value, type_ = winreg.QueryValueEx(key, "")
            if type_ in [winreg.REG_SZ, winreg.REG_EXPAND_SZ]:
                if "outlook.exe" in value.lower():
                    try:
                        if openMailWithOutlook(filename):
                            return
                    except Exception:
                        pass  # Fall back to default handler
        finally:
            winreg.CloseKey(key)

    openfile.openFile(filename)


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
