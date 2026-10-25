# Welcome Files

The demo task files Task Coach ships: `Welcome.tsk`, which the first
run copies to the user's documents folder and opens
(`Settings._setup_first_run_welcome_file()`), and `Welcome-dark.tsk`,
the same file for the dark theme, installed beside it for anyone to
open. Every package installs both (deb, rpm, Arch, AppImage, Flatpak,
Windows, macOS); the deb install test checks they are there.

## Colours

Item colours are the user's: each task, category and note gets its
own in its Appearance tab. Task Coach's own colours are the status
colours ([TASK_STATUS.md](TASK_STATUS.md)) and the calendar's
(Preferences > Theme). The Welcome files are the only item colours
Task Coach ships, so their rows must read well with the default
status colours.

No background serves both themes: the light theme draws dark status
text, the dark theme light text, and each coloured row of the light
file measures 1.0 to 1.2:1 in the dark theme. So `Welcome.tsk` is for
the light theme and `Welcome-dark.tsk` for the dark one, **ruled by
designer 2026-10-25**: "it's probably not possible to have bg colors
work for both, the user chooses bg color ... we can decide on only
light for demo", then "possibly have a welcome.tsk for dark mode. and
a script that changes the bg colors for dark mode welcome", and "build
and include both".

`tools/welcome_colours.py` writes both files' background colours from
one hue per coloured category (`PALETTE`): toward white for the light
file, toward black for the dark one, until a text colour keeps 90%
(`KEPT`) of the contrast it has on that theme's plain rows (the status
backgrounds in `config/defaults.py`: white, and #282828 in the dark
theme). For text darker than both backgrounds (lighter, in the dark
theme) the share kept does not depend on the text colour, so a change
of the status text colours needs no change here; a change of the
status backgrounds needs the script run again. The rows are then as
readable as plain rows, within 10%: the status colours' own contrast
sets the bound.

An item with its own text colour ("Appearance is adjustable") keeps
both colours in both files: the pair reads the same in either theme.

`WelcomeFilesTest` checks that both files are the script's output,
that each coloured row keeps 90% of the contrast of every default
status colour of its theme, and that the files differ in background
colours only.
