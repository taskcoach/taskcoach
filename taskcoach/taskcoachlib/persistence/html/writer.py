'''
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
'''

import os
from . import generator
from taskcoachlib import meta


css = '''/*
CSS file generated by %(name)s %(version)s for:
%%s.
You can edit this file, it will not be overwritten by %(name)s.
*/
'''%meta.data.metaDict + generator.css + '''
/* Other possibilities to tune the layout include:

   Change the styles for a header of a specific column, in this case the subject
   column. Note how this style overrides the default style in the HTML file:

   th.subject {
      text-align: center;
   }

   If the exported HTML file contains tasks it is possible to change the color
   of completed (or overdue, duesoon, late, inactive, active) tasks like this:

   .completed {
       color: red;
   }

*/
'''

class HTMLWriter(object):
    def __init__(self, fd, filename=None):
        self.__fd = fd
        self.__filename = filename
        self.__cssFilename = os.path.splitext(filename)[0] + '.css' if filename else ''

    def write(self, viewer, settings, selectionOnly=False, separateCSS=False, columns=None):
        cssFilename = os.path.basename(self.__cssFilename) if separateCSS else ''
        htmlText, count = generator.viewer2html(viewer, settings, cssFilename,
                                                selectionOnly, columns)
        self.__fd.write(htmlText)
        if separateCSS:
            self._writeCSS()
        return count

    def _writeCSS(self, open=open): # pylint: disable=W0622
        if not self.__cssFilename or os.path.exists(self.__cssFilename):
            return
        try:
            fd = open(self.__cssFilename, 'wb')
            fd.write(css%self.__filename)
            fd.close()
        except IOError:
            pass
