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
Changes for Task Coach: Timer cleanup fix for wx.Timer crash on window destroy

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

Component: desktop/
Name: desktop (Cross-platform Desktop Integration)
Author: Paul Boddie
Version: 0.5.3 (August 2019)
License: LGPL v3 or later
Source: Based on https://pypi.org/project/desktop3/
Copied on: Unknown (pre-2016)
Changes for Task Coach:
  - 2025-12: Fixed Python 3.12+ SyntaxWarning by converting docstring to raw string
Note: Provides desktop.open() and desktop.get_desktop() for cross-platform URL/file opening.
      Used in taskcoachlib/tools/openfile.py and taskcoachlib/render.py.

---

## Removed Libraries (Python 3 Migration)

The following libraries were previously bundled but have been removed:

- **aui/**: Now using wx.lib.agw.aui from wxPython directly
- **customtreectrl.py**: Now using wx.lib.agw.customtreectrl from wxPython directly
- **hypertreelist.py**: Now using wx.lib.agw.hypertreelist from wxPython directly
  (with patch applied via apply-wxpython-patch.sh for Debian Bookworm)
- **squaremap/**: Replaced with squaremap package from PyPI
- **snarl.py**: Removed (Windows Snarl notifications - superseded by built-in notifier)
- **guid.py**: Removed (no longer used)

See docs/PYTHON3_MIGRATION_NOTES.md for details on these changes.
