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
8. **Ruled by designer 2026-10-04**: mail works with the local mail
   programs only, never over the network: "all of the email
   functionalities should only coordinate with local software apps,
   nothing over the network. If the app cannot provide all those
   fields with the DnD, then we should only get the ones that are
   communicated via DnD or published apis/open-methods." Done
   2026-10-04 (To Do 16 in
   [REFINEMENT_REFACTOR.md](REFINEMENT_REFACTOR.md#to-do)): the IMAP
   reader, its password dialog and `keyring` are gone, and so is the
   reading of Thunderbird's profile, whose message numbers are keys
   into Thunderbird's own index (its `.msf` files), not the mails'
   places in the folder files ([The Drop](#the-drop)). Mail (Ctrl+M)
   sends nothing either: it opens the mail program with a new message
   through a `mailto:` link, the user sends it. A mail program that
   refuses a message without recipient gets it again addressed to
   `recipient@example.com`, **ruled by designer 2026-10-05** ("use
   the most common one ... something like recipient at example.com"):
   reserved for examples (RFC 2606) and accepting no mail (null MX,
   RFC 7505), so a message sent unchanged bounces. Any other failure
   is shown. It used to be `recipient@domain.com`, a company's domain
   whose mail is delivered (P233 in
   [REFINEMENT_REFACTOR.md](REFINEMENT_REFACTOR.md#pre-existing-issues)).

## Fields

| Field | In the file | From the mail |
|---|---|---|
| Subject | `subject` | `Subject`, decoded |
| From | `fromName` | the first `From` address's display name, empty when there is none |
| From address | `fromAddress` | its address |
| Sent | `sentDateTime` | `Date`, in local time, whole seconds; not set when missing or unreadable |
| Location | `location` | `mid:` and the `Message-ID` without its angle brackets, escaped as a URL (RFC 2392); empty when there is none |

`type="mail"`; while releases before 2.0.3.0 are supported it is
written as `type="uri"`, the link they keep, and read back as a mail
by its `mid:` link. A mail without a link stays `type="mail"`, which
they drop ([PERSISTENCE_XML.md](PERSISTENCE_XML.md#versions-and-compatibility)).
A missing attribute is empty or not set
([PERSISTENCE_XML.md](PERSISTENCE_XML.md#defaults)). The model:
`MailAttachment` (`domain/attachment/attachment.py`); every attachment
answers `from_name()`, `from_address()` and `sent_datetime()`, empty
for files and links, so the columns and sort keys work on mixed lists.

## Reading a Mail

`mailer.parse_mail()` (`mailer/__init__.py`) parses the bytes with
`email.policy.default`, which decodes encoded headers (accents) and
reads addresses and dates; `mail_fields()` makes the fields.
`read_mails()` reads a file a mail program dropped: one mail, or
several in mbox format (a `From ` line before each). Headers in UTF-8
(RFC 6532) or Latin-1 are read as text, never as bytes the task file
could not hold.

## The Drop

Each mail program hands its mails over its own way; Task Coach reads
them by one set of rules, so a program need not be named, and each
path ends in the same fields; the viewer makes one attachment per mail,
in one command (`on_drop_mail()`, `gui/viewer/mixin.py`). The drop target
is `DropTarget` (`widgets/draganddrop.py`).

- **A mail file in a temporary folder:** a dropped file that starts as
  a mail (an mbox `From ` line, or headers with a sender) and lies under
  the system's temporary folder, or in a folder named `tmp` or `temp`
  (or one below it), where the programs write what they drag, is read
  as the mails it holds (`mailer.dropped_mails()`). A mail saved
  elsewhere stays a file attachment: the file is kept.
- **Thunderbird's message URIs as text** (`mailbox-message://`,
  `imap-message://`), one or several, even run together, or a macOS
  link (`public.url`) to a message (`mailbox:`, `imap:`): on X11 the
  `.eml` files the same drag offers later in its list are asked of
  Thunderbird while the drop is handled (`x11_drag_files()`: GTK's
  clipboard on the `XdndSelection`, for `text/uri-list`; PyGObject,
  GTK's X11 backend) and read as above. Otherwise not read: a message,
  once the drop has ended, says to save the mail as a file and drag
  the file (`thunderbird.message_uris()`, `unreadable()`). For URIs
  as text the log has a `[MAIL]` line with the mails read from the
  drag's files. A URI's number is a
  key into Thunderbird's index (Thunderbird 102 to 140,
  `nsParseMailbox.cpp` and `nsMsgDatabase::CreateNewHdr()`: the next
  free row), so the 2.0.3.0 reader, which took it for the mail's place
  in the folder file, attached an empty or another mail; an IMAP
  mail's is a number on the server.
- **Outlook (classic)**, recognized by its own `RenPrivateMessages`
  format (not `Object Descriptor`, which any OLE program's drag offers):
  the mails are asked from the running Outlook (`mailer/outlook.py`).
- Anything else: a file, a link or text, as before.

Which format wx takes: GTK the source's first format Task Coach
accepts (Wayland reverses the source's order); Windows and macOS Task
Coach's first format the source offers, in the order `public.url`,
Outlook's, text, files. macOS rewrites a format name with no dot, so
there only `public.url` and files can match.

### By Program and System

Researched 2026-09-30 from the programs' sources; each row is a test
in `MailDropTest`.

| Program | System | What arrives | Result |
|---|---|---|---|
| Evolution 3.44 and later | Linux | a `text/uri-list` of one mbox file with every mail, `/tmp/drag-n-drop-XXXXXX/<YYYYMMDDHHMMSS>_<subject>` (`.mbox` since 3.56; several: `Messages from <folder>`) | mails |
| Evolution before 3.44 | Linux | the same, in `~/.cache/evolution/tmp/drag-n-drop-XXXXXX/` | mails |
| Evolution Flatpak | Linux | the same file straight in `~/.var/app/org.gnome.Evolution/cache/evolution/tmp/` | mails |
| Thunderbird 115 and later | Linux X11, one message | text first: the message's URI; the `.eml` file later in the list | mails, the file asked of the drag (without PyGObject, as in the AppImage: a message says why) |
| Thunderbird | Linux Wayland, or several messages | a `text/uri-list` of `.eml` files, `/tmp/dnd_file*/<subject>.eml`, deleted after 5 minutes | mails |
| Thunderbird | Windows | text first: the URI, several run together | not read: a message says why |
| Thunderbird | macOS | `public.url`: the message's URL; one message only | not read: a message says why |
| Claws Mail | Linux | a `text/uri-list`, one file per mail, `~/.claws-mail/tmp/<subject>.<number>.txt` | mails |
| Claws Mail, mail without a subject | Linux | the mail's own file in the mail folder | a file attachment |
| Outlook (classic) | Windows | `RenPrivateMessages`, `FileGroupDescriptorW`, `FileContents` (IStorage, which wx cannot read) | mails, from the running Outlook; not tested |
| Apple Mail | macOS | a `message:` link with the Message-ID | a link attachment |
| KMail | Linux | `akonadi:` links, which wx refuses in a `text/uri-list` | nothing |

Not supported: Geary (drags only within itself), the new Outlook for
Windows (a delayed file drop wx cannot take), Outlook for Mac
(proprietary formats), Claws Mail on Windows (no drag to other
programs). Thunderbird has not offered `text/x-moz-message` to other
programs since version 52 (2017): it lives only inside its
`application/x-moz-custom-clipdata`.

Sources: Evolution 3.56.2 `src/mail/message-list.c` (drag types),
`src/mail/em-utils.c` (`em_utils_selection_set_urilist`), commit
409c789f (temporary files moved to `/tmp`, 3.44) and 8f17ed9e
(Flatpak); Thunderbird 140 `mail/base/content/about3Pane.js` (drag
start), `mailnews/local/src/nsParseMailbox.cpp` and
`mailnews/db/msgdb/src/nsMsgDatabase.cpp` (message keys, comm-esr102
to comm-esr140), Gecko `dom/events/DataTransfer.cpp` (custom
clipdata, bug 1226977), `widget/gtk/nsDragSessionSource.cpp`
(`GetSourceList()`, the targets' order),
`widget/windows/nsDataObj.cpp`, `widget/cocoa/nsDragService.mm`; Claws
Mail 4.4.0 `src/summaryview.c`; KMail `messagelib`
`messagelist/src/widget.cpp`; wxWidgets 3.2.7 `src/gtk/dnd.cpp`,
`src/msw/ole/droptgt.cpp`, `src/osx/carbon/dataobj.cpp`; Outlook's
formats from a Qt drop target's listing (forum.qt.io, topic 70101) and
github.com/yasoonOfficial/outlook-dndprotocol.

### Testing

- `tests/unittests/widgetTests/MailDropTest.py`: each program and
  system of the table, the data wx hands over.
- `tests/unittests/MailerTest.py`: reading mails (encoded headers,
  UTF-8 or Latin-1 in headers, mbox files).
- `tools/fake_mail_drag.py`: a window that drags as each program does,
  with the files where the program writes them, into the running
  application. What a wx drag source cannot make (KMail's links,
  Outlook's formats, macOS promises) is left to the tests.

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
