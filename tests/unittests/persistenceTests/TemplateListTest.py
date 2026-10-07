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

import os
import shutil
import tempfile
import test, xml
from taskcoachlib import persistence


class Fake(object):
    def __init__(self, *args, **kwargs):
        pass


class TemplateReaderThatThrowsTooNewException(Fake):
    def read(self, *args, **kwargs):  # pylint: disable=W0613
        raise persistence.xml.reader.XMLReaderTooNewException


class TemplateReaderThatThrowsIOError(Fake):
    def read(self, *args, **kwargs):  # pylint: disable=W0613
        raise IOError


class TemplateReaderThatThrowsParseError(Fake):
    def read(self, *args, **kwargs):  # pylint: disable=W0613
        raise xml.etree.ElementTree.ParseError


class FakeFileClass(Fake):
    def close(self):
        pass


class FileClassThatRaisesIOError(object):
    def __init__(self, *args, **kwargs):  # pylint: disable=W0613
        raise IOError


class TemplateListUnderTest(persistence.TemplateList):
    def _template_filenames(self):
        return ["dummy.tsktmpl"]


class TemplateListTestCase(test.TestCase):
    def test_path_without_templates(self):
        template_list = persistence.TemplateList(".")
        self.assertEqual([], template_list.tasks())

    def test_handle_too_new_exception(self):
        template_list = TemplateListUnderTest(
            ".", TemplateReaderThatThrowsTooNewException, FakeFileClass
        )
        self.assertEqual([], template_list.tasks())

    def test_handle_io_error_while_opening_file(self):
        template_list = TemplateListUnderTest(
            ".", open_file=FileClassThatRaisesIOError
        )
        self.assertEqual([], template_list.tasks())

    def test_handle_io_error_while_reading_template(self):
        template_list = TemplateListUnderTest(
            ".", TemplateReaderThatThrowsIOError, FakeFileClass
        )
        self.assertEqual([], template_list.tasks())

    def test_handle_parse_error_while_reading_template(self):
        template_list = TemplateListUnderTest(
            ".", TemplateReaderThatThrowsParseError, FakeFileClass
        )
        self.assertEqual([], template_list.tasks())


class TemplateSavedForOlderReleasesTest(test.TestCase):
    """A template saved by 2.0.3.0 before it wrote the forms older
    releases read, which skip it, is saved again in them when read
    (docs/PERSISTENCE_XML.md, Versions and Compatibility)."""

    def setUp(self):
        super().setUp()
        self.path = tempfile.mkdtemp()
        self.filename = os.path.join(self.path, "template.tsktmpl")

    def tearDown(self):
        shutil.rmtree(self.path)
        super().tearDown()

    def read_template_written_with(self, versions):
        with open(self.filename, "w", encoding="utf-8") as fd:
            fd.write(
                '<?xml version="1.0" encoding="utf-8"?>\n'
                '<?taskcoach release="2.0.3" %s?>\n'
                '<tasks><task id="t1" subject="Template"/></tasks>\n'
                % versions
            )
        template_list = persistence.TemplateList(self.path)
        with open(self.filename, encoding="utf-8") as fd:
            subjects = [each.subject() for each in template_list.tasks()]
            return subjects, fd.read()

    def test_a_template_older_releases_skip_is_saved_again(self):
        subjects, written = self.read_template_written_with('tskversion="38"')
        self.assertEqual(
            (["Template"], True),
            (subjects, 'tskversion="37" tskformat="38"' in written),
        )

    def test_a_template_older_releases_read_is_left_alone(self):
        _, written = self.read_template_written_with('tskversion="37"')
        self.assertIn('release="2.0.3" tskversion="37"?>', written)
