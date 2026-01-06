# Third-Party Libraries Bundled with Task Coach

This directory contains third-party libraries that are bundled with Task Coach
for compatibility or because they require modifications for Task Coach.

Last Updated: 2025-12

---

Component: deltaTime.py
Name: delta_time (Natural Language Time Parser)
Author: Paul McGuire
Version: Upstream December 2024
License: MIT
Source: https://github.com/pyparsing/pyparsing/blob/master/examples/delta_time.py
Copied on: 2025-11
Changes for Task Coach: Added backward compatibility alias (nlTimeExpression = time_expression)
Note: Requires pyparsing >= 3.1.3

---

Component: ntlm/
Name: python-ntlm (NTLM Authentication)
Author: Ben Dyer, Dmitry A. Rozmanov, Matthijs Mullender
Version: No version number (2011)
License: LGPL v3 or later
Source: https://github.com/bendyer/python-ntlm
Copied on: 2012-07-31
Changes for Task Coach:
  - Made __init__.py non-empty for packaging
  - Removed HTTPNtlmAuthHandler.py (unused Python 2 code using urllib2)
Note: Only IMAPNtlmAuthHandler.py is used (for IMAP/NTLM authentication in thunderbird.py)

---

Component: smartdatetimectrl.py
Name: SmartDateTimeCtrl
Author: Jerome Laheurte <fraca7@free.fr>, Frank Niessink <frank@niessink.com>
Version: 1.0
Date: 2012-11-03
License: GPL v3
Source: https://bitbucket.org/fraca7/smartdatetimectrl
Copied on: 2012-11-03
Changes for Task Coach:
  - Timer cleanup fix for wx.Timer crash on window destroy
  - 2025-12: Fixed dark theme issue - set explicit text foreground color for month header in calendar popup (issue #43)

---

Component: timeline/
Name: Timeline Widget
Author: Unknown (appears to be Task Coach custom)
Version: Unknown
License: See timeline/license.txt
Source: Unknown
Note: wxPython timeline visualization widget

---

Component: wxScheduler/
Name: wxScheduler
Author: Unknown
Version: Unknown
License: Unknown
Source: Unknown (possibly derived from wxScheduler project)
Note: Calendar/schedule visualization widget for wxPython

---

## Removed Libraries (Python 3 Migration)

The following libraries were previously bundled but have been removed:

- **desktop/**: Replaced with direct OS calls (xdg-open, open, os.startfile) in tools/openfile.py.
  The module provided desktop.open() and desktop.get_desktop() but was redundant since modern
  systems have standardized file opening via xdg-open (Linux), open (macOS), or os.startfile (Windows).
  The KDE4-specific date formatting code (using PyKDE4/PyQt4) was also removed as dead code.
- **aui/**: Now using wx.lib.agw.aui from wxPython directly
- **customtreectrl.py**: Now using wx.lib.agw.customtreectrl from wxPython directly
- **hypertreelist.py**: Now using wx.lib.agw.hypertreelist from wxPython directly
  (with patch applied via apply-wxpython-patch.sh for Debian Bookworm)
- **squaremap/**: Replaced with squaremap package from PyPI
- **snarl.py**: Removed (Windows Snarl notifications - superseded by built-in notifier)
- **guid.py**: Removed (no longer used)

See docs/PYTHON3_MIGRATION_NOTES.md for details on these changes.
