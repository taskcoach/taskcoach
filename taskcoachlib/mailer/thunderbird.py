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

from taskcoachlib import persistence, operating_system
from taskcoachlib.thirdparty.ntlm import IMAPNtlmAuthHandler
from taskcoachlib.widgets.password import GetPassword
from taskcoachlib.i18n import _
import os
import stat
import re
import imaplib
import configparser
import wx
import socket
import mailbox


_RX_MAILBOX_MESSAGE = re.compile(
    r"mailbox-message://(.*)@(.*)/(.*)#((?:-)?\d+)"
)
_RX_IMAP_MESSAGE = re.compile(r"imap-message://([^@]+)@([^/]+)/(.*)#(\d+)")
_RX_IMAP = re.compile(
    r"imap://([^@]+)@([^/]+)/fetch%3EUID%3E(?:/|\.)(.*)%3E(\d+)"
)
_RX_MAILBOX = re.compile(r"mailbox://([^?]+)\?number=(\d+)")


class ThunderbirdError(Exception):
    pass


class ThunderbirdCancelled(ThunderbirdError):
    pass


def unquote(s):
    """Converts %nn sequences into corresponding characters. I
    couldn't find anything in the standard library to do this, but I
    probably didn't search hard enough."""

    rx = re.compile("%([0-9a-fA-F][0-9a-fA-F])")
    mt = rx.search(s)
    while mt:
        s = s[: mt.start(1) - 1] + chr(int(mt.group(1), 16)) + s[mt.end(1) :]
        mt = rx.search(s)

    return s


def loadPreferences():
    """Reads Thunderbird's prefs.js file and return a dictionary of
    configuration options."""

    config = {}

    # Regex to parse user_pref("key", value) lines safely
    pref_pattern = re.compile(r'user_pref\s*\(\s*"([^"]+)"\s*,\s*(.+?)\s*\)\s*;')

    for line in open(os.path.join(getDefaultProfileDir(), "prefs.js"), "r"):
        if line.startswith("user_pref("):
            match = pref_pattern.match(line.strip())
            if match:
                key = match.group(1)
                value_str = match.group(2)

                # Parse the value safely
                if value_str == "true":
                    value = True
                elif value_str == "false":
                    value = False
                elif value_str.startswith('"') and value_str.endswith('"'):
                    # String value - handle escape sequences
                    value = value_str[1:-1].replace('\\"', '"').replace('\\\\', '\\')
                else:
                    # Try to parse as number
                    try:
                        if '.' in value_str:
                            value = float(value_str)
                        else:
                            value = int(value_str)
                    except ValueError:
                        value = value_str

                config[key] = value

    return config


def getThunderbirdDir():
    path = None

    if operating_system.isMac():
        path = os.path.join(os.environ["HOME"], "Library", "Thunderbird")
    elif os.name == "posix":
        path = os.path.join(os.environ["HOME"], ".thunderbird")
        if not os.path.exists(path):
            path = os.path.join(os.environ["HOME"], ".mozilla-thunderbird")
    elif os.name == "nt":
        if "APPDATA" in os.environ:
            path = os.path.join(os.environ["APPDATA"], "Thunderbird")
        elif "USERPROFILE" in os.environ:
            path = os.path.join(
                os.environ["USERPROFILE"], "Application Data", "Thunderbird"
            )
    else:
        raise EnvironmentError("Unsupported platform: %s" % os.name)

    if path is None:
        raise ThunderbirdError(_("Could not find Thunderbird data dir"))

    return path


_PORTABLECACHE = None


def getDefaultProfileDir():
    """Returns Thunderbird's default profile directory"""

    global _PORTABLECACHE  # pylint: disable=W0603

    path = getThunderbirdDir()

    # Thunderbird Portable does not have a profiles.ini file, only one
    # profile. And there's only one way to know where it
    # is... Hackish.

    if os.name == "nt" and not os.path.exists(
        os.path.join(path, "profiles.ini")
    ):
        if _PORTABLECACHE is not None:
            return _PORTABLECACHE

        import wmi  # pylint: disable=W0404

        for process in wmi.WMI().Win32_Process():
            if (
                process.ExecutablePath
                and process.ExecutablePath.lower().endswith(
                    "thunderbirdportable.exe"
                )
            ):
                _PORTABLECACHE = os.path.join(
                    os.path.split(process.ExecutablePath)[0], "Data", "profile"
                )
                break
        else:
            raise ThunderbirdError(_("Could not find Thunderbird profile."))

        return _PORTABLECACHE

    parser = configparser.RawConfigParser()
    parser.read([os.path.join(path, "profiles.ini")])

    for section in parser.sections():
        if parser.has_option(section, "Default") and int(
            parser.get(section, "Default")
        ):
            if int(parser.get(section, "IsRelative")):
                return os.path.join(path, parser.get(section, "Path"))
            return parser.get(section, "Path")

    for section in parser.sections():
        if (
            parser.has_option(section, "Name")
            and parser.get(section, "Name") == "default"
        ):
            if int(parser.get(section, "IsRelative")):
                return os.path.join(path, parser.get(section, "Path"))
            return parser.get(section, "Path")

    raise ThunderbirdError(_("No default section in profiles.ini"))


