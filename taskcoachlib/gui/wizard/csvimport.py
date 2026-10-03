"""
Task Coach - Your friendly task manager
Copyright (C) 2011 Task Coach developers <developers@taskcoach.org>

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

from taskcoachlib import meta
from taskcoachlib.i18n import _
import chardet
import codecs
import locale
import wx
import csv
import io
import wx.grid as gridlib
import wx.adv as wiz


def _encodings():
    """The encodings the wizard offers: (Python codec, name, script)."""
    return [
        ("utf-8", "UTF-8", ""),
        ("utf-8-sig", "UTF-8", _("with byte order mark")),
        ("utf-16", "UTF-16", ""),
        ("cp1252", "Windows-1252", _("Western European")),
        ("iso8859-1", "ISO-8859-1", _("Western European")),
        ("iso8859-15", "ISO-8859-15", _("Western European")),
        ("mac-roman", "Mac Roman", _("Western European")),
        ("cp1250", "Windows-1250", _("Central European")),
        ("iso8859-2", "ISO-8859-2", _("Central European")),
        ("cp1251", "Windows-1251", _("Cyrillic")),
        ("koi8-r", "KOI8-R", _("Cyrillic")),
        ("cp1253", "Windows-1253", _("Greek")),
        ("cp1254", "Windows-1254", _("Turkish")),
        ("cp1255", "Windows-1255", _("Hebrew")),
        ("cp1256", "Windows-1256", _("Arabic")),
        ("cp1257", "Windows-1257", _("Baltic")),
        ("cp1258", "Windows-1258", _("Vietnamese")),
        ("shift_jis", "Shift JIS", _("Japanese")),
        ("euc_jp", "EUC-JP", _("Japanese")),
        ("gb18030", "GB18030", _("Chinese, simplified")),
        ("big5", "Big5", _("Chinese, traditional")),
        ("euc_kr", "EUC-KR", _("Korean")),
    ]


def _codec(name):
    """Python's own name for an encoding, or None if it has none."""
    try:
        return codecs.lookup(name).name
    except (LookupError, TypeError):
        return None


def encoding_choices(guess):
    """The encodings to offer, as (codec, label), and the guessed one's
    index: chardet's guess, plain ASCII read as UTF-8, no guess as the
    system's encoding; a guess not in the list comes first."""
    choices = [
        (_codec(codec), "%s (%s)" % (name, script) if script else name)
        for codec, name, script in _encodings()
    ]
    codec = _codec(guess) if guess else None
    if codec == "ascii":
        codec = "utf-8"
    codec = codec or _codec(locale.getpreferredencoding(False)) or "utf-8"
    codecs_offered = [each for each, label in choices]
    if codec not in codecs_offered:
        choices.insert(0, (codec, guess or codec))
        return choices, 0
    return choices, codecs_offered.index(codec)


class CSVDialect(csv.Dialect):
    def __init__(
        self, delimiter=",", quotechar='"', doublequote=True, escapechar=None
    ):
        self.delimiter = delimiter
        self.quotechar = quotechar
        self.quoting = csv.QUOTE_MINIMAL
        self.lineterminator = "\r\n"
        self.doublequote = doublequote
        self.escapechar = escapechar

        csv.Dialect.__init__(self)


