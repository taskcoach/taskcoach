#!/usr/bin/env python3
"""Drag mails into Task Coach as a mail program would, without it.

A window with one button per mail program and system: pressing a button
starts a drag offering what that program offers, in its order, with the
files it would write where it would write them. Drop it on a task or an
attachment list. docs/EMAIL_ATTACHMENTS.md, The Drop, has the sources;
tests/unittests/widgetTests/MailDropTest.py checks what Task Coach does
with each.

    python3 tools/fake_mail_drag.py

What a wx drag source cannot make is left out: KMail's text/uri-list
of akonadi: links, Outlook's FileContents (IStorage), file promises on
macOS, a drag with several pasteboard items; MailDropTest covers them.
Files are removed when the window closes.
"""

import argparse
import os
import shutil
import signal
import struct
import sys
import tempfile

import wx

MAILS = (
    ("Quote", "quote7@example.com", "Renée Martin", "renee@example.com"),
    (
        "Invoice 4471",
        "inv4471@example.com",
        "Invoicing",
        "billing@example.com",
    ),
)


def mail(subject, message_id, name, address, crlf=False):
    text = (
        "From: %s <%s>\n"
        "Date: Tue, 29 Sep 2026 14:05:00 -0400\n"
        "Subject: %s\n"
        "Message-ID: <%s>\n"
        "Content-Type: text/plain; charset=utf-8\n\nText.\n"
        % (name, address, subject, message_id)
    )
    return text.replace("\n", "\r\n" if crlf else "\n").encode()


def mbox(mails):
    return b"".join(
        b"From %s Tue Sep 29 18:05:00 2026\n" % each[3].encode() + mail(*each)
        for each in mails
    )


