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

import test
from taskcoachlib.domain import attachment, category, date, effort, note
from taskcoachlib.domain import task
from taskcoachlib.domain.base import NO_ICON
from taskcoachlib.persistence.xml.defaults import DEFAULTS

# Defaults that are another field's value, not a new item's
DERIVED = {"creationDateTime", "modificationDateTime", "reminderBeforeSnooze"}


def appearance(item):
    return dict(
        fgColor=item.foregroundColor(),
        bgColor=item.backgroundColor(),
        font=item.font(),
        icon=item.icon_id(),
        noIcon=item.icon_id() == NO_ICON,
        ordering=item.ordering(),
    )


def composite(item):
    return dict(
        appearance(item),
        subject=item.subject(),
        description=item.description(),
        expandedContexts=item.expandedContexts(),
        previewShown=item.is_preview_shown(),
    )


class DefaultsTest(test.TestCase):
    """A new item holds each field's default in the list, so an item
    saved without an attribute reads back as it was
    (docs/PERSISTENCE_XML.md, Defaults)."""

    def setUp(self):
        super().setUp()
        new_task = task.Task()
        recurrence = date.Recurrence()
        self.fields = dict(
            task=dict(
                composite(new_task),
                plannedstartdate=new_task.plannedStartDateTime(),
                duedate=new_task.dueDateTime(),
                actualstartdate=new_task.actualStartDateTime(),
                completiondate=new_task.completionDateTime(),
                percentageComplete=new_task.percentageComplete(),
                budget=new_task.budget(),
                plannedDuration=new_task.plannedDuration(),
                plannedDurationMode=new_task.plannedDurationMode(),
                priority=new_task.priority(),
                hourlyFee=new_task.hourlyFee(),
                fixedFee=new_task.fixedFee(),
                reminder=new_task.reminder(),
                prerequisites=new_task.prerequisites(),
                shouldMarkCompletedWhenAllChildrenCompleted=(
                    new_task.shouldMarkCompletedWhenAllChildrenCompleted()
                ),
                categories=new_task.categories(),
            ),
            recurrence=dict(
                unit=recurrence.unit,
                amount=recurrence.amount,
                count=recurrence.count,
                max=recurrence.max,
                stop_datetime=recurrence.stop_datetime,
                sameWeekday=recurrence.sameWeekday,
                recurBasedOnCompletion=recurrence.recurBasedOnCompletion,
                weekdays=recurrence.weekdays,
            ),
        )
        new_note = note.Note()
        self.fields["note"] = dict(
            composite(new_note), categories=new_note.categories()
        )
        new_category = category.Category("")
        self.fields["category"] = dict(
            composite(new_category),
            filtered=new_category.isFiltered(),
            exclusiveSubcategories=new_category.hasExclusiveSubcategories(),
            stylePriority=new_category.stylePriority(),
        )
        # An attachment's subject is its file name unless given
        new_attachment = attachment.FileAttachment("plan.txt")
        self.fields["attachment"] = dict(
            appearance(new_attachment),
            previewShown=new_attachment.is_preview_shown(),
        )
        new_mail = attachment.MailAttachment("mid:1@example.com")
        self.fields["mail"] = dict(
            fromName=new_mail.from_name(),
            fromAddress=new_mail.from_address(),
            sentDateTime=new_mail.sent_datetime(),
        )
        new_effort = effort.Effort(new_task)
        self.fields["effort"] = dict(
            stop=new_effort.getStop(),
            entryMode=new_effort.entryMode(),
            description=new_effort.description(),
            previewShown=new_effort.is_preview_shown(),
        )

    def test_new_items_hold_the_defaults(self):
        for kind, fields in self.fields.items():
            self.assertEqual(
                {name: DEFAULTS[name][0] for name in fields}, fields, kind
            )

    def test_every_default_is_checked(self):
        checked = {name for fields in self.fields.values() for name in fields}
        self.assertEqual(set(DEFAULTS) - DERIVED, checked)