class ThunderbirdMailboxReader(object):
    """Extracts an e-mail from a Thunderbird file. Behaves like a
    stream object to read this e-mail."""

    def __init__(self, url):
        """url is the internal reference to the mail, as collected
        through drag-n-drop."""

        mt = _RX_MAILBOX_MESSAGE.search(url)
        if mt is None:
            raise ThunderbirdError(
                _(
                    "Malformed Thunderbird internal ID:\n%s. Please file a bug report."
                )
                % url
            )

        self.url = url

        # The url has the form
        # mailbox-message://<username>@<hostname>//<filename>#<id>. Or
        # so I hope.

        config = loadPreferences()

        self.user = unquote(mt.group(1))
        self.server = unquote(mt.group(2))
        self.path = unquote(mt.group(3)).split("/")
        self.offset = int(mt.group(4))

        for i in range(200):
            base = "mail.server.server%d" % i
            if "%s.userName" % base in config:
                if (
                    config["%s.userName" % base] == self.user
                    and config["%s.hostname" % base] == self.server
                ):
                    # First try the relative path.
                    if "%s.directory-rel" % base in config:
                        path = config["%s.directory-rel" % base]
                        if path.startswith("[ProfD]"):
                            path = os.path.join(
                                getDefaultProfileDir(), path[7:]
                            )
                        self.filename = os.path.join(path, *tuple(self.path))
                        if os.path.exists(self.filename):
                            break
                        else:
                            self.filename = os.path.join(
                                config["%s.directory" % base],
                                *tuple(self.path)
                            )
                            if os.path.exists(self.filename):
                                break
        else:
            raise ThunderbirdError(
                _(
                    "Could not find directory for ID\n%s.\nPlease file a bug report."
                )
                % url
            )

        self.fp = open(self.filename, "rb")
        if self.offset >= 0:
            self.fp.seek(self.offset)
        else:
            self.fp.seek(self.offset, os.SEEK_END)

        self.done = False

    def read(self):
        """Buffer-like read() method"""

        if self.done:
            return ""

        lines = []

        # In theory, the message ends with a single dot. As always, in
        # theory, theory is like practice but in practice...

        starting = True

        for line in self.fp:
            if not starting:
                if line.startswith("From "):
                    break
            lines.append(line)
            starting = False

        self.done = True
        return "".join(lines)

    def __iter__(self):
        class Iterator(object):
            def __init__(self, fp):
                self.fp = fp

            def __iter__(self):
                return self

            def __next__(self):
                line = self.fp.readline()
                if line.strip() == ".":
                    raise StopIteration
                return line

        return Iterator(self.fp)

    def saveToFile(self, fp):
        fp.write(self.read())


