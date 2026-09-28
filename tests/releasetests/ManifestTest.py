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
import test


class ManifestTest(test.TestCase):
    def setUp(self):
        manifestFile = open(os.path.join(test.projectRoot, "MANIFEST"))
        manifestLines = manifestFile.readlines()
        manifestFile.close()
        self.manifest = [
            os.path.join(test.projectRoot, filename[:-1])
            for filename in manifestLines
        ]

    def missingPyFiles(self, *folders):
        missing = []
        for root, dirs, files in os.walk(
            os.path.join(test.projectRoot, *folders)
        ):
            pyfiles = [
                os.path.join(root, filename)
                for filename in files
                if filename.endswith(".py")
            ]
            for filename in pyfiles:
                if filename not in self.manifest:
                    missing.append(filename)
        return missing

    def test_all_source_py_files_are_in_manifest(self):
        self.assertEqual([], self.missingPyFiles("taskcoachlib"))

    def testAllUnittestPyFilesAreInManifest(self):
        self.assertEqual([], self.missingPyFiles("tests", "unittests"))

    def testAllReleasetestPyFilesAreInManifest(self):
        self.assertEqual([], self.missingPyFiles("tests", "releasetests"))

    def testAllIntegrationtestPyFilesAreInManifest(self):
        self.assertEqual([], self.missingPyFiles("tests", "integrationtests"))
