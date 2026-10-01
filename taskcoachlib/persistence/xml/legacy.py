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

# What is written only so that releases reading tskversion 37 (2.0.2.0
# and later) open the file as they left it: the old forms next to the
# new ones, and fields this release does not use. All of it goes, with
# its calls, when tskversion becomes 38; the reader keeps reading
# these forms, for the files saved meanwhile (docs/PERSISTENCE_XML.md,
# Versions and Compatibility).

_FIELDS = "_fields_for_older_releases"


def keep(item, icon, selected_icon, stated_modification):
    """Keep what the item's node held for older releases: its selected
    icon, with the icon it went with, and whether it stated its
    modification date."""
    setattr(
        item,
        _FIELDS,
        dict(
            icon=icon,
            selected_icon=selected_icon,
            stated_modification=stated_modification,
        ),
    )


def selected_icon(item):
    """The selected icon to write: the one read, while the item's icon
    is still the one it went with."""
    fields = getattr(item, _FIELDS, None)
    if fields and fields["selected_icon"] and fields["icon"] == item.icon_id():
        return fields["selected_icon"]
    return None


def stated_modification(item):
    """Whether the file stated the item's modification date, also when
    it equals the creation date (left out otherwise, its default)."""
    fields = getattr(item, _FIELDS, None)
    return bool(fields and fields["stated_modification"])


def members(category, ids_in_file):
    """The category's members in the file, as older releases read
    membership: on the category."""
    return " ".join(
        sorted(
            each.id()
            for each in category.members()
            if each.id() in ids_in_file
        )
    )


def attachment_type(attachment):
    """A mail is a mid: link, which older releases cannot read as a
    mail: they get a link."""
    if attachment.type_ == "mail" and _is_mail_link(attachment.location()):
        return "uri"
    return attachment.type_


def _is_mail_link(location):
    return location.startswith("mid:")
