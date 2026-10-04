"""
Task Coach - Your friendly task manager
Copyright (C) 2014 Task Coach developers <developers@taskcoach.org>

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

import re


class StrftimeFix(object):
    """Mixin class to fix strftime() so that it works with years < 1900"""

    def strftime(self, *args):
        if self.year >= 1900:
            return super().strftime(*args)
        result = self.replace(year=self.year + 1900).strftime(*args)
        return re.sub(str(self.year + 1900), str(self.year), result)


def round_fix(number, ndigits=None):
    # Fixed the "round(0.5) < 1" problem (float value storage problem)
    return round(number + 1e-12, ndigits)
