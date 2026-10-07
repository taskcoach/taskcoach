# Synchronization

A possible future feature: the same tasks in Task Coach and on other
devices (phones, other computers, web calendars). Research only, no
code: **ruled by designer 2026-10-06** ("a future potential feature
but not ... an actual code feature at this time, only document what
you've found so far"). Add findings here as they come.

## Why

Task Coach runs on desktops only and never had an Android app; users
have asked for their tasks on phones since at least 2013 (the
SourceForge forum thread "Android?", still answered "no Android plans"
in January 2026).

## What Task Coach Had

- SyncML (Funambol servers): dropped in 2013 (38d6270b7, "Get rid of
  SyncML in its present form"); its leftovers removed in January 2026
  (58a4eb06b, #130).
- Sync with Task Coach's own iPhone app over the local network: removed
  in January 2026 (b4fa2efe1, 58a4eb06b).
- Todo.txt, a shared text file: removed 2026-10-06
  ([TODO_TXT.md](TODO_TXT.md)). Its lessons are below.

Kept for exchange, one way: the iCalendar export (tasks as `VTODO`,
efforts as `VEVENT`), CSV export and import, HTML export.

## CalDAV

The standard for calendars and tasks kept on a server (RFC 4791).
Tasks are iCalendar `VTODO` items (RFC 5545), the format the iCalendar
export already writes. CardDAV (RFC 6352) is the same for contacts;
tasks do not need it.

- Servers: Nextcloud, Open-Xchange (hosted by providers such as IONOS),
  SOGo, Radicale, Fastmail and others.
- Android: DAVx5 syncs the server's task lists into task apps such as
  Tasks.org, jtx Board and OpenTasks.
- Python: the `caldav` library (actively maintained, version 3).
- Subtasks: a child names its parent (`RELATED-TO;RELTYPE=PARENT`);
  the standard allows any depth. Apps differ in how deep they show and
  edit: some only one level.
- Categories: `CATEGORIES` is a flat list of labels, with no hierarchy.
  Task Coach's category tree would be flattened (`Parent/Child`) or
  reduced to the last name.
- Prerequisites: RFC 9253 adds relations such as `DEPENDS-ON`; support
  in apps not checked.

What a task would carry:

| Task Coach | VTODO |
|---|---|
| ID | `UID` |
| Subject, description | `SUMMARY`, `DESCRIPTION` |
| Planned start, due date | `DTSTART`, `DUE` |
| Completion date | `COMPLETED`, `STATUS:COMPLETED` |
| Percentage complete | `PERCENT-COMPLETE` |
| Priority | `PRIORITY` (0 to 9, 1 the highest; the export caps it at 3) |
| Recurrence | `RRULE` (some of Task Coach's options) |
| Reminder | `VALARM` |
| Parent task | `RELATED-TO` |
| Categories | `CATEGORIES` (flat) |
| Attachments | `ATTACH` (links) |

No standard place: efforts (time tracking), budget, fees, actual start,
notes beyond the description, the category tree. They can travel as
`X-` properties, which servers keep and other apps ignore.

## Lessons From Todo.txt

What a sync design needs, from what went wrong there:

- One record per task, with a stable ID (Task Coach's ID as `UID`),
  never one file compared line by line.
- The server's change tracking (an ETag per item, a sync token per
  list) to know what changed on each side.
- A deletion elsewhere never deletes silently: the task's efforts,
  notes and attachments go with it. Ask, or keep it, and make it
  undoable.
- A value the other side cannot hold is not cleared when it comes back
  (dates keep their times, categories stay the same categories).
- A rule decided up front for a task changed on both sides.

## Sources

- [RFC 4791, CalDAV](https://www.rfc-editor.org/rfc/rfc4791)
- [RFC 5545, iCalendar](https://www.rfc-editor.org/rfc/rfc5545)
  (`VTODO`, `RELATED-TO`, `CATEGORIES`)
- [RFC 9253, iCalendar relationships](https://www.rfc-editor.org/rfc/rfc9253.html)
- [python caldav](https://caldav.readthedocs.io/stable/tutorial.html)
- [Tasks.org and CalDAV subtasks](https://github.com/tasks/tasks/issues/3023)
- [Task Coach forum: Android?](https://sourceforge.net/p/taskcoach/discussion/users/thread/176a9f79/)