class ThunderbirdImapReader(object):
    def __init__(self, url):
        mt = _RX_IMAP.search(url)
        if mt is None:
            mt = _RX_IMAP_MESSAGE.search(url)
            if mt is None:
                raise ThunderbirdError(
                    _('Unrecognized URL scheme: "%s"') % url
                )

        self.url = url

        self.user = unquote(mt.group(1))
        self.server = mt.group(2)
        port = None
        if ":" in self.server:
            self.server, port = self.server.split(":")
            port = int(port)
        self.box = mt.group(3)
        self.uid = int(mt.group(4))

        config = loadPreferences()

        stype = None
        # We iterate over a maximum of 100 mailservers. You'd think that
        # mailservers would be numbered consecutively, but apparently
        # that is not always the case, so we cannot assume that because
        # serverX does not exist, serverX+1 won't either.
        for serverIndex in range(100):
            name = "mail.server.server%d" % serverIndex
            if (
                name + ".hostname" in config
                and self.__equal_servers(
                    config[name + ".hostname"], self.server
                )
                and config[name + ".type"] == "imap"
            ):
                if name + ".port" in config:
                    port = int(config[name + ".port"])
                if name + ".socketType" in config:
                    stype = config[name + ".socketType"]
                break
        self.ssl = stype == 3

        if self.server in ("imap.google.com", "imap.googlemail.com"):
            # When dragging mail from Thunderbird that uses Gmail via IMAP the
            # server reported is imap.google.com, but for a direct connection we
            # need to connect with imap.gmail.com:
            self.server = "imap.gmail.com"
        elif name + ".realhostname" in config:
            self.server = config[name + ".realhostname"]
        self.port = port or {True: 993, False: 143}[self.ssl]

    @staticmethod
    def __equal_servers(server1, server2):
        """Return whether the servers are the same."""
        gmail_servers = (
            "imap.gmail.com",
            "imap.google.com",
            "imap.googlemail.com",
        )
        if server1 in gmail_servers and server2 in gmail_servers:
            return True
        else:
            return server1 == server2

    def _getMail(self):
        """Retrieve the email message from the IMAP server as specified by
        the dropped URL."""
        imap_class = imaplib.IMAP4_SSL if self.ssl else imaplib.IMAP4
        try:
            imap = imap_class(self.server, self.port)
        except socket.gaierror as reason:
            error_message = _(
                "Could not open an IMAP connection to "
                "%(server)s:%(port)s\nto retrieve Thunderbird "
                "email message:\n%(reason)s"
            ) % dict(server=self.server, port=self.port, reason=reason)
            raise ThunderbirdError(error_message)

        password_domain = "%s:%d" % (self.server, self.port)
        pwd = GetPassword(password_domain, self.user)
        if pwd is None:
            raise ThunderbirdCancelled("User canceled")

        while True:
            try:
                if "AUTH=CRAM-MD5" in imap.capabilities:
                    response, dummy = imap.login_cram_md5(
                        str(self.user), str(pwd)
                    )
                elif "AUTH=NTLM" in imap.capabilities:
                    domain = wx.GetTextFromUser(
                        _("Please enter the domain for user %s") % self.user
                    )
                    domain_username = "\\".join(
                        [domain.upper(), str(self.user)]
                    )
                    response, dummy_parameters = imap.authenticate(
                        "NTLM",
                        IMAPNtlmAuthHandler.IMAPNtlmAuthHandler(
                            domain_username, str(pwd)
                        ),
                    )
                else:
                    response, dummy_parameters = imap.login(self.user, pwd)
            except imap.error as reason:
                response = "KO"
                (error_message,) = reason.args

            if response == "OK":
                break

            pwd = GetPassword(password_domain, self.user, reset=True)
            if pwd is None:
                raise ThunderbirdCancelled("User canceled")

        # Two possibilities for separator...

        response, dummy_parameters = imap.select(self.box)

        if response != "OK":
            response, dummy_parameters = imap.select(
                self.box.replace("/", ".")
            )
            if response != "OK":
                raise ThunderbirdError(
                    _('Could not select inbox "%s"\n(%s)')
                    % (self.box, response)
                )

        response, parameters = imap.uid("FETCH", str(self.uid), "(RFC822)")

        if response != "OK":
            raise ThunderbirdError(_("No such mail: %d") % self.uid)

        return parameters[0][1]

    def saveToFile(self, fp):
        fp.write(self._getMail())


class ThunderbirdLocalMailboxReader(object):
    """Reads email from a local Thunderbird mailbox."""

    def __init__(self, url):
        self.url = url

    def _getMail(self):
        match = _RX_MAILBOX.match(self.url)
        if match is None:
            raise ThunderbirdError(
                _('Unrecognized URL scheme: "%s"') % self.url
            )
        path = unquote(match.group(1))
        # Note that the number= part of the URL is not the message key, but
        # rather an offset in the mbox file.
        offset = int(match.group(2))
        # So we skip the first offset bytes before reading the contents:
        with open(path, "rb") as mbox:
            mbox.seek(offset)
            contents = mbox.read(4 * 1024 * 1024)  # Assume message size <= 4MB
        # Then we get a filename for a temporary file...
        filename = persistence.get_temp_file()
        # And save the remaining contents of the original mbox file:
        with open(filename, "wb") as tmpmbox:
            tmpmbox.write(contents)
        # Now we can open the temporary mbox file...
        mb = mailbox.mbox(filename)
        # And the message we look for should be the first one:
        return mb.get_string(0)

    def saveToFile(self, fp):
        fp.write(self._getMail())


def getMail(id_):
    if id_.startswith("mailbox-message://"):
        reader = ThunderbirdMailboxReader(id_)
    elif id_.startswith("imap"):
        reader = ThunderbirdImapReader(id_)
    elif id_.startswith("mailbox:"):
        reader = ThunderbirdLocalMailboxReader(id_)
    else:
        raise TypeError("Not supported: %s" % id_)

    filename = persistence.get_temp_file(suffix=".eml")
    reader.saveToFile(open(filename, "wb"))

    if os.name == "nt":
        os.chmod(filename, stat.S_IREAD)

    return filename