class CSVImportOptionsPage(wiz.WizardPageSimple):
    def __init__(self, filename, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.delimiter = wx.Choice(self, wx.ID_ANY)
        self.delimiter.Append(_("Comma"))
        self.delimiter.Append(_("Tab"))
        self.delimiter.Append(_("Space"))
        self.delimiter.Append(_("Colon"))
        self.delimiter.Append(_("Semicolon"))
        self.delimiter.Append(_("Pipe"))
        self.delimiter.SetSelection(0)

        # Chosen by the user when chardet's guess shows garbled
        self.encoding_choice = wx.Choice(self)

        self.date = wx.Choice(self)
        self.date.Append(_("DD/MM (day first)"))
        self.date.Append(_("MM/DD (month first)"))
        self.date.SetSelection(0)

        self.quoteChar = wx.Choice(self, wx.ID_ANY)
        self.quoteChar.Append(_("Simple quote"))
        self.quoteChar.Append(_("Double quote"))
        self.quoteChar.SetSelection(1)

        self.quotePanel = wx.Panel(self, wx.ID_ANY)
        self.doubleQuote = wx.RadioButton(
            self.quotePanel, wx.ID_ANY, _("Double it")
        )
        self.doubleQuote.SetValue(True)
        self.escapeQuote = wx.RadioButton(
            self.quotePanel, wx.ID_ANY, _("Escape with")
        )
        self.escapeChar = wx.TextCtrl(
            self.quotePanel, wx.ID_ANY, "\\", size=(50, -1)
        )
        self.escapeChar.Enable(False)
        self.escapeChar.SetMaxLength(1)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        hsizer.Add(self.doubleQuote, 1, wx.ALL, 3)
        hsizer.Add(self.escapeQuote, 1, wx.ALL, 3)
        hsizer.Add(self.escapeChar, 1, wx.ALL, 3)
        self.quotePanel.SetSizer(hsizer)

        self.importSelectedRowsOnly = wx.CheckBox(
            self, wx.ID_ANY, _("Import only the selected rows")
        )
        self.importSelectedRowsOnly.SetValue(False)

        self.hasHeaders = wx.CheckBox(
            self, wx.ID_ANY, _("First line describes fields")
        )
        self.hasHeaders.SetValue(True)

        self.grid = gridlib.Grid(self)
        self.grid.SetRowLabelSize(0)
        self.grid.SetColLabelSize(0)
        self.grid.CreateGrid(0, 0)
        self.grid.EnableEditing(False)
        self.grid.SetSelectionMode(gridlib.Grid.GridSelectRows)
        self.grid.SetMinSize((-1, 150))  # A few rows of the preview

        vsizer = wx.BoxSizer(wx.VERTICAL)
        grid_sizer = wx.FlexGridSizer(0, 2, 0, 0)

        grid_sizer.Add(
            wx.StaticText(self, wx.ID_ANY, _("Encoding")),
            0,
            wx.ALIGN_CENTRE_VERTICAL | wx.ALL,
            3,
        )
        grid_sizer.Add(self.encoding_choice, 0, wx.ALL, 3)

        grid_sizer.Add(
            wx.StaticText(self, wx.ID_ANY, _("Delimiter")),
            0,
            wx.ALIGN_CENTRE_VERTICAL | wx.ALL,
            3,
        )
        grid_sizer.Add(self.delimiter, 0, wx.ALL, 3)

        grid_sizer.Add(
            wx.StaticText(self, wx.ID_ANY, _("Date format")),
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.ALL,
            3,
        )
        grid_sizer.Add(self.date, 0, wx.ALL, 3)

        grid_sizer.Add(
            wx.StaticText(self, wx.ID_ANY, _("Quote character")),
            0,
            wx.ALIGN_CENTRE_VERTICAL | wx.ALL,
            3,
        )
        grid_sizer.Add(self.quoteChar, 0, wx.ALL, 3)

        grid_sizer.Add(
            wx.StaticText(self, wx.ID_ANY, _("Escape quote")),
            0,
            wx.ALIGN_CENTRE_VERTICAL | wx.ALL,
            3,
        )
        grid_sizer.Add(self.quotePanel, 0, wx.ALL, 3)

        grid_sizer.Add(self.importSelectedRowsOnly, 0, wx.ALL, 3)
        grid_sizer.Add((0, 0))

        grid_sizer.Add(self.hasHeaders, 0, wx.ALL, 3)
        grid_sizer.Add((0, 0))

        grid_sizer.AddGrowableCol(1)
        vsizer.Add(grid_sizer, 0, wx.EXPAND | wx.ALL, 3)

        vsizer.Add(self.grid, 1, wx.EXPAND | wx.ALL, 3)

        self.SetSizer(vsizer)

        self.headers = None

        self.filename = filename
        with open(filename, "rb") as csv_file:
            guess = chardet.detect(csv_file.read())["encoding"]
        self.encodings, index = encoding_choices(guess)
        for codec, label in self.encodings:
            self.encoding_choice.Append(label)
        self.encoding_choice.SetSelection(index)
        self.encoding = self.encodings[index][0]
        self.OnOptionChanged(None)

        self.encoding_choice.Bind(wx.EVT_CHOICE, self.on_encoding_chosen)

        self.delimiter.Bind(wx.EVT_CHOICE, self.OnOptionChanged)
        self.quoteChar.Bind(wx.EVT_CHOICE, self.OnOptionChanged)
        self.hasHeaders.Bind(wx.EVT_CHECKBOX, self.OnOptionChanged)
        self.doubleQuote.Bind(wx.EVT_RADIOBUTTON, self.OnOptionChanged)
        self.escapeQuote.Bind(wx.EVT_RADIOBUTTON, self.OnOptionChanged)
        self.escapeChar.Bind(wx.EVT_TEXT, self.OnOptionChanged)

    def on_encoding_chosen(self, event):
        self.encoding = self.encodings[self.encoding_choice.GetSelection()][0]
        self.OnOptionChanged(event)

    def OnOptionChanged(self, event):  # pylint: disable=W0613
        self.escapeChar.Enable(self.escapeQuote.GetValue())

        if self.filename is None:
            self.grid.SetRowLabelSize(0)
            self.grid.SetColLabelSize(0)
            if self.grid.GetNumberCols():
                self.grid.DeleteRows(0, self.grid.GetNumberRows())
                self.grid.DeleteCols(0, self.grid.GetNumberCols())
        else:
            if self.doubleQuote.GetValue():
                doublequote = True
                escapechar = None
            else:
                doublequote = False
                escapechar = self.escapeChar.GetValue()[:1] or None
            self.dialect = CSVDialect(
                delimiter={0: ",", 1: "\t", 2: " ", 3: ":", 4: ";", 5: "|"}[
                    self.delimiter.GetSelection()
                ],
                quotechar={0: "'", 1: '"'}[self.quoteChar.GetSelection()],
                doublequote=doublequote,
                escapechar=escapechar,
            )

            # As the import reads it: bytes the encoding cannot read
            # show as replacement characters, asking for another one
            with open(
                self.filename,
                encoding=self.encoding,
                errors="replace",
                newline="",
            ) as fp:
                text = fp.read()
            reader = csv.reader(io.StringIO(text), dialect=self.dialect)

            if self.hasHeaders.GetValue():
                self.headers = next(reader, [])
            else:
                # Empty fields at the end of a line may be omitted
                hsize = 0
                for line in reader:
                    hsize = max(hsize, len(line))
                self.headers = [_("Field #%d") % idx for idx in range(hsize)]
                reader = csv.reader(io.StringIO(text), dialect=self.dialect)

            if self.grid.GetNumberCols():
                self.grid.DeleteRows(0, self.grid.GetNumberRows())
                self.grid.DeleteCols(0, self.grid.GetNumberCols())
            self.grid.InsertCols(0, len(self.headers))

            self.grid.SetColLabelSize(20)
            for idx, header in enumerate(self.headers):
                self.grid.SetColLabelValue(idx, header)

            lineno = 0
            for line in reader:
                self.grid.InsertRows(lineno, 1)
                for idx, value in enumerate(line):
                    if idx < self.grid.GetNumberCols():
                        self.grid.SetCellValue(lineno, idx, value)
                lineno += 1

    def GetOptions(self):
        return dict(
            dialect=self.dialect,
            dayfirst=self.date.GetSelection() == 0,
            importSelectedRowsOnly=self.importSelectedRowsOnly.GetValue(),
            selectedRows=self.GetSelectedRows(),
            hasHeaders=self.hasHeaders.GetValue(),
            filename=self.filename,
            encoding=self.encoding,
            fields=self.headers,
        )

    def GetSelectedRows(self):
        selected_rows = []
        for block in self.grid.GetSelectedRowBlocks():
            selected_rows.extend(
                range(block.GetTopRow(), block.GetBottomRow() + 1)
            )
        return selected_rows

    def CanGoNext(self):
        if self.filename is not None:
            self.GetNext().SetOptions(self.GetOptions())
            return True, None
        return False, _("Please select a file.")


class CSVImportMappingPage(wiz.WizardPageSimple):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # (field name, multiple values allowed)

        self.fields = [
            (_("None"), True),
            (_("ID"), False),
            (_("Subject"), False),
            (_("Description"), True),
            (_("Category"), True),
            (_("Priority"), False),
            (_("Planned start date"), False),
            (_("Due date"), False),
            (_("Actual start date"), False),
            (_("Completion date"), False),
            (_("Reminder date"), False),
            (_("Budget"), False),
            (_("Fixed fee"), False),
            (_("Hourly fee"), False),
            (_("Percent complete"), False),
        ]
        self.choices = []
        self.interior = wx.ScrolledWindow(self)
        self.interior.EnableScrolling(False, True)
        self.interior.SetScrollRate(10, 10)

        sizer = wx.BoxSizer()
        sizer.Add(self.interior, 1, wx.EXPAND)
        self.SetSizer(sizer)

    def SetOptions(self, options):
        self.options = options

        if self.interior.GetSizer():
            self.interior.GetSizer().Clear(True)

        for child in self.interior.GetChildren():
            self.interior.RemoveChild(child)
        self.choices = []

        gsz = wx.FlexGridSizer(0, 2, 4, 2)

        gsz.Add(
            wx.StaticText(
                self.interior, wx.ID_ANY, _("Column header in CSV file")
            )
        )
        gsz.Add(
            wx.StaticText(
                self.interior, wx.ID_ANY, _("%s attribute") % meta.name
            )
        )
        gsz.Add((3, 3))
        gsz.Add((3, 3))
        tcFieldNames = [field[0] for field in self.fields]
        for fieldName in options["fields"]:
            gsz.Add(
                wx.StaticText(self.interior, wx.ID_ANY, fieldName),
                flag=wx.ALIGN_CENTER_VERTICAL,
            )

            choice = wx.Choice(self.interior, wx.ID_ANY)
            for tcFieldName in tcFieldNames:
                choice.Append(tcFieldName)
            choice.SetSelection(self.findFieldName(fieldName, tcFieldNames))
            self.choices.append(choice)

            gsz.Add(choice, flag=wx.ALIGN_CENTER_VERTICAL)

        gsz.AddGrowableCol(1)
        self.interior.SetSizer(gsz)
        gsz.Layout()

    def findFieldName(self, fieldName, fieldNames):
        def fieldNameIndex(fieldName, fieldNames):
            return (
                fieldNames.index(fieldName) if fieldName in fieldNames else 0
            )

        index = fieldNameIndex(fieldName, fieldNames)
        return (
            index
            if index
            else fieldNameIndex(
                fieldName[:6], [fieldName[:6] for fieldName in fieldNames]
            )
        )

    def CanGoNext(self):
        wrongFields = []
        countNotNone = 0

        for index, (fieldName, canMultiple) in enumerate(self.fields):
            count = 0
            for choice in self.choices:
                if choice.GetSelection() == index:
                    count += 1
                if choice.GetSelection() != 0:
                    countNotNone += 1
            if count > 1 and not canMultiple:
                wrongFields.append(fieldName)

        if countNotNone == 0:
            return False, _("No field mapping.")

        if len(wrongFields) == 1:
            return (
                False,
                _('The "%s" field cannot be selected several times.')
                % wrongFields[0],
            )

        if len(wrongFields):
            return False, _(
                "The fields %s cannot be selected several times."
            ) % ", ".join(['"%s"' % fieldName for fieldName in wrongFields])

        return True, None

    def GetOptions(self):
        options = dict(self.options)
        options["mappings"] = [
            self.fields[choice.GetSelection()][0] for choice in self.choices
        ]
        return options


class CSVImportWizard(wiz.Wizard):
    def __init__(self, filename, *args, **kwargs):
        kwargs["style"] = wx.RESIZE_BORDER | wx.DEFAULT_DIALOG_STYLE
        super().__init__(*args, **kwargs)

        self.optionsPage = CSVImportOptionsPage(filename, self)
        self.mappingPage = CSVImportMappingPage(self)
        self.optionsPage.SetNext(self.mappingPage)
        self.mappingPage.SetPrev(self.optionsPage)

        self.SetPageSize((600, -1))
        # The wizard's size fits the pages, the preview grid included
        self.GetPageAreaSizer().Add(self.optionsPage)

        self.Bind(wiz.EVT_WIZARD_PAGE_CHANGING, self.OnPageChanging)
        self.Bind(wiz.EVT_WIZARD_PAGE_CHANGED, self.OnPageChanged)

    def OnPageChanging(self, event):
        if event.GetDirection():
            can, msg = event.GetPage().CanGoNext()
            if not can:
                wx.MessageBox(msg, _("Information"), wx.OK)
                event.Veto()

    def OnPageChanged(self, event):
        if event.GetPage() == self.optionsPage:
            pass  # XXXTODO

    def RunWizard(self):
        return super().RunWizard(self.optionsPage)

    def GetOptions(self):
        return self.mappingPage.GetOptions()
