# Flatpak icons

Nuvola icons copied from `taskcoachlib/gui/icons/nuvola`, installed into the
exported `hicolor` theme under the app-id namespace (sizes 16-128 + 256 + SVG):

- `io.github.taskcoach.TaskCoach` - app icon + idle tray (Nuvola `korganizer`)
- `io.github.taskcoach.TaskCoach.clock` - tray, tracking (Nuvola `clock`)
- `io.github.taskcoach.TaskCoach.timer` - tray, tracking (Nuvola `ktimer`)

256: rendered from SVG (`korganizer`, `clock`) or upscaled from 128 (`ktimer`,
no vector exists). SVGs ship for all but `.timer`.

Nuvola by David Vignoni (icon-king.com); SVGs from Wikimedia Commons. LGPL-2.1+.
