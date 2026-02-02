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

import locale
from taskcoachlib.widgets.numericctrl import NumericCtrl


def _get_configured_currency_decimal_places():
    """Get currency decimal places from preferences, falling back to locale.

    Fallback chain: configured pref -> locale frac_digits -> 2
    """
    try:
        from taskcoachlib.config import settings
        val = settings.Settings().get("view", "currency_decimal_places")
        if val:
            return int(val)
    except Exception:
        pass
    frac = locale.localeconv().get("frac_digits", 2)
    if frac == 127:  # CHAR_MAX = not available
        frac = 2
    return frac


class CurrencyCtrl(NumericCtrl):
    """Currency input control: NumericCtrl with decimal_places from locale.

    Gets decimal_places from locale.localeconv()["frac_digits"] (2 for
    USD/EUR, 0 for JPY, 3 for BHD). Falls back to 2 if frac_digits is
    127 (CHAR_MAX = not available) or if configured in preferences.
    """

    def __init__(self, parent, value=0.0, decimal_char=None, **kwargs):
        decimal_places = _get_configured_currency_decimal_places()
        super().__init__(
            parent,
            value=value,
            decimal_places=decimal_places,
            decimal_char=decimal_char,
            **kwargs,
        )
