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

import test, urllib.request, urllib.error, urllib.parse, re
from taskcoachlib import help  # pylint: disable=W0622


class MSDownloadTest(test.TestCase):
    def testExeInPage(self):
        req = urllib.request.Request(help._MSURL)
        req.add_header(
            "User-Agent",
            "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.36",
        )
        try:
            content = urllib.request.build_opener().open(req).read()
        except Exception as message:  # pylint: disable=W0703
            self.fail("Could not download page: %s" % str(message))

        self.assertTrue(re.search(r"vcredist[a-zA-Z0-9_-]*\.exe", content))
