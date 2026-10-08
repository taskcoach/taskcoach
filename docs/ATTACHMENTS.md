# Attachments

What an attachment holds, how it is added, shown, opened and saved.
E-mail attachments have their own document:
[EMAIL_ATTACHMENTS.md](EMAIL_ATTACHMENTS.md).

## Decisions

- **Ruled by designer 2026-09-30:** the attachment list shows every
  column but the ID by default, in the main list and in the editors'
  attachment tabs; Location is a column. A settings file that already
  lists its columns keeps them.
- **Ruled by designer 2026-09-30:** a dropped e-mail keeps the mail's
  fields and a link to it, not the mail
  ([EMAIL_ATTACHMENTS.md](EMAIL_ATTACHMENTS.md#decisions)).
- **Ruled by designer 2026-09-29:** attachment styling is deferred; an
  attachment draws only its own style (D3 in
  [MASTER_SCHEDULER_REFACTOR.md](MASTER_SCHEDULER_REFACTOR.md#deferred-and-will-not-do),
  [APPEARANCE_STYLES.md](APPEARANCE_STYLES.md#todo)).

## Kinds

An attachment holds a reference, never the content, plus its own
subject, description, notes, colours and icon, all in the task file.
Tasks, notes and categories own attachments (`AttachmentOwner`), and
an attachment owns notes (`NoteOwner`).

| Kind | `type` in the file | Location | Opened with |
|---|---|---|---|
| File | `file` | a path | the system's program for the file |
| Link | `uri` | an address: a web page, a folder (`file://`), an Apple Mail message (`message:`) | the system's program for the address |
| E-mail | `mail` | a `mid:` link to the mail by its Message-ID | the mail program registered for `mid:` links |

A file stays where it is: moved, renamed or deleted, the attachment
points at nothing, and the list shows it with a red file icon. Its
path is absolute, or relative to Preferences > Files > Attachment base
directory (`file`/`attachmentbase`) when that is set and the file is
under it (`getRelativePath()`), so a folder of documents can move or
be shared between computers.

## Adding

- **Drop on a task, note or category** (list, tree, calendar), or on
  an editor's attachment tab (`AttachmentDropTargetMixin`,
  `gui/viewer/mixin.py`): a file becomes a file attachment, a folder a
  `file://` link, a dragged address a link, a mail an e-mail
  attachment. Dropped on an empty part of a task list, a new task
  holds them, named after the first. The drop target
  (`DropTarget`, `widgets/draganddrop.py`) tells the kinds apart
  ([EMAIL_ATTACHMENTS.md](EMAIL_ATTACHMENTS.md#the-drop) for mails).
- **Add attachment...** picks a file
  (`uicommand.AddAttachment`); an editor's attachment tab has New.
- A drop opens the owner's editor on its attachment tab and an editor
  for the new attachments.

## Opening

Open (`AttachmentOpen`) and Open all attachments (Shift+Ctrl+O,
`OpenAllAttachments`) call `open_attachments()`
(`gui/uicommand/uicommand.py`): each attachment's `open()` hands its
location to the system (`tools/openfile.py`: `os.startfile` on
Windows, `open` on macOS, `xdg-open` elsewhere); a file's relative
path is first joined to the attachment base directory. A failure shows
an error.

## Attachment List

`AttachmentViewer` (`gui/viewer/attachment.py`), in the main window
and on the editors' attachment tabs (settings sections
`attachmentviewer`, `attachmentviewerintaskeditor`, `...innoteeditor`,
`...incategoryeditor`, `config/defaults.py`).

| Column | Shows | Sort key |
|---|---|---|
| Type | Email, Link, Folder, File (always shown) | |
| Subject | the subject (always shown) | `subject` |
| Location | path, address or `mid:` link | `location` |
| From, From address, Sent | an e-mail's fields, empty for the others | `fromName`, `fromAddress`, `sentDateTime` |
| Description | the description | `description` |
| Notes | an icon when it has notes | |
| Creation date, Modification date | | `creationDateTime`, `modificationDateTime` |
| ID | the internal ID, hidden by default | `id` |

Sort keys are found by name (`Attachment.<key>SortFunction`), which is
why they are camelCase; the columns' names are the same strings.

## Editor

`AttachmentEditor` (`gui/dialog/editor.py`): the Description page
(`AttachmentSubjectPage`) shows Subject, Type (with its icon), Location
(Browse for a file), Description and the dates; then Notes, Appearance
and Path. An e-mail's page differs
([EMAIL_ATTACHMENTS.md](EMAIL_ATTACHMENTS.md#editor)).

## Model

`domain/attachment/attachment.py`: `Attachment` (location as an
`Attribute`, event `attachment.location`; sort keys; the e-mail fields
empty), `FileAttachment`, `URIAttachment`, `MailAttachment`.
`AttachmentFactory(location, type)` makes one from the file's `type`;
very old files named the kind by a `FILE:`, `URI:` or `MAIL:` prefix.
Commands: `AddAttachmentCommand`, `RemoveAttachmentCommand`,
`CutAttachmentCommand`, `EditAttachmentLocationCommand`
(`command/attachmentCommands.py`). What the exports write:
[EXPORTS.md](EXPORTS.md).

## In the File

An `attachment` node inside its owner's node: the base attributes
(`id`, dates, `subject`, appearance), `type`, `location` (always
written), an e-mail's fields, a `description` element and `note`
nodes. Defaults: [PERSISTENCE_XML.md](PERSISTENCE_XML.md#defaults).

## Before 2.0.3.0

- Up to file version 22, attachments were read from a
  `<name>_attachments` folder next to the task file (the reader still
  does, for those files).
- 1.x embedded a dropped mail in the task file (a `data` element).
  Since #378 (February 2026) that data is not read: the attachment
  keeps a placeholder location, `(embedded <extension> - data not
  migrated)`.
