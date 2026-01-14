# Task Coach - Your friendly task manager

Task Coach is a free/libre/open task manager for keeping track of projects and todo lists.

It's over 20 years old, and development was stagnant in recent years. Here, the project is continued again and has been updated to Python3!

## Quick Start

Download the package for your system from the [latest release](https://github.com/taskcoach/taskcoach/releases):

| Platform | Package |
|----------|---------|
| Windows | `TaskCoach-2.0.1.17-windows-x64-setup.exe` |
| Windows (portable) | `TaskCoach-2.0.1.17-windows-x64-portable.zip` | 
| Debian 12 (Bookworm) | `taskcoach_2.0.1.17_debian-12-bookworm.deb` |
| Debian 13 (Trixie) | `taskcoach_2.0.1.17_debian-13-trixie.deb` |
| Debian Sid | `taskcoach_2.0.1.17_debian-sid.deb` |
| Ubuntu 22.04 (Jammy) | `taskcoach_2.0.1.17_ubuntu-22.04-jammy.deb` |
| Ubuntu 24.04 (Noble) | `taskcoach_2.0.1.17_ubuntu-24.04-noble.deb` |
| Linux Mint | Use Ubuntu `.deb` (Mint is Ubuntu-based) |
| Arch Linux / Manjaro | `taskcoach-2.0.1.17-arch.pkg.tar.zst` |
| Fedora 39/40 | `taskcoach-2.0.1.17-fedora40.noarch.rpm` |
| Any Linux (x86_64) | `TaskCoach-2.0.1.17-x86_64.AppImage` |

After installing, Task Coach should be in normal system launchers (Applications → Office → Task Coach). For CLI, the launch command is `taskcoach.py`.

**Example: Install on Debian Trixie** (similar for other Debian/Ubuntu systems, just different .deb file)

```bash
cd ~/Downloads
wget https://github.com/taskcoach/taskcoach/releases/latest/download/taskcoach_2.0.1.17_debian-13-trixie.deb
sudo apt install ./taskcoach_2.0.1.17_debian-13-trixie.deb
```

To uninstall:
```bash
sudo apt remove taskcoach
sudo apt autoremove  # optional: remove unused dependencies
```

**Example: Install on Arch Linux / Manjaro**

```bash
cd ~/Downloads
wget https://github.com/taskcoach/taskcoach/releases/latest/download/taskcoach-2.0.1.17-arch.pkg.tar.zst
sudo pacman -U taskcoach-2.0.1.17-arch.pkg.tar.zst
```

To uninstall:
```bash
sudo pacman -R taskcoach
sudo pacman -Qdtq | sudo pacman -Rs -  # optional: remove orphaned dependencies
```

**Example: Install on Fedora**

```bash
cd ~/Downloads
wget https://github.com/taskcoach/taskcoach/releases/latest/download/taskcoach-2.0.1.17-fedora40.noarch.rpm
sudo dnf install ./taskcoach-2.0.1.17-fedora40.noarch.rpm
```

To uninstall:
```bash
sudo dnf remove taskcoach
sudo dnf autoremove  # optional: remove unused dependencies
```

**Or run the AppImage (any Linux, no install needed)**

```bash
cd ~/Downloads
wget https://github.com/taskcoach/taskcoach/releases/latest/download/TaskCoach-2.0.1.17-x86_64.AppImage
chmod +x TaskCoach-2.0.1.17-x86_64.AppImage
```

To launch the AppImage, open the file or run:
```
./TaskCoach-2.0.1.17-x86_64.AppImage
```

To remove: simply delete the AppImage file.

## Running from Source

For development or if you prefer running from git:

```bash
git clone --depth 1 https://github.com/taskcoach/taskcoach.git
cd taskcoach
./setup.sh
./taskcoach-run.sh
```

See [docs/DEBIAN_BOOKWORM_SETUP.md](docs/DEBIAN_BOOKWORM_SETUP.md) for detailed setup options, troubleshooting, and platform-specific instructions.

### Testing after git installaion

Quick sanity check to verify the installation:

```bash
./test_taskcoach.sh
```

This tests Python version, dependencies, module imports, and wxPython patch status.

## License

Task Coach is free software licensed under the [GNU General Public License v3](https://www.gnu.org/licenses/gpl-3.0.html).

Copyright (C) 2004-2025 Task Coach developers

## Architecture Overview

Task Coach is a desktop application developed in Python using wxPython for its GUI. It follows the Model-View-Controller pattern with three main layers:

- **Domain layer**: Classes for tasks, categories, effort, notes and other domain objects
- **GUI layer**: Viewers, controllers, dialogs, menus and other GUI components
- **Persistence layer**: Loading/saving domain objects to XML files (.tsk) and exporting to various formats

## Source Code Overview

Key packages:

| Package | Description |
|---------|-------------|
| `domain` | Domain objects (tasks, categories, effort, notes) |
| `gui` | Viewers, dialogs, and UI components |
| `command` | Undo/redo-capable user actions (Command pattern) |
| `config` | User settings and TaskCoach.ini handling |
| `persistence` | .tsk file format (XML) and export functionality |
| `i18n` | Internationalization and translations |
| `widgets` | Adapted wxPython widgets |

## Documentation

- [DEBIAN_BOOKWORM_SETUP.md](docs/DEBIAN_BOOKWORM_SETUP.md) - Detailed installation and setup
- [PACKAGING.md](docs/PACKAGING.md) - Building .deb packages
- [CRITICAL_WXPYTHON_PATCH.md](docs/CRITICAL_WXPYTHON_PATCH.md) - wxPython compatibility patch details

## Support

- Report bugs or request features at GitHub Issues: https://github.com/taskcoach/taskcoach/issues
- Ask for help or have other open discussion at https://github.com/orgs/taskcoach/discussions
