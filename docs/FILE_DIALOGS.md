# File Dialogs

Where each file dialog opens. **Ruled by designer 2026-10-06** (P240
in [REFINEMENT_REFACTOR.md](REFINEMENT_REFACTOR.md#pre-existing-issues):
"proceed ... as you propose"), the convention of Microsoft's
guidelines for its common dialogs (Apple and GNOME leave it to the
application):

1. The folder last chosen in a dialog of the same kind this session.
2. Before that, the open task file's folder.
3. With no saved task file, the Documents folder: XDG's
   `XDG_DOCUMENTS_DIR` on Linux, the home folder when it is not set
   (`wx.StandardPaths.GetDocumentsDir()`).

| Kind | Dialogs |
|---|---|
| Task files | Open, Merge, Save selection, Save As |
| Each export | Export as HTML, as CSV, as iCalendar ([EXPORTS.md](EXPORTS.md)) |
| Each import | Import CSV, Import template |
| Attachments | Add attachment, an attachment editor's Browse |

Exceptions, kept from the releases:

- **Save As** opens next to the current file, suggesting "name
  copy.tsk"; with no saved file, as the rule says.
- **Attachments** keep the folder last chosen across sessions
  (`[file] lastattachmentpath`); without one, rules 2 and 3.
- **Restoring a backup** opens in the backed-up file's folder.

Before, the dialogs had four rules: the task file dialogs and the
exports opened in the home folder until a file was opened, then in
its folder, and a Save As into another folder left them in the old
one; Import CSV, Import template and Add attachment opened in the
folder Task Coach was started from, on Windows its program folder
(`launcher.pyw` changes to it).

Code: `IOController.start_folder()` and `attachment_folder()` in
`taskcoachlib/gui/iocontroller.py`. Tests: `FileDialogFolderTest` in
`tests/unittests/guiTests/IOControllerTest.py`.
