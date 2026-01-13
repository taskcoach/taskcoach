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

import os
import urllib.parse
from taskcoachlib import patterns, mailer
from taskcoachlib.domain import base
from taskcoachlib.tools import openfile
from pubsub import pub
from taskcoachlib.domain.note.noteowner import NoteOwner
from functools import total_ordering


def getRelativePath(path, basePath=os.getcwd()):
    """Tries to guess the relative version of 'path' from 'basePath'. If
    not possible, return absolute 'path'. Both 'path' and 'basePath' must
    be absolute."""

    path = os.path.realpath(os.path.normpath(path))
    basePath = os.path.realpath(os.path.normpath(basePath))

    drive1, path1 = os.path.splitdrive(path)
    drive2, path2 = os.path.splitdrive(basePath)

    # No relative path is possible if the two are on different drives.
    if drive1 != drive2:
        return path

    if path1.startswith(path2):
        if path1 == path2:
            return ""

        if path2 == os.path.sep:
            return path1[1:].replace("\\", "/")

        return path1[len(path2) + 1 :].replace("\\", "/")

    path1 = path1.split(os.path.sep)
    path2 = path2.split(os.path.sep)

    while path1 and path2 and path1[0] == path2[0]:
        path1.pop(0)
        path2.pop(0)

    while path2:
        path1.insert(0, "..")
        path2.pop(0)

    return os.path.join(*path1).replace("\\", "/")  # pylint: disable=W0142


@total_ordering
class Attachment(base.Object, NoteOwner):
    """Abstract base class for attachments."""

    type_ = "unknown"

    def __init__(self, location, *args, **kwargs):
        if "subject" not in kwargs:
            kwargs["subject"] = location
        super().__init__(*args, **kwargs)
        self.__location = location

    def data(self):
        return None

    def setParent(self, parent):
        # FIXME: We shouldn't assume that pasted items are composite
        # in PasteCommand.
        pass

    def location(self):
        return self.__location

    def setLocation(self, location):
        if location != self.__location:
            self.__location = location
            self.markDirty()
            pub.sendMessage(
                self.locationChangedEventType(), newValue=location, sender=self
            )

    @classmethod
    def locationChangedEventType(class_):
        return "pubsub.attachment.location"

    @classmethod
    def monitoredAttributes(class_):
        return base.Object.monitoredAttributes() + ["location"]

    def open(self, workingDir=None):
        raise NotImplementedError

    # Note: We intentionally do NOT override __hash__ or __eq__ here.
    # The parent class (base.Object) provides stable ID-based hashing
    # which is required for observer registration to work correctly.
    # Using location-based hashing caused KeyError crashes when the
    # location changed after observer registration (issue #84).

    def __lt__(self, other):
        try:
            return self.location() < other.location()
        except AttributeError:
            return False

    def __getstate__(self):
        try:
            state = super().__getstate__()
        except AttributeError:
            state = dict()
        state.update(dict(location=self.location()))
        return state

    @patterns.eventSource
    def __setstate__(self, state, event=None):
        try:
            super().__setstate__(state, event=event)
        except AttributeError:
            pass
        self.setLocation(state["location"])

    def __getcopystate__(self):
        # Don't include id and creationDateTime - copies should get new ones
        state = super().__getcopystate__()
        state.update(dict(location=self.location()))
        return state

    def __unicode__(self):
        return self.subject()

    @classmethod
    def modificationEventTypes(class_):
        eventTypes = super(Attachment, class_).modificationEventTypes()
        return eventTypes + [class_.locationChangedEventType()]


class FileAttachment(Attachment):
    type_ = "file"

    def open(
        self, workingDir=None, openAttachment=openfile.openFile
    ):  # pylint: disable=W0221
        return openAttachment(self.normalizedLocation(workingDir))

    def normalizedLocation(self, workingDir=None):
        location = self.location()
        if self.isLocalFile():
            if workingDir and not os.path.isabs(location):
                location = os.path.join(workingDir, location)
            location = os.path.normpath(location)
        return location

    def isLocalFile(self):
        return urllib.parse.urlparse(self.location())[0] == ""


class URIAttachment(Attachment):
    type_ = "uri"

    def __init__(self, location, *args, **kwargs):
        if location.startswith("message:") and "subject" not in kwargs:
            kwargs["subject"] = _("Mail.app message")
        super().__init__(location, *args, **kwargs)

    def open(self, workingDir=None):
        return openfile.openFile(self.location())


class MailAttachment(Attachment):
    type_ = "mail"

    def __init__(self, location, *args, **kwargs):
        self._readMail = kwargs.pop("readMail", mailer.readMail)
        subject, content = self._readMail(location)

        kwargs.setdefault("subject", subject)
        kwargs.setdefault("description", content)

        super().__init__(location, *args, **kwargs)

    def open(self, workingDir=None):
        return mailer.openMail(self.location())

    def read(self):
        return self._readMail(self.location())

    def data(self):
        try:
            return open(self.location(), "rb").read()
        except IOError:
            return None


def AttachmentFactory(location, type_=None, *args, **kwargs):
    if type_ is None:
        if location.startswith("URI:"):
            return URIAttachment(
                location[4:], subject=location[4:], description=location[4:]
            )
        elif location.startswith("FILE:"):
            return FileAttachment(
                location[5:], subject=location[5:], description=location[5:]
            )
        elif location.startswith("MAIL:"):
            return MailAttachment(
                location[5:], subject=location[5:], description=location[5:]
            )

        return FileAttachment(location, subject=location, description=location)

    try:
        return {
            "file": FileAttachment,
            "uri": URIAttachment,
            "mail": MailAttachment,
        }[type_](location, *args, **kwargs)
    except KeyError:
        raise TypeError("Unknown attachment type: %s" % type_)