def write(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as file:
        file.write(data)
    return path


def clipdata(flavours):
    """Mozilla's application/x-moz-custom-clipdata: per flavour, a
    big-endian type 1, then the name and the data in UTF-16LE with
    their byte lengths; 0 at the end."""
    blob = b""
    for name, value in flavours:
        name, value = name.encode("utf-16-le"), value.encode("utf-16-le")
        blob += struct.pack(">II", 1, len(name)) + name
        blob += struct.pack(">I", len(value)) + value
    return blob + struct.pack(">I", 0)


class Scenarios:
    """What each program drags: (label, system, a function giving the
    data objects in the program's order)."""

    def __init__(self, folder):
        self.folder = folder  # Removed at exit
        self.temp = tempfile.gettempdir()

    def __temp(self, *parts):
        return os.path.join(
            self.temp, "fake-mail-drag-" + str(os.getpid()), *parts
        )

    @staticmethod
    def uri(index):
        # The number is a key into Thunderbird's own index
        return "mailbox-message://nobody@Local%%20Folders/Inbox#%d" % (
            index + 1
        )

    def all(self):
        return [
            ("Evolution 3.56 (Linux)", "linux", self.evolution),
            ("Evolution, 2 mails (Linux)", "linux", self.evolution_two),
            ("Evolution Flatpak (Linux)", "linux", self.evolution_flatpak),
            ("Thunderbird, X11 (Linux)", "linux", self.thunderbird_x11),
            (
                "Thunderbird, IMAP, X11 (Linux)",
                "linux",
                self.thunderbird_imap_x11,
            ),
            (
                "Thunderbird, Wayland or 2 mails (Linux)",
                "linux",
                self.thunderbird_files,
            ),
            ("Claws Mail, 2 mails (Linux)", "linux", self.claws),
            ("Thunderbird (Windows)", "win32", self.thunderbird_windows),
            (
                "Thunderbird, 2 mails (Windows)",
                "win32",
                self.thunderbird_windows_two,
            ),
            ("Thunderbird (macOS)", "darwin", self.thunderbird_macos),
            ("Apple Mail (macOS)", "darwin", self.apple_mail),
            ("Saved .eml file (not a drag of a mail)", "any", self.saved_file),
        ]

    @staticmethod
    def files(*paths):
        data = wx.FileDataObject()
        for path in paths:
            data.AddFile(path)
        return data

    @staticmethod
    def custom(name, data):
        custom = wx.CustomDataObject(name)
        custom.SetData(data)
        return custom

    @staticmethod
    def text(value):
        return wx.TextDataObject(value)

    def evolution(self):
        path = write(
            self.__temp("drag-n-drop-EVO356", "20260929140500_Quote.mbox"),
            mbox(MAILS[:1]),
        )
        return [
            self.custom("x-uid-list", b"folder://local/Inbox\x001\x00"),
            self.files(path),
        ]

    def evolution_two(self):
        path = write(
            self.__temp("drag-n-drop-EVO002", "Messages from Inbox.mbox"),
            mbox(MAILS),
        )
        return [
            self.custom(
                "x-uid-list",
                b"folder://local/Inbox\x001\x00folder://local/Inbox\x002\x00",
            ),
            self.files(path),
        ]

    def evolution_flatpak(self):
        # Its cache's tmp folder, outside the system's temporary folder
        path = write(
            os.path.join(
                self.folder,
                "org.gnome.Evolution",
                "cache",
                "evolution",
                "tmp",
                "20260929140500_Quote.mbox",
            ),
            mbox(MAILS[:1]),
        )
        return [
            self.custom("x-uid-list", b"folder://local/Inbox\x001\x00"),
            self.files(path),
        ]

    def thunderbird_x11(self):
        uri = self.uri(0)
        eml = write(
            self.__temp("dnd_file", "Quote.eml"), mail(*MAILS[0], crlf=True)
        )
        return [
            self.text(uri),
            self.custom(
                "application/x-moz-custom-clipdata",
                clipdata([("text/x-moz-message", uri)]),
            ),
            self.custom(
                "text/x-moz-url",
                ("mailbox:///Inbox?number=0").encode("utf-16-le"),
            ),
            self.files(eml),
        ]

    def thunderbird_imap_x11(self):
        uri = "imap-message://alice%40example.com@imap.example.com/INBOX#77"
        eml = write(
            self.__temp("dnd_file", "Quote.eml"), mail(*MAILS[0], crlf=True)
        )
        return [self.text(uri), self.files(eml)]

    def thunderbird_files(self):
        return [
            self.custom("application/x-moz-internal-item-list", b""),
            self.files(
                write(
                    self.__temp("dnd_file", "Quote.eml"),
                    mail(*MAILS[0], crlf=True),
                ),
                write(
                    self.__temp("dnd_file-1", "Invoice 4471.eml"),
                    mail(*MAILS[1], crlf=True),
                ),
            ),
        ]

    def claws(self):
        tmp = os.path.join(self.folder, ".claws-mail", "tmp")
        return [
            self.files(
                write(os.path.join(tmp, "Quote.42.txt"), mail(*MAILS[0])),
                write(
                    os.path.join(tmp, "Invoice 4471.43.txt"), mail(*MAILS[1])
                ),
            ),
            self.custom(
                "claws-mail/msg-path-list",
                b"#mh/Mailbox/inbox\n<quote7@example.com>",
            ),
        ]

    def thunderbird_windows(self):
        uri = self.uri(0)
        eml = write(
            os.path.join(self.temp, "Quote.eml"), mail(*MAILS[0], crlf=True)
        )
        return [self.text(uri), self.files(eml)]

    def thunderbird_windows_two(self):
        # The URIs concatenated, with no separator
        return [self.text(self.uri(0) + self.uri(1))]

    def thunderbird_macos(self):
        url = "mailbox:///Users/alice/Library/Thunderbird/Profiles/p/Mail/"
        url += "Local%20Folders/Inbox?number=1"
        return [
            self.text(self.uri(0)),
            self.custom("public.url", url.encode()),
        ]

    def apple_mail(self):
        return [self.custom("public.url", b"message:%3Cquote7@example.com%3E")]

    def saved_file(self):
        return [
            self.files(
                write(
                    os.path.join(self.folder, "Documents", "Quote.eml"),
                    mail(*MAILS[0]),
                )
            )
        ]


class Window(wx.Frame):
    def __init__(self, scenarios):
        super().__init__(None, title="Fake mail drag", size=(420, 520))
        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(
            wx.StaticText(
                panel, label="Press a button and drag it onto Task Coach:"
            ),
            0,
            wx.ALL,
            8,
        )
        system = {"linux": "linux", "win32": "win32", "darwin": "darwin"}.get(
            sys.platform, "linux"
        )
        for label, where, make in scenarios.all():
            button = wx.Button(panel, label=label)
            button.Enable(where in ("any", system))
            button.Bind(
                wx.EVT_LEFT_DOWN,
                lambda event, make=make, label=label: self.drag(make, label),
            )
            sizer.Add(button, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 4)
        panel.SetSizer(sizer)

    def drag(self, make, label):
        composite = wx.DataObjectComposite()
        for data in make():
            composite.Add(data)
        source = wx.DropSource(self)
        source.SetData(composite)
        print(
            "%s: %s" % (label, source.DoDragDrop(wx.Drag_CopyOnly)), flush=True
        )


class Wake(wx.Timer):
    def Notify(self):
        pass  # Python runs, and so its signal handlers


def main():
    argparse.ArgumentParser(description=__doc__.split("\n\n")[0]).parse_args()
    # Outside the system temporary folder, as Flatpak and Claws Mail
    # keep their own
    folder = tempfile.mkdtemp(
        prefix="fake-mail-drag-", dir=os.path.expanduser("~/.cache")
    )
    try:
        app = wx.App(False)
        Window(Scenarios(folder)).Show()
        # Ctrl+C or a kill ends the loop, so the files are removed too;
        # the timer lets Python see the signal while wx waits
        for number in (signal.SIGINT, signal.SIGTERM):
            signal.signal(number, lambda *args: app.ExitMainLoop())
        timer = Wake()
        timer.Start(250)
        app.MainLoop()
    finally:
        shutil.rmtree(folder, ignore_errors=True)
        shutil.rmtree(
            os.path.join(
                tempfile.gettempdir(), "fake-mail-drag-" + str(os.getpid())
            ),
            ignore_errors=True,
        )


if __name__ == "__main__":
    main()
