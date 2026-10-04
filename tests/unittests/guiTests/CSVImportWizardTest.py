"""
Task Coach - Your friendly task manager
Copyright (C) 2004-2026 Task Coach developers <developers@taskcoach.org>

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
import tempfile
import test
import wx
from taskcoachlib import persistence
from taskcoachlib.domain import category, task
from taskcoachlib.gui.wizard import csvimport

POLISH = "Zapłacić rachunek za prąd"
FILE_TEXT = '"Subject","Due date"\r\n"%s","2026-10-11"\r\n' % POLISH


class EncodingChoiceTest(test.wxTestCase):
    """File > Import > CSV's Encoding choice (P174): chardet's guess,
    which the user can change while looking at the preview."""

    def options_page(self, data):
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            f.write(data)
        self.addCleanup(os.remove, f.name)
        wizard = csvimport.CSVImportWizard(
            f.name, self.frame, wx.ID_ANY, "Import CSV"
        )
        # Unless destroyed with the test's frame
        self.addCleanup(lambda: wizard and wizard.Destroy())
        return wizard.optionsPage

    def choose(self, page, codec):
        index = [each for each, label in page.encodings].index(codec)
        page.encoding_choice.SetSelection(index)
        page.on_encoding_chosen(None)

    def test_the_guess_is_chosen(self):
        page = self.options_page(FILE_TEXT.encode("utf-8"))
        self.assertEqual("UTF-8", page.encoding_choice.GetStringSelection())
        self.assertEqual(POLISH, page.grid.GetCellValue(0, 0))

    def test_choosing_an_encoding_reloads_the_preview(self):
        page = self.options_page(FILE_TEXT.encode("cp1250"))
        self.choose(page, "cp1250")
        self.assertEqual(POLISH, page.grid.GetCellValue(0, 0))

    def test_the_import_reads_the_chosen_encoding(self):
        page = self.options_page(FILE_TEXT.encode("cp1250"))
        self.choose(page, "cp1250")
        tasks = task.TaskList()
        persistence.CSVReader(tasks, category.CategoryList()).read(
            mappings=["Subject", "Due date"], **page.GetOptions()
        )
        self.assertEqual([POLISH], [each.subject() for each in tasks])

    def test_an_encoding_that_cannot_read_the_file(self):
        # Shown with replacement characters, no error
        page = self.options_page(FILE_TEXT.encode("cp1250"))
        self.choose(page, "utf-8")
        self.assertIn("�", page.grid.GetCellValue(0, 0))

    def test_ascii_is_offered_as_utf_8(self):
        choices, index = csvimport.encoding_choices("ascii")
        self.assertEqual("utf-8", choices[index][0])

    def test_a_guess_not_in_the_list_comes_first(self):
        choices, index = csvimport.encoding_choices("IBM866")
        self.assertEqual((0, ("cp866", "IBM866")), (index, choices[0]))
