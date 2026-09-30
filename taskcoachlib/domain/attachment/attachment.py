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
from taskcoachlib import patterns
from taskcoachlib.domain import base, date
from taskcoachlib.domain.base.attribute import Attribute
from taskcoachlib.tools import openfile
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


def _text_sort_key(field, sortCaseSensitive=False, **kwargs):
    if sortCaseSensitive:
        return field
    return lambda item: field(item).lower()


@total_ordering
class Attachment(base.Object, NoteOwner):
    """Abstract base class for attachments.

    Appearance (derived and effective values) is handled by the base class
    and the master loop. Attachments have no inheritance - always
    use system theme.
    """

    type_ = "unknown"

    def __init__(self, location, *args, **kwargs):
        if "subject" not in kwargs:
            # Use filename without extension as subject, not full path/URL
            filename = os.path.basename(location)
            kwargs["subject"] = os.path.splitext(filename)[0] or location
        super().__init__(*args, **kwargs)
        self.__location = Attribute(location, self, self._on_location_changed)
        # Note: Effective appearance is computed by the master loop

    def set_parent(self, parent):
        # FIXME: We shouldn't assume that pasted items are composite
        # in PasteCommand.
        pass

    def location(self):
        return self.__location.get()

    def setLocation(self, location, event=None):
        self.__location.set(location, event=event)

    def _on_location_changed(self, event):
        event.addSource(self, type=self.locationChangedEventType())

    @classmethod
    def locationChangedEventType(class_):
        return "attachment.location"

    @staticmethod
    def locationSortFunction(**kwargs):
        return _text_sort_key(lambda item: item.location(), **kwargs)

    @classmethod
    def locationSortEventTypes(cls):
        return (cls.locationChangedEventType(),)

    # A mail's own fields: other attachments have none

    def from_name(self):
        return ""

    def from_address(self):
        return ""

    def sent_datetime(self):
        return date.DateTime()

    @classmethod
    def mail_changed_event_type(cls):
        return "%s.mail" % cls

    @staticmethod
    def fromNameSortFunction(**kwargs):
        return _text_sort_key(lambda item: item.from_name(), **kwargs)

    @classmethod
    def fromNameSortEventTypes(cls):
        return (cls.mail_changed_event_type(),)

    @staticmethod
    def fromAddressSortFunction(**kwargs):
        return _text_sort_key(lambda item: item.from_address(), **kwargs)

    @classmethod
    def fromAddressSortEventTypes(cls):
        return (cls.mail_changed_event_type(),)

    @staticmethod
    def sentDateTimeSortFunction(**kwargs):  # pylint: disable=W0613
        return lambda item: item.sent_datetime()

    @classmethod
    def sentDateTimeSortEventTypes(cls):
        return (cls.mail_changed_event_type(),)

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
        self.setLocation(state["location"], event=event)

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
    """A mail kept in the user's mail program: its subject, sender and
    sent date, and a mid: link to it by its Message-ID, not the mail
    itself (docs/EMAIL_ATTACHMENTS.md)."""

    type_ = "mail"

    def __init__(
        self,
        location,
        *args,
        from_name="",
        from_address="",
        sent_datetime=None,
        **kwargs
    ):
        super().__init__(location, *args, **kwargs)
        self.__from_name = Attribute(from_name, self, self._on_mail_changed)
        self.__from_address = Attribute(
            from_address, self, self._on_mail_changed
        )
        self.__sent_datetime = Attribute(
            date.DateTime() if sent_datetime is None else sent_datetime,
            self,
            self._on_mail_changed,
        )

    def open(self, workingDir=None):
        # The mail program registered for mid: links shows the mail
        return openfile.openFile(self.location())

    def from_name(self):
        return self.__from_name.get()

    def from_address(self):
        return self.__from_address.get()

    def sent_datetime(self):
        return self.__sent_datetime.get()

    def _on_mail_changed(self, event):
        event.addSource(self, type=self.mail_changed_event_type())

    def __getstate__(self):
        state = super().__getstate__()
        state.update(self.__mail_state())
        return state

    @patterns.eventSource
    def __setstate__(self, state, event=None):
        super().__setstate__(state, event=event)
        self.__from_name.set(state["from_name"], event=event)
        self.__from_address.set(state["from_address"], event=event)
        self.__sent_datetime.set(state["sent_datetime"], event=event)

    def __getcopystate__(self):
        state = super().__getcopystate__()
        state.update(self.__mail_state())
        return state

    def __mail_state(self):
        return dict(
            from_name=self.from_name(),
            from_address=self.from_address(),
            sent_datetime=self.sent_datetime(),
        )

    @classmethod
    def modificationEventTypes(cls):
        return super().modificationEventTypes() + [
            cls.mail_changed_event_type()
        ]


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
