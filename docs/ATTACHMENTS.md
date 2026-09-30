# Attachments

What an attachment holds, and what a dropped e-mail becomes.

## Kinds

An attachment holds a reference, never the content, plus its own
subject, description, notes, colours and icon, all in the task file.

| Type (in the file) | Location | Opened with |
|---|---|---|
| File (`file`) | a path | the system's program for the file |
| Link (`uri`) | an address: a web page, a folder (`file://`), an Apple Mail message (`message:`) | the system's program for the address |
| E-mail (`mail`) | a `mid:` link to the mail by its Message-ID | the mail program registered for `mid:` links |

A file stays where it is. Its path is absolute, or relative to
Preferences > Files > Attachment base directory when that is set.

## E-mail Attachments

**Ruled by designer 2026-09-30** (P31 in
[MASTER_SCHEDULER_REFACTOR.md](MASTER_SCHEDULER_REFACTOR.md#pre-existing-issues)):
a dropped mail keeps the mail's subject, sender and sent date, and a
link to it; not the mail, nor its text. The mail stays in the mail
program, where the link, the sender and the date find it.

| Field | In the file |
|---|---|
| Subject | `subject` |
| From (the sender's name) | `fromName` |
| From address | `fromAddress` |
| Sent, in local time | `sentDateTime` |
| Location: `mid:` and the Message-ID, URL-escaped (RFC 2392) | `location` |

- Each field has its own column in the attachment list. Every column
  but the ID shows by default.
- In the editor, a mail's fields show the mail as it is, read-only; its
  description, notes and appearance are the user's.
- A missing field is empty ([PERSISTENCE_XML.md](PERSISTENCE_XML.md#defaults)).

### The Drop

Each mail program hands the mail over its own way. Each path ends in
the same fields (`mailer.mail_fields()`), from which the viewer makes
the attachment (`onDropMail()`):

- **Thunderbird:** the mail's URI, in UTF-16. The mail is read from
  the profile's mailbox file or from the IMAP server
  (`mailer/thunderbird.py`).
- **Evolution, Claws Mail:** a file in their temporary folder
  (`mailer.read_mail()`).
- **Outlook (Windows):** the mails selected in Outlook, read through
  Outlook (`mailer/outlook.py`). Not tested since the 2026-09-30
  rewrite.
- **Apple Mail:** a `message:` link, kept as a link attachment.

Dropped on an empty part of a task list, the mail makes a new task
with its subject, holding the attachment.

### Opening

The `mid:` link goes to the system, like any link. Evolution is
registered for these links. Thunderbird opens them since version 87
where it is registered for them; some Linux packages do not register
it. Outlook does not open them.

## Before 2.0.3.0

- Up to file version 22, attachments were read from a
  `<name>_attachments` folder next to the task file.
- 1.x embedded a dropped mail in the task file. Since #378 (February
  2026) that data is not read: the attachment keeps a placeholder
  location.
- Later, a dropped mail's location was a temporary copy, deleted at
  exit. These attachments load as they are, with the mail's subject
  and, as their description, its text.
