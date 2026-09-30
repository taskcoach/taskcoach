# E-mail Attachments

What a mail dragged from a mail program becomes, how it is read, shown
and opened. Attachments in general: [ATTACHMENTS.md](ATTACHMENTS.md).

## Decisions

**Ruled by designer 2026-09-30** (P31 in
[MASTER_SCHEDULER_REFACTOR.md](MASTER_SCHEDULER_REFACTOR.md#pre-existing-issues)):

1. A dropped mail keeps the least that finds it again: its subject,
   sender and sent date, and a link to it. Not the mail, nor its text:
   the text would bloat the task file, and the mail stays in the mail
   program. Later: opening the mail program's search on these fields,
   and the mail's own attachments.
2. Each value has its own field, not text in the description: the
   sender's name (From) and address (From address) apart, the sent
   date (Sent), and the Message-ID as a `mid:` link in the location.
3. The editor shows every field. They show the mail as it is, so they
   are read-only; only the description, the notes and the appearance
   are the user's.
4. Each field has a column in the attachment list, as has the
   location; every column but the ID shows by default
   ([ATTACHMENTS.md](ATTACHMENTS.md#decisions)).
5. One design for every mail program: whatever a program drags becomes
   the same fields. Outlook gets the `mid:` link too; its own way of
   opening a mail (by Outlook's ID, from a temporary file) is gone: it
   worked only until Task Coach exited.
6. Open hands the `mid:` link to the system, like any link.
7. No new package: Python's standard `email` package reads the mails.
   `chardet` stays, for the CSV import.

## Fields

| Field | In the file | From the mail |
|---|---|---|
| Subject | `subject` | `Subject`, decoded |
| From | `fromName` | the first `From` address's display name, empty when there is none |
| From address | `fromAddress` | its address |
| Sent | `sentDateTime` | `Date`, in local time, whole seconds; not set when missing or unreadable |
| Location | `location` | `mid:` and the `Message-ID` without its angle brackets, escaped as a URL (RFC 2392); empty when there is none |

`type="mail"`. A missing attribute is empty or not set
([PERSISTENCE_XML.md](PERSISTENCE_XML.md#defaults)). The model:
`MailAttachment` (`domain/attachment/attachment.py`); every attachment
answers `from_name()`, `from_address()` and `sent_datetime()`, empty
for files and links, so the columns and sort keys work on mixed lists.

## Reading a Mail

`mailer.parse_mail()` (`mailer/__init__.py`) parses the bytes with
`email.policy.default`, which decodes encoded headers (accents) and
reads addresses and dates; `mail_fields()` makes the fields.
`read_mails()` reads a file a mail program dropped: one mail, or
several in mbox format (a `From ` line before each).

## The Drop

Each mail program hands the mails over its own way; each path ends in
the same fields, and the viewer makes one attachment per mail, in one
command (`onDropMail()`, `gui/viewer/mixin.py`). The drop target is
`DropTarget` (`widgets/draganddrop.py`).

| Program | What it drags | How Task Coach reads it |
|---|---|---|
| Evolution | a file in mbox format, one or several mails, in a `drag-n-drop-XXXXXX` folder: in `/tmp` (seen 2026-09-30), before in `~/.cache/evolution/tmp` | a file drop whose folder is named so: `read_mails()` |
| Claws Mail | a file in `~/.claws-mail/tmp` | a file drop from that folder: `read_mails()` |
| Thunderbird | the message's URI (`mailbox-message://`, `imap-message://`), UTF-16 (`text/x-moz-message`) | the mail from the profile's mailbox file or the IMAP server (`mailer/thunderbird.py`) |
| Outlook (Windows) | its own formats | the selected mails, asked from the running Outlook (`mailer/outlook.py`); not tested since the 2026-09-30 rewrite |
| Apple Mail | a `message:` link | kept as a link attachment |

On GTK, a dropped file list (`text/uri-list`) reaches the file names
object, so every file drop takes one path (`onFileDrop()`), which
hands those two programs' files to the mail drop (P33).

## Editor

A mail's Description page (`AttachmentSubjectPage`,
`gui/dialog/editor.py`): Subject, Type, Location, From, From address
and Sent, drawn as text, not in input boxes, since they cannot change
([DEVELOPMENT.md](DEVELOPMENT.md#design), "Read-only looks read-only";
a long value is cut, whole in its tooltip); then the Description,
which takes the focus, whatever column opened the editor. Several attachments with a mail among them: the subject and
location are read-only and empty.

## Opening

The `mid:` link goes to the system, like any link. Evolution is
registered for these links. Thunderbird opens them since version 87
where it is registered for them; some Linux packages do not register
it. Outlook does not open them.

## Before 2.0.3.0

- 1.x embedded a dropped mail in the task file; since #378 (February
  2026) that data is not read
  ([ATTACHMENTS.md](ATTACHMENTS.md#before-2030)).
- Later, a dropped mail's location was a temporary copy of the mail,
  deleted at exit, and its text the description. No save worked while
  the copy existed (Python 2 code), and once it was gone the
  attachment and its notes vanished on the next open (P31). Such
  attachments now load as they are.
